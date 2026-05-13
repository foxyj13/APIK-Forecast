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

    def get_model_data(
        self,
        station: dict,
        time_depth: str = "7d",
        time_forecast: str = "0d",
        now_date=None,
    ) -> dict:
        logging.info(
            "Считываю данные моделирования с Open-Meteo для станции %s (%s)",
            station["code"],
            station["full_name"],
        )

        # Сформировать json для получения данных
        # 1) отдельно для past: считать -> разложить в словарь station
        # 2) и отдельно для future: считать -> разложить в словарь station
        # 3) и отдельно для current, чтобы выделить значение recent: считать -> разложить в словарь station
        # 4) Сформировать сетку по времени (time_future)
        # 5) Сформировать пределы сетки по времени (time_range_future)

        # 6) Проверить и отладить случай, когда нет прямого соответствия для параметра (просто пропустить, оставив пустой список)

        return {}
