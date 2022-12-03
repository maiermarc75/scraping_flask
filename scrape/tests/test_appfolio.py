import pytest
from django.core.exceptions import ValidationError

from ...api.serializers import PropertySerializer
from ..appfolio import ScrapingEngine
from ..base import ScrapingTask

pytestmark = pytest.mark.django_db


class TestAppfolioScraper:
    def test_scraping(self, appfolio_urls):
        for url in appfolio_urls:
            engine = ScrapingEngine(source_url=url)
            scraping_task = ScrapingTask(source_url=url)
            engine.run(scraping_task=scraping_task)
            result = scraping_task.scraped_data
            property_serializer = PropertySerializer(data=result)
            try:
                property_serializer.is_valid(raise_exception=True)
            except ValidationError as err:
                print(err)
            return True
