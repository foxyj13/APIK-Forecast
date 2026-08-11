import logging
import pickle


class Reporter:
    def __init__(self, args): ...

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
