import pytest
from django.core.exceptions import ValidationError

from ...api.serializers import PropertySerializer
from ..base import ScrapingTask
from ..entrata import ScrapingEngine

pytestmark = pytest.mark.django_db


class TestEntrataScraper:
    def test_scraping(self, entrata_urls):
        for url in entrata_urls:
            print(url)
            engine = ScrapingEngine(source_url=url)
            scraping_task = ScrapingTask(source_url=url)
            engine.run(scraping_task=scraping_task)
            result = scraping_task.scraped_data
            property_serializer = PropertySerializer(data=result)
            try:
                property_serializer.is_valid(raise_exception=True)
                print(url + "success")
            except ValidationError as err:
                print(err)
        return True
