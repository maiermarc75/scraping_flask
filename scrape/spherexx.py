import concurrent.futures
import io
import re
from xml.dom import ValidationErr

import requests
from bs4 import BeautifulSoup
from django.core.files import File
from geopy.geocoders import Nominatim

from .base import BaseScrapingEngine
from .keywordselector import KeywordDrivenCandidate


class ScrapingEngine(BaseScrapingEngine, KeywordDrivenCandidate):
    def __init__(self, source_url):
        BaseScrapingEngine.__init__(self, source_url)
        KeywordDrivenCandidate.__init__(self)

    def get_keyword(self):
        return "spherexx"

    def run(self, scraping_task):
        self.main_url = scraping_task.source_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        }
        try:
            self.main_soup = self.get_soup(self.main_url)
            nav_link_list = self.get_link()
            property_info = self.get_information()
            property_info.update(nav_link_list)
            property_info["propertyunit_set"] = self.get_floorplan(
                property_info["floorplans_link"]
            )
            property_info["propertyphoto_set"] = self.get_photo(
                property_info["gallery_link"]
            )
            property_info.update(self.get_amenity(property_info["amenities_link"]))
            scraping_task.scraped_data = property_info.copy()
            return scraping_task
        except Exception as err:
            err = "This url has some problems with run spherexx"
            raise ValidationErr(err)

    def get_link(self):
        main_menubar_soup = self.main_soup.find_all(
            "li", attrs={"class": "header__sidenav-item"}
        )
        if not main_menubar_soup:
            main_menubar_soup = self.main_soup.find_all(
                "div", attrs={"id": "section-nav-menu-Leasing"}
            )[0]
            a_tag_list = main_menubar_soup.find_all("a")
        else:
            a_tag_list = [x.a for x in main_menubar_soup]
        link_obj = {}
        for tag in a_tag_list:
            tag_string = str(tag).lower()
            link_temp = self.main_url + tag["href"]
            if "floor" in tag_string:
                link_obj["floorplans_link"] = link_temp
            elif "amenit" in tag_string:
                link_obj["amenities_link"] = link_temp
            elif "gallery" in tag_string:
                link_obj["gallery_link"] = link_temp
            elif "contact" in tag_string:
                link_obj["contact_link"] = link_temp
            elif "tour" in tag_string:
                link_obj["tour_link"] = link_temp
        if not "tour_link" in link_obj:
            link_obj["tour_link"] = self.main_url
        return link_obj

    def get_information(self):
        main_soup_str = str(self.main_soup)
        try:
            latitude = re.findall(r'latitude"\:\"(.+)"', main_soup_str)[0]
            longitude = re.findall(r'longitude"\:\"(.+)"', main_soup_str)[0]
        except:
            la_long_titude = re.findall(r"center=(.+?)&", main_soup_str)[0].split(",")
            latitude = la_long_titude[0]
            longitude = la_long_titude[1]
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.reverse(latitude + "," + longitude).raw["address"]
        state = location["state"]
        country_code = location["country_code"].upper()
        postal_code = location["postcode"]
        if "city" in location.keys():
            city = location["city"]
        elif "township" in location.keys():
            city = location["township"]
        else:
            city = location["county"]
        address = f"{location['road']} {city}, {location['ISO3166-2-lvl4'].split('-')[1]} {postal_code}"
        pet_check = re.findall("pet friendly", str(self.main_soup), re.IGNORECASE)
        name = self.main_soup.title.string.strip()
        if not pet_check:
            pet_friendly = False
        else:
            pet_friendly = True
        try:
            phone = re.findall(r'telephone"\:\"(.+)"', main_soup_str)[0]
        except:
            phone = re.findall(r'tel\:(.+?)"', main_soup_str)[0]
        property_info = {
            "name": name,
            "homepage_link": self.main_url,
            "address": address,
            "latitude": round(float(latitude), 5),
            "longtitude": round(float(longitude), 5),
            "city": city,
            "country_code": country_code,
            "state": state,
            "postal_code": postal_code,
            "pet_friendly": pet_friendly,
            "phone": phone,
        }
        return property_info

    def get_photo(self, gallery_link):
        propertyphoto_list = []
        photo_soup = self.get_soup(gallery_link)
        photo_tag_list = photo_soup.find_all("img", attrs={"class": "image__img"})
        if not photo_tag_list:
            photo_tag_list = photo_soup.find_all("img", attrs={"class": "pBackground"})
            photo_url_list = [x["data-src"] for x in photo_tag_list[:-1]]
        else:
            photo_url_list = [x["src"] for x in photo_tag_list[:-1]]
        subdomain = re.findall(
            r"^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/\n]+)",
            self.main_url,
            re.IGNORECASE | re.DOTALL,
        )[0]
        subdomain = subdomain.replace(".com", "")
        download_imag_threading = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for idx, _url in enumerate(photo_url_list):
                download_imag_threading.append(
                    executor.submit(self.download_img, subdomain, _url, idx)
                )
            for item in download_imag_threading:
                propertyphoto_list.append(item.result())
        return propertyphoto_list

    def download_img(self, subdomain, _url, idx):
        res = requests.get(_url)
        extension = re.findall(r"\.(\w+)&", _url)[0]
        image_name = f"{subdomain}{idx}.{extension}"
        return {
            "name": image_name,
            "photo": File(
                io.BytesIO(res.content),
                image_name,
            ),
            "category": "*-*",
        }

    def get_amenity(self, amenity_link):
        amenity_soup = self.get_soup(amenity_link)
        div_tag_list = amenity_soup.find_all("div", attrs={"class": "amenities__items"})
        reverse_num = 0
        if not div_tag_list:
            div_tag_list = amenity_soup.find_all(
                "div", attrs={"class": "textAmenities all"}
            )[0].find_all("div", recursive=False)
            reverse_num = 1
        interior_tag_list = div_tag_list[0 - reverse_num].ul.find_all("li")
        community_tag_list = div_tag_list[1 - reverse_num].ul.find_all("li")
        community_amenity = [{"name": x.string} for x in community_tag_list]
        interior_features = [{"name": x.string} for x in interior_tag_list]
        return {
            "propertyamenity_set": community_amenity,
            "propertyunitamenity_set": interior_features,
        }

    def get_floorplan(self, _url):
        floorplan_soup = self.get_soup(_url)
        floorplan_list = []
        tag_list = floorplan_soup.find_all("div", attrs={"class": "floorplans__info"})
        if not tag_list:
            tag_list = floorplan_soup.find_all(
                "div", attrs={"class": "fpcontainerShadow"}
            )
            tag_list = [x.p for x in tag_list]
            for item in tag_list:
                bed_bath_sf = re.findall("[0-9]+", str(item))
                bedrooms = bed_bath_sf[0]
                bathrooms = bed_bath_sf[0]
                floor_area = bed_bath_sf[0]
                floorplan_list.append(
                    {
                        "bedrooms": bedrooms,
                        "bathrooms": bathrooms,
                        "floor_area": floor_area,
                        "starting_rent": 0,
                    }
                )
        else:
            for item in tag_list:
                temp_tag = item.find_all("span")
                bedrooms = re.findall("[0-9]+", temp_tag[0].string)
                if bedrooms:
                    bedrooms = bedrooms[0]
                else:
                    bedrooms = 1
                bathrooms = re.findall("[0-9]+", temp_tag[1].string)[0]
                floor_area = re.findall("[0-9]+", temp_tag[2].string)[0]
                floorplan_list.append(
                    {
                        "bedrooms": bedrooms,
                        "bathrooms": bathrooms,
                        "floor_area": floor_area,
                        "starting_rent": 0,
                    }
                )
        return floorplan_list

    def get_soup(self, _url):
        resp = requests.get(_url, headers=self.headers).content
        return BeautifulSoup(resp, "html.parser")
