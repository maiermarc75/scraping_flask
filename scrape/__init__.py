import importlib


def get_scraping_data(self, data):
    engine_mod_path = (
        self.__module__[: self.__module__.rfind(".")]
        + ".scrape.scraper_"
        + data["module_path"].lower()
    )

    engine_module = importlib.import_module(engine_mod_path)  # engine module
    scrape_engine = engine_module.PropertyScrapingEngine(data)
    scrape_engine.scrape()
    return scrape_engine.get_result()
