import concurrent.futures
import io
import re

import requests
from bs4 import BeautifulSoup
from django.core.files import File
from geopy.geocoders import Nominatim
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from scrape.setting import state_lookup_dict


class ScrapingEngine:
    def run(self, scraping_task):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        }
        self.main_url = scraping_task.source_url

        # try:
        self.main_soup = self.get_soup(self.main_url)
        property_info = {}
        link_group = self.get_link()
        property_info = link_group.copy()
        property_info.update(self.get_cominfo())

        property_info.update(self.get_amenity(link_group["amenities_link"]))
        property_info["propertyphoto_set"] = self.get_photos(
            link_group["gallery_link"], property_info["name"]
        )
        property_info["propertyunit_set"] = self.get_floorplan(
            link_group["floorplans_link"]
        )
        scraping_task.scraped_data = property_info.copy()
        return scraping_task
        # except Exception as err:
        #     err = "This url has some problems with run myzeki"
        #     raise Exception(err)

    def get_link(self):
        menu_list = self.main_soup.find_all(
            "div", attrs={"class": "menu-sidebar__element"}
        )
        link_obj = {}
        for item in menu_list:
            if item.a == None:
                continue
            link_temp = self.main_url + item.a["href"]
            _str = item.text.lower()
            if "floor" in _str:
                link_obj["floorplans_link"] = link_temp
            elif "amenit" in _str:
                link_obj["amenities_link"] = link_temp
            elif "gallery" in _str or "photo" in _str:
                link_obj["gallery_link"] = link_temp
            elif "contact" in _str:
                link_obj["contact_link"] = link_temp
            elif "tour" in _str:
                link_obj["tour_link"] = link_temp
        if not "tour_link" in link_obj:
            link_obj["tour_link"] = self.main_url
        return link_obj

    def get_cominfo(self):
        map_tag = self.main_soup.find_all("library-token", attrs={"type": "address"})[0]
        main_soup_str = str(self.main_soup)
        name = self.main_soup.title.string.strip()
        map_link = map_tag.a["href"]
        map_resp = requests.get(map_link, headers=self.headers)
        try:
            latitude, longitude = re.findall("/@(.+?),(.+?),", map_resp.url)[0]
        except:  # noqa
            latitude, longitude = re.findall("/@(.+?),(.+?),", map_resp.text)[0]
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.reverse(latitude + "," + longitude).raw["address"]
        country_code = location["country_code"].upper()
        address = map_tag.text
        city = map_tag.a.contents[2].split(",")[0]
        postal_code = map_tag.a.contents[2].split(",")[1].strip().split(" ")[1]
        state = location["state"]
        phone = re.findall(r'href="tel\:(.+?)"', main_soup_str)[0]
        pet_check = re.findall("pet friendly", str(self.main_soup), re.IGNORECASE)
        pet_friendly = False
        if not pet_check:
            pet_friendly = False
        else:
            pet_friendly = True
        info = {
            "name": name,
            "homepage_link": self.main_url,
            "address": address,
            "city": city,
            "state": state,
            "country_code": country_code,
            "postal_code": postal_code,
            "phone": phone,
            "pet_friendly": pet_friendly,
            "latitude": round(float(latitude), 5),
            "longitude": round(float(longitude), 5),
        }
        return info

    def get_photos(self, gallery_link, property_name):
        photo_soup = self.get_soup(gallery_link, delay=25)
        img_div_tag_list = photo_soup.find_all("div", attrs={"class": "wrapper-media"})
        photo_urls = [
            x.img["src"] for x in img_div_tag_list if not "data:image" in x.img["src"]
        ]
        propertyphoto_set = []
        download_imag_threading = []
        index = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for item in photo_urls:
                index += 1
                extension = "webp"
                download_imag_threading.append(
                    executor.submit(
                        self.download_img, item, property_name, index, extension
                    )
                )
            for item in download_imag_threading:
                propertyphoto_set.append(item.result())

        return propertyphoto_set

    def get_amenity(self, amenity_link):
        amenity_soup = self.get_soup(amenity_link)
        amenity_tag = amenity_soup.find_all(
            "div", attrs={"class": "s-block-text__content"}
        )
        ul_tag = [x.ul for x in amenity_tag if x.ul != None][0]
        community_amenity = [{"name": x.text} for x in ul_tag.find_all("li")]
        interior_features = []
        return {
            "propertyamenity_set": community_amenity,
            "propertyunitamenity_set": interior_features,
        }

    def get_floorplan(self, floorplans_link):
        propertyunit_set = []
        floor_plan_soup = self.get_soup(floorplans_link)
        floor_plan_tag_list = floor_plan_soup.find_all(
            "div", attrs={"class": "wrap-model-item"}
        )
        info_tag_list = [
            x.find_all("div", attrs={"class": "model-info"})[0]
            for x in floor_plan_tag_list
        ]
        for item in info_tag_list:
            try:
                bed_bath = item.find_all("div", attrs={"class": "model-subtitle"})[
                    0
                ].text
                bedrooms = re.findall(r"(\d+)", bed_bath)[1]
                bathrooms = re.findall(r"(\d+)", bed_bath)[2]
                sqft_text = item.find_all("div", attrs={"class": "sqft"})[0].text
                floor_area = re.findall(r"\d+,?\d+", sqft_text)[0]
                starting_rent = 0
            except:  # noqa
                pass
            else:
                propertyunit_set.append(
                    {
                        "bedrooms": bedrooms,
                        "bathrooms": bathrooms,
                        "floor_area": floor_area,
                        "starting_rent": starting_rent,
                    }
                )
        return propertyunit_set

    def get_soup(self, _url, delay=10):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=800,5000")
        options.add_argument("--no-sandbox")
        options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        driver.get(_url)
        _soup = BeautifulSoup(driver.page_source, features="html.parser")
        driver.close()
        return _soup

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
