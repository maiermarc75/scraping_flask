import importlib
import re

import requests
import sentry_sdk
from bs4 import BeautifulSoup

from scrape import setting

class Scraping:
    def __init__(self) -> None:
        self.source_url = ""
        self.scraped_data = {}

def get_scraping_data(_url):
    url, resp = valid_url(_url)
    keyword = search_keyword(resp)
    module_path = f"scrape.{keyword}"
    engine_module = importlib.import_module(module_path)  # engine module
    engine_class = getattr(engine_module, "ScrapingEngine")
    scrape_engine = engine_class()
    scraping_task = Scraping()
    scraping_task.source_url = url
    property_info = scrape_engine.run(scraping_task)
    return property_info


def valid_url(_url):
    """Check a URL is valid or not and return full URL if the url has only domain.

    Args:
        _url (string): e.g. github.com,  https://github.com/, https://github.com,
    Return:
        if _url is valid
            URL(string) Rsponse(requests.models.Response)
            e.g: "https://github.com", <Response [200]>
        else
            false
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
    }
    if _url == "":
        raise Exception("Invalid URL")
    if _url[-1] == "/":
        _url = _url[:-1]
    if not "http" in _url:
        _url = "https://" + _url
    resp = requests.get(_url, headers=headers)
    if resp.status_code < 400:
        return (_url, resp)
    else:
        raise Exception("Invalid URL")


def search_keyword(resp):
    """Search counts of service keywords in resp content and return service with max counts

    Args:
        resp (requests.models.Response): _description_

    Returns:
        string: service string with max counts
    """
    resp_str = resp.text
    keyword_freq = {}
    for service in setting.services:
        keyword_freq[service] = len(
            re.findall(f"\\b{service}\\b", resp_str, re.IGNORECASE | re.DOTALL)
        )
    if sum(keyword_freq.values()) == 0:
        raise Exception("Not found Service")
    service_with_max = max(keyword_freq, key=keyword_freq.get)
    return service_with_max
