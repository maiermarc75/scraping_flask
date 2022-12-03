import concurrent.futures
import io
import re

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
        return "goldoller"

    def run(self, scraping_task):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        }
        self.main_url = scraping_task.source_url
        try:
            property_info = {}
            self.main_soup = self.get_soup(self.main_url)
            property_info = self.get_infomation()
            link_group = self.get_link()
            property_info.update(link_group)
            amenities_info = self.get_amenity(link_group["amenities_link"])
            property_info.update(amenities_info)
            property_info["propertyphoto_set"] = self.get_photo(
                link_group["gallery_link"]
            )
            property_info["propertyunit_set"] = self.get_floorplan(
                link_group["floorplans_link"]
            )
            scraping_task.scraped_data = property_info.copy()
            return scraping_task
        except:
            print("this url has some proplems with engine")
        return property

    def get_link(self):
        nav_li_link = self.main_soup.find_all("nav")[0].ul.find_all("li")
        link_obj = {}
        for tag in nav_li_link:
            tag_string = str(tag).lower()
            link_temp = tag.a["href"]
            if not "http" in link_temp:
                link_temp = self.main_url + link_temp
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
        if not "amenities_link" in link_obj:
            link_obj["amenities_link"] = self.main_url
        return link_obj

    def get_amenity(self, amenity_link):
        propertyunitamenity_set = []
        if "#" in amenity_link or amenity_link == self.main_url:
            amenity_div = self.main_soup.find_all(attrs={"id": "amenities"})[0]
            propertyamenity_set = [
                {"name": x.h6.text}
                for x in amenity_div.find_all("div", attrs={"class": "item"})
            ]
            if not propertyamenity_set:
                amenity_tag_items = amenity_div.find_all(
                    "div", attrs={"class": "vc_custom_heading"}
                )
                propertyamenity_set = [{"name": x.text} for x in amenity_tag_items]
        else:
            amenity_soup = self.get_soup(amenity_link)
            amenity_soup_str = str(amenity_soup)
            try:
                ul_contain = re.findall(
                    "COMMUNITY FEATURES(.*?)</ul",
                    amenity_soup_str,
                    re.IGNORECASE | re.DOTALL,
                )[0]
                li_tag_list = BeautifulSoup(ul_contain).find_all("li")
                propertyamenity_set = [
                    {"name": x.string.replace("\xa0", "")} for x in li_tag_list
                ]
                ul_contain = re.findall(
                    "APARTMENT FEATURES(.*?)</ul",
                    amenity_soup_str,
                    re.IGNORECASE | re.DOTALL,
                )[0]
                li_tag_list = BeautifulSoup(ul_contain).find_all("li")
                propertyunitamenity_set = [
                    {"name": x.string.replace("\xa0", "")} for x in li_tag_list
                ]
            except:
                li_tag_list = amenity_soup.find_all(attrs={"class": "amenities"})[0]
                li_tag_list = li_tag_list.find_all("h6")
                propertyamenity_set = [
                    {"name": x.string.replace("\xa0", "")} for x in li_tag_list
                ]
        return {
            "propertyamenity_set": propertyamenity_set,
            "propertyunitamenity_set": propertyunitamenity_set,
        }

    def get_photo(self, gallery_link):
        common_payload = """
        action=vc_get_vc_grid_data&vc_action=vc_get_vc_grid_data
        &tag=vc_media_grid&data%5Bvisible_pages%5D=5&data%5Bpage_id%5D=19&data%5Bstyle%5D=all
        &data%5Baction%5D=vc_get_vc_grid_data&data%5Btag%5D=vc_media_grid&vc_post_id=19&
        """
        gallery_paylod = {
            "https://www.coventrygreenapts.com": "data%5Bshortcode_id%5D=1664985212817-33434cb38e168669b72b6bad4239112b-9&_vcnonce=4d74dc49df",
            "https://www.gobexleyhouse.com": "data%5Bshortcode_id%5D=1664285255374-c357b284-879f-1&_vcnonce=13aafd41d5",
            "https://www.goradiusattenmile.com": "data%5Bshortcode_id%5D=1664979111883-2c63f4cc-2f0e-8&_vcnonce=cf8ef0885d",
            "https://www.gorutherfordglen.com": "data%5Bshortcode_id%5D=1668200229919-8c73527d-58f5-9&_vcnonce=d7114862ad",
            "https://www.gosteeplechase.com": "data%5Bshortcode_id%5D=1668014934018-207b403d-aa28-1&_vcnonce=002e558cd7",
            "https://www.gosuttonplace.com": "data%5Bshortcode_id%5D=1664984353144-42f2ccfc556b462e7c4dc264a740d873-7&_vcnonce=2205408f52",
            "https://www.gothelaurel.com": "data%5Bshortcode_id%5D=1664224721807-6576b9ef-9bd9-0&_vcnonce=a13be35393",
            "https://www.gothewillows.com": "data%5Bshortcode_id%5D=1664224188670-5190ae2a-2c54-3&_vcnonce=8b3d4ade78",
            "https://www.thesheldonatsuffern.com": "",
        }
        propertyphoto_list = []
        gallery_soup = self.get_soup(gallery_link)
        gallery_div_tag = gallery_soup.find_all(attrs={"id": "gallery"})
        if not gallery_div_tag:
            gallery_div_tag = gallery_soup.find_all(attrs={"class": "housing-items"})
        # if not gallery_div_tag:
        #     gallery_div_tag = gallery_soup.find_all(attrs={"id": "housing-gallery-container"})
        if not gallery_div_tag:
            gallery_div_tag = gallery_soup.find_all(
                attrs={"class": "wpb_gallery_slides"}
            )
        if not gallery_div_tag:
            gallery_div_tag = gallery_soup.find_all(attrs={"class": "gallery-items"})
        if not gallery_div_tag:
            gallery_div_tag = requests.post(
                self.main_url
                + f"/wp-admin/admin-ajax.php?{common_payload}{gallery_paylod[self.main_url]}",
                headers=self.headers,
            )
            gallery_div_tag = [BeautifulSoup(gallery_div_tag.content)]
        img_url_list = [x["src"] for x in gallery_div_tag[0].find_all("img")]
        download_imag_threading = []
        subdomain = re.findall(
            r"^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/\n]+)",
            self.main_url,
            re.IGNORECASE | re.DOTALL,
        )[0]
        subdomain = subdomain.replace(".com", "")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for idx, _url in enumerate(img_url_list):
                download_imag_threading.append(
                    executor.submit(self.download_img, subdomain, _url, idx)
                )
            for item in download_imag_threading:
                propertyphoto_list.append(item.result())
        return propertyphoto_list

    def get_floorplan(self, floorplans_link):
        floorplan_soup = self.get_soup(floorplans_link)
        propertyunit_set = []
        try:
            floorplan_div_tag = floorplan_soup.find_all(
                "div", attrs={"id": "floor-plan-list"}
            )[0]
            floorplan_item_list = [
                x.find_all("span") for x in floorplan_div_tag.find_all("a")
            ]
            for item in floorplan_item_list:
                floor_area = self.get_number(item[0].string)[0]
                bed_bath_str = item[1].string
                bedrooms = self.convert_english_no(bed_bath_str.split(" ")[0])
                studio_flag = 0
                if "studio" in bed_bath_str.lower():
                    studio_flag = 1
                bathrooms = self.convert_english_no(
                    bed_bath_str.split(" ")[2 - studio_flag]
                )
                propertyunit_set.append(
                    {
                        "floor_area": floor_area,
                        "bedrooms": bedrooms,
                        "bathrooms": bathrooms,
                        "starting_rent": 0,
                    }
                )
        except:
            # only https://www.liveatone.com/
            floorplan_link_list = floorplan_soup.find_all(
                "a", attrs={"class": "filter"}
            )
            floorplan_link_list = [x["href"] for x in floorplan_link_list]
            for link in floorplan_link_list:
                temp_soup = self.get_soup(link)
                floorplan_list = [
                    x.span.text
                    for x in temp_soup.find_all(attrs={"class": "floor-plan-item"})
                ]
                for item in floorplan_list:
                    number_list = self.get_number(item)
                    if len(number_list) < 3:
                        bedrooms = "1"
                        bathrooms = "1"
                        floor_area = number_list[0]
                    else:
                        bedrooms = number_list[0]
                        bathrooms = number_list[1]
                        floor_area = number_list[2]
                    propertyunit_set.append(
                        {
                            "floor_area": floor_area,
                            "bedrooms": bedrooms,
                            "bathrooms": bathrooms,
                            "starting_rent": 0,
                        }
                    )

        return propertyunit_set

    def get_infomation(self):
        address = ""
        main_soup_str = str(self.main_soup)
        try:
            latitude = re.findall(r'latitude"\:\s"(.+)"', main_soup_str)[0]
            longitude = re.findall(r'longitude"\:\s"(.+)"', main_soup_str)[0]
            map_div_tag = self.main_soup.find_all("div", attrs={"class": "address"})
            address = map_div_tag[0].text
        except:
            map_link = re.findall('(https://goo.gl.+?)"', main_soup_str)
            if not map_link:
                map_div_link = self.main_soup.find_all(
                    "div", attrs={"class": "address"}
                )[0]
                map_link = map_div_link.a["href"]
            else:
                map_link = map_link[0]

            map_resp = requests.get(map_link, headers=self.headers)
            latitude, longitude = re.findall("/@(.+?),(.+?),", map_resp.url)[0]
            map_a_tag = self.main_soup.find_all("a", attrs={"href": map_link})
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.reverse(latitude + "," + longitude).raw["address"]
        country_code = location["country_code"].upper()
        try:
            street = self.remove_rn(map_a_tag[0].contents[0])
            city, state_code = map_a_tag[0].contents[2].strip().split(",")
            postal_code = self.get_number(state_code)[0]
            state = state_code.replace(postal_code, "").strip()
            address = f"{street} {city}, {state} {postal_code}"
        except:
            if address == "":
                state = location["state"]
                postal_code = location["postcode"]
                if "city" in location.keys():
                    city = location["city"]
                elif "township" in location.keys():
                    city = location["township"]
                else:
                    city = location["county"]
                address = f"{location['road']} {city}, {location['ISO3166-2-lvl4'].split('-')[1]} {postal_code}"
            else:
                address_split = address.split(",")
                city = address_split[1].strip()
                state, postal_code = address_split[2].strip().split(" ")
        if len(state) == 2:
            state = state_lookup_dict[state]
        pet_check = re.findall("\\bpet\\b", str(self.main_soup), re.IGNORECASE)
        name = self.main_soup.title.string.strip()
        if not pet_check:
            pet_friendly = False
        else:
            pet_friendly = True
        try:
            phone = re.findall(r'telephone"\:\"(.+)"', main_soup_str)[0]
        except:
            phone = self.remove_rn(
                re.findall(r'tel:(.+?)"', main_soup_str, re.IGNORECASE | re.DOTALL)[0]
            )
        property_info = {
            "name": name,
            "homepage_link": self.main_url,
            "address": address,
            "latitude": round(float(latitude), 5),
            "longitude": round(float(longitude), 5),
            "city": city,
            "country_code": country_code,
            "state": state,
            "postal_code": postal_code,
            "pet_friendly": pet_friendly,
            "phone": phone,
        }
        return property_info

    def get_soup(self, _url):
        resp = requests.get(_url, headers=self.headers).content
        return BeautifulSoup(resp, "html.parser")

    def remove_rn(self, _str):
        return _str.replace("\r", "").replace("\n", "")

    def download_img(self, subdomain, _url, idx):
        res = requests.get(_url)
        extension = re.findall(r"\.(\w+)", _url)[-1]
        image_name = f"{subdomain}{idx}.{extension}"
        return {
            "name": image_name,
            "photo": File(
                io.BytesIO(res.content),
                image_name,
            ),
            "category": "*-*",
        }

    def get_number(self, _str):
        return re.findall(r"[-+]?(?:\d*\.\d+|\d+)", _str)

    def convert_english_no(self, _str):
        try:
            float(_str)
            return _str
        except:
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
