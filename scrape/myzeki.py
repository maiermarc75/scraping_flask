import concurrent.futures
import io
import re

import requests
from django.core.files import File
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from geopy.geocoders import Nominatim
from scrape.setting import state_lookup_dict


class ScrapingEngine():

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
        property_info["state"] = state_lookup_dict[property_info["state"]]
        property_info["latitude"] = "{:8.5f}".format(
            float(property_info["latitude"])
        )
        property_info["longitude"] = "{:8.5f}".format(
            float(property_info["longitude"])
        )
        scraping_task.scraped_data = property_info.copy()
        return scraping_task
        # except Exception as err:
        #     err = "This url has some problems with run myzeki"
        #     raise ValidationErr(err)

    def get_link(self):
        menu_list = self.main_soup.find_all("div", attrs={"class": "menu-sidebar__element"})
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

    def get_photos(self, gallery_link, property_name):
        photo_soup = self.get_soup(gallery_link)
        img_div_tag_list = photo_soup.find_all("div", attrs={"class": "wrapper-media"})
        photo_urls = [x.img["src"] for x in img_div_tag_list if not "data:image" in x.img["src"]]
        propertyphoto_set = []
        download_imag_threading = []
        index = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for item in photo_urls:
                index += 1
                extension_item = "webp"
                extension = extension_item[0]
                download_imag_threading.append(
                    executor.submit(
                        self.download_img, item, property_name, index, extension
                    )
                )
            for item in download_imag_threading:
                propertyphoto_set.append(item.result())

        return propertyphoto_set

    def get_cominfo(self):
        map_tag = self.main_soup.find_all("library-token", attrs={"type": "address"})[0]
        main_soup_str = str(self.main_soup)
        name = self.main_soup.title.string.strip()
        map_link = map_tag.a["href"]
        map_resp = requests.get(map_link, headers=self.headers)
        try:
            latitude, longitude = re.findall("/@(.+?),(.+?),", map_resp.url)[0]
        except: # noqa
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
            "latitude": latitude,
            "longitude": longitude,
        }
        return info

    def get_amenity(self, amenity_link):
        amenity_soup = self.get_soup(amenity_link)
        amenity_tag = amenity_soup.find_all("div", attrs={"class": "s-block-text__content"})
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
        floor_plan_tag_list = floor_plan_soup.find_all("div", attrs={"class": "wrap-model-item"})
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
        options = Options()
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=options
        )
        driver.get(_url)
        # driver.implicitly_wait(10)
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
