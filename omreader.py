import logging

import openmeteo_requests
import requests_cache
from retry_requests import retry


class OMReader:
    def __init__(self, url, model):
        self.url = url
        self.model = model

        self.openmeteo = None

    def connect(self):
        logging.info("Подключаю Open-Meteo API клиента")

        try:
            # Setup the Open-Meteo API client with a cache and retry mechanism
            cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
            retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
            self.openmeteo = openmeteo_requests.Client(session=retry_session)
        except Exception as ex:
            logging.error("Ошибка подключения API клиента!")
            logging.error("Exception: %s", ex)
            return False

        logging.info("OK!")
        return True

    def get_model_data(self):
        pass
