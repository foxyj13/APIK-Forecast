import os
import datetime
import logging
import pickle
import sys

from validator import Validator
from writer import Writer


class Reporter:
    def __init__(self, args: dict, now_dates_forec_obs: dict[str, str]):
        self.args = args

        self.mode = args["main-args"]["mode"]
        self.case = args["main-args"]["case"]

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
        for fname in self.in_files:
            if not os.path.exists(fname):
                logging.error(
                    "Файл %s не существует. Формирование QC-отчета невозможно", fname
                )
                logging.info("Остановка программы")
                sys.exit(1)

    def _load_data(self):
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

    # def _write_metrics(self, metrics: dict):
    #     logging.info("Запись метрик в файлы")

    def _gen_metrics_files(self):
        logging.info("Генерация сводных xlsx-файлов с оценками")

        metrics = self._get_metrics()

        writer = Writer(self.args)

        writer.write_metrics(self.in_data, metrics)

    # def _gen_images(self):
    #     logging.info("Генерация сводных рисунков с наблюдениями и прогнозами")

    def gen_qc_report(self):
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
            self._gen_metrics_files()

            # Генерация сводных рисунков с наблюдениями и прогнозами
            # self._gen_images()
        else:
            logging.info("Не для всех прогнозов наблюдения в наличии.")
            logging.info("Остановка программы")
            sys.exit(1)
