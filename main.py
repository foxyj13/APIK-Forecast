# Arshan Project
import argparse
import datetime
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
            }

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
    # Получение аргументов программы
    parser = argparse.ArgumentParser(
        description="Meteostations and model forecasts reader"
    )

    parser.add_argument(
        "--mode",
        help="Program mode (obs_plot | obs_forec_plot | forec_adj):\n\tobs_plot - observations only plot only;\n\tobs_forec_plot - observations and global forecasts plot only;\n\tforec_adj - get local forecasts and plot them and observations",
        type=str,
        choices=["obs_plot", "obs_forec_plot", "forec_adj"],
        default="obs_plot",
    )
    parser.add_argument(
        "--time-depth",
        help="Time depth for observations and/or forecasts (1d, 7d, 30d, 365d, c_yr)",
        type=str,
        choices=["1d", "7d", "30d", "365d", "c_yr"],
        default="1d",
    )
    parser.add_argument(
        "--time-forecast",
        help="Time forecast (0d, 1d, 2d, ..., 14d)",
        type=str,
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
    args = parser.parse_args()
    time_depth = args.time_depth
    time_forecast = args.time_forecast
    now_date = (
        args.now_date
    )  # datetime.datetime.strptime(args.now_date, "%Y-%m-%d").date()

    if (args.mode == "forec_adj") and (time_forecast == "0d"):
        print(
            "Program arguments ERROR: for --mode=forec_adj value for --time-forecast must be > 0d"
        )
        sys.exit(1)

    if (args.qc_gen == "yes") and (now_date == now):
        print(
            "Program arguments ERROR: for --qc-gen=yes value for --now_date must be < today date"
        )
        sys.exit(1)

    # Чтение конфигурационного файла .ini (args.config)
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

    init_logging(config)

    logging.info("Начинаем работу!")

    # Чтение перечня станций и перечня параметров для каждой станции
    stations = read_stations(main_config["stations-file"])

    # -----------------------------------------------------
    db_reader = DBReader(
        server=db_config["server"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
    )

    mode = main_config.get("mode", "")
    if mode == "interactive":
        # Это для построения интерактивных графиков.
        if main_config.get("variables", ""):
            variables = list(map(str.strip, main_config["variables"].split(",")))
        else:
            all_variables_names = set()
            for station in stations:
                all_variables_names.update(set(station["parameters"].keys()))
            variables = list(all_variables_names)

        if db_reader.connect():
            # Read stations data.
            logging.info("Считываем данные")
            all_stations = []
            for station in stations:
                station = db_reader.get_station_data(
                    station=station, time_depth=time_depth
                )
                if station:
                    all_stations.append(station)
                else:
                    logging.warning("Внимание! Какие-то проблемы. Пропускаю станцию.")
            # Plot stations data.
            logging.info("Строим интерактивные графики")
            plotter_js = PlotterJS(
                config=dict(main_config), stations=all_stations, time_depth=time_depth
            )
            plotter_js.make_plots(variables=variables)

    elif mode == "static":
        # Это для построения статичных графиков.
        logging.info("Строим статичные графики")
        plotter = Plotter(dict(main_config))
        if db_reader.connect():
            export_enabled = main_config.getboolean(
                "export-enable"
            )  # main_config["export-enable"]
            for station in stations:
                station = db_reader.get_station_data(
                    station=station, time_depth=time_depth
                )
                if station:
                    plotter.make_table(station=station)
                    plotter.make_plots(station=station, time_depth=time_depth)
                    # Экспорт в CSV (если включен)
                    if export_enabled:
                        if station:
                            plotter.export_to_csv(
                                station=station, time_depth=time_depth
                            )
                        else:
                            logging.warning(
                                "Не удалось получить данные за год для станции %s",
                                station["code"],
                            )
                else:
                    logging.warning("Внимание! Какие-то проблемы. Пропускаю станцию.")
    else:
        logging.error('Неизвестный режим: "%s".', mode)

    logging.info("Заканчиваем работу")


if __name__ == "__main__":
    main()
