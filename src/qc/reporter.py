import datetime
import logging
import pickle


class Reporter:
    def __init__(self, args: dict, now_dates: list[datetime.date]):
        self.mode = args["main-args"]["mode"]
        self.case = args["main-args"]["case"]

        self.forecast_args = args["forecast-args"]

        self.data_folder = args["data-args"]["data-folder"]
        self.exp_name = args["data-args"]["experiment-name"]

        self.output_folder = args["main-args"]["output-folder"]

        self.now_dates = now_dates

        # Формирование списка pkl-файлов

    def get_file_list(self):
        logging.info("Получение списка необходимых файлов с прогнозами")
        ...

    def gen_qc_report(self):
        logging.info("Генерация QC-отчета")
        ...


# data_files = get_file_list(...)
# if data_files:
#     logging.info("Запуск генерации QC-отчета")
#     gen_qc_report(...)
