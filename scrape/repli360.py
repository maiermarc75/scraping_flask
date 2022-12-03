import concurrent.futures
import io
import re
from xml.dom import ValidationErr

import requests
from bs4 import BeautifulSoup
from django.core.files import File
from geopy.geocoders import Nominatim

from .base import BaseScrapingEngine, state_lookup_dict
from .keywordselector import KeywordDrivenCandidate


class ScrapingEngine(BaseScrapingEngine, KeywordDrivenCandidate):
    def __init__(self, source_url):
        BaseScrapingEngine.__init__(self, source_url)
        KeywordDrivenCandidate.__init__(self)

    def get_keyword(self):
        return "repli360"

    def run(self, scraping_task):
        self.repli360_site_id = {
            "https://www.parcatwc.com": "910",
            "https://www.argylelake.com": "896",
            "https://www.emeraldcovesavannah.com": "194",
            "https://www.vantagestpete.com": "199",
            "https://rentnow.westvillagelofts.com": "27",
        }
        self.main_url = scraping_task.source_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        }
        try:
            self.main_soup = self.get_soup(self.main_url)
            if self.main_url == "https://rentnow.westvillagelofts.com":
                property_info = self.rentnow()
            else:
                nav_link_list = self.get_link()
                property_info = self.get_information()
                property_info.update(nav_link_list)
                property_info["propertyunit_set"] = self.get_floorplan()
                property_info["propertyphoto_set"] = self.get_photo(
                    property_info["gallery_link"]
                )
                property_info.update(self.get_amenity(property_info["amenities_link"]))
            scraping_task.scraped_data = property_info.copy()
            return scraping_task
        except Exception as err:
            err = "This url has some problems with run repli360"
            raise ValidationErr(err)

    def get_link(self):
        main_menubar_soup = self.main_soup.find(role="menubar")
        a_tag_list = main_menubar_soup.find_all("a")
        link_obj = {}
        for tag in a_tag_list:
            tag_string = str(tag)
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
        return link_obj

    def get_information(self):
        main_soup_str = str(self.main_soup)
        latitude = re.findall(r'latitude"\:\s"(.+)"', main_soup_str)[0]
        longitude = re.findall(r'longitude"\:\s"(.+)"', main_soup_str)[0]
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.reverse(latitude + "," + longitude).raw["address"]
        city = re.findall(r'addressLocality"\:\s"(.+)"', main_soup_str)[0]
        state = location["state"]
        country_code = location["country_code"].upper()
        postal_code = location["postcode"]
        address = f"{location['road']} {city}, {location['ISO3166-2-lvl4'].split('-')[1]} {postal_code}"
        pet_check = re.findall("pet friendly", str(self.main_soup), re.IGNORECASE)
        name = self.main_soup.title.string.strip()
        if not pet_check:
            pet_friendly = False
        else:
            pet_friendly = True
        phone = re.findall(r'telephone"\:\s"(.+)"', main_soup_str)[0]
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
        photo_tag_list = photo_soup.find_all("div", attrs={"class": "image-container"})
        photo_url_list = [x.a.img["data-src"] for x in photo_tag_list]
        download_imag_threading = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for idx, _url in enumerate(photo_url_list):
                download_imag_threading.append(executor.submit(self.download_img, _url))
            for item in download_imag_threading:
                propertyphoto_list.append(item.result())
        return propertyphoto_list

    def download_img(self, _url):
        res = requests.get(_url)
        image_name = _url.rsplit("/", 1)[-1]
        return {
            "name": f"{self.repli360_site_id[self.main_url]}{image_name}",
            "photo": File(
                io.BytesIO(res.content),
                f"{self.repli360_site_id[self.main_url]}{image_name}",
            ),
            "category": "*-*",
        }

    def get_amenity(self, amenity_link):
        amenity_soup = self.get_soup(amenity_link)
        amenity_soup_str = str(amenity_soup)

        if self.main_url == "https://www.vantagestpete.com":
            url = "https://app.repli360.com/admin/rrac_amenities_view"
            resp = requests.post(
                url=url, params={"site_id": "199", "featured": "undefined"}
            ).content
            resp_soup = BeautifulSoup(resp, "html.parser")
            community_tag_list = resp_soup("div", {"class": "side_click"})[0]("span")
            interior_tag_list = resp_soup("div", {"class": "side_click"})[1]("span")
        else:
            id_contain = re.findall(
                "community amenities</span(.*?)ul",
                amenity_soup_str,
                re.IGNORECASE | re.DOTALL,
            )[0]
            id = re.findall('id="(.+?)"', id_contain)
            community_tag_list = amenity_soup(id=id)[0]("li")

            id_contain = re.findall(
                "interior [fl](.*?)ul", amenity_soup_str, re.IGNORECASE | re.DOTALL
            )[0]
            id = re.findall('id="(.+?)"', id_contain)
            interior_tag_list = amenity_soup(id=id)[0]("li")

        community_amenity = [{"name": x.string} for x in community_tag_list]
        interior_features = [{"name": x.string} for x in interior_tag_list]
        return {
            "propertyamenity_set": community_amenity,
            "propertyunitamenity_set": interior_features,
        }

    def get_floorplan(self):
        url = "https://app.repli360.com/admin/rrac-template-five"
        resp = requests.post(
            url=url, params={"site_id": self.repli360_site_id[self.main_url]}
        ).content
        floorplan_soup = BeautifulSoup(resp, "html.parser")
        tr_tag_list2 = [x("tr") for x in floorplan_soup("tbody")[:-1]]
        floorplan_list = []
        for tr_tag1 in tr_tag_list2:
            for tr_tag in tr_tag1:
                bedrooms = self.convert_english_no(
                    re.findall(r"\w+", tr_tag("td")[1].string)[0]
                )
                bathrooms = re.findall("[0-9]+", tr_tag("td")[1].string)[1]
                floor_area = re.findall("[0-9]+", tr_tag("td")[2].string)[0]
                try:
                    starting_rent = re.findall(
                        "[0-9]+,?[0-9]+", tr_tag("strong")[0].string
                    )[0].replace(",", "")
                except:
                    starting_rent = 0
                floorplan_list.append(
                    {
                        "bedrooms": bedrooms,
                        "bathrooms": bathrooms,
                        "floor_area": floor_area,
                        "starting_rent": starting_rent,
                    }
                )
        return floorplan_list

    def get_soup(self, _url):
        resp = requests.get(_url, headers=self.headers).content
        return BeautifulSoup(resp, "html.parser")

    def convert_english_no(self, _str):
        switcher = {
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8",
            "nine": "9",
            "zero": "0",
            "0": "0",
            "studio": "1",
        }
        return switcher.get(_str.lower(), "0")

    def rentnow(self):
        name = self.main_soup.title.string.strip()
        address_link = self.main_soup("div", {"id": "1278778787"})[0]
        street, city = (x.string for x in address_link("p"))
        state = re.findall(r"[, ](\w+)", city)[0]
        postal_code = re.findall(r"[, ](\w+)", city)[1]
        address = f"{street} {city}"
        city = city.split(",")[0]
        pet_friendly = True
        pet_list = re.findall("Pet Friendly", str(self.main_soup), re.IGNORECASE)
        phone = self.main_soup("div", {"id": "1776110877"})[0].string
        if not pet_list:
            pet_friendly = False
        property_info = {
            "name": name,
            "homepage_link": self.main_url,
            "gallery_link": self.main_url,
            "amenities_link": self.main_url,
            "floorplans_link": self.main_url,
            "tour_link": self.main_url,
            "contact_link": self.main_url,
            "address": address,
            "latitude": None,
            "longtitude": None,
            "city": city,
            "country_code": "US",
            "state": state_lookup_dict[state],
            "postal_code": postal_code,
            "pet_friendly": pet_friendly,
            "phone": phone,
        }
        property_info["propertyunit_set"] = self.get_floorplan()
        property_info["propertyphoto_set"] = self.get_photo(self.main_url)
        property_info.update(self.get_amenity(self.main_url))
        return property_info
