# Arshan Project

import argparse
import datetime

# from datetime import datetime
import logging
import os
import sys
from copy import deepcopy
from configparser import ConfigParser
from logging.handlers import TimedRotatingFileHandler

import openpyxl

from plotter import Plotter
from plotter_js import PlotterJS
from dbreader import DBReader
from omreader import OMReader
from validator import Validator
from adjustmenter import Adjustmenter


def read_args():
    parser = argparse.ArgumentParser(
        description="Meteostations and model forecasts reader"
    )

    parser.add_argument(
        "--mode",
        help="Program mode (obs_plot | forec_adj):\n\tobs_plot - observations only plot only;\n\tforec_adj - get local forecasts and plot them and observations",
        type=str,
        choices=["obs_plot", "forec_adj", "forec_stat"],
        default="obs_plot",
    )
    parser.add_argument(
        "--add-globforecast-plot",
        help="Should the program draw a global forecast? (no, yes)",
        type=str,
        choices=["no", "yes"],
        default="no",
    )
    parser.add_argument(
        "--time-depth",
        help="Time depth for observations and/or forecasts (1d, 3d, 7d, 14d, 30d)",
        type=str,
        choices=["1d", "3d", "7d", "14d", "30d"],
        default="1d",
    )
    parser.add_argument(
        "--time-forecast",
        help="Time forecast (0d, 1d, 3d, 7d, 14d)",
        type=str,
        choices=["0d", "1d", "3d", "7d", "14d"],
        default="0d",
    )
    parser.add_argument(
        "--qc-gen",
        help="Turn off/on QC-report generation mode (no, yes)",
        type=str,
        choices=["no", "yes"],
        default="no",
    )
    now = datetime.date.today()
    parser.add_argument(
        "--now-date",
        help="Now date for QC-report generation (yyyy-mm-dd)",
        type=str,
        default=now,
    )
    parser.add_argument(
        "--config",
        help="Configuration file (config.ini)",
        type=str,
        default="config.ini",
    )

    return parser.parse_args()


def init_logging(config):
    log_folder = config["main"]["log-folder"]
    if not os.path.isdir(log_folder):
        os.mkdir(log_folder)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(module)s.%(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            TimedRotatingFileHandler(
                filename=os.path.join(log_folder, "meteo.log"),
                when="midnight",
                encoding="utf-8",
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )


def read_stations(stations_file: str) -> list:
    wb = openpyxl.open(stations_file)
    ws_stations = wb["Станции"]
    ws_parameters = wb["Параметры"]

    all_parameters = {}
    for par_row_id in range(2, ws_parameters.max_row + 1):
        par_codes = str(ws_parameters[f"B{par_row_id}"].value).split(";")
        for par_code in par_codes:
            all_parameters[par_code] = {
                "name": ws_parameters[f"D{par_row_id}"].value,
                "code": par_code,
                "full_name": ws_parameters[f"C{par_row_id}"].value,
                "short_name": ws_parameters[f"A{par_row_id}"].value,
                "no_value": ws_parameters[f"E{par_row_id}"].value,
                "min_value": ws_parameters[f"F{par_row_id}"].value,
                "max_value": ws_parameters[f"G{par_row_id}"].value,
                "db_predictors": {
                    ttt: {}
                    for ttt in [
                        tmp.strip()
                        for tmp in str(ws_parameters[f"H{par_row_id}"].value).split(";")
                    ]
                },
                "om_parameter": ws_parameters[f"I{par_row_id}"].value,
                "om_predictors": [
                    tmp.strip()
                    for tmp in str(ws_parameters[f"J{par_row_id}"].value).split(";")
                ],
            }

    for par_code, par_code_info in all_parameters.items():
        for pred_name in par_code_info["db_predictors"]:
            pred_name_codes = []
            no_val = -999
            min_val = -999
            max_val = -999
            for pred_code, pred_info in all_parameters.items():
                if pred_info["name"] == pred_name:
                    pred_name_codes.append(pred_code)
                    no_val = pred_info["no_value"]
                    min_val = pred_info["min_value"]
                    max_val = pred_info["max_value"]
            par_code_info["db_predictors"][pred_name]["codes"] = pred_name_codes
            par_code_info["db_predictors"][pred_name]["no_value"] = no_val
            par_code_info["db_predictors"][pred_name]["min_value"] = min_val
            par_code_info["db_predictors"][pred_name]["max_value"] = max_val

    stations = []
    for st_row_id in range(2, ws_stations.max_row + 1):
        parameters = {}
        value = ws_stations[f"C{st_row_id}"].value
        if not value:
            continue
        par_codes = str(value).split(";")
        for par_code in par_codes:
            par_code = par_code.strip()
            if par_code in all_parameters:
                parameters[all_parameters[par_code]["name"]] = deepcopy(
                    all_parameters[par_code]
                )
            else:  #'Неизвестный режим: "%s".', mode
                st_name = ws_stations[f"A{st_row_id}"].value
                st_code = str(ws_stations[f"B{st_row_id}"].value)
                logging.warning(
                    "Внимание! Для станции %s (%s) отсутствует параметр в кодом %s. Пропускаю этот параметр.",
                    st_name,
                    st_code,
                    par_code,
                )
        stations.append(
            {
                "full_name": ws_stations[f"A{st_row_id}"].value,
                "code": str(ws_stations[f"B{st_row_id}"].value),
                "lat": ws_stations[f"E{st_row_id}"].value,
                "lon": ws_stations[f"F{st_row_id}"].value,
                "parameters": parameters,
            }
        )

    return stations


def main():
    # ------------ Получение аргументов программы ------------
    args = read_args()
    mode = args.mode
    time_depth = args.time_depth
    time_forecast = args.time_forecast
    add_globforecast_plot = args.add_globforecast_plot
    now_date = datetime.datetime.strptime(
        args.now_date, "%Y-%m-%d"
    ).date()  # args.now_date

    now = datetime.date.today()

    # ------------ Чтение конфигурационного файла .ini (args.config) ------------
    config = ConfigParser()
    config.read(
        os.path.join(str(os.path.dirname(__file__)), args.config), encoding="utf8"
    )
    db_config = config["DB"]
    om_config = config["OM"]
    main_config = config["main"]

    if not os.path.exists(main_config["log-folder"]):
        os.mkdir(main_config["log-folder"])

    if not os.path.exists(main_config["images-folder"]):
        os.mkdir(main_config["images-folder"])

    if not os.path.exists(main_config["web-folder"]):
        os.mkdir(main_config["web-folder"])

    if not os.path.exists(main_config["csv-folder"]):
        os.mkdir(main_config["csv-folder"])

    if not os.path.exists(main_config["ml-verbose-folder"]):
        os.mkdir(main_config["ml-verbose-folder"])

    if args.qc_gen == "yes":
        main_config["export_enable"] = "True"

    init_logging(config)
    logging.info("Начинаем работу!")

    logging.info("Проверка сочетания значений входных ключей программы")

    if int(time_depth[:-1]) < int(time_forecast[:-1]):
        time_forecast = time_depth
        logging.warning(
            "Значение time_depth (%s) должно быть больше или равно time_forecast (%s). Значение time_forecast изменено на %s",
            time_depth,
            time_forecast,
            time_depth,
        )

    if ((mode == "forec_adj") or (mode == "forec_stat")) and (time_forecast == "0d"):
        logging.error(
            "Ошибка сочетания значений входных ключей программы: при --mode=forec_adj значение для --time-forecast должно быть БОЛЬШЕ 0d"
        )
        logging.info("Остановка программы")
        sys.exit(1)

    if mode == "forec_stat":
        if add_globforecast_plot == "yes":
            logging.info(
                "Глобальный прогноз отрисован не будет, т.к. задан расчет стат. прогноза (mode=forec_stat), а не уточнение глобального прогноза (mode=forec_adj)"
            )
            add_globforecast_plot = "no"

    if (args.qc_gen == "yes") and (now_date == now):
        logging.error(
            "Ошибка сочетания значений входных ключей программы: при --qc-gen=yes значение для --now_date должно быть МЕНЬШЕ текущей даты"
        )
        logging.info("Остановка программы")
        sys.exit(1)

    # ------------ Чтение перечня станций и перечня параметров для каждой станции ------------
    stations = read_stations(main_config["stations-file"])

    # ----------- Если прогноз нужно корректировать или рассчитывать стат. прогноз: ------------
    # Чтение конфигурационного файла для ML-блока (config_ml.ini)
    if (mode == "forec_adj") or (mode == "forec_stat"):
        logging.info("Проверка наличия config_ml.ini")
        if not os.path.exists(main_config["ml-config-file"]):
            logging.error(
                "Файл %s отсутствует. Невозможно продолжать работу в режиме корректировка прогнозов (mode = %s)",
                main_config["ml-config-file"],
                mode,
            )
            logging.info("Остановка программы")
            sys.exit(1)

        logging.info("Считывание информации из %s", main_config["ml-config-file"])
        config_ml = ConfigParser()
        config_ml.read(
            os.path.join(str(os.path.dirname(__file__)), main_config["ml-config-file"]),
            encoding="utf8",
        )
        if not config_ml:
            logging.error(
                "Не удалось прочитать файл %s. Проверьте формат и структуру файла",
                main_config["ml-config-file"],
            )
            logging.info("Остановка программы")
            sys.exit(1)

        ml_adjust = Adjustmenter(
            config=config_ml,
            now_date=now_date,
            time_depth=time_depth,
            time_forecast=time_forecast,
            verbose=main_config["ml-verbose"],
            verbose_dir=main_config["ml-verbose-folder"],
        )

    # ------------ Чтение данных наблюдений ------------
    db_reader = DBReader(
        server=db_config["server"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
    )

    if db_reader.connect():
        logging.info("Считываем данные наблюдений")
        dell_stations = []
        for idx, station in enumerate(stations):
            station = db_reader.get_station_data(station=station, time_depth=time_depth)
            if not station:
                dell_stations.append(idx)
                logging.warning("Внимание! Какие-то проблемы. Пропускаю станцию.")

        if dell_stations:
            logging.info(
                "Удаление из рассмотрения %d станций, наблюдения для которых считать не удалось: %s",
                len(dell_stations),
                [
                    f"{stations[idx]['full_name']} ({stations[idx]['code']})"
                    for idx in dell_stations
                ],
            )
            for idx in sorted(dell_stations, reverse=True):
                del stations[idx]

        if not stations:
            logging.info(
                "Нет ни одной станции для рассмотрения. Возможная причина: 1) ни одна станция не указана для рассмотрения; 2) ни по одной станции ни для одного параметра не удалось считать данные"
            )
            sys.exit(1)

    if ((mode == "forec_adj") or (mode == "forec_stat")) or (
        add_globforecast_plot == "yes"
    ):
        # ------------ Чтение глобальных прогнозов ------------
        om_reader = OMReader(url=om_config["url"], model=om_config["model"])

        if om_reader.connect():
            logging.info("Считываем глобальные прогнозы")

            # ------------ Чтение глобальных прогнозов ------------
            for station in stations:
                status = False

                if mode == "forec_adj":
                    status, station = om_reader.get_model_data(
                        station=station,
                        time_depth=time_depth,
                        time_forecast=time_forecast,
                        now_date=now_date,
                    )

                if not status:
                    logging.error("Глобальный прогноз не используется")
                    status, station = db_reader.get_station_predictors(
                        station=station,
                        time_depth=time_depth,
                        time_forecast=time_forecast,
                    )

                    if not status:
                        logging.error(
                            "Предикторы для статистического прогноза не получены. Остановка программы"
                        )
                        sys.exit(1)

            # ------------ Если прогноз нужно корректировать или рассчитывать стат прогноз ------------
            if (mode == "forec_adj") or (mode == "forec_stat"):
                logging.info("Формируем локальные прогнозы")

                for station in stations:
                    # ------------ Корректировка глобальных прогнозов или расчет стат прогноза (ML-блок) ------------
                    #       (локальные прогнозы)
                    station = ml_adjust.get_local_forecast(station)

                # ------------ Вывод результата: отрисовка, экспорт, html ------------
                if add_globforecast_plot == "yes":
                    # Отрисовка наблюдения + локальный (уточненный) прогноз + глобальный (сырой) прогноз
                    logging.info(
                        "Строим статичные графики: наблюдения + локальный (уточненный) прогноз + глобальный (сырой) прогноз"
                    )

                    plotter = Plotter(
                        dict(main_config), glob_forecast=True, local_forecast=True
                    )
                else:
                    # Отрисовка наблюдения + локальный (уточненный) прогноз
                    logging.info(
                        "Строим статичные графики: наблюдения + локальный прогноз"
                    )

                    plotter = Plotter(
                        dict(main_config), glob_forecast=False, local_forecast=True
                    )
            else:
                # Отрисовка наблюдения + глобальный (сырой) прогноз
                logging.info(
                    "Строим статичные графики: наблюдения + глобальный (сырой) прогноз"
                )

                plotter = Plotter(
                    dict(main_config), glob_forecast=True, local_forecast=False
                )

            for station in stations:
                plotter.make_table_forecast(station=station)
                plotter.make_plots_forecast(
                    station=station,
                    time_depth=time_depth,
                    time_forecast=time_forecast,
                )

                # # Экспорт в CSV (если включен в congig.ini)
                # #   Проверка на включенность опции внутри самой функции export_to_csv
                # plotter.export_to_csv_forecast(
                #     station=station,
                #     time_depth=time_depth,
                #     time_forecast=time_forecast,
                # )

            # ------------ Расчет метрик ------------
            validator = Validator(time_depth=time_depth, time_forecast=time_forecast)
            logging.info("Рассчитываем метрики по имеющимся данным")
            for station in stations:
                station = validator.get_metrics(station)

        else:
            logging.error("Не удалось получить глобальные прогнозы!")

    else:
        # ------------ Отрисовка только наблюдений, экспорт, html ------------
        # all_stations = []
        # for station in stations:
        #     if station:
        #         all_stations.append(station)
        #     else:
        #         logging.warning("Внимание! Какие-то проблемы. Пропускаю станцию.")
        all_stations = stations

        plot_mode = main_config.get("mode", "")
        if plot_mode == "interactive":
            # Построение интерактивных графиков
            # Выбор перерменных для отрисовки (если указаны в config.ini, то: берем их; иначе: все)
            if main_config.get("variables", ""):
                variables = list(map(str.strip, main_config["variables"].split(",")))
            else:
                all_variables_names = set()
                for station in stations:
                    all_variables_names.update(set(station["parameters"].keys()))
                variables = list(all_variables_names)

            if all_stations:
                # Отрисовка данных
                logging.info("Строим интерактивные графики")
                plotter_js = PlotterJS(
                    config=dict(main_config),
                    stations=all_stations,
                    time_depth=time_depth,
                )
                plotter_js.make_plots(variables=variables)

        elif plot_mode == "static":
            # Построение статичных графиков
            logging.info("Строим статичные графики")
            plotter = Plotter(dict(main_config))
            if all_stations:
                for station in all_stations:
                    plotter.make_table(station=station)
                    plotter.make_plots(station=station, time_depth=time_depth)

                    # Экспорт в CSV (если включен в congig.ini)
                    #   Проверка на включенность опции внутри самой функции export_to_csv
                    plotter.export_to_csv(station=station, time_depth=time_depth)
        else:
            logging.error('Неизвестный режим отрисовки: "%s".', plot_mode)

    logging.info("Заканчиваем работу")


if __name__ == "__main__":
    main()
