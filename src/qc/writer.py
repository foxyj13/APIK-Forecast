import logging
import os

from openpyxl import Workbook
import pandas as pd


class Writer:
    def __init__(self, args: dict):
        self.mode = args["main-args"]["mode"]
        self.start_date_str = args["main-args"]["start-date"]
        self.end_date_str = args["main-args"]["end-date"]
        self.output_folder = args["main-args"]["output-folder"]

        self.time_depth = args["forecast-args"]["time-depth"]
        self.time_forecast = args["forecast-args"]["time-forecast"]
        self.forecast_type = args["forecast-args"]["forecast-type"]

        self.exp_name = args["data-args"]["experiment-name"]

        self.qc_filename_prefix = (
            "apik-forecast_metrics_"
            + self.exp_name
            + "_"
            + self.forecast_type
            + "_td"
            + self.time_depth
            + "_tf"
            + self.time_forecast
        )

        self.self_metrics = ["min", "max", "mean", "med"]
        self.sub_self = [
            "obs",
            "local_td" + self.time_depth,
            "global_td" + self.time_depth,
            "local_tf" + self.time_forecast,
            "global_tf" + self.time_forecast,
        ]
        self.mutual_metrics = ["me", "mae", "rmse", "r2", "mre", "nse", "kge"]
        self.sub_mutual = [
            "local" + self.time_depth,
            "global" + self.time_depth,
            "local" + self.time_forecast,
            "global" + self.time_forecast,
        ]

    def _gen_dfs_metrics(self, metrics: dict) -> dict:

        def get_station_codes_par_names_lists() -> tuple[list, list]:
            station_codes = set()
            par_names = set()

            for now_date_str in metrics.keys():
                station_codes.update(metrics[now_date_str].keys())

                for station_code in metrics[now_date_str].keys():
                    par_names.update(metrics[now_date_str][station_code].keys())

            return list(station_codes), list(par_names)

        logging.info(
            "Формирование датафреймов со всеми оценками: 1 датафрейм = 1 станция 1 метео-параметр"
        )

        station_codes, par_names = get_station_codes_par_names_lists()

        columns = pd.MultiIndex.from_tuples(
            [(metr, sub) for metr in self.self_metrics for sub in self.sub_self]
            + [(metr, sub) for metr in self.mutual_metrics for sub in self.sub_mutual]
        )

        dfs = {}
        for station_code in station_codes:
            dfs[station_code] = {}
            for par_name in par_names:
                dfs_st_par = pd.DataFrame(columns=columns)
                # Заполнить датафрейм значениями метрик для каждой даты now_date_str, где индексом будет now_date_str, а значениями будут соответствующие метрики
                for now_date_str in metrics.keys():
                    if (
                        station_code in metrics[now_date_str]
                        and par_name in metrics[now_date_str][station_code]
                    ):
                        row_values = []
                        for metr in self.self_metrics:
                            row_values = [
                                metrics[now_date_str][station_code][par_name]["obs"][
                                    metr
                                ],
                                metrics[now_date_str][station_code][par_name]["local"][
                                    "past"
                                ][metr],
                            ]
                            if (
                                "global"
                                in metrics[now_date_str][station_code][par_name]
                            ):
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "global"
                                    ]["past"][metr]
                                )
                            else:
                                row_values.append(None)
                            row_values.append(
                                metrics[now_date_str][station_code][par_name]["local"][
                                    "future"
                                ][metr]
                            )
                            if (
                                "global"
                                in metrics[now_date_str][station_code][par_name]
                            ):
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "global"
                                    ]["future"][metr]
                                )
                            else:
                                row_values.append(None)

                        for metr in self.mutual_metrics:
                            row_values.append(
                                metrics[now_date_str][station_code][par_name]["local"][
                                    "past"
                                ][metr]
                            )
                            if (
                                "global"
                                in metrics[now_date_str][station_code][par_name]
                            ):
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "global"
                                    ]["past"][metr]
                                )
                            else:
                                row_values.append(None)
                            row_values.append(
                                metrics[now_date_str][station_code][par_name]["local"][
                                    "future"
                                ][metr]
                            )
                            if (
                                "global"
                                in metrics[now_date_str][station_code][par_name]
                            ):
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "global"
                                    ]["future"][metr]
                                )
                            else:
                                row_values.append(None)

                        dfs_st_par.loc[now_date_str] = row_values

                dfs[station_code][par_name] = dfs_st_par

        return {}

    def _collect_info(self, in_data_0: dict) -> dict:
        logging.info(
            "Сбор информации о расчетах для формирования 1-го листа с аннотацией"
        )

        info = {}

        for idx_station, station in enumerate(in_data_0["stations"]):
            st_code = station["code"]
            info[st_code] = {}
            info[st_code]["station"] = {
                "full_name": station["full_name"],
                "lat": station["lat"],
                "lon": station["lon"],
            }

            info[st_code]["parameters"] = {}
            for idx_par, par_name in enumerate(station["parameters"]):
                info[st_code]["parameters"][par_name] = {
                    "code": station["parameters"][par_name]["code"],
                    "name": station["parameters"][par_name]["name"],
                    "min": station["parameters"][par_name]["min"],
                    "max": station["parameters"][par_name]["max"],
                }

                if "prepast" in station["timeline"]:
                    #  DB
                    info[st_code]["parameters"][par_name]["data-source"] = "db"
                    info[st_code]["parameters"][par_name]["predictors"] = station[
                        "parameters"
                    ][par_name]["db_predictors"]
                    info[st_code]["parameters"][par_name]["om_parameter"] = None
                else:
                    # OM
                    info[st_code]["parameters"][par_name]["data-source"] = "om"
                    info[st_code]["parameters"][par_name]["predictors"] = station[
                        "parameters"
                    ][par_name]["om_predictors"]
                    info[st_code]["parameters"][par_name]["om_parameter"] = station[
                        "parameters"
                    ][par_name]["om_parameter"]

                info[st_code]["parameters"][par_name]["ml_models"] = []
                for model in station["parameters"][par_name]["models"]:
                    model_cfg_pars = station["parameters"][par_name]["models"][model][
                        "model_cfg"
                    ]["cfg_pars"]
                    model_cfg_type = station["parameters"][par_name]["models"][model][
                        "model_cfg"
                    ]["cfg_type"]
                    info[st_code]["parameters"][par_name]["ml_models"].append(
                        f"{model}({model_cfg_pars})[{model_cfg_type}]"
                    )

        info["config"] = {
            "mode": in_data_0["args"]["mode"],
            "forecast-type": in_data_0["args"]["forecast-type"],
            "time-depth": in_data_0["args"]["time-depth"],
            "time-forecast": in_data_0["args"]["time-forecast"],
        }
        if "prepast" in in_data_0["stations"][0]["timeline"]:
            info["config"]["om_model"] = None
        else:
            info["config"]["om_model"] = in_data_0["config_ini"]["om"]["model"]

        return info

    def write_info_sheet_to_station_file(self, wb, info, st_code):
        logging.info(
            "Запись информации о расчетах в 1-й лист файла с метриками для станции"
        )

        ws = wb.create_sheet(title="Info")

        ws["A1"] = "Станция"
        ws["A2"], ws["B2"], ws["C2"], ws["D2"] = "Код", "Название", "Широта", "Долгота"
        ws["A3"], ws["B3"], ws["C3"], ws["D3"] = (
            st_code,
            info[st_code]["station"]["full_name"],
            info[st_code]["station"]["lat"],
            info[st_code]["station"]["lon"],
        )

        ws["A5"] = "Параметры"
        (
            ws["A6"],
            ws["B6"],
            ws["C6"],
            ws["D6"],
            ws["E6"],
            ws["F6"],
            ws["G6"],
            ws["H6"],
            ws["I6"],
        ) = (
            "Код",
            "Суффикс",
            "Название",
            "Минимум",
            "Максимум",
            "Предикторы",
            "ОМ-соответствие",
            "Кол-во ML-моделей",
            "Список ML-моделей (<конфигурация>)[тип конфигурации]",
        )

        irow = 7
        for par_name, parameter in info[st_code]["parameters"].items():
            ws.cell(column=1, row=irow).value = parameter["code"]  # A
            ws.cell(column=2, row=irow).value = par_name  # B
            ws.cell(column=3, row=irow).value = parameter["name"]  # C
            ws.cell(column=4, row=irow).value = parameter["min"]  # D
            ws.cell(column=5, row=irow).value = parameter["max"]  # E
            ws.cell(column=6, row=irow).value = parameter["predictors"]  # F
            ws.cell(column=7, row=irow).value = parameter["om_parameter"]  # G
            ws.cell(column=8, row=irow).value = len(parameter["ml_models"])  # H
            ws.cell(column=9, row=irow).value = parameter["ml_models"]  # I

            irow = irow + 1

        irow = irow + 1
        ws.cell(column=1, row=irow).value = "Параметры расчета"
        (
            ws.cell(column=1, row=irow + 1).value,
            ws.cell(column=2, row=irow + 1).value,
            ws.cell(column=3, row=irow + 1).value,
            ws.cell(column=4, row=irow + 1).value,
            ws.cell(column=5, row=irow + 1).value,
        ) = (
            "Режим расчета",
            "Тип прогноза",
            "Источник данных",
            "Период обучения",
            "Период прогноза",
        )
        (
            ws.cell(column=1, row=irow + 2).value,
            ws.cell(column=2, row=irow + 2).value,
            ws.cell(column=3, row=irow + 2).value,
            ws.cell(column=4, row=irow + 2).value,
            ws.cell(column=5, row=irow + 2).value,
        ) = (
            info["config"]["mode"],
            info["config"]["forecast-type"],
            info["config"]["om_model"],
            info["config"]["time-depth"],
            info["config"]["time-forecast"],
        )

    def write_info_sheet_to_parameter_file(self, wb, info, par_name):
        logging.info(
            "Запись информации о расчетах в 1-й лист файла с метриками для параметра"
        )

        ws = wb.create_sheet(title="Info")

        ws["A1"] = "Параметр"
        (
            ws["A2"],
            ws["B2"],
            ws["C2"],
            ws["D2"],
            ws["E2"],
            ws["F2"],
            ws["G2"],
            ws["H2"],
            ws["I2"],
        ) = (
            "Коды",
            "Суффикс",
            "Название",
            "Минимум",
            "Максимум",
            "Предикторы",
            "ОМ-соответствие",
            "Кол-во ML-моделей",
            "Список ML-моделей (<конфигурация>)[тип конфигурации]",
        )
        # Строка 3: заполняется ниже

        ws["A5"] = "Станции"
        ws["A6"], ws["B6"], ws["C6"], ws["D6"] = "Код", "Название", "Широта", "Долгота"

        irow = 7
        par_codes = set()
        for st_code, station in info.items():
            if st_code != "config":
                par_codes.update(station["parameters"][par_name]["code"])

                ws.cell(column=1, row=irow).value = st_code  # A
                ws.cell(column=2, row=irow).value = station["station"]["full_name"]  # B
                ws.cell(column=3, row=irow).value = station["station"]["lat"]  # C
                ws.cell(column=4, row=irow).value = station["station"]["lon"]  # D

                irow = irow + 1

        any_st_code = list(info.keys())[0]
        (
            ws["A3"],
            ws["B3"],
            ws["C3"],
            ws["D3"],
            ws["E3"],
            ws["F3"],
            ws["G3"],
            ws["H3"],
            ws["I3"],
        ) = (
            list(par_codes),
            par_name,
            info[any_st_code][par_name]["name"],
            info[any_st_code][par_name]["min"],
            info[any_st_code][par_name]["max"],
            info[any_st_code][par_name]["predictors"],
            info[any_st_code][par_name]["om_parameter"],
            len(info[any_st_code][par_name]["ml_models"]),
            info[any_st_code][par_name]["ml_models"],
        )

        irow = irow + 1
        ws.cell(column=1, row=irow).value = "Параметры расчета"
        (
            ws.cell(column=1, row=irow + 1).value,
            ws.cell(column=2, row=irow + 1).value,
            ws.cell(column=3, row=irow + 1).value,
            ws.cell(column=4, row=irow + 1).value,
            ws.cell(column=5, row=irow + 1).value,
        ) = (
            "Режим расчета",
            "Тип прогноза",
            "Источник данных",
            "Период обучения",
            "Период прогноза",
        )
        (
            ws.cell(column=1, row=irow + 2).value,
            ws.cell(column=2, row=irow + 2).value,
            ws.cell(column=3, row=irow + 2).value,
            ws.cell(column=4, row=irow + 2).value,
            ws.cell(column=5, row=irow + 2).value,
        ) = (
            info["config"]["mode"],
            info["config"]["forecast-type"],
            info["config"]["om_model"],
            info["config"]["time-depth"],
            info["config"]["time-forecast"],
        )

    def write_1_file_is_1_station_all_parameters(self, info: dict, dfs: dict) -> None:
        logging.info(
            "Формирование серии файлов: 1 файл = 1 станция с метриками по всем метео-параметрам"
        )

        # Цикл по станциям:
        for station_code in dfs.keys():
            out_file = os.path.join(
                self.output_folder,
                self.qc_filename_prefix + "_station_" + station_code + ".xlsx",
            )

            #  Создать файл
            wb = Workbook()

            #   Сформировать 1-й лист (Info), на основе словаря info (для записи используется openpyxl)
            self.write_info_sheet_to_station_file(wb, info, station_code)
            wb.save(out_file)

            # Открыть файл с помощью pandas.ExcelWriter
            with pd.ExcelWriter(out_file, engine="openpyxl", mode="a") as writer:
                # Цикл по метео-параметрам:
                for par_name in dfs[station_code].keys():
                    # Запись датафрейма dfs[station_code][par_name] на отдельный лист с именем par_name
                    dfs[station_code][par_name].to_excel(writer, sheet_name=par_name)

    def write_1_file_is_1_parameter_all_stations(self, info: dict, dfs: dict) -> None:
        logging.info(
            "Формирование серии файлов: 1 файл = 1 метео-параметр (по имени) с метриками по станциям"
        )

        # Получить список всех метео-параметров из словаря dfs
        par_names = set()
        for station_code in dfs.keys():
            par_names.update(dfs[station_code].keys())

        # Цикл по именам метео-параметров из par_names:
        for par_name in par_names:
            out_file = os.path.join(
                self.output_folder,
                self.qc_filename_prefix + "_parameter_" + par_name + ".xlsx",
            )

            #  Создать файл
            wb = Workbook()

            #   Сформировать 1-й лист (Info), на основе словаря info (для записи используется openpyxl)
            self.write_info_sheet_to_parameter_file(wb, info, par_name)
            wb.save(out_file)

            # Открыть файл с помощью pandas.ExcelWriter
            with pd.ExcelWriter(out_file, engine="openpyxl", mode="a") as writer:
                # Цикл по станциям:
                for station_code in dfs.keys():
                    if par_name in dfs[station_code]:

                        # Запись датафрейма dfs[station_code][par_name] на отдельный лист с именем station_code
                        dfs[station_code][par_name].to_excel(
                            writer, sheet_name=station_code
                        )

    def write_metrics(self, in_data: dict, metrics: dict) -> None:
        logging.info("Запись вычисленных метрик в файлы")

        info = self._collect_info(in_data[list(in_data.keys())[0]])
        dfs = self._gen_dfs_metrics(metrics)

        self.write_1_file_is_1_station_all_parameters(info, dfs)
        self.write_1_file_is_1_parameter_all_stations(info, dfs)
