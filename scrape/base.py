from enum import Enum

state_lookup_dict = {
    "Alaska": "Alaska",
    "AK": "Alaska",
    "Alabama": "Alabama",
    "AL": "Alabama",
    "Arkansas": "Arkansas",
    "AR": "Arkansas",
    "Arizona": "Arizona",
    "AZ": "Arizona",
    "California": "California",
    "CA": "California",
    "Colorado": "Colorado",
    "CO": "Colorado",
    "Connecticut": "Connecticut",
    "CT": "Connecticut",
    "District_of_Columbia": "District of Columbia",
    "DC": "District of Columbia",
    "Delaware": "Delaware",
    "DE": "Delaware",
    "Florida": "Florida",
    "FL": "Florida",
    "Georgia": "Georgia",
    "GA": "Georgia",
    "South Carolina": "South Carolina",
    "SC": "South Carolina",
    "Hawaii": "Hawaii",
    "HI": "Hawaii",
    "Iowa": "Iowa",
    "IA": "Iowa",
    "Idaho": "Idaho",
    "ID": "Idaho",
    "Illinois": "Illinois",
    "IL": "Illinois",
    "Indiana": "Indiana",
    "IN": "Indiana",
    "Kansas": "Kansas",
    "KS": "Kansas",
    "Kentucky": "Kentucky",
    "KY": "Kentucky",
    "Louisiana": "Louisiana",
    "LA": "Louisiana",
    "Massachusetts": "Massachusetts",
    "MA": "Massachusetts",
    "Maryland": "Maryland",
    "MD": "Maryland",
    "Maine": "Maine",
    "ME": "Maine",
    "Michigan": "Michigan",
    "MI": "Michigan",
    "Minnesota": "Minnesota",
    "MN": "Minnesota",
    "Missouri": "Missouri",
    "MO": "Missouri",
    "Mississippi": "Mississippi",
    "MS": "Mississippi",
    "Montana": "Montana",
    "MT": "Montana",
    "North_Carolina": "North Carolina",
    "NC": "North Carolina",
    "North_Dakota": "North Dakota",
    "ND": "North Dakota",
    "Nebraska": "Nebraska",
    "NE": "Nebraska",
    "New_Hampshire": "New Hampshire",
    "NH": "New Hampshire",
    "New_Jersey": "New Jersey",
    "NJ": "New Jersey",
    "New_Mexico": "New Mexico",
    "NM": "New Mexico",
    "Nevada": "Nevada",
    "NV": "Nevada",
    "New_York": "New York",
    "NY": "New York",
    "Ohio": "Ohio",
    "OH": "Ohio",
    "Oklahoma": "Oklahoma",
    "OK": "Oklahoma",
    "Oregon": "Oregon",
    "OR": "Oregon",
    "Pennsylvania": "Pennsylvania",
    "PA": "Pennsylvania",
    "Rhode_Island": "Rhode Island",
    "RI": "Rhode Island",
    "South_Carolina": "South Carolina",
    "SC": "South Carolina",
    "South_Dakota": "South Dakota",
    "SD": "South Dakota",
    "Tennessee": "Tennessee",
    "TN": "Tennessee",
    "Texas": "Texas",
    "TX": "Texas",
    "Utah": "Utah",
    "UT": "Utah",
    "Virginia": "Virginia",
    "VA": "Virginia",
    "Vermont": "Vermont",
    "VT": "Vermont",
    "Washington": "Washington",
    "WA": "Washington",
    "Wisconsin": "Wisconsin",
    "WI": "Wisconsin",
    "West_Virginia": "West Virginia",
    "WV": "West Virginia",
    "Wyoming": "Wyoming",
    "WY": "Wyoming",
    "Alberta": "Alberta",
    "AB": "Alberta",
    "British_Columbia": "British Columbia",
    "BC": "British Columbia",
    "Manitoba": "Manitoba",
    "MB": "Manitoba",
    "New_Brunswick": "New Brunswick",
    "NB": "New Brunswick",
    "Newfoundland_and_Labrador": "Newfoundland and Labrador",
    "NF": "Newfoundland and Labrador",
    "Nova_Scotia": "Nova Scotia",
    "NS": "Nova Scotia",
    "Ontario": "Ontario",
    "ON": "Ontario",
    "Prince_Edward_Island": "Prince Edward Island",
    "PE": "Prince Edward Island",
    "Quebec": "Quebec",
    "PQ": "Quebec",
    "Saskatchewan": "Saskatchewan",
    "SK": "Saskatchewan",
}


class ScrapingTask:
    class Status(Enum):
        CREATED = "CREATED"
        RUNNING = "RUNNING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    def __init__(self, source_url, engine=None):
        self.source_url = source_url
        self.engine = None
        self.status = ScrapingTask.Status.CREATED
        self.scraped_data = {}


class BaseScrapingEngine:
    def __init__(self, source_url):
        self.source_url = source_url

    def run(self, scraping_task):
        scraping_task.result = {}
        scraping_task.status = ScrapingTask.Status.RUNNING
        scraping_task.status = ScrapingTask.Status.COMPLETED
        return scraping_task


class SettingsAcceptor:
    def apply_settings(settings_data):
        raise NotImplementedError()


class ScrapingEngineSelector(BaseScrapingEngine):
    engines = []

    def __init__(self):
        self.engines = []

    def add_engine(self, engine):
        self.engines.append(engine)
        return self.engines

    def run(self, scraping_task):
        engine = self.select_engine(scraping_task)
        # if "appfolio" in str(engine):
        #     return False
        return engine.run(scraping_task)

    def select_engine(scraping_task):
        raise NotImplementedError()


class KeywordDrivenCandidate:
    def __init__(self):
        pass

    def get_keyword(self):
        raise NotImplementedError()
