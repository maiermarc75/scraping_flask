import json

import requests
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError

from .base import BaseScrapingEngine, state_lookup_dict
from .keywordselector import KeywordDrivenCandidate

# from django.core.files import File


class ScrapingEngine(BaseScrapingEngine, KeywordDrivenCandidate):
    def __init__(self, source_url):
        BaseScrapingEngine.__init__(self, source_url)
        KeywordDrivenCandidate.__init__(self)

    def get_keyword(self):
        return "pedcorliving"

    def run(self, scraping_task):
        try:
            main_url = scraping_task.source_url
            property = {}
            link_group = {}
            link_group["amenities_link"] = main_url + "/amenities"
            link_group["floorplans_link"] = main_url + "/floorplans"
            link_group["gallery_link"] = main_url + "/gallery"
            link_group["contact_link"] = main_url + "/contact"
            link_group["homepage_link"] = main_url
            link_group["tour_link"] = main_url

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
            url_cominfo = main_url
            com_info_container = BeautifulSoup(
                requests.get(url_cominfo).content, "html.parser"
            )
            com_info = com_info_container.find_all(
                "script", {"type": "application/ld+json"}
            )
            com_info_json = json.loads(com_info[0].contents[0])
            # print(com_info_json)
            property = {
                "name": com_info_json["@graph"][0]["name"],
                "homepage_link": main_url,
                "amenities_link": link_group["amenities_link"],
                "floorplans_link": link_group["floorplans_link"],
                "gallery_link": link_group["gallery_link"],
                "contact_link": link_group["contact_link"],
                "tour_link": link_group["tour_link"],
                "address": com_info_json["@graph"][0]["address"]["streetAddress"],
                "city": com_info_json["@graph"][0]["address"]["addressLocality"],
                "state": com_info_json["@graph"][0]["address"]["addressregion"],
                "country_code": com_info_json["@graph"][0]["address"][
                    "addressCountry"
                ].replace("A", ""),
                "postal_code": com_info_json["@graph"][0]["address"]["postalCode"],
                "phone": com_info_json["@graph"][0]["telephone"],
                "pet_friendly": pet_allowed,
                "latitude": float(com_info_json["@graph"][0]["geo"]["latitude"]),
                "longitude": float(com_info_json["@graph"][0]["geo"]["longitude"]),
            }

            amenity_container = BeautifulSoup(
                requests.get(link_group["amenities_link"]).content, "html.parser"
            )
            amenity_group = amenity_container.find_all(attrs={"class": "mt-12"})
            propertyamenity_set = []
            propertyunitamenity_set = []
            # print(amenity_group)
            amenity_set = amenity_group[0].find_all(attrs={"class": "leading-tight"})
            unitamenity_set = amenity_group[1].find_all(
                attrs={"class": "leading-tight"}
            )
            for amenity_item in unitamenity_set:
                temp = {"name": amenity_item.text}
                propertyunitamenity_set.append(temp)
            for amenity_item in amenity_set:
                temp = {"name": amenity_item.text}
                propertyamenity_set.append(temp)
            property["propertyamenity_set"] = propertyamenity_set
            property["propertyunitamenity_set"] = propertyunitamenity_set
            print(property)

            floorplan_container = BeautifulSoup(
                requests.get(link_group["floorplans_link"]).content, "html.parser"
            )
            floorplan_group = floorplan_container.find_all("script")
            propertyunit_set = []
            for item in floorplan_group:
                if "window.floorplans" in str(item):
                    floorplan_text = item.text.split("}}")
                    for floorplan_text_item in floorplan_text:
                        if "];" in floorplan_text_item:
                            continue
                        if ",{" in floorplan_text_item:
                            floorplan_text_item = floorplan_text_item.replace(",{", "{")
                            print(floorplan_text_item)
                        temp_text = floorplan_text_item.replace(
                            "window.floorplans = [", ""
                        )
                        temp_text = temp_text + "}}"
                        # print(floorplan_text_item + "}}")
                        temp_json = json.loads(temp_text)
                        print(temp_json)
                        bedrooms = temp_json["Bedroom"].replace("'", "")
                        bathrooms = temp_json["Bathroom"].replace("'", "")
                        temp = {
                            "bedrooms": int(bedrooms),
                            "bathrooms": float(bathrooms),
                            "floor_area": temp_json["MinSqFt"],
                            "starting_rent": temp_json["MinRent"],
                        }
                        propertyunit_set.append(temp)
            property["propertyunit_set"] = propertyunit_set
            print(property)

            photo_container = BeautifulSoup(
                requests.get(link_group["gallery_link"]).content, "html.parser"
            )
            photo_group = photo_container.find_all(
                attrs={"class": "gallery-grid__item"}
            )
            for photo_item in photo_group:
                photo_img = photo_item.find("img")
                photo_img = photo_img["src"]
                print(photo_img)
            propertyphoto_set = []
            property["propertyphoto_set"] = propertyphoto_set
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
            err = "This is custom url and some change are detected..."
            raise ValidationError(err)
