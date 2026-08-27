import os
import datetime
import logging
import pickle
import sys

from plotter_qc import PlotterQC
from validator import Validator
from writer import Writer


class Reporter:
    def __init__(self, args: dict, now_dates_forec_obs: dict[str, str]):
        self.args = args

        self.mode = args["main-args"]["mode"]
        self.case = args["main-args"]["case"]
        self.start_date = args["main-args"]["start-date"]
        self.end_date = args["main-args"]["end-date"]
        # self.step_date = args["main-args"]["step-date"]

        self.forecast_args = args["forecast-args"]
        self.time_depth = args["forecast-args"]["time-depth"]
        self.time_forecast = args["forecast-args"]["time-forecast"]
        self.forecast_type = args["forecast-args"]["forecast-type"]

        self.data_folder = args["data-args"]["data-folder"]
        self.exp_name = args["data-args"]["experiment-name"]

        self.output_folder = args["main-args"]["output-folder"]

        self.now_dates_forec_obs = now_dates_forec_obs
        self.now_dates = list(
            set(now_dates_forec_obs.keys()) | set(now_dates_forec_obs.values())
        )

        # Словарь для хранения считанных данных
        self.in_data = {}

        # Словарь для хранения осей времени для каждого прогноза
        self.timelines = {}

        # Формирование списка файлов для дальнейшего анализа результатов
        # Формат имен файлов:
        #   apik-forecast_<experiment-name>_<forecast-type>_<now-date>_td<time-depth>_tf<time-forecast>.pkl
        self.in_files = [
            os.path.join(
                self.data_folder,
                f"apik-forecast_{self.exp_name}_{self.forecast_type}_{str(now_date)}_td{self.time_depth}_tf{self.time_forecast}.pkl",
            )
            for now_date in self.now_dates
        ]

        # Проверка, что все фалы из сгенерированного списка присутствуют в указанной директории с данными
        flag = True
        for fname in self.in_files:
            if not os.path.exists(fname):
                logging.error("Файл %s не существует", fname)
                flag = False

        if not flag:
            logging.error("Недостаточно файлов для работы")
            logging.info("Остановка программы")
            sys.exit(1)

    def _combine_obs_forecasts(self) -> dict:
        logging.info("Агрегация данных для дальнейшей отрисовки или экспорта")
        logging.info(
            "Сведение данных наблюдений от разных прогнозов на одну ось по времени"
        )

        # { "stations": {
        #   "code": {"full_name", "lat", "lon",
        #       "parameters": {
        #           <par_name>: {"code", "name", "om_parameter",
        #                       "obs": {datetime: float, ...}, # использовать setdefault()
        #                       "local": {"past": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}
        #                               "future": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}},
        #                       "global": {"past": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}
        #                                "future": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}}
        #           }
        #       }
        #   }, ...
        # },
        #  "obs_timeline": [datetime, ...] # сгенерирован нужный
        # }

        data_dict = {}
        data_dict["stations"] = {}
        start_time = (
            datetime.datetime.strptime(self.start_date, "%Y-%m-%d")
            - datetime.timedelta(days=int(self.time_depth[:-1]))
            + datetime.timedelta(hours=1)
        )
        end_time = datetime.datetime.strptime(
            self.end_date, "%Y-%m-%d"
        ) + datetime.timedelta(days=int(self.time_forecast[:-1]) + 1)
        hours_diff = ((end_time - start_time).days + 1) * 24

        data_dict["obs_timeline"] = [
            (start_time + datetime.timedelta(hours=dh)).replace(
                tzinfo=datetime.timezone.utc
            )
            for dh in range(hours_diff)
        ]

        for now_date, now_date_info in self.in_data.items():
            stations: list = now_date_info["stations"]
            for station in stations:
                st_code = station["code"]
                if st_code not in data_dict["stations"]:
                    data_dict["stations"][st_code] = {
                        "full_name": station["full_name"],
                        "lat": station["lat"],
                        "lon": station["lon"],
                        "parameters": {},
                    }

                for par_name, par_info in station["parameters"].items():
                    if par_name not in data_dict["stations"][st_code]["parameters"]:
                        data_dict["stations"][st_code]["parameters"][par_name] = {
                            "code": par_info["code"],
                            "full_name": par_info["full_name"],
                            "om_parameter": par_info["om_parameter"],
                            "obs": {},
                            "local": {"past": {}, "future": {}},
                            "global": {"past": {}, "future": {}},
                        }

                    for obs_time, obs_data in zip(
                        station["timeline"]["past"][self.time_depth],
                        par_info["data"][self.time_depth],
                    ):
                        if obs_time in data_dict["obs_timeline"]:
                            data_dict["stations"][st_code]["parameters"][par_name][
                                "obs"
                            ].setdefault(obs_time, obs_data)

                    if par_info["data_local"]:
                        data_dict["stations"][st_code]["parameters"][par_name]["local"][
                            "past"
                        ][now_date] = {
                            "data": par_info["data_local"]["past"][self.time_depth],
                            "timeline": station["timeline"]["past"][self.time_depth],
                        }

                        data_dict["stations"][st_code]["parameters"][par_name]["local"][
                            "future"
                        ][now_date] = {
                            "data": par_info["data_local"]["future"][
                                self.time_forecast
                            ],
                            "timeline": station["timeline"]["future"][
                                self.time_forecast
                            ],
                        }
                    else:
                        data_dict["stations"][st_code]["parameters"][par_name]["local"][
                            "past"
                        ][now_date] = {
                            "data": [None]
                            * len(station["timeline"]["past"][self.time_depth]),
                            "timeline": station["timeline"]["past"][self.time_depth],
                        }

                        data_dict["stations"][st_code]["parameters"][par_name]["local"][
                            "future"
                        ][now_date] = {
                            "data": [None]
                            * len(station["timeline"]["future"][self.time_forecast]),
                            "timeline": station["timeline"]["future"][
                                self.time_forecast
                            ],
                        }

                    if par_info["om_parameter"] and (
                        par_info["om_parameter"] in station["predictors_data"]
                    ):
                        data_dict["stations"][st_code]["parameters"][par_name][
                            "global"
                        ]["past"][now_date] = {
                            "data": station["predictors_data"][
                                par_info["om_parameter"]
                            ]["past"][self.time_depth],
                            "timeline": station["timeline"]["past"][self.time_depth],
                        }

                        data_dict["stations"][st_code]["parameters"][par_name][
                            "global"
                        ]["future"][now_date] = {
                            "data": station["predictors_data"][
                                par_info["om_parameter"]
                            ]["future"][self.time_forecast],
                            "timeline": station["timeline"]["future"][
                                self.time_forecast
                            ],
                        }
                    else:
                        data_dict["stations"][st_code]["parameters"][par_name][
                            "global"
                        ]["past"][now_date] = {
                            "data": [None]
                            * len(station["timeline"]["past"][self.time_depth]),
                            "timeline": station["timeline"]["past"][self.time_depth],
                        }

                        data_dict["stations"][st_code]["parameters"][par_name][
                            "global"
                        ]["future"][now_date] = {
                            "data": [None]
                            * len(station["timeline"]["future"][self.time_forecast]),
                            "timeline": station["timeline"]["future"][
                                self.time_forecast
                            ],
                        }

        # { "stations": {
        #   "code": {"full_name", "lat", "lon",
        #       "parameters": {
        #           <par_name>: {"code", "full_name", "om_parameter",
        #                       "obs": [float, ...],
        #                       "local": {"past": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}
        #                               "future": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}},
        #                       "global": {"past": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}
        #                                "future": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}}

        #           }
        #       }
        #   }, ...
        # },
        #  "obs_timeline": [datetime, ...] # сгенерирован нужный
        # }

        for station, station_info in data_dict["stations"].items():
            for par_name, par_info in station_info["parameters"].items():
                obs_list = [
                    par_info["obs"].get(time_val, None)
                    for time_val in data_dict["obs_timeline"]
                ]

                par_info["obs"] = obs_list

        return data_dict

    def _get_metrics(self) -> dict[str, list]:
        logging.info("Вычисление метрик")

        validator = Validator(self.time_depth, self.time_forecast)

        metrics = {}

        # for idx_now_date, now_date in enumerate(self.now_dates[:-1]):
        for now_date_str, now_date_next_str in self.now_dates_forec_obs.items():

            stations_now = self.in_data[now_date_str]["stations"]
            stations_next = self.in_data[now_date_next_str]["stations"]

            metrics[now_date_str] = {}

            for idx_station, (station_now, station_next) in enumerate(
                zip(stations_now, stations_next)
            ):
                if station_now["code"] != station_next["code"]:
                    logging.error(
                        "Рассинхронизация порядка записи станций с кодами: %s и %s",
                        station_now["code"],
                        station_next["code"],
                    )
                    logging.info("Остановка программы")
                    sys.exit(1)

                logging.info(
                    "Дата старта прогноза [%s]: станция [%s] %s",
                    now_date_str,
                    station_now["code"],
                    station_now["full_name"],
                )

                st_metrics = validator.get_metrics(station_now, station_next)
                metrics[now_date_str][station_now["code"]] = st_metrics

        return metrics

    def _load_data(self) -> None:
        logging.info("Загрузка данных из pkl-файлов")

        for now_date, fname in zip(self.now_dates, self.in_files):
            with open(fname, "rb") as in_file:
                self.in_data[str(now_date)] = pickle.load(in_file)

            self.timelines[str(now_date)] = {
                "past": self.in_data[str(now_date)]["stations"][0]["timeline"]["past"],
                "future": self.in_data[str(now_date)]["stations"][0]["timeline"][
                    "future"
                ],
            }

    def gen_qc_report(self) -> None:
        def check_obs_avail_for_now_date_forecast() -> bool:
            result = True

            for now_date_str, now_date_next_str in self.now_dates_forec_obs.items():
                if set(
                    self.timelines[now_date_str]["future"][self.time_forecast]
                ) < set(self.timelines[now_date_next_str]["past"][self.time_depth]):
                    pass
                else:
                    logging.error(
                        "Отсутствуют наблюдения для прогноза от %s в файле с прогнозом от %s",
                        now_date_str,
                        now_date_next_str,
                    )
                    result = False

            return result

        logging.info("Генерация QC-отчета")

        # Загрузка данных из pkl-файлов
        self._load_data()

        # Проверка наличия наблюдений для прогнозов
        if check_obs_avail_for_now_date_forecast():

            # Генерация сводных xlsx-файлов с оценками
            logging.info("Генерация сводных xlsx-файлов с оценками")
            metrics = self._get_metrics()
            writer = Writer(self.args)
            writer.write_metrics(self.in_data, metrics)

            # Агрегация данных для дальнейшей отрисовки или экспорта
            data_obs_forec = self._combine_obs_forecasts()

            # Генерация сводных рисунков с наблюдениями и прогнозами
            plotter_qc = PlotterQC(self.args, self.now_dates_forec_obs, data_obs_forec)
            plotter_qc.make_plots()

        else:
            logging.info("Не для всех прогнозов наблюдения в наличии.")
            logging.info("Остановка программы")
            sys.exit(1)

    def export_data(self):
        logging.info("Экспорт данных")

        # Загрузка данных из pkl-файлов
        self._load_data()

        # Агрегация данных для дальнейшей отрисовки или экспорта
        data_obs_forec = self._combine_obs_forecasts()

        # Генерация сводных xlsx-файлов с данными
        logging.info("Генерация сводных xlsx-файлов с данными")
        writer = Writer(self.args)
        writer.write_data(
            self.in_data, data_obs_forec, list(self.now_dates_forec_obs.keys())
        )
