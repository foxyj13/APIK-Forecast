import os
import datetime
import logging
import pickle
import sys

from validator import Validator
from writer import Writer


class Reporter:
    def __init__(self, args: dict, now_dates: list[datetime.date]):
        self.mode = args["main-args"]["mode"]
        self.case = args["main-args"]["case"]

        self.forecast_args = args["forecast-args"]
        self.time_depth = args["forecast-args"]["time-depth"]
        self.time_forecast = args["forecast-args"]["time-forecast"]
        self.forecast_type = args["forecast-args"]["forecast-type"]

        self.data_folder = args["data-args"]["data-folder"]
        self.exp_name = args["data-args"]["experiment-name"]

        self.output_folder = args["main-args"]["output-folder"]

        self.now_dates = now_dates

        # Словарь для хранения считанных данных
        self.in_data = {}

        # Словарь для хранения наблюдений и оси времени сквозных для всей серии прогнозов
        # self.in_obs = {"timeline": [], "obs": []}

        # Формирование списка файлов для дальнейшего анализа результатов
        # Формат имен файлов:
        #   apik-forecast_<experiment-name>_<forecast-type>_<now-date>_td<time-depth>_tf<time-forecast>.pkl
        self.in_files = [
            os.path.join(
                self.data_folder,
                f"apik-forecast_{self.exp_name}>_<forecast-type>_{str(now_date)}_td{self.time_depth}_tf{self.time_forecast}.pkl",
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

    def _get_metrics(self) -> dict[str, list]:
        logging.info("Вычисление метрик")

        validator = Validator(self.time_depth, self.time_forecast)

        metrics = {}

        for idx_now_date in range(len(self.now_dates[:-1])):
            now_date_str = str(self.now_dates[idx_now_date])
            now_date_next_str = str(self.now_dates[idx_now_date + 1])

            stations_now = self.in_data[now_date_str]["stations"]
            stations_next = self.in_data[now_date_next_str]["stations"]

            metrics[now_date_str] = []

            for idx_station, (station_now, station_next) in enumerate(
                zip(stations_now, stations_next)
            ):
                logging.info(
                    "Дата старта прогноза [%s]: станция [%s] %s",
                    now_date_str,
                    station_now["code"],
                    station_now["full_name"],
                )

                st_metrics = validator.get_metrics(station_now, station_next)
                metrics[now_date_str].append(st_metrics)

        return metrics

    def _write_metrics(self, metrics: dict):
        logging.info("Запись метрик в файлы")

    def _gen_metrics_files(self):
        logging.info("Генерация сводных xlsx-файлов с оценками")

        metrics = self._get_metrics()

        writer = Writer(args)

        writer.write_metrics(self.in_data, metrics)

    def _gen_images(self):
        logging.info("Генерация сводных рисунков с наблюдениями и прогнозами")

    def gen_qc_report(self):
        logging.info("Генерация QC-отчета")

        # Загрузка данных из pkl-файлов
        self._load_data()

        # Генерация сводных xlsx-файлов с оценками
        self._gen_metrics_files()

        # Генерация сводных рисунков с наблюдениями и прогнозами
        self._gen_images()
