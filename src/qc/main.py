import argparse
import datetime
import logging
import math
import os
import sys
import subprocess
from configparser import ConfigParser
from logging.handlers import TimedRotatingFileHandler

from joblib import Parallel, delayed

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


def init() -> dict:

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

    if not os.path.exists(log_folder):
        os.mkdir(log_folder)

    if not os.path.exists(main_args["output-folder"]):
        os.mkdir(main_args["output-folder"])

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

        if int(forecast_args["time-depth"][:-1]) <= int(
            forecast_args["time-forecast"][:-1]
        ):
            logging.error(
                "В режиме QC период обучения (time-depth) должен быть строго больше периода прогноза (time-forecast)"
            )
            return {}

        if int(main_args["step-date"][:-1]) > int(forecast_args["time-depth"][:-1]):
            logging.warning(
                "Шаг расчета QC-отчета (step-date = %s) превышает период обучения (time-depth = %s): значение step-date будет заменено на time-depth",
                main_args["step-date"],
                forecast_args["time-depth"],
            )
            main_args["step-date"] = forecast_args["time-depth"]

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

    if (
        main_args["mode"] == "qc" and main_args["case"] == "forecast_prepared"
    ) or main_args["mode"] == "export":
        if not os.path.exists(data_folder):
            logging.error(
                "Неверно указана или отсутствует директория с данными (с pkl-файлами): %s",
                data_folder,
            )
            return {}

    return {
        "main-args": main_args,
        "forecast-args": forecast_args,
        "data-args": {
            # "log-folder": log_folder,
            "data-folder": data_folder,
            "experiment-name": exp_name,
        },
    }


def run_forecast(forecast_main_program: str, args: dict, now_date_str: str) -> bool:

    logging.info("Расчет прогнозов от %s", now_date_str)

    try:
        run_list = [
            sys.executable,
            forecast_main_program,
            "--mode",
            args["forecast-args"]["mode"],
            "--add-globforecast-plot",
            args["forecast-args"]["add-globforecast-plot"],
            "--time-depth",
            args["forecast-args"]["time-depth"],
            "--time-forecast",
            args["forecast-args"]["time-forecast"],
            "--forecast-type",
            args["forecast-args"]["forecast-type"],
            "--now-date",
            now_date_str,
            "--config",
            args["forecast-args"]["config"],
        ]
        result = subprocess.run(
            run_list,
            capture_output=True,  # Captures stdout and stderr
            text=True,  # Returns strings instead of bytes
            check=True,  # Throws CalledProcessError if the script fails
        )

        logging.info("Успешно")

    except subprocess.CalledProcessError as e:
        logging.error("Script failed with exit code: %s", e.returncode)
        logging.error("Error output: %s", e.stderr)


def main():
    args = init()

    if not args:
        logging.error("Проверьте настройки программы в файлах .ini")
        logging.info("Остановка программы")
        sys.exit(1)

    if args["main-args"]["mode"] == "qc":
        logging.info("Запуск в режиме генерации QC-отчета")

        start_date = datetime.datetime.strptime(
            args["main-args"]["start-date"], "%Y-%m-%d"
        ).date()
        end_date = datetime.datetime.strptime(
            args["main-args"]["end-date"], "%Y-%m-%d"
        ).date()
        step_days = int(args["main-args"]["step-date"][:-1])

        n_steps = math.ceil((end_date - start_date).days / step_days) + 1

        now_dates = [
            start_date + datetime.timedelta(days=step_days * x) for x in range(n_steps)
        ]
        # Добавление дополнительных прогнозов, чтобы было достаточно наблюдений для оценки качества
        # Сделать словарь соответствия целевого прогноза и прогноза с наблюдениями
        # Если для каких-то целевых прогнозов нет прогнозов с наблюдениями, то добавить их в расчет и проверку наличия
        date_forec_obs = {}
        for now_date in now_dates:
            now_dates_with_obs = [
                now_date + datetime.timedelta(days=dd)
                for dd in range(
                    int(args["forecast-args"]["time-forecast"][:-1]) + 1,
                    int(args["forecast-args"]["time-depth"][:-1]) + 1,
                    1,
                )
            ]
            if not now_dates_with_obs:
                now_dates_with_obs = [
                    now_date
                    + datetime.timedelta(
                        days=int(args["forecast-args"]["time-depth"][:-1]) + 1
                    )
                ]
            obs_in_now_dates = set(now_dates) & set(now_dates_with_obs)
            date_forec_obs[str(now_date)] = (
                str(list(obs_in_now_dates)[0])
                if obs_in_now_dates
                else str(now_dates_with_obs[0])
            )

        if args["main-args"]["case"] == "need_forecast":
            logging.info("Запуск расчета прогнозов")

            forecast_main_program = os.path.join("src", "forecast", "main.py")

            # Распараллеливание цикла запуска расчета прогнозов
            # delayed_calls = [
            #     delayed(run_forecast)(forecast_main_program, args, now_date)
            #     for now_date in now_dates
            # ]
            # result = Parallel(j_jobs=-1)(delayed_calls)

            # Последовательный запуск расчета прогнозов
            dates_forec_list = sorted(
                list(set(date_forec_obs.keys()) | set(date_forec_obs.values()))
            )
            for now_date in dates_forec_list:
                run_forecast(forecast_main_program, args, now_date)

        elif args["main-args"]["case"] == "forecast_prepared":
            logging.info(
                "Расчет прогнозов не требуется. Работа с предподготовленными прогнозами"
            )

        logging.info("Запуск генерации QC-отчета")
        qc_reporter = Reporter(args, date_forec_obs)
        qc_reporter.gen_qc_report()

    if args["main-args"]["mode"] == "export":
        logging.info("Запуск экспорта данных")
        # exporter = Reporter(args)
        # exporter.export_data()

    logging.info("Заканчиваем работу")


if __name__ == "__main__":
    main()
