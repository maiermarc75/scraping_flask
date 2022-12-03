import pytest
from django.core.exceptions import ValidationError

from ...api.serializers import PropertySerializer
from ..base import ScrapingTask
from ..leaselabs import ScrapingEngine

pytestmark = pytest.mark.django_db


class TestLeaselabScraper:
    def test_scraping(self, leaselab_urls):
        for url in leaselab_urls:
            try:
                engine = ScrapingEngine(source_url=url)
                scraping_task = ScrapingTask(source_url=url)
                engine.run(scraping_task=scraping_task)
                result = scraping_task.scraped_data
                property_serializer = PropertySerializer(data=result)
                property_serializer.is_valid(raise_exception=True)
            except ValidationError as err:
                print(err)
        return True
