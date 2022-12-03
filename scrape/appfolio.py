import concurrent.futures
import http.client
import io
import json
from urllib.request import Request, urlopen
from xml.dom import ValidationErr

import requests
from bs4 import BeautifulSoup
from django.core.files import File

from .base import BaseScrapingEngine, state_lookup_dict
from .keywordselector import KeywordDrivenCandidate

link_group = {}


class ScrapingEngine(BaseScrapingEngine, KeywordDrivenCandidate):
    def __init__(self, source_url):
        BaseScrapingEngine.__init__(self, source_url)
        KeywordDrivenCandidate.__init__(self)

    def get_keyword(self):
        return "appfolio"

    def run(self, scraping_task):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        }
        self.main_url = scraping_task.source_url
        try:
            self.main_soup = self.get_soup(self.main_url)
            property_info = {}
            photo_set = {}
            link_group = self.get_links()
            property_info = self.get_cominfo(link_group)
            amenity_group = self.get_amenity(link_group["amenities_link"])
            photo_set = self.get_photos(property_info["name"])
            property_info.update(amenity_group)
            property_info.update(photo_set)
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
            err = "This url has some problems with run appfolio"
            raise ValidationErr(err)

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
        try:
            link_group = {}
            url_container = self.main_soup
            try:
                href_container = url_container.find("nav")
                if href_container is None:
                    err = "This url has some problems with get_links"
                    raise ValidationErr(err)
            except Exception as err:
                err = "This url has some problems with get_links"
                raise ValidationErr(err)
            a_tag_container = href_container.find_all("a")
            exist_link_type_dict = {
                "amenit": "amenities_link",
                "property": "amenities_link",
                "availab": "floorplans_link",
                "gallery": "gallery_link",
                "photo": "gallery_link",
                "contact": "contact_link",
                "tour": "tour_link",
            }

            for idx in range(len(a_tag_container)):
                temp = a_tag_container[idx]["href"]
                for key in list(exist_link_type_dict.keys()):
                    if key in str(temp.lower()):
                        link_group[exist_link_type_dict[key]] = self.main_url + temp
            link_group = self.test_link(link_group)
            return link_group
        except Exception as err:
            err = "This url has some problems with get_links"
            raise ValidationErr(err)

    def get_photos(self, name):
        try:
            url_container = self.main_soup
            photo_container = url_container.find_all(attrs={"class": "image-container"})
            photo_change = []

            for item in photo_container:
                item_img = item.find("img")
                if 'class="image"' in str(item_img):
                    continue
                else:
                    photo_change.append(item_img["data-src"])
            propertyphoto_set = []
            photo_set = {}
            download_imag_threading = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for index, url in enumerate(photo_change):
                    idx = url.rfind(".")
                    extension = url[idx:].split("&")[0]
                    download_imag_threading.append(
                        executor.submit(self.download_img, url, index, extension, name)
                    )
                for idx, item in enumerate(download_imag_threading):
                    if idx == 0:
                        photo_set["highlight_photo"] = item.result()
                    else:
                        propertyphoto_set.append(item.result())

            photo_set["propertyphoto_set"] = propertyphoto_set
            return photo_set
        except Exception as err:
            err = "This url has some problems with get_photos"
            raise ValidationErr(err)

    def get_cominfo(self, link_group):
        main_info = {}
        url_container = self.main_soup
        pet_info_text = url_container.text
        pet_allowed = pet_info_text.find("Pet Friendly")
        if pet_allowed > 0:
            pet_allowed = True
        else:
            pet_allowed = False
        url_decter = url_container.find_all("script", {"type": "application/ld+json"})
        if len(url_decter) == 0:
            url_foot_container = url_container.find(
                attrs={"class": "dmFooterContainer"}
            )
            url_address_container = url_foot_container.find_all(
                attrs={"class": "dmNewParagraph"}
            )
            for item in url_address_container:
                item_text = str(item.text)
                if item_text[0] in "0123456789":
                    item_address = item.find(attrs={"class": "font-size-NaN"})
                    if item_address is None:
                        item_address = item.find_all("span")
                        streetAddress = item_address[0].text
                        address_complex = item_address[1].text.split(" ")
                        addressCity = address_complex[0].replace(", ", "")
                        addressState = address_complex[1]
                        addressPostal = address_complex[2]
                        main_info["address"] = streetAddress
                        main_info["city"] = addressCity
                        main_info["state"] = addressState
                        main_info["postal_code"] = addressPostal
                    else:
                        item_address = item.find_all("div")
                        streetAddress = item_address[1].text

                        address_complex = item_address[2].text.split(" ")
                        addressCity = address_complex[0].replace(", ", "")
                        addressState = address_complex[1]
                        addressPostal = address_complex[2]
                        main_info["address"] = streetAddress
                        main_info["city"] = addressCity
                        main_info["state"] = addressState
                        main_info["postal_code"] = addressPostal
                if "phone" in item_text.lower():
                    telephone_num = item.text.replace("phone: ", "")
                    main_info["telephone"] = telephone_num
                if item_text[0] == "(":
                    telephone_num = item.text
                    main_info["telephone"] = telephone_num
            main_info = {
                "homepage_link": self.main_url,
                "amenities_link": link_group["amenities_link"],
                "floorplans_link": link_group["floorplans_link"],
                "gallery_link": link_group["gallery_link"],
                "contact_link": link_group["contact_link"],
                "tour_link": link_group["tour_link"],
                "country_code": "US",
                "pet_friendly": pet_allowed,
                "phone": telephone_num,
                "address": streetAddress,
                "city": addressCity,
                "state": addressState,
                "postal_code": addressPostal,
                "latitude": float(0),
                "longitude": float(0),
            }
            main_info["name"] = url_address_container[
                len(url_address_container) - 1
            ].text
            return main_info
        else:
            com_info_json = json.loads(url_decter[1].contents[0])
            main_info = {
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
                "phone": com_info_json["telephone"],
                "pet_friendly": pet_allowed,
                "latitude": float(com_info_json["geo"]["latitude"]),
                "longitude": float(com_info_json["geo"]["longitude"]),
            }

        return main_info

    def get_amenity(self, amenities_link):
        try:
            req = Request(
                url=amenities_link,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    + " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"
                },
            )
            webpage = urlopen(req).read()
            url_container = BeautifulSoup(webpage, "html.parser")
            amenity_group = {}

            temp = []
            propertyamenity_set = []
            propertyunitamenity_set = []
            amenity_group_container = url_container.find(
                attrs={"class": "u_PROPERTYDETAILS"}
            )
            if amenity_group_container is None:
                amenity_group_container = url_container.find(
                    attrs={"class": "u_PropertyDetails"}
                )
                if amenity_group_container is None:
                    amenity_group_container = url_container.find(
                        attrs={"class": "u_Amenities"}
                    )
                    h3_container = amenity_group_container.find("h3")
                    for h3_text in h3_container:
                        temp.append(h3_text.text)
                else:
                    li_container = amenity_group_container.find_all("li")
                    for item in li_container:
                        temp.append(item.text)
            else:
                li_container = amenity_group_container.find_all("li")
                for item in li_container:
                    temp.append(item.text)
            for item_index in temp:
                if "$" in item_index:
                    break
                temp_item = {"name": item_index}
                propertyamenity_set.append(temp_item)

            amenity_group["propertyunitamenity_set"] = propertyunitamenity_set
            amenity_group["propertyamenity_set"] = propertyamenity_set
            return amenity_group
        except Exception as err:
            err = "This url has some problems with get_amenity"
            raise ValidationErr(err)

    def get_floorplan(self, floorplans_link):
        try:
            conn = http.client.HTTPSConnection("www.reserveatpalmerranch.com")
            payload = ""
            headers = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                + "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
            }
            conn.request(
                "GET",
                "/_dm/s/rt/actions/sites/10458ae9/collections/appfolio-listings/ENGLISH_UK",
                payload,
                headers,
            )

            res = conn.getresponse()
            data = res.read()
            # print(data.decode("utf-8"))
            ne_data = data.decode("utf-8")
            test_data = json.loads(ne_data)
            test_json = json.loads(test_data["value"])
            test_data = list(map(lambda data: data["data"], test_json))
            market_rent = 0
            bathrooms = 0
            bedrooms = 0
            square_feet = 0
            propertyunit_set = []
            for item in test_data:
                market_rent = item["market_rent"]
                bathrooms = item["bathrooms"]
                bedrooms = item["bedrooms"]
                square_feet = item["square_feet"]
                print(item["market_rent"])
                print(item["bathrooms"])
                print(item["bedrooms"])
                print(item["square_feet"])
                temp = {
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "starting_rent": market_rent,
                    "floor_area": square_feet,
                }
                propertyunit_set.append(temp)

            return propertyunit_set
        except Exception as err:
            err = "This url has some problems with get_floorplan"
            raise ValidationErr(err)

    def get_soup(self, _url):
        resp = requests.get(_url, headers=self.headers).content
        return BeautifulSoup(resp, "html.parser")

    def download_img(self, url, index, extension, name):
        res = requests.get(url, stream=True)
        if res.status_code == 200:
            if index == 0:
                return File(io.BytesIO(res.content), name + "." + extension)
            return {
                "name": name + f"{index}",
                "photo": File(
                    io.BytesIO(res.content),
                    name + f"{index}." + extension,
                ),
                "category": "*-*",
            }
