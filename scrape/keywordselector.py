import importlib
import re
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from config.settings.base import PROPERTY_SCRAPING_ENGINE_PARAMS

from .base import KeywordDrivenCandidate, ScrapingEngineSelector, SettingsAcceptor


class KeywordDrivenScrapingEngineSelector(ScrapingEngineSelector, SettingsAcceptor):
    def apply_settings(self, source_url, settings_data=PROPERTY_SCRAPING_ENGINE_PARAMS):
        for class_path in settings_data["CANDIDATE_CLASSES"]:
            module_path = class_path[: class_path.rindex(".")]
            class_path_position = 1 + class_path.rindex(".")
            class_name = class_path[class_path_position:]
            engine_module = importlib.import_module(module_path)
            engine_class = getattr(engine_module, class_name)
            engine = engine_class(source_url=source_url)
            self.add_engine(engine)

    def select_engine(self, scraping_task):
        keywords = []
        for engine in self.engines:
            assert isinstance(engine, KeywordDrivenCandidate)
            keywords.append(engine.get_keyword())
        keyword_freq = self.load_keyword_freq(keywords, scraping_task.source_url)
        dominant_keyword = self.get_dominant(keyword_freq, keywords)
        engine = self.find(dominant_keyword)
        return engine

    def load_keyword_freq(self, keywords, source_url):
        keyword_freq = {}
        req = Request(
            url=source_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                + " AppleWebKit/537.36 (KHTML, like Gecko) "
                + "Chrome/105.0.0.0 Safari/537.36"
            },
        )
        webpage = urlopen(req).read()
        keyword_freq_container = str(BeautifulSoup(webpage, "html.parser"))
        for keyword in keywords:
            keyword_freq[keyword] = len(
                re.findall(f"\\b{keyword}\\b", keyword_freq_container)
            )
        if sum(keyword_freq.values()) == 0:
            raise Exception("Not found Engine")
        return keyword_freq

    def get_dominant(self, keyword_freq, keywords):
        dominant_keyword_num = 0
        for keyword in keywords:
            if keyword in str(keyword_freq):
                if dominant_keyword_num < keyword_freq[keyword]:
                    dominant_keyword_num = keyword_freq[keyword]
                    dominant_keyword_text = keyword
        return dominant_keyword_text

    def find(self, dominant_keyword):
        for engine in self.engines:
            keyword_detector = engine.get_keyword()
            if dominant_keyword in keyword_detector:
                return engine
