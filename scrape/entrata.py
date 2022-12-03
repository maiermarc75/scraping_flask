import concurrent.futures
import io
import json
from xml.dom import ValidationErr

import requests
from bs4 import BeautifulSoup
from django.core.files import File

from .base import BaseScrapingEngine, state_lookup_dict
from .keywordselector import KeywordDrivenCandidate


class ScrapingEngine(BaseScrapingEngine, KeywordDrivenCandidate):
    def __init__(self, source_url):
        BaseScrapingEngine.__init__(self, source_url)
        KeywordDrivenCandidate.__init__(self)

    def get_keyword(self):
        return "entrata"

    def run(self, scraping_task):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        }
        self.main_url = scraping_task.source_url
        try:
            self.main_soup = self.get_soup(self.main_url)

            property_info = {}
            link_group = self.get_links()
            if self.main_url == "https://www.thepointatdoral.com":
                link_group[
                    "floorplans_link"
                ] = "https://www.thepointatdoral.com/doral/the-point-at-doral"
            amenity_group = self.get_amenity(link_group["amenities_link"])
            property_info = self.get_cominfo(link_group)
            property_info["propertyphoto_set"] = self.get_photos(
                link_group["gallery_link"], property_info["name"]
            )
            property_info.update(amenity_group)
            property_info["propertyunit_set"] = self.get_floorplan(
                link_group["floorplans_link"]
            )
            property_info["state"] = state_lookup_dict[property_info["state"]]
            property_info["latitude"] = "{:8.5f}".format(
                float(property_info["latitude"])
            )
            property_info["longitude"] = "{:8.5f}".format(
                float(property_info["longitude"])
            )
            scraping_task.scraped_data = property_info.copy()
            return scraping_task
        except Exception as err:
            err = "This url has some problems with run entrata"
            raise ValidationErr(err)

    def get_href_link(self):
        id_url_detector = ["menuElem", "header-nav", "head-wrap"]
        item_attr_keys = ["id", "class"]
        for item in id_url_detector:
            for item_attr in item_attr_keys:
                href_link = self.main_soup.find(attrs={item_attr: item})
                if href_link is not None:
                    return href_link

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
        href_link = self.get_href_link()
        a_tag_container = href_link.find_all("a")
        link_group = {}
        exist_link_type_dict = {
            "amenit": "amenities_link",
            # "property": "amenities_link",
            "feature": "floorplans_link",
            "floor": "floorplans_link",
            "student": "floorplans_link",
            "convention": "floorplans_link",
            "gallery": "gallery_link",
            "photo": "gallery_link",
            "contact": "contact_link",
            "application": "contact_link",
            "direction": "tour_link",
            "tour": "tour_link",
        }

        for idx in range(len(a_tag_container)):
            temp = a_tag_container[idx]["href"]
            for key in list(exist_link_type_dict.keys()):
                if key in str(temp.lower()):
                    if "http" not in temp:
                        temp = "https:" + temp
                    link_group[exist_link_type_dict[key]] = temp
        link_group = self.test_link(link_group)
        return link_group

    def get_photos(self, gallery_link, property_name):
        photo_info_container = self.get_soup(gallery_link)
        photo_infos = photo_info_container.find("div", {"id": "photos-group"})
        if photo_infos is None:
            photo_infos = photo_info_container.find("div", {"class": "photo-viewer"})
        photo_info = photo_infos.find_all("img")
        photo_urls = []
        for item in photo_info:
            photo_urls.append(item["data-big"])
        propertyphoto_set = []
        download_imag_threading = []
        index = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for item in photo_urls:
                index += 1
                url = item
                idx = url.rfind(".")
                extension_item = url[idx:].split("&")
                extension = extension_item[0]
                download_imag_threading.append(
                    executor.submit(
                        self.download_img, url, property_name, index, extension
                    )
                )
            for item in download_imag_threading:
                propertyphoto_set.append(item.result())

        return propertyphoto_set

    def get_cominfo(self, link_group):
        pet_info_text = str(self.main_soup)
        pet_allowed = pet_info_text.find("Pet Friendly")
        if pet_allowed > 0:
            pet_allowed = True
        else:
            pet_allowed = False

        com_info = self.main_soup.find_all("script", {"type": "application/ld+json"})
        com_info_city_state = self.main_soup.find_all("script")
        com_info_city = ""
        com_info_state = ""
        for item in com_info_city_state:
            temp = str(item)
            if "ppConfig =" in temp:
                for line in temp.splitlines():
                    if "ppConfig =" in line:
                        line_split = line.split(",")
                        for derive_item in line_split:
                            if "city_state_name" in derive_item:
                                derive_item_info = derive_item.split(":")
                                derive_item_info_detail = derive_item_info[1].split("-")
                                com_info_city = derive_item_info_detail[0]
                                com_info_state = derive_item_info_detail[1].replace(
                                    '"', ""
                                )

        com_info_json = json.loads(com_info[0].contents[0])
        property = {
            "name": com_info_json["name"],
            "homepage_link": self.main_url,
            "amenities_link": link_group["amenities_link"],
            "floorplans_link": link_group["floorplans_link"],
            "gallery_link": link_group["gallery_link"],
            "contact_link": link_group["contact_link"],
            "tour_link": link_group["tour_link"],
            "address": com_info_json["address"]["streetAddress"],
            "city": com_info_city,
            "state": com_info_state,
            "country_code": "US",
            "postal_code": com_info_json["address"]["postalCode"],
            "phone": com_info_json["telephone"],
            "pet_friendly": pet_allowed,
            "latitude": float(com_info_json["geo"]["latitude"]),
            "longitude": float(com_info_json["geo"]["longitude"]),
        }
        return property

    def get_amenity(self, amenities_link):
        propertyunitamenity_set = []
        propertyamenity_set = []
        amenity_container = self.get_soup(amenities_link)
        amenity_group = {}
        class_amenity_detector = "pp-content"
        amenity_info = amenity_container.find(attrs={"class": class_amenity_detector})
        amenity_community_detector = ["Community Amenities", "EXPERIENCE"]
        propertyamenity_set = []
        for amenity_detector_item in amenity_community_detector:
            community_amenity_temp = amenity_info.find(
                "h2", text=lambda text: text and amenity_detector_item in text
            )
            if community_amenity_temp is not None:
                community_amenity = community_amenity_temp.find_next(
                    "div", attrs={"class": "amenity-group"}
                )
                if community_amenity is None:
                    community_amenity_container = amenity_info.find(
                        attrs={"class": "thumb-group"}
                    )
                    community_amenity_span = community_amenity_container.find_all(
                        "span"
                    )
                    for item in community_amenity_span:
                        if item.text == "":
                            pass
                        else:
                            temp = {"name": item.text}
                            propertyamenity_set.append(temp)
                            print(item.text)

                else:
                    community_amenity_span = community_amenity.find_all("span")
                    for item in community_amenity_span:
                        temp = {"name": item.text}
                        propertyamenity_set.append(temp)
                    if (
                        community_amenity_temp.find_next(
                            "div", attrs={"class": "additional-amenities"}
                        )
                        is not None
                    ):
                        community_amenity = community_amenity_temp.find_next(
                            "div", attrs={"class": "additional-amenities"}
                        )
                        community_amenity_span = community_amenity.find_all("span")
                        for item in community_amenity_span:
                            temp = {"name": item.text}
                            propertyamenity_set.append(temp)
                        print(propertyamenity_set)
        amenity_unit_detector = [
            "Apartment Amenities",
            "APARTMENT",
            "Other Amenities",
        ]
        propertyunitamenity_set = []
        for amenity_detector_item in amenity_unit_detector:
            unit_amenity_temp = amenity_info.find(
                "h2", text=lambda text: text and amenity_detector_item in text
            )
            if unit_amenity_temp is not None:
                unit_amenity = unit_amenity_temp.find_next(
                    "div", attrs={"class": "amenity-group"}
                )
                if unit_amenity is None:
                    unit_amenity_container = amenity_info.find(
                        attrs={"class": "additional-amenities"}
                    )
                    unit_amenity_span = unit_amenity_container.find_all("span")
                    for item in unit_amenity_span:
                        if item.text == "":
                            pass
                        else:
                            temp = {"name": item.text}
                            propertyunitamenity_set.append(temp)
                            print(item.text)

                else:
                    unit_amenity_span = unit_amenity.find_all("span")
                    for item in unit_amenity_span:
                        temp = {"name": item.text}
                        propertyunitamenity_set.append(temp)
                    if (
                        unit_amenity_temp.find_next(
                            "div", attrs={"class": "additional-amenities"}
                        )
                        is not None
                    ):
                        unit_amenity = unit_amenity_temp.find_next(
                            "div", attrs={"class": "additional-amenities"}
                        )
                        unit_amenity_span = unit_amenity.find_all("span")
                        for item in unit_amenity_span:
                            temp = {"name": item.text}
                            propertyunitamenity_set.append(temp)
        amenity_group["propertyamenity_set"] = propertyamenity_set
        amenity_group["propertyunitamenity_set"] = propertyunitamenity_set

        return amenity_group

    def get_floorplan(self, floorplans_link):
        propertyunit_set = []
        floor_plan_container = self.get_soup(floorplans_link)
        floor_plan_info = floor_plan_container.find(
            "div", attrs={"id": "floorplan-overview-content"}
        )
        floor_plan_detail = floor_plan_info.find_all("span")
        floor_plan_total = ""
        for item in floor_plan_detail:
            floor_plan_total += " : " + item.text
        floor_plan_tatic = floor_plan_total.split("Beds / Baths")
        for item in floor_plan_tatic:
            for line in item.splitlines():
                Bed_info = 0
                Bath_info = 0
                Rent_info = 0
                sqft_info = 0
                if "*" not in line and "Rent" in line:
                    real_floorplan = line.split(" : ")
                    if (
                        real_floorplan[len(real_floorplan) - 1] != ""
                        and real_floorplan[len(real_floorplan) - 1] != "+"
                    ):
                        sqft_info = real_floorplan[len(real_floorplan) - 1]
                    elif (
                        real_floorplan[len(real_floorplan) - 2] != ""
                        and real_floorplan[len(real_floorplan) - 2] != "+"
                    ):
                        sqft_info = real_floorplan[len(real_floorplan) - 2]
                    elif (
                        real_floorplan[len(real_floorplan) - 3] != ""
                        and real_floorplan[len(real_floorplan) - 3] != "+"
                    ):
                        sqft_info = real_floorplan[len(real_floorplan) - 3]
                    else:
                        sqft_info = real_floorplan[len(real_floorplan) - 4]
                    sqft_info = int(
                        sqft_info.replace("+", "").replace(",", "").replace("-", "")
                    )
                    for real_floorplan_item in range(len(real_floorplan)):
                        if "/ " in str(real_floorplan[real_floorplan_item]):
                            real_info = real_floorplan[real_floorplan_item].split("/")
                            Bed_info = (
                                real_info[0].replace("bd", "").replace("\xa0", "")
                            )
                            Bath_info = real_info[1].replace("ba", "")
                            if "studio" in Bed_info.lower():
                                Bed_info = 0
                        if "$" in str(real_floorplan[real_floorplan_item]):
                            Rent_info = real_floorplan[real_floorplan_item].replace(
                                "from\xa0", ""
                            )
                        else:
                            Rent_info = 0
                    temp = {
                        "bedrooms": Bed_info,
                        "bathrooms": Bath_info,
                        "floor_area": sqft_info,
                        "starting_rent": Rent_info,
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
