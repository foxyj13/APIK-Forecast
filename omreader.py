from copy import deepcopy
import logging

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from timezonefinder import TimezoneFinder


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
        lat = station["lat"]
        lon = station["lon"]

        # timezone_obj = TimezoneFinder()
        # timezone_str = timezone_obj.timezone_at(lng=lon, lat=lat)

        om_parameters_list = []
        db_parameters_list = []
        for db_par in station["parameters"].keys():
            if station["parameters"][db_par]["om_parameter"]:
                om_parameters_list.append(station["parameters"][db_par]["om_parameter"])
                db_parameters_list.append(db_par)

        request_params = {
            "latitude": lat,
            "longitude": lon,
            "wind_speed_unit": "ms",
            "timezone": "auto",  # timezone_str,
            "models": self.model,
        }

        # 1) отдельно для past: считать -> разложить в словарь station
        request_params_past = deepcopy(request_params)
        request_params_past["hourly"] = om_parameters_list
        request_params_past["past_days"] = int(time_depth[:-1])
        request_params_past["forecast_days"] = 2

        responses = self.openmeteo.weather_api(self.url, params=request_params_past)

        # разложить в словарь
        for idx, db_par in enumerate(db_parameters_list):
            station["parameters"][db_par]["om_data"] = {}
            station["parameters"][db_par]["om_data"]["past"] = {}
            station["parameters"][db_par]["om_data"]["past"][time_depth] = (
                responses[0].Hourly().Variables(idx).ValuesAsNumpy().tolist()
            )

        # Получить сетку по времени для past
        station["om_time_past"] = {}
        station["om_time_past"][time_depth] = (
            pd.date_range(
                start=pd.to_datetime(
                    responses[0].Hourly().Time(), unit="s"
                ),  # , utc=True
                end=pd.to_datetime(
                    responses[0].Hourly().TimeEnd(), unit="s"
                ),  # , utc=True
                freq=pd.Timedelta(seconds=responses[0].Hourly().Interval()),
                inclusive="left",
            )
            .to_pydatetime()
            .tolist()
        )

        # 2) и отдельно для future: считать -> разложить в словарь station
        request_params_future = deepcopy(request_params)
        request_params_future["hourly"] = om_parameters_list
        request_params_future["past_days"] = 0
        request_params_future["forecast_days"] = int(time_forecast[:-1]) + 2

        responses = self.openmeteo.weather_api(self.url, params=request_params_future)

        # разложить в словарь
        for idx, db_par in enumerate(db_parameters_list):
            station["parameters"][db_par]["om_data"]["future"] = {}
            station["parameters"][db_par]["om_data"]["future"][time_forecast] = (
                responses[0].Hourly().Variables(idx).ValuesAsNumpy().tolist()
            )

        # Получить сетку по времени для future
        station["om_time_future"] = {}
        station["om_time_future"][time_forecast] = (
            pd.date_range(
                start=pd.to_datetime(
                    responses[0].Hourly().Time(), unit="s"
                ),  # , utc=True
                end=pd.to_datetime(
                    responses[0].Hourly().TimeEnd(), unit="s"
                ),  # , utc=True
                freq=pd.Timedelta(seconds=responses[0].Hourly().Interval()),
                inclusive="left",
            )
            .to_pydatetime()
            .tolist()
        )

        # 3) и отдельно для current, чтобы выделить значение recent: считать -> разложить в словарь station
        request_params_current = deepcopy(request_params)
        request_params_current["current"] = om_parameters_list
        request_params_current["past_days"] = 0
        request_params_current["forecast_days"] = 0

        responses = self.openmeteo.weather_api(self.url, params=request_params_current)

        # разложить в словарь
        for idx, db_par in enumerate(db_parameters_list):
            station["parameters"][db_par]["om_data"]["past"]["recent"] = (
                responses[0].Current().Variables(idx).Value()
            )

        station["om_time_past"]["recent"] = pd.to_datetime(
            responses[0].Current().Time(), unit="s"  # , utc=True
        ).to_pydatetime()

        # 5) Сформировать пределы сетки по времени (time_range_future)

        return station
