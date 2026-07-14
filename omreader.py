from copy import deepcopy
import datetime
import logging

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

# from timezonefinder import TimezoneFinder


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
            self.openmeteo = openmeteo_requests.Client(session=retry_session)  # type: ignore
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
    ) -> tuple[bool, dict]:

        def check_normalize_timeline(
            time_depth: str,
            time_type: str,  # "past" | "prerast",
            datetime_ranges: dict,  # station["om_time_range_past"],
            timelines: dict,  # station["om_time_past"],
            parameters: dict,  # station["om_parameters"]
        ):
            logging.info(
                "[%s] Проверка данных: должны быть ежечасными. Если какого-то часа не хватает, то добавляется None",
                time_type,
            )

            # dt_range = [
            #     datetime_ranges[time_depth][0].replace(
            #         minute=0, second=0, microsecond=0
            #     )
            #     + datetime.timedelta(hours=1),
            #     datetime_ranges[time_depth][1].replace(
            #         minute=0, second=0, microsecond=0
            #     ),
            # ]
            dt_range = datetime_ranges

            hours_diff = ((dt_range[1] - dt_range[0]).days + 1) * 24
            tl_ref = [
                dt_range[0] + datetime.timedelta(hours=dh) for dh in range(hours_diff)
            ]
            tl = timelines[time_depth]

            missed_idx = []

            for idx, val in enumerate(tl_ref):
                if idx < len(tl):
                    if (tl[idx] != tl_ref[idx]) and (tl[idx] > tl_ref[idx]):
                        tl.insert(idx, val)
                        missed_idx.append(idx)
                else:
                    tl.append(val)
                    missed_idx.append(idx)
            timelines[time_depth] = tl

            if missed_idx:
                for par_name, par_info in parameters.items():
                    for idx in missed_idx:
                        if idx < len(par_info[time_type][time_depth]):
                            par_info[time_type][time_depth].insert(idx, None)
                        else:
                            par_info[time_type][time_depth].append(None)

            logging.info(
                "[%s] Добавлено моментов времени: %d", time_depth, len(missed_idx)
            )

            return timelines, parameters

        logging.info(
            "Считываю данные моделирования с Open-Meteo для станции %s (%s)",
            station["code"],
            station["full_name"],
        )

        # Инициализация ветки в station для хранения OM-метеопараметров
        station["om_parameters"] = {}

        # Формирование перечня OM-метеопараметров, необходимых для дальнейшей работы по этой станции
        om_parameters_list = set()
        for _, par_info in station["parameters"].items():
            om_parameters_list = (
                om_parameters_list
                | set(par_info["om_predictors"])
                | set(par_info["om_parameter"])
            )

        om_parameters_list = [
            par_name
            for par_name in list(om_parameters_list)
            if (par_name is not None) and (par_name.lower() != "none")
        ]

        # Сформировать json для получения данных
        lat = station["lat"]
        lon = station["lon"]

        # timezone_obj = TimezoneFinder()
        # timezone_str = timezone_obj.timezone_at(lng=lon, lat=lat)

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

        try:
            responses = self.openmeteo.weather_api(self.url, params=request_params_past)  # type: ignore
        except Exception as ex:
            logging.error("Ошибка получения данных для исторического периода!")
            logging.error("Exception: %s", ex)
            return False, station

        # Получение сетки по времени для past
        om_time_past = (
            pd.date_range(
                start=pd.to_datetime(responses[0].Hourly().Time(), unit="s", utc=True),
                end=pd.to_datetime(responses[0].Hourly().TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=responses[0].Hourly().Interval()),
                inclusive="left",
            )
            .to_pydatetime()
            .tolist()
        )
        om_time_past[:] = [val + station["station_timeshift"] for val in om_time_past]

        # Вырезать интервал, соответстующий наблюдениям
        try:
            idx_start = om_time_past.index(station["db_time_past"][time_depth][0])
        except ValueError:
            logging.error(
                "Ошибка получения начала интервала по времени для исторических прогнозов!"
            )
            return False, station

        try:
            idx_end = om_time_past.index(station["db_time_past"][time_depth][-1])
        except ValueError:
            logging.error(
                "Ошибка получения конца интервала по времени для исторических прогнозов!"
            )
            return False, station

        station["om_time_past"] = {}
        station["om_time_past"][time_depth] = om_time_past[idx_start : idx_end + 1]

        # Запись границ сетки по времени
        station["om_time_range_past"] = {}
        station["om_time_range_past"][time_depth] = [
            om_time_past[idx_start],
            om_time_past[idx_end],
        ]

        # разложить в словарь значения параметров
        for idx, om_par in enumerate(om_parameters_list):
            station["om_parameters"][om_par] = {}
            station["om_parameters"][om_par]["past"] = {}
            station["om_parameters"][om_par]["past"][time_depth] = (
                responses[0].Hourly().Variables(idx).ValuesAsNumpy().tolist()[idx_start : idx_end + 1]  # type: ignore
            )

        # Проверка данных на ежечасность
        om_time_past_corr, om_parameters = check_normalize_timeline(
            time_depth,
            "past",
            station["om_time_range_past"],
            station["om_time_past"],
            station["om_parameters"],
        )
        station["om_time_past"] = om_time_past_corr
        station["om_parameters"] = om_parameters

        # 2) отдельно выделить значение recent (уже считаны) -> разложить в словарь station
        try:
            idx = station["om_time_past"][time_depth].index(
                station["db_time_past"]["recent"]
            )
        except ValueError:
            logging.error("Ошибка получения текущего момента времени (recent)!")
            return False, station

        for om_par in om_parameters_list:
            station["om_parameters"][om_par]["past"]["recent"] = station[
                "om_parameters"
            ][om_par]["past"][time_depth][idx]

        station["om_time_past"]["recent"] = station["db_time_past"]["recent"]

        # 3) и отдельно для future: считать -> разложить в словарь station
        if int(time_forecast[:-1]) > 0:
            request_params_future = deepcopy(request_params)
            request_params_future["hourly"] = om_parameters_list
            request_params_future["past_days"] = 0
            request_params_future["forecast_days"] = int(time_forecast[:-1]) + 2

            try:
                responses = self.openmeteo.weather_api(  # type: ignore
                    self.url, params=request_params_future
                )
            except Exception as ex:
                logging.error("Ошибка получения данных для прогнозного периода!")
                logging.error("Exception: %s", ex)
                return False, station

            # Получение сетки по времени для future
            om_time_future = (
                pd.date_range(
                    start=pd.to_datetime(
                        responses[0].Hourly().Time(), unit="s", utc=True  # type: ignore
                    ),
                    end=pd.to_datetime(
                        responses[0].Hourly().TimeEnd(), unit="s", utc=True  # type: ignore
                    ),
                    freq=pd.Timedelta(seconds=responses[0].Hourly().Interval()),  # type: ignore
                    inclusive="left",
                )
                .to_pydatetime()
                .tolist()
            )
            om_time_future[:] = [
                val + station["station_timeshift"] for val in om_time_future
            ]

            # Вырезать интервал, соответстующий заданному периоду
            try:
                idx_start = om_time_future.index(station["db_time_past"]["recent"])
            except ValueError:
                logging.error(
                    "Ошибка получения начала интервала по времени для прогноза вперед!"
                )
                return False, station

            date_future_end = station["db_time_past"]["recent"] + datetime.timedelta(
                days=int(time_forecast[:-1])
            )
            try:
                idx_end = om_time_future.index(date_future_end)
            except ValueError:
                logging.error(
                    "Ошибка получения конца интервала по времени для прогноза вперед!"
                )
                return False, station

            station["om_time_future"] = {}
            station["om_time_future"][time_forecast] = om_time_future[
                idx_start : idx_end + 1
            ]

            # Запись границ сетки по времени
            station["om_time_range_future"] = {}
            station["om_time_range_future"][time_forecast] = [
                om_time_future[idx_start],
                om_time_future[idx_end],
            ]

            # разложить в словарь значения параметров
            for idx, om_par in enumerate(om_parameters_list):
                station["om_parameters"][om_par]["future"] = {}
                station["om_parameters"][om_par]["future"][time_forecast] = (
                    responses[0].Hourly().Variables(idx).ValuesAsNumpy().tolist()[idx_start : idx_end + 1]  # type: ignore
                )

            # Проверка данных на ежечасность
            om_time_future_corr, om_parameters = check_normalize_timeline(
                time_forecast,
                "future",
                station["om_time_range_future"],
                station["om_time_future"],
                station["om_parameters"],
            )
            station["om_time_future"] = om_time_future_corr
            station["om_parameters"] = om_parameters

        return True, station
