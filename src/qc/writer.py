import logging

import openpyxl
import pandas as pd


class Writer:
    def __init__(self, args: dict): ...

    def _gen_dfs_metrics(self, metrics: dict) -> dict:
        logging.info(
            "Формирование датафреймов со всеми оценками: 1 датафрейм = 1 станция 1 метео-параметр"
        )

        return {}

    def _collect_info(self, in_data: dict) -> dict:
        logging.info(
            "Сбор информации о расчетах для формирования 1-го листа с аннотацией"
        )

        return {}

    def write_1_file_is_1_station_all_parameters(self, info: dict, dfs: dict) -> None:
        logging.info(
            "Формирование серии файлов: 1 файл = 1 станция с метриками по всем метео-параметрам"
        )

        # Цикл по станциям:
        #   Создать файл
        #   Сформировать 1-й лист (Info), на основе словаря info (для записи используется openpyxl)
        #   Цикл по переменным (по имени):
        #       Ззпись соответствующего датафрейма на отдельный лист с именем переменной (для записи используется pandas)
        #   Закрыть файл

    def write_1_file_is_1_parameter_all_stations(self, info: dict, dfs: dict) -> None:
        logging.info(
            "Формирование серии файлов: 1 файл = 1 метео-параметр (по имени) с метриками по станциям"
        )

        # Цикл по именам метео-параметров (вообще всех возможных по всем станциям в этом расчете):
        #   Создать файл
        #   Сформировать 1-й лист (Info), на основе словаря info (для записи используется openpyxl)
        #   Цикл по станциям:
        #       Ззпись соответствующего датафрейма на отдельный лист с кодом станции (для записи используется pandas)
        #   Закрыть файл

    def write_metrics(self, in_data: dict, metrics: dict) -> None:
        logging.info("Запись вычисленных метрик в файлы")

        info = self._collect_info(in_data)
        dfs = self._gen_dfs_metrics(metrics)

        self.write_1_file_is_1_station_all_parameters(info, dfs)
        self.write_1_file_is_1_parameter_all_stations(info, dfs)
