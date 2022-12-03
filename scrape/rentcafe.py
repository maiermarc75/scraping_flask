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
        return "rentcafe"

    def url_detect(self, url_cominfo):
        try:
            com_info_container = BeautifulSoup(
                requests.get(url_cominfo).content, "html.parser"
            )
            com_info = com_info_container.find_all(
                "script", {"type": "application/ld+json"}
            )
            if "name" in str(com_info[0]):
                com_info_text = str(com_info[0])
                name_position = com_info_text.find("name")
                address_position = com_info_text.find("address")
                if name_position < address_position:
                    return True
                else:
                    return False
            else:
                com_info_text = str(com_info[1])
                name_position = com_info_text.find("name")
                address_position = com_info_text.find("address")
                if name_position < address_position:
                    return True
                else:
                    return False
        except Exception as err:
            raise ValidationErr(err)

    def run(self, scraping_task):
        try:
            main_url = scraping_task.source_url
            property = {}
            result = self.url_detect(main_url)
            if result is True:
                property = self.get_property(main_url)
                scraping_task.scraped_data = property
                return scraping_task
            else:
                pass
            link_group = self.get_links(main_url)

            property = self.get_cominfo(
                main_url, link_group["mapsand_link"], link_group
            )
            property["propertyphoto_set"] = self.get_photos(
                link_group["gallery_link"], name=property["name"]
            )
            amenity_group = self.get_amenity(link_group["amenities_link"])
            property["propertyamenity_set"] = amenity_group["propertyamenity_set"]
            property["propertyunitamenity_set"] = amenity_group[
                "propertyunitamenity_set"
            ]
            property["propertyunit_set"] = self.get_floorplan(
                link_group["floorplans_link"]
            )
            scraping_task.scraped_data["name"] = property["name"]
            scraping_task.scraped_data["homepage_link"] = property["homepage_link"]
            scraping_task.scraped_data["amenities_link"] = property["amenities_link"]
            scraping_task.scraped_data["floorplans_link"] = property["floorplans_link"]
            scraping_task.scraped_data["gallery_link"] = property["gallery_link"]
            scraping_task.scraped_data["contact_link"] = property["contact_link"]
            scraping_task.scraped_data["tour_link"] = property["tour_link"]
            scraping_task.scraped_data["address"] = property["address"]
            scraping_task.scraped_data["city"] = property["city"]
            scraping_task.scraped_data["state"] = state_lookup_dict[property["state"]]
            scraping_task.scraped_data["country_code"] = property["country_code"]
            scraping_task.scraped_data["postal_code"] = property["postal_code"]
            scraping_task.scraped_data["phone"] = property["phone"]
            scraping_task.scraped_data["pet_friendly"] = property["pet_friendly"]
            scraping_task.scraped_data["latitude"] = "{:8.5f}".format(
                float(property["latitude"])
            )
            scraping_task.scraped_data["longitude"] = "{:8.5f}".format(
                float(property["longitude"])
            )
            scraping_task.scraped_data["propertyphoto_set"] = property[
                "propertyphoto_set"
            ]
            scraping_task.scraped_data["propertyamenity_set"] = property[
                "propertyamenity_set"
            ]
            scraping_task.scraped_data["propertyunitamenity_set"] = property[
                "propertyunitamenity_set"
            ]
            scraping_task.scraped_data["propertyunit_set"] = property[
                "propertyunit_set"
            ]
            return scraping_task
        except Exception as err:
            err = "This url has some problems with run rentcafe"
            raise ValidationErr(err)

    def test_link(self, main_url, link_group):
        key_list = list(link_group.keys())
        exist_link_type_list = [
            "floorplans_link",
            "amenities_link",
            "gallery_link",
            "tour_link",
            "contact_link",
            "mapsand_link",
        ]
        for link_type in exist_link_type_list:
            if link_type not in key_list:
                link_group[link_type] = main_url
        return link_group

    def get_links(self, main_url):
        try:
            url_container = BeautifulSoup(requests.get(main_url).content, "html.parser")
            id_url_detector = "navwrapper"
            href_link = url_container.find(attrs={"id": id_url_detector})
            a_tag_container = href_link.find_all("a")
            # exist_link_type_dict = {
            #     "amenit": "amenities_link",
            #     "property": "amenities_link",
            #     "availab": "floorplans_link",
            #     "gallery": "gallery_link",
            #     "photo": "gallery_link",
            #     "contact": "contact_link",
            #     "tour": "tour_link",
            #     "map": "mapsand_link",
            # }
            # link_group = {}
            # for idx in range(len(a_tag_container)):
            #     temps = a_tag_container[idx]["href"].split(".")
            #     temp = temps[0]
            #     if "#" in temp:
            #         pass
            #     for key in list(exist_link_type_dict.keys()):
            #         if key in str(temp.lower()):
            #             link_group[exist_link_type_dict[key]] = main_url + "/" + temp
            # link_group = self.test_link(main_url, link_group)
            # return link_group
            link_group = {}

            for x in range(len(a_tag_container)):
                temps = a_tag_container[x]["href"].split(".")
                temp = temps[0]
                if "#" in temp:
                    pass
                elif "amenit" in temp:
                    link_group["amenities_link"] = main_url + "/" + temp
                elif "floorplan" in temp:
                    link_group["floorplans_link"] = main_url + "/" + temp
                elif "photo" in temp:
                    link_group["gallery_link"] = main_url + "/" + temp
                elif "contact" in temp:
                    link_group["contact_link"] = main_url + "/" + temp
                elif "tour" in temp:
                    link_group["tour_link"] = main_url + "/" + temp
                elif "map" in temp:
                    link_group["mapsand_link"] = main_url + "/" + temp
                else:
                    pass
            return link_group
        except Exception as err:
            err = "This url has some problems with get_links"
            raise ValidationErr(err)

    def get_photos(self, gallery_link, name):
        try:
            photo_info_container = BeautifulSoup(
                requests.get(gallery_link).content, "html.parser"
            )
            photo_info = photo_info_container.findAll("img", {"class": "lazyload"})
            photo_urls = []
            for item in photo_info:
                photo_urls.append(item["data-src"])
            propertyphoto_set = []
            index = 0
            for item in photo_urls:
                index += 1
                url = item
                idx = url.rfind(".")
                extension_item = url[idx:].split("?")
                extension = extension_item[0]

                res = requests.get(url, stream=True)
                if res.status_code == 200:
                    propertyphoto_set.append(
                        {
                            "name": name + f"{index}",
                            "photo": File(
                                io.BytesIO(res.content),
                                name + f"{index}." + extension,
                            ),
                            "category": "*-*",
                        }
                    )
            return propertyphoto_set
        except Exception as err:
            err = "This url has some problems with get_photos"
            raise ValidationErr(err)

    def get_cominfo(self, main_url, mapsand_link, link_group):
        try:
            url_pet_friendly = main_url
            pet_info_container = BeautifulSoup(
                requests.get(url_pet_friendly).content, "html.parser"
            )
            pet_info_text = str(pet_info_container)
            pet_allowed = pet_info_text.find("Pet Friendly")
            if pet_allowed > 0:
                pet_allowed = True
            else:
                pet_allowed = False
            url_cominfo = mapsand_link
            com_info_container = BeautifulSoup(
                requests.get(url_cominfo).content, "html.parser"
            )
            com_info = com_info_container.find_all(
                "script", {"type": "application/ld+json"}
            )
            com_info_json = json.loads(com_info[1].contents[0])
            print(com_info_json)
            property = {
                "name": com_info_json["address"]["name"],
                "homepage_link": main_url,
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
                "phone": com_info_json["address"]["telephone"],
                "pet_friendly": pet_allowed,
                "latitude": float(com_info_json["geo"]["latitude"]),
                "longitude": float(com_info_json["geo"]["longitude"]),
            }
            return property
        except Exception as err:
            err = "This url has some problems with get_infomation"
            raise ValidationErr(err)

    def get_amenity(self, amenities_link):
        try:
            amenity_group = {}
            propertyunitamenity_set = []
            propertyamenity_set = []
            amenity_container = BeautifulSoup(
                requests.get(amenities_link).content, "html.parser"
            )
            class_amenity_detector = "amenities"
            amenity_info = amenity_container.find(
                attrs={"class": class_amenity_detector}
            )
            id_community_amenity_dedector = "CommunityAmenities"
            communityAmenities = amenity_info.find(
                attrs={"id": id_community_amenity_dedector}
            )
            communityAmenities_info = communityAmenities.find(
                attrs={"class": "amenities-list"}
            )
            communityAmenities_info_li = communityAmenities_info.find_all("li")
            for item in communityAmenities_info_li:
                if len(item.text) < 100:
                    temp = {"name": item.text}
                    propertyamenity_set.append(temp)
                else:
                    pass
            id_unit_amenity_dedector = "PropertyAmenities"
            PropertyAmenities = amenity_info.find(
                attrs={"id": id_unit_amenity_dedector}
            )
            PropertyAmenities_info = PropertyAmenities.find(
                attrs={"class": "amenities-list"}
            )

            PropertyAmenities_info_li = PropertyAmenities_info.find_all("li")
            for item in PropertyAmenities_info_li:
                temp = {"name": item.text}
                propertyunitamenity_set.append(temp)
            amenity_group["propertyamenity_set"] = propertyamenity_set
            amenity_group["propertyunitamenity_set"] = propertyunitamenity_set
            return amenity_group
        except Exception as err:
            err = "This url has some problems with get_amenity"
            raise ValidationErr(err)

    def get_floorplan(self, main_url):
        try:
            propertyunit_set = []
            floorplan_container = BeautifulSoup(
                requests.get(main_url).content, "html.parser"
            )
            floorplan_sub_container = floorplan_container.find_all("script")
            print(len(floorplan_sub_container))
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
        except Exception as err:
            err = "This url has some problems with get_floorplans"
            raise ValidationErr(err)

    def get_property(self, main_url):
        try:
            amenities_content = BeautifulSoup(
                requests.get(main_url + "/amenities").content, "html.parser"
            )
            pet_allowed = amenities_content.find("pet friendly")
            if pet_allowed == -1:
                pet_allowed = False
            else:
                pet_allowed = True
            data = json.loads(
                amenities_content.find(
                    "script", {"type": "application/ld+json"}
                ).contents[0]
            )
            property = {
                "name": data["name"],
                "homepage_link": main_url,
                "amenities_link": main_url + "/amenities",
                "floorplans_link": main_url + "/floorplans",
                "gallery_link": main_url + "/photogallery",
                "contact_link": main_url + "/contactus",
                "tour_link": main_url + "/scheduletour",
                "address": data["address"]["streetAddress"],
                "city": data["address"]["addressLocality"],
                "state": state_lookup_dict[data["address"]["addressRegion"]],
                "country_code": data["address"]["addressCountry"],
                "postal_code": data["address"]["postalCode"],
                "phone": data["telephone"],
                "pet_friendly": pet_allowed,
                "latitude": "{:8.5f}".format(float(data["geo"]["latitude"])),
                "longitude": "{:8.5f}".format(float(data["geo"]["longitude"])),
            }
            propertyunitamenity_set = []
            amenity_groups = amenities_content.find_all(
                "ul", {"class": "ysi-amenity-list list-unstyled mb-0 row"}
            )
            if len(amenity_groups) != 0:
                propertyamenity_set = []
                for index, amenity_container in enumerate(
                    amenity_groups[0].find_all("li")
                ):
                    propertyamenity_set.append(
                        {
                            "name": amenity_container.find(
                                "span",
                                {"data-selenium-id": f"CommAmenity{index + 1}"},
                            ).contents[0]
                        }
                    )
                property["propertyamenity_set"] = propertyamenity_set

                if len(amenity_groups) == 2:
                    for index, amenity_container in enumerate(
                        amenity_groups[1].find_all("li")
                    ):
                        propertyunitamenity_set.append(
                            {
                                "name": amenity_container.find(
                                    "span",
                                    {
                                        "data-selenium-id": "AptAmenity{}".format(
                                            index + 1
                                        )
                                    },
                                ).contents[0]
                            }
                        )

            brochure_content = BeautifulSoup(
                requests.get(main_url + "/brochure").text, "html.parser"
            )
            tr_group = (
                brochure_content.find("div", {"id": "nav-list-view"})
                .find("tbody")
                .find_all("tr")
            )
            propertyunit_set = []
            for index, tr in enumerate(tr_group):
                propertyunit_set.append(
                    {
                        "bedrooms": int(
                            "0"
                            + "".join(
                                filter(
                                    str.isdigit,
                                    tr.find(
                                        "span",
                                        {
                                            "data-selenium-id": "Floorplan{}Beds".format(
                                                index + 1
                                            )
                                        },
                                    ).contents[0],
                                )
                            )
                        ),
                        "bathrooms": float(
                            "0"
                            + "".join(
                                filter(
                                    str.isdigit,
                                    tr.find(
                                        "span",
                                        {
                                            "data-selenium-id": "Floorplan{}Baths".format(
                                                index + 1
                                            )
                                        },
                                    ).contents[0],
                                )
                            )
                        ),
                        "floor_area": float(
                            "0"
                            + "".join(
                                filter(
                                    str.isdigit,
                                    tr.find(
                                        "span",
                                        {
                                            "data-selenium-id": "Floorplan{}SqFt".format(
                                                index + 1
                                            )
                                        },
                                    ).contents[0],
                                )
                            )
                        ),
                        "starting_rent": float(
                            "0"
                            + "".join(
                                filter(
                                    str.isdigit,
                                    tr.find(
                                        "span",
                                        {
                                            "data-selenium-id": "Floorplan{}Rent".format(
                                                index + 1
                                            )
                                        },
                                    ).contents[0],
                                )
                            )
                        ),
                        "propertyunitamenity_set": propertyunitamenity_set,
                    }
                )

            property["propertyunit_set"] = propertyunit_set

            propertyphoto_set = []
            photo_page = BeautifulSoup(
                requests.get(main_url + "/photogallery").text, "html.parser"
            )
            carousel_items = photo_page.find(
                "div",
                {"id": "Photos"},
            ).find_all("div", {"class": "carousel-item"})
            for index, item in enumerate(carousel_items):
                url = item.find("a")["href"]
                idx = url.rfind(".")
                extension = url[idx:]
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
            return property
        except Exception as err:
            err = "This url has some problems with get_property"
            raise ValidationErr(err)
