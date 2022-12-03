from .base import BaseScrapingEngine


class PropertyScrapingEngine(BaseScrapingEngine):
    def __init__(self, uri):
        self.uri = uri

    def scrape(self):
        return {"name": "Dummy Property", "pet_friendly": False}
