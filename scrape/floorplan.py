import concurrent.futures
import io
import re
import time

import requests
from bs4 import BeautifulSoup
from django.core.files import File
from geopy.geocoders import Nominatim
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from scrape.setting import state_lookup_dict


class Floorplan:
    def __init__(self) -> None:
        self.most_used_words = [
            "bed",
            "bath",
            "studio",
            "sq",
            "ft",
            "sf",
            "starting",
            "start",
            "rent",
            "available",
        ]
        # self.most_used_words = ["bed", "bath", "studio", "floor", "plan", "sq", "ft", "sf", "apply", "conact", "price", "pric", "pricing" "call", "us", "starting", "start", "rent", "available"]
        self.root_deep = []

    def run(self, _url):
        url_list = [
            # "https://www.abbeyapartmenthomes.com/springfield/the-abbey-apartments/conventional/",
            # "https://www.accessculvercity.com/culver-city/access-culver-city/conventional/",
            # "https://www.aceroestrellacommons.com/goodyear/acero-estrella-commons/conventional/#/",
            # "https://www.acerowestsalem.com/salem-salem/acero-west-salem-apartments/conventional/",
            # "https://www.deerhavenapts.com/apartments/wa/wenatchee/floor-plans#/",
            # "https://www.delpradoapts.com/apartments/ca/pleasanton/floor-plans",
            # "https://columbiapointeapts.com/floor-plans/",
            # "https://coventrygreenapts.com/floor-plans/",
            # "https://goaquaapartments.com/floor-plans/",
            # "https://gobexleyhouse.com/floor-plans/",
            # "https://www.thedomainoakland.com/domain-oakland-oakland-ca/floorplans",
            # "https://dakotaaptslacey.com/floor-plans",
            # "https://www.courtyardsontheparkapts.com/Floor-plans.aspx",
            # "https://rentnow.westvillagelofts.com/",
            "https://www.argylelake.com/floor-plans",
            # "https://www.vantagestpete.com/floor-plans",
            # "https://www.liveatwillowshores.com/floorplans/",
            # "https://www.deckerliving.com/models",
            # "https://www.athenaaptsliving.com/models",
            # "https://www.remiliving.com/models"
        ]
        try:
            for x in url_list:
                self.root_deep = []
                soup = self.get_soup(x)
                # for item in soup.body.find_all(recursive=False):
                last_soup = self.get_match_words(soup.body)
                # print(last_soup)
                file = open("counts.txt", "a")
                file.write(x + "\n" + str(self.root_deep) + "\n\n")
                file.close()
        except:
            pass

    def get_match_words(self, soup):
        counts_list = []
        children = soup.find_all(recursive=False)
        if not children:
            return soup
        for item in children:
            temp_str = str(item).lower()
            counts = 0
            for word in self.most_used_words:
                if word in temp_str:
                    counts += 1
            counts_list.append(counts)
        max_count = max(counts_list)
        self.root_deep.append(counts_list)
        fit_soup = children[counts_list.index(max_count)]
        self.get_match_words(fit_soup)

    def get_soup(self, _url, delay=10):
        options = Options()
        # options.add_argument("--headless")
        options.add_argument("--window-size=1920,1024")
        # options.add_argument("--no-sandbox")
        # options.add_argument(
        #     "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        # )
        # options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        driver.get(_url)
        total_height = int(driver.execute_script("return document.body.scrollHeight"))
        for i in range(1, total_height, 5):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.01)
        _soup = BeautifulSoup(driver.page_source, features="html.parser")
        # driver.close()
        return _soup
