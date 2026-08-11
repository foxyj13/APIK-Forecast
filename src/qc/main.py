import argparse
import logging
import os
import sys
from configparser import ConfigParser
from logging.handlers import TimedRotatingFileHandler

from reporter import Reporter


def init_logging(log_folder):
    if not os.path.isdir(log_folder):
        os.mkdir(log_folder)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(module)s.%(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            TimedRotatingFileHandler(
                filename=os.path.join(log_folder, "qc_export.log"),
                when="midnight",
                encoding="utf-8",
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )


# cases.get(in_mode, [])
# model_set = [model.strip() for model in par_model_cfg["model-set"].split(",")]


def get_args() -> dict:

    def check_qc_case(qc_case: str) -> bool:
        cases = ["need_forecast", "forecast_prepared"]

        if qc_case not in cases:
            return False

        return True

    def check_forecast_mode(fc_mode: str) -> bool:
        cases = ["forec_adj", "forec_stat"]

        if fc_mode not in cases:
            return False

        return True

    def check_forecast_type(fc_type: str) -> bool:
        cases = ["realtime", "historical"]

        if fc_type not in cases:
            return False

        return True

    parser = argparse.ArgumentParser(
        description="Observations-forecasts exporter and QC-report generator"
    )

    default_fargs = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "config", "args_qc.ini"
    )
    parser.add_argument(
        "--fargs",
        help="ini-file with input program arguments",
        type=str,
        default=default_fargs,
    )

    input_args = parser.parse_args()
    fargs = input_args.fargs

    # Чтение настроек и определение режима работы: генерация QC-отчета или Экспорт данных
    config = ConfigParser()
    config.read(fargs, encoding="utf8")

    main_args = dict(config["ARGS"])
    forecast_args = dict(config["FORECAST_ARGS"])

    # Чтение настроек прогноза
    config_forecast_file = forecast_args["config"]
    config_forecast = ConfigParser()
    config_forecast.read(config_forecast_file, encoding="utf8")

    forecast_main_config = config_forecast["main"]

    log_folder = forecast_main_config["log-folder"]
    data_folder = forecast_main_config["ml-info-folder"]
    exp_name = forecast_main_config["experiment-name"]

    # if not os.path.exists(log_folder):
    #     os.mkdir(log_folder)

    # Старт логирования
    init_logging(log_folder)
    logging.info("Начинаем работу!")

    logging.info("Проверка и корректировка заданных натроек")
    if main_args["mode"] == "qc":
        if not check_qc_case(main_args["case"]):
            logging.error(
                "Ошибочный вариант работы (case) в режиме QC: %s", main_args["case"]
            )
            return {}
    elif main_args["mode"] == "export":
        ...
    else:
        logging.error("Ошибочный режим работы: %s", main_args["mode"])
        return {}

    if not check_forecast_mode(forecast_args["mode"]):
        logging.error(
            "Указан неверный режим расчета прогноза: %s", forecast_args["mode"]
        )
        return {}

    if not check_forecast_type(forecast_args["forecast-type"]):
        logging.error(
            "Указан неверный тип прогноза: %s", forecast_args["forecast-type"]
        )
        return {}

    return {
        "main-args": main_args,
        "forecast-args": forecast_args,
        "data_args": {
            "log-folder": log_folder,
            "data-folder": data_folder,
            "experiment-name": exp_name,
        },
    }


def main():
    args = get_args()

    if not args:
        logging.error("Проверьте настройки программы в файлах .ini")
        logging.info("Остановка программы")
        sys.exit(1)

    if args["main-args"]["mode"] == "qc":
        logging.info("Запуск в режиме генерации QC-отчета")
        if args["main-args"]["case"] == "need_forecast":
            logging.info("Запуск расчета прогнозов")

            # import subprocess
            # for r in range(5):
            #     subprocess.run(f"main.py --sd {r}")

        elif args["main-args"]["case"] == "forecast_prepared":
            logging.info(
                "Расчет прогнозов не требуется. Работа с предподготовленными прогнозами"
            )

        logging.info("Запуск генерации QC-отчета")
        qc_reporter = Reporter(args)
        qc_reporter.gen_qc_report()

    if args["main-args"]["mode"] == "export":
        logging.info("Запуск экспорта данных")
        # exporter = Reporter(args)
        # exporter.export_data()


if __name__ == "main":
    main()
