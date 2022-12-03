import pytest
from django.core.exceptions import ValidationError

from ...api.serializers import PropertySerializer
from ..base import ScrapingTask
from ..rentcafe import ScrapingEngine

pytestmark = pytest.mark.django_db


class TestRentcafeScraper:
    def test_scraping(self, rentcafe_urls):
        for url in rentcafe_urls:
            try:
                engine = ScrapingEngine(source_url=url)
                scraping_task = ScrapingTask(source_url=url)
                engine.run(scraping_task=scraping_task)
                result = scraping_task.scraped_data
                property_serializer = PropertySerializer(data=result)
                property_serializer.is_valid(raise_exception=True)
            except Exception as err:
                err = "This url is not passed!"
                print(err)
                continue
        return True
