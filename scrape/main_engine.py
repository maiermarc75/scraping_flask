import importlib

from config.settings.base import (
    PROPERTY_SCRAPING_ENGINE,
    PROPERTY_SCRAPING_ENGINE_PARAMS,
)

from .base import ScrapingTask


def run_scraping_task(source_url):
    module_path = PROPERTY_SCRAPING_ENGINE[: PROPERTY_SCRAPING_ENGINE.rindex(".")]
    class_path_position = 1 + PROPERTY_SCRAPING_ENGINE.rindex(".")
    class_name = PROPERTY_SCRAPING_ENGINE[class_path_position:]
    engine_module = importlib.import_module(module_path)
    engine_class = getattr(engine_module, class_name)
    engine = engine_class()

    engine.apply_settings(
        source_url=source_url,
        settings_data=PROPERTY_SCRAPING_ENGINE_PARAMS,
    )

    scraping_task = ScrapingTask(source_url=source_url)

    scraping_task = engine.run(scraping_task)

    return scraping_task.scraped_data
