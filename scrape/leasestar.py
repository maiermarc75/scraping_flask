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
        return "leasestar"

    def run(self, scraping_task):
        try:
            self.headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
            }
            self.main_url = scraping_task.source_url
            self.main_soup = self.get_soup(self.main_url)
            # if "thedomainoakland" in str(main_url):
            #     property = self.get_special_property(main_url)

            # else:
            property_info = {}
            link_group = self.get_links()
            property_info = self.get_cominfo(link_group)
            photo_set = self.get_photos(
                link_group["gallery_link"], name=property_info["name"]
            )
            property_info["propertyphoto_set"] = photo_set["propertyphoto_set"]
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
            # err = "This url has some problems with run leasestar"
            raise ValidationErr(err)

    def get_href_link(self):
        id_url_detector = ["menuElem", "header-nav", "head-wrap"]
        item_attr_keys = ["id", "class"]
        url_container = self.main_soup
        for item in id_url_detector:
            for item_attr in item_attr_keys:
                href_link = url_container.find(attrs={item_attr: item})
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

    def get_cominfo(self, link_group):
        pet_info_container = self.main_soup
        pet_info_text = str(pet_info_container)
        pet_allowed = pet_info_text.find("Pet Friendly")
        if pet_allowed > 0:
            pet_allowed = True
        else:
            pet_allowed = False

        com_info = self.main_soup.find_all("script", {"type": "application/ld+json"})

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
            "city": com_info_json["address"]["addressLocality"],
            "state": com_info_json["address"]["addressRegion"],
            "country_code": "US",
            "postal_code": com_info_json["address"]["postalCode"],
            "phone": com_info_json["telephone"],
            "pet_friendly": pet_allowed,
            "latitude": float(com_info_json["geo"]["latitude"]),
            "longitude": float(com_info_json["geo"]["longitude"]),
        }
        return property

    def get_photos(self, gallery_link, name):
        photo_set = {}
        photo_info_container = self.get_soup(gallery_link)
        photo_info = photo_info_container.findAll("div", {"class": "img_wrapper"})
        photo_urls = []
        for item in photo_info:
            photo_urls.append(item.meta["content"])
        propertyphoto_set = []
        index = 0
        download_imag_threading = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for item in photo_urls:
                if item == "":
                    continue
                index += 1
                url = "Https:" + item
                idx = url.rfind(".")
                extension_item = url[idx:].split("?")
                extension = extension_item[0]

                download_imag_threading.append(
                    executor.submit(self.download_img, url, name, index, extension)
                )
            for item in download_imag_threading:
                propertyphoto_set.append(item.result())
        photo_set["propertyphoto_set"] = propertyphoto_set

        return photo_set

    def get_amenity(self, amenities_link):
        """get amenity
        amenity container = amenity_container
        amenity group container = amenity_info
        property amenity info = communityAmenities
        unit amenity info = PropertyAmenities
        """
        amenity_info = self.get_soup(amenities_link)
        amenities_keys = ["CommunityAmenities", "client-panel-0"]
        propertyamenity_set = []
        for amenities_keys_item in amenities_keys:
            communityAmenities = amenity_info.find(attrs={"id": amenities_keys_item})
            if communityAmenities is not None:
                communityAmenities_info_li = communityAmenities.find_all("li")
                for item in communityAmenities_info_li:
                    temp = {"name": item.text}
                    propertyamenity_set.append(temp)
        amenities_apartment_keys = ["ApartmentAmenities", "client-panel-1"]
        propertyunitamenity_set = []
        for amenities_keys_item in amenities_apartment_keys:
            PropertyAmenities = amenity_info.find(attrs={"id": amenities_keys_item})
            if PropertyAmenities is not None:
                PropertyAmenities_info_li = PropertyAmenities.find_all("li")
                for item in PropertyAmenities_info_li:
                    temp = {"name": item.text}
                    propertyunitamenity_set.append(temp)
        amenity_group = {}
        amenity_group["propertyamenity_set"] = propertyamenity_set
        amenity_group["propertyunitamenity_set"] = propertyunitamenity_set
        return amenity_group

    def get_floorplan(self, floorplans_link):
        propertyunit_set = []
        floorplan_container = self.get_soup(floorplans_link)
        floorplan_sub_container = floorplan_container.find_all("script")
        line_list = []
        for item in floorplan_sub_container:
            item_result = str(item)
            if "var pageData" in item_result:
                keys = ["sqft", "beds", "baths", "lowPrice"]
                k = 0
                for line in item_result.splitlines():
                    k += 1
                    if line.split(":")[0].strip() in keys:

                        line_detail = line.split(":")
                        line_detail_A = line_detail[0].strip()
                        line_detail_B = line_detail[1].strip()
                        line_list.append(line_detail_A + ":" + line_detail_B)
        line_list = line_list[2:]
        beds = 0
        sqft = 0
        bath = 0
        price = 0
        index = 0
        for item in line_list:
            line_info = item.split(":")
            line_info_A = line_info[0]
            line_info_B = line_info[1]
            if "sqft" in line_info_A:
                line_info_B = line_info_B.replace('"', "")
                sqft = float(line_info_B.replace(",", ""))
            elif "beds" in line_info_A:
                line_info_B = line_info_B.replace("'", "")
                beds = float(line_info_B.replace(",", ""))
            elif "bath" in line_info_A:
                line_info_B = line_info_B.replace("'", "")
                bath = float(line_info_B.replace(",", ""))
            elif "Price" in line_info_A:
                price = float(line_info_B.replace(",", ""))
            index += 1
            if index % 4 == 0:
                temp = {
                    "bedrooms": beds,
                    "bathrooms": bath,
                    "floor_area": sqft,
                    "starting_rent": price,
                }
                propertyunit_set.append(temp)
        return propertyunit_set

    def get_special_property(self):
        id_url_detector = "header"
        href_link = self.main_soup.find(attrs={"id": id_url_detector})
        a_tag_container = href_link.find_all("a")
        url_group = []
        for x in range(len(a_tag_container)):
            temps = a_tag_container[x]["href"].split(".")
            temp = temps[0].replace("#", "/")
            if "amenit" in temp.lower():
                url_group.append(self.main_url + temp)
                amenities_link = self.main_url + temp
            elif "floor" in temp.lower():
                url_group.append(self.main_url + temp)
                floorplans_link = self.main_url + temp
            elif "feature" in temp.lower():
                url_group.append(self.main_url + temp)
                floorplans_link = self.main_url + temp
            elif "gallery" in temp.lower():
                url_group.append(self.main_url + temp)
                gallery_link = self.main_url + temp
            elif "photo" in temp.lower():
                url_group.append(self.main_url + temp)
                gallery_link = self.main_url + temp
            elif "contact" in temp.lower():
                url_group.append(self.main_url + temp)
                contact_link = self.main_url + temp
            elif "tour" in temp.lower():
                url_group.append(self.main_url + temp)
                tour_link = self.main_url + temp
            elif "neigh" in temp.lower():
                url_group.append(self.main_url + temp)
                tour_link = self.main_url + temp
            elif "map" in temp.lower():
                url_group.append(self.main_url + temp)
        pet_info_text = str(self.main_soup)
        pet_allowed = pet_info_text.find("Pet Friendly")
        if pet_allowed > 0:
            pet_allowed = True
        else:
            pet_allowed = False
        com_info = self.main_soup.find_all("script")
        com_info_main = ""
        property = {
            "name": "",
            "postal_code": "",
        }
        for item in com_info:
            com_info_text = str(item)
            if "GMapsModule" in com_info_text:
                com_info_main = com_info_text
        for line in com_info_main.splitlines():
            if "latitude" in line:
                G_info = line.split('"id"')
                for item in G_info:
                    if "Domain Oakland" in item:
                        com_info_text_main = item.split(",")
                        for x in com_info_text_main:

                            x_detail = x.split(":")
                            if "name" in x_detail[0]:
                                temp = x_detail[1].replace('"', "")
                                property["name"] = temp
                            elif "zip" in x_detail[0]:
                                temp = x_detail[1].replace('"', "")
                                property["postal_code"] = temp
                            elif "city" in x_detail[0]:
                                temp = x_detail[1].replace('"', "")
                                property["city"] = temp
                            elif "state" in x_detail[0]:
                                property["state"] = x_detail[1].replace('"', "")
                            elif "latitude" in x_detail[0]:
                                property["latitude"] = float(
                                    x_detail[1].replace('"', "")
                                )
                            elif "longitude" in x_detail[0]:
                                property["longitude"] = float(
                                    x_detail[1].replace('"', "")
                                )
                            elif "address" in x_detail[0]:
                                property["address"] = x_detail[1].replace('"', "")
        phone_number = self.main_soup.find(
            "div", attrs={"class": "phone-number info"}
        ).text.replace("\n", "")
        property = {
            "name": property["name"],
            "homepage_link": self.main_url,
            "amenities_link": amenities_link,
            "floorplans_link": floorplans_link,
            "gallery_link": gallery_link,
            "contact_link": contact_link,
            "tour_link": tour_link,
            "address": property["address"],
            "city": property["city"],
            "state": property["state"],
            "country_code": "US",
            "postal_code": property["postal_code"],
            "phone": phone_number,
            "pet_friendly": pet_allowed,
            "latitude": property["latitude"],
            "longitude": property["longitude"],
        }

        propertyunitamenity_set = []
        propertyamenity_set = []
        amenity_container = BeautifulSoup(
            requests.get(amenities_link).text, "html.parser"
        )
        amenity_info = amenity_container.find(attrs={"class": "amenities-1"}).find_all(
            "span"
        )
        for tag in amenity_info:
            tag_info = tag.text.replace("\n", "")
            temp = {
                "name": tag_info,
            }
            propertyamenity_set.append(temp)
        property["propertyamenity_set"] = propertyamenity_set
        property["propertyunitamenity_set"] = propertyunitamenity_set

        url_photogallery = gallery_link
        photo_info_container = BeautifulSoup(
            requests.get(url_photogallery).content, "html.parser"
        )
        photo_info = photo_info_container.find("div", attrs={"id": "gallery"})
        photo_info_imgs = photo_info.find_all("img")
        photo_urls = []
        for item in photo_info_imgs:
            photo_urls.append(item["data-src"])
        propertyphoto_set = []
        index = 0
        for item in photo_urls:
            index += 1
            url = "https://www.thedomainoakland.com" + item
            idx = url.rfind(".")
            extension_item = url[idx:].split("?")
            extension = extension_item[0]
            res = requests.get(url, stream=True)
            if res.status_code == 200:
                propertyphoto_set.append(
                    {
                        "name": property["name"] + f"{index}",
                        "photo": File(
                            io.BytesIO(res.content),
                            property["name"] + f"{index}." + extension,
                        ),
                        "category": "*-*",
                    }
                )
                if index == 0:
                    property["highlight_photo"] = File(
                        io.BytesIO(res.content), property["name"] + "." + extension
                    )
        property["propertyphoto_set"] = propertyphoto_set

        propertyunit_set = []
        floorplan_container = BeautifulSoup(
            requests.get(floorplans_link).content, "html.parser"
        )
        floorplan_info = floorplan_container.find_all(
            "div", attrs={"class": "floorplan-info"}
        )
        for item in floorplan_info:
            bedbath = item.find(attrs={"class": "bedbath"}).text
            bedbathinfo = bedbath.split("|")
            bed_info = bedbathinfo[0].split(" ")
            bath_info = bedbathinfo[1].split(" ")
            sqft = item.find(attrs={"class": "sqft"}).text.replace("\n", "")
            if "-" in sqft:
                sqft = sqft.split("-")
                sqft = sqft[0].replace(" ", "").replace("Sqft:", "").replace(" ", "")
            sqft = sqft.replace("Sqft:", "").replace(" ", "")
            price = item.find("strong").text.replace("\n", "").replace("$", "")
            temp = {
                "bedrooms": bed_info[0],
                "bathrooms": bath_info[1],
                "floor_area": sqft,
                "lowPrice": price,
            }
            propertyunit_set.append(temp)
        property["propertyunit_set"] = propertyunit_set
        return property

    def get_soup(self, _url):
        resp = requests.get(_url, headers=self.headers).content
        return BeautifulSoup(resp, "html.parser")

    def download_img(self, url, name, index, extension):
        res = requests.get(url, stream=True)
        if res.status_code == 200:
            return {
                "name": name + f"{index}",
                "photo": File(
                    io.BytesIO(res.content),
                    name + f"{index}." + extension,
                ),
                "category": "*-*",
            }
