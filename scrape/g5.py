import concurrent.futures
import http.client
import io
import json

import requests
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.files import File

from .base import BaseScrapingEngine, state_lookup_dict
from .keywordselector import KeywordDrivenCandidate


class ScrapingEngine(BaseScrapingEngine, KeywordDrivenCandidate):
    def __init__(self, source_url):
        KeywordDrivenCandidate.__init__(self)
        BaseScrapingEngine.__init__(self, source_url)

    def get_keyword(self):
        return "g5"

    def run(self, scraping_task):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        }
        self.main_url = scraping_task.source_url
        try:
            self.main_soup = self.get_soup(self.main_url)
            property_info = {}
            link_group = self.get_links()

            property_info = self.get_cominfo(link_group)
            property_info["propertyphoto_set"] = self.get_photos(
                link_group["gallery_link"], property_info["name"]
            )
            property_info = self.get_cominfo(link_group)
            amenity_group = self.get_amenity(link_group["amenities_link"])
            property_info.update(amenity_group)
            property_info["propertyunit_set"] = self.get_floorplan(
                link_group["floorplans_link"]
            )
            property_info["latitude"] = "{:8.5f}".format(
                float(property_info["latitude"])
            )
            property_info["longitude"] = "{:8.5f}".format(
                float(property_info["longitude"])
            )
            property_info["state"] = state_lookup_dict[property_info["state"]]
            scraping_task.scraped_data = property_info.copy()
            return scraping_task
        except Exception as err:
            err = "This url has some problems with run g5"
            raise ValidationError(err)

    def test_link(self, link_group):
        key_list = list(link_group.keys())
        exist_link_type_list = [
            "floorplans_link",
            "amenities_link",
            "gallery_link",
            "tour_link",
            "contact_link",
        ]
        for link_type in exist_link_type_list:
            if link_type not in key_list:
                link_group[link_type] = self.main_url
        return link_group

    def get_links(self):
        main_url_change = self.main_url.split(".com")
        url_container = self.main_soup
        href_link = url_container.find(attrs={"id": "drop-target-nav"})
        a_tag_container = href_link.find_all("a")
        link_group = {}
        exist_link_type_dict = {
            "amenit": "amenities_link",
            "property": "amenities_link",
            "floor": "floorplans_link",
            "feature": "floorplans_link",
            "gallery": "gallery_link",
            "photo": "gallery_link",
            "contact": "contact_link",
            "tour": "tour_link",
        }
        for idx in range(len(a_tag_container)):
            temp = a_tag_container[idx]["href"]
            if "https://" in str(temp):
                for key in list(exist_link_type_dict.keys()):
                    if key in str(temp.lower()):
                        temp = temp
                        link_group[exist_link_type_dict[key]] = temp
            else:
                for key in list(exist_link_type_dict.keys()):
                    if key in str(temp.lower()):
                        temp = main_url_change[0] + ".com" + temp
                        link_group[exist_link_type_dict[key]] = temp
                        break
        link_group = self.test_link(link_group)
        return link_group

    def get_photos(self, gallery_link, name):
        photo_set = {}
        propertyphoto_set = []
        photo_container = self.get_soup(gallery_link)
        photo_detector = ["photo-cards-mosaic", "full-gallery"]
        for detector_key in photo_detector:
            photo_info = photo_container.find(attrs={"class": detector_key})
            if photo_info is not None:
                break
        photo_urls = []
        if photo_info is None:
            raise ValidationError("The URL cannot be scraped (unable to get photos)")
        img_tag_container = photo_info.find_all("img")
        for item in img_tag_container:
            photo_urls.append(item["src"])
        index = 0
        download_imag_threading = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for item in photo_urls:
                index += 1
                url = item
                idx = url.rfind(".")
                extension_item = url[idx:].split("&")
                extension = extension_item[0]
                download_imag_threading.append(
                    executor.submit(self.download_img, url, name, index, extension)
                )
            for item in download_imag_threading:
                propertyphoto_set.append(item.result())
        photo_set["propertyphoto_set"] = propertyphoto_set
        return photo_set

    def get_cominfo(self, link_group):
        def phone_format(n):
            return format(int(n[:-1]), ",").replace(",", "-") + n[-1]

        pet_info_container = self.main_soup
        pet_info_text = str(pet_info_container)
        pet_allowed = pet_info_text.find("Pet Friendly")
        if pet_allowed > 0:
            pet_allowed = True
        else:
            pet_allowed = False
        phone_container = self.main_soup
        phone_a_href = phone_container.find_all("a")
        for href_item in phone_a_href:
            if "href" in str(href_item):
                phone_info = href_item["href"]
                if "tel:" in phone_info:
                    phone_info = (
                        phone_info.replace("tel:", "")
                        .replace("-", " ")
                        .replace("%20", " ")
                        .replace("(", "")
                        .replace(")", "")
                        .replace(" ", "")
                    )
                    break
        phone_info = phone_format(phone_info)
        cominfo_container = self.main_soup
        com_info = cominfo_container.find("script", {"type": "application/ld+json"})
        com_info_json = json.loads(com_info.contents[0])
        property = {
            "name": com_info_json["name"],
            "homepage_link": self.main_url,
            "amenities_link": link_group["amenities_link"],
            "floorplans_link": link_group["floorplans_link"],
            "gallery_link": link_group["gallery_link"],
            "contact_link": link_group["contact_link"],
            "tour_link": link_group["tour_link"],
            "address": com_info_json["address"]["streetAddress"],
            "city": com_info_json["address"]["addressLocality"],
            "state": com_info_json["address"]["addressRegion"],
            "country_code": "US",
            "postal_code": com_info_json["address"]["postalCode"],
            "phone": phone_info,
            "pet_friendly": pet_allowed,
            "latitude": float(com_info_json["geo"]["latitude"]),
            "longitude": float(com_info_json["geo"]["longitude"]),
        }
        return property

    def get_amenity(self, amenities_link):
        propertyamenity_set = []
        propertyunitamenity_set = []
        amenity_group = {}
        amenity_container = self.get_soup(amenities_link)
        amenity_groups = amenity_container.find_all(attrs={"class": "html-content"})
        index = -1
        for amenity_dector in amenity_groups:
            index += 1
            if amenity_dector.find("h2") is not None:
                community_keys = [
                    "community",
                ]
                for key in community_keys:
                    if key in amenity_dector.find("h2").text.lower():
                        community_amenity_info = amenity_dector.find_all("li")
                        if community_amenity_info is None:
                            community_amenity_info = amenity_dector.find_all("p")

                        propertyamenity_set = []
                        for community_text in community_amenity_info:
                            temp = {"name": community_text.text}
                            propertyamenity_set.append(temp)
                unit_keys = ["inside", "in-home", "aparment"]
                for key in unit_keys:
                    if key in amenity_dector.find("h2").text.lower():
                        unit_amenity_info = amenity_dector.find_all("li")
                        if unit_amenity_info is None:
                            unit_amenity_info = amenity_dector.find_all("p")
                        propertyunitamenity_set = []
                        for unit_text in unit_amenity_info:
                            temp = {"name": unit_text.text}
                            propertyunitamenity_set.append(temp)
            else:
                if amenity_dector.find_all("li") is not None:
                    community_amenity_info = amenity_dector.find_all("li")
        amenity_group["propertyamenity_set"] = propertyamenity_set
        amenity_group["propertyunitamenity_set"] = propertyunitamenity_set
        return amenity_group

    def get_floorplan(self, floorplans_link):
        try:
            propertyunit_set = []
            floorplan_container = self.get_soup(floorplans_link)
            floorplan_scripts_container = floorplan_container.find("script")
            floorplan_scripts_container_str = str(floorplan_scripts_container)
            for item in floorplan_scripts_container_str.splitlines():
                if "G5_STORE_ID" in item:
                    store_id = (
                        item.replace('"G5_STORE_ID": ', "")
                        .replace('"', "")
                        .replace(" ", "")
                        .replace(",", "")
                    )
                    conn = http.client.HTTPSConnection("inventory.g5marketingcloud.com")
                    payload = ""
                    headers = {}
                    store_id_text = (
                        "/api/v1/apartment_complexes/" + store_id + "/floorplans"
                    )
                    conn.request("GET", store_id_text, payload, headers)
                    res = conn.getresponse()
                    data = res.read()
                    data_text = str(data)
                    if len(data_text) < 5:
                        if "deer" in floorplans_link:
                            return propertyunit_set
                        return self.get_api_liveatsocial()
                    data_test = data_text.replace("b'", "").replace("'", "")
                    data_json = json.loads(data_test)
                    for item in data_json["floorplans"]:
                        temp = {
                            "bedrooms": item["beds"],
                            "bathrooms": item["baths"],
                            "floor_area": item["sqft"],
                            "starting_rate": item["starting_rate"],
                        }
                        propertyunit_set.append(temp)
            return propertyunit_set
        except Exception as err:
            err = "This url has some problems with get_floorplan"
            raise ValidationError(err)

    def get_api_liveatsocial(self):
        url = (
            "https://entrata.liveatsocial28.com/gainesville/social28/student?"
            + "&amp;is_responsive_snippet=1&amp;snippet_type=website"
            + "&amp;occupancy_type=10&amp;locale_code=en_US&amp;is_collapsed=1&amp;include_paragraph_content=1&amp"
        )
        url_container = BeautifulSoup(requests.get(url).content, "html.parser")
        url_container_analysing = url_container.find_all("span")
        floor_plan_total = ""
        propertyunit_set = []
        for item in url_container_analysing:
            floor_plan_total += " : " + item.text
        floor_plan_total.replace("\xa0\xa0/", "").replace("\n665\n+\n", "")
        floor_plan_tatic = floor_plan_total.split("Bed / Bath")
        for item in floor_plan_tatic:
            item = item.replace("\xa0\xa0/", "").replace("\n665\n+\n", "")
            if "Deposit" in item:
                starting_rate = 0
                if "Student" in item:
                    item_cut = item.split("Student")
                    item = item_cut[0]
                item_cut_again = item.split("Sq. Ft")
                item_cut_bdba = item_cut_again[0].split(":")
                for item_index in item_cut_bdba:
                    if item_index == "":
                        continue
                    else:
                        if "bd" in item_index and "ba" in item_index:
                            bd_ba = item_index.split(" ")
                            bedrooms = bd_ba[1].replace("bd", "")
                            bathrooms = bd_ba[2].replace("ba", "")
                item_cut_sqft = item_cut_again[1].split(":")
                sqft = 0
                item_index_result = ""
                for item_index in item_cut_sqft:
                    if item_index == "":
                        continue
                    else:
                        for x in range(len(item_index)):

                            if item_index[x] in "1234567890":
                                item_index_result += item_index[x]
                if item_index_result == "":
                    sqft = 0
                else:
                    sqft = int(item_index_result)
                temp = {
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "floor_area": sqft,
                    "starting_rate": starting_rate,
                }
                propertyunit_set.append(temp)
        return propertyunit_set

    def get_soup(self, _url):
        resp = requests.get(_url, headers=self.headers).content
        return BeautifulSoup(resp, "html.parser")

    def download_img(self, url, property_name, index, extension):
        res = requests.get(url, stream=True)
        if res.status_code == 200:
            return {
                "name": property_name + f"{index}",
                "photo": File(
                    io.BytesIO(res.content),
                    property_name + f"{index}." + extension,
                ),
                "category": "*-*",
            }
