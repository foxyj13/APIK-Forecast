import logging
import os

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
import pandas as pd

FT_BOLD = Font(bold=True)
FT_BOLD_BLUE = Font(color="000066CC", bold=True)
COL_WIDHT = 12
COL_WIDHT_2X = 24


class Writer:
    def __init__(self, args: dict):
        self.mode = args["main-args"]["mode"]
        self.start_date_str = args["main-args"]["start-date"]
        self.end_date_str = args["main-args"]["end-date"]
        self.step_date_str = args["main-args"]["step-date"]
        self.output_folder = args["main-args"]["output-folder"]

        self.time_depth = args["forecast-args"]["time-depth"]
        self.time_forecast = args["forecast-args"]["time-forecast"]
        self.forecast_type = args["forecast-args"]["forecast-type"]

        self.exp_name = args["data-args"]["experiment-name"]

        self.metrics_filename_prefix = (
            "apik-forecast_metrics_"
            + self.exp_name
            + "_"
            + self.start_date_str
            + "_"
            + self.end_date_str
            + "_step"
            + self.step_date_str
            + "_"
            + self.forecast_type
            + "_td"
            + self.time_depth
            + "_tf"
            + self.time_forecast
        )

        self.data_filename_prefix = (
            "apik-forecast_data_"
            + self.exp_name
            + "_"
            + self.start_date_str
            + "_"
            + self.end_date_str
            + "_step"
            + self.step_date_str
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
            "loc_td" + self.time_depth,
            "glob_td" + self.time_depth,
            "loc_tf" + self.time_forecast,
            "glob_tf" + self.time_forecast,
        ]
        self.mutual_metrics = ["me", "mae", "rmse", "r2", "mre", "nse", "kge"]
        self.sub_mutual = [
            "loc_td" + self.time_depth,
            "glob_td" + self.time_depth,
            "loc_tf" + self.time_forecast,
            "glob_tf" + self.time_forecast,
        ]

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
                    "min": station["parameters"][par_name]["min_value"],
                    "max": station["parameters"][par_name]["max_value"],
                }

                if "prepast" in station["timeline"] and station["timeline"]["prepast"]:
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
            "forecast-type": in_data_0["args"]["forecast_type"],
            "time-depth": in_data_0["args"]["time_depth"],
            "time-forecast": in_data_0["args"]["time_forecast"],
        }
        if (
            "prepast" in in_data_0["stations"][0]["timeline"]
            and in_data_0["stations"][0]["timeline"]["prepast"]
        ):
            info["config"]["om_model"] = None
        else:
            info["config"]["om_model"] = in_data_0["config_ini"]["om"]["model"]

        return info

    def _collect_ml_models_info(self, in_data: dict, now_dates: list) -> dict:
        logging.info(
            "Формирование датафреймов с перечнем и характеристиками ML-моделей для записи в файлы"
        )

        dict_ml_models = {}

        for now_date in now_dates:
            dict_ml_models[now_date] = {}
            for station in in_data[now_date]["stations"]:
                station_code = station["code"]
                if station_code not in dict_ml_models[now_date]:
                    dict_ml_models[now_date][station_code] = {}
                for par_name, par_info in station["parameters"].items():
                    if par_name not in dict_ml_models[now_date][station_code]:
                        dict_ml_models[now_date][station_code][par_name] = {}
                    dict_ml_models[now_date][station_code][par_name] = "; ".join(
                        [
                            f"{model_name}({model_info['model_cfg']['cfg_pars']})[{model_info['model_cfg']['cfg_type']}]"
                            for model_name, model_info in par_info["models"].items()
                        ]
                    )

        return dict_ml_models

    # exp_data =
    # { "stations": {
    #   "code": {"full_name", "lat", "lon",
    #       "parameters": {
    #           <par_name>: {"code", "full_name", "om_parameter",
    #                       "obs": [float, ...],
    #                       "local": {"past": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}
    #                               "future": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}},
    #                       "global": {"past": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}
    #                                "future": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}}

    #           }
    #       }
    #   }, ...
    # },
    #  "obs_timeline": [datetime, ...] # сгенерирован нужный
    # }
    def _gen_dfs_data(self, exp_data: dict, now_dates: list) -> dict:
        logging.info(
            "Формирование датафреймов с данными: 1 датафрейм = 1 станция 1 метео-параметр"
        )
        col_names = now_dates
        col_subnames = [
            "loc_td" + self.time_depth,
            "loc_tf" + self.time_forecast,
            "glob_td" + self.time_depth,
            "glob_tf" + self.time_forecast,
        ]
        columns = pd.MultiIndex.from_tuples(
            [("obs", "obs")]
            + [(col, subcol) for col in col_names for subcol in col_subnames]
        )

        indeces = [
            str(tl_date.replace(tzinfo=None)) for tl_date in exp_data["obs_timeline"]
        ]

        dfs = {}

        for station_code, station_data in exp_data["stations"].items():
            dfs[station_code] = {}
            for par_name, par_data in station_data["parameters"].items():
                dfs_st_par = pd.DataFrame(columns=columns, index=indeces)

                # Заполнение датафрейма
                dfs_st_par.loc[indeces, ("obs", "obs")] = par_data["obs"]

                for now_date in now_dates:
                    idxs = [
                        str(tl_date.replace(tzinfo=None))
                        for tl_date in par_data["local"]["past"][now_date]["timeline"]
                    ]
                    dfs_st_par.loc[idxs, (now_date, col_subnames[0])] = par_data[
                        "local"
                    ]["past"][now_date]["data"]

                    idxs = [
                        str(tl_date.replace(tzinfo=None))
                        for tl_date in par_data["local"]["future"][now_date]["timeline"]
                    ]
                    dfs_st_par.loc[idxs, (now_date, col_subnames[1])] = par_data[
                        "local"
                    ]["future"][now_date]["data"]

                    idxs = [
                        str(tl_date.replace(tzinfo=None))
                        for tl_date in par_data["global"]["past"][now_date]["timeline"]
                    ]
                    dfs_st_par.loc[idxs, (now_date, col_subnames[2])] = par_data[
                        "global"
                    ]["past"][now_date]["data"]

                    idxs = [
                        str(tl_date.replace(tzinfo=None))
                        for tl_date in par_data["global"]["future"][now_date][
                            "timeline"
                        ]
                    ]
                    dfs_st_par.loc[idxs, (now_date, col_subnames[3])] = par_data[
                        "global"
                    ]["future"][now_date]["data"]

                dfs[station_code][par_name] = dfs_st_par

        return dfs

    def _gen_dfs_metrics(self, metrics: dict) -> dict:

        # def get_station_codes_par_names_lists() -> tuple[list, list]:
        #     station_codes = set()
        #     par_names = set()

        #     for now_date_str in metrics.keys():
        #         station_codes.update(metrics[now_date_str].keys())

        #         for station_code in metrics[now_date_str].keys():
        #             par_names.update(metrics[now_date_str][station_code].keys())

        #     return sorted(list(station_codes)), sorted(list(par_names))

        def get_station_codes_par_names() -> dict[str, list[str]]:
            station_pars = {}

            for now_date_str, stations in metrics.items():
                for station_code, parameters in stations.items():
                    if station_code not in station_pars:
                        station_pars[station_code] = set()
                    station_pars[station_code].update(parameters.keys())

            for station_code, par_names in station_pars.items():
                par_names = sorted(list(par_names))

            return station_pars

        logging.info(
            "Формирование датафреймов со всеми оценками: 1 датафрейм = 1 станция 1 метео-параметр"
        )

        station_parameters = get_station_codes_par_names()

        columns = pd.MultiIndex.from_tuples(
            [(metr, sub) for metr in self.self_metrics for sub in self.sub_self]
            + [(metr, sub) for metr in self.mutual_metrics for sub in self.sub_mutual]
        )

        dfs = {}
        for station_code, par_names in station_parameters.items():
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
                            row_values.append(
                                metrics[now_date_str][station_code][par_name]["obs"][
                                    metr
                                ]
                            )

                            if metrics[now_date_str][station_code][par_name]["local"][
                                "past"
                            ]:
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "local"
                                    ]["past"][metr]
                                )
                            else:
                                row_values.append(None)

                            if (
                                "global"
                                in metrics[now_date_str][station_code][par_name]
                            ) and (
                                metrics[now_date_str][station_code][par_name]["global"][
                                    "past"
                                ]
                            ):
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "global"
                                    ]["past"][metr]
                                )
                            else:
                                row_values.append(None)

                            if metrics[now_date_str][station_code][par_name]["local"][
                                "future"
                            ]:
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "local"
                                    ]["future"][metr]
                                )
                            else:
                                row_values.append(None)

                            if (
                                "global"
                                in metrics[now_date_str][station_code][par_name]
                            ) and (
                                metrics[now_date_str][station_code][par_name]["global"][
                                    "future"
                                ]
                            ):
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "global"
                                    ]["future"][metr]
                                )
                            else:
                                row_values.append(None)

                        for metr in self.mutual_metrics:
                            if metrics[now_date_str][station_code][par_name]["local"][
                                "past"
                            ]:
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "local"
                                    ]["past"][metr]
                                )
                            else:
                                row_values.append(None)

                            if (
                                "global"
                                in metrics[now_date_str][station_code][par_name]
                            ) and metrics[now_date_str][station_code][par_name][
                                "global"
                            ][
                                "past"
                            ]:
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "global"
                                    ]["past"][metr]
                                )
                            else:
                                row_values.append(None)

                            if metrics[now_date_str][station_code][par_name]["local"][
                                "future"
                            ]:
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "local"
                                    ]["future"][metr]
                                )
                            else:
                                row_values.append(None)

                            if (
                                "global"
                                in metrics[now_date_str][station_code][par_name]
                            ) and metrics[now_date_str][station_code][par_name][
                                "global"
                            ][
                                "future"
                            ]:
                                row_values.append(
                                    metrics[now_date_str][station_code][par_name][
                                        "global"
                                    ]["future"][metr]
                                )
                            else:
                                row_values.append(None)

                        dfs_st_par.loc[now_date_str] = row_values

                dfs[station_code][par_name] = dfs_st_par

        return dfs

    def _write_info_sheet_to_station_file(self, wb, info, st_code):
        logging.info(
            "Запись информации о расчетах в файл с метриками для станции %s", st_code
        )

        ws = wb.create_sheet(title="Info", index=0)

        ws.column_dimensions["A"].width = COL_WIDHT
        ws.column_dimensions["B"].width = COL_WIDHT
        ws.column_dimensions["C"].width = COL_WIDHT
        ws.column_dimensions["D"].width = COL_WIDHT
        ws.column_dimensions["E"].width = COL_WIDHT
        ws.column_dimensions["F"].width = COL_WIDHT_2X
        ws.column_dimensions["G"].width = COL_WIDHT_2X
        # ws.column_dimensions["H"].width = COL_WIDHT
        # ws.column_dimensions["I"].width = COL_WIDHT

        ws["A1"] = "QC-отчет для периода:"
        ws["A1"].font = FT_BOLD_BLUE

        ws["A2"], ws["B2"], ws["C2"] = "Начало", "Конец", "Шаг"
        ws["A2"].font, ws["B2"].font, ws["C2"].font = FT_BOLD, FT_BOLD, FT_BOLD

        ws["A3"], ws["B3"], ws["C3"] = (
            self.start_date_str,
            self.end_date_str,
            self.step_date_str,
        )

        ws["A5"] = "Станция"
        ws["A5"].font = FT_BOLD_BLUE

        ws["A6"], ws["B6"], ws["C6"], ws["D6"] = "Код", "Название", "Широта", "Долгота"
        ws["A6"].font, ws["B6"].font, ws["C6"].font, ws["D6"].font = (
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
        )

        ws["A7"], ws["B7"], ws["C7"], ws["D7"] = (
            st_code,
            info[st_code]["station"]["full_name"],
            info[st_code]["station"]["lat"],
            info[st_code]["station"]["lon"],
        )

        ws["A9"] = "Параметры"
        ws["A9"].font = FT_BOLD_BLUE

        (
            ws["A10"],
            ws["B10"],
            ws["C10"],
            ws["D10"],
            ws["E10"],
            ws["F10"],
            ws["G10"],
            # ws["H10"],
            # ws["I10"],
        ) = (
            "Код",
            "Суффикс",
            "Название",
            "Минимум",
            "Максимум",
            "Предикторы",
            "ОМ-соответствие",
            # "Кол-во ML-моделей",
            # "Список ML-моделей (<конфигурация>)[тип конфигурации]",
        )
        (
            ws["A10"].font,
            ws["B10"].font,
            ws["C10"].font,
            ws["D10"].font,
            ws["E10"].font,
            ws["F10"].font,
            ws["G10"].font,
            # ws["H10"].font,
            # ws["I10"].font,
        ) = (
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            # FT_BOLD,
            # FT_BOLD,
        )

        irow = 11
        for par_name, parameter in info[st_code]["parameters"].items():
            ws.cell(column=1, row=irow).value = parameter["code"]  # A
            ws.cell(column=2, row=irow).value = par_name  # B
            ws.cell(column=3, row=irow).value = parameter["name"]  # C
            ws.cell(column=4, row=irow).value = parameter["min"]  # D
            ws.cell(column=5, row=irow).value = parameter["max"]  # E
            ws.cell(column=6, row=irow).value = "; ".join(parameter["predictors"])  # F
            ws.cell(column=7, row=irow).value = parameter["om_parameter"]  # G
            # ws.cell(column=8, row=irow).value = len(parameter["ml_models"])  # H
            # ws.cell(column=9, row=irow).value = "; ".join(parameter["ml_models"])  # I

            irow = irow + 1

        irow = irow + 1
        ws.cell(column=1, row=irow).value = "Параметры расчета"
        ws.cell(column=1, row=irow).font = FT_BOLD_BLUE

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
            ws.cell(column=1, row=irow + 1).font,
            ws.cell(column=2, row=irow + 1).font,
            ws.cell(column=3, row=irow + 1).font,
            ws.cell(column=4, row=irow + 1).font,
            ws.cell(column=5, row=irow + 1).font,
        ) = (
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
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

        irow = irow + 4
        ws.cell(column=1, row=irow).value = "Метрики"
        ws.cell(column=1, row=irow).font = FT_BOLD_BLUE

        (
            ws.cell(column=1, row=irow + 1).value,
            ws.cell(column=1, row=irow + 1).font,
            ws.cell(column=2, row=irow + 1).value,
        ) = ("min", FT_BOLD, "Минимальное значение")
        (
            ws.cell(column=1, row=irow + 2).value,
            ws.cell(column=1, row=irow + 2).font,
            ws.cell(column=2, row=irow + 2).value,
        ) = ("max", FT_BOLD, "Максимальное значение")
        (
            ws.cell(column=1, row=irow + 3).value,
            ws.cell(column=1, row=irow + 3).font,
            ws.cell(column=2, row=irow + 3).value,
        ) = ("mean", FT_BOLD, "Среднее значение")
        (
            ws.cell(column=1, row=irow + 4).value,
            ws.cell(column=1, row=irow + 4).font,
            ws.cell(column=2, row=irow + 4).value,
        ) = ("med", FT_BOLD, "Медианное значение")

        (
            ws.cell(column=1, row=irow + 5).value,
            ws.cell(column=1, row=irow + 5).font,
            ws.cell(column=2, row=irow + 5).value,
        ) = ("me", FT_BOLD, "Средняя ошибка")
        (
            ws.cell(column=1, row=irow + 6).value,
            ws.cell(column=1, row=irow + 6).font,
            ws.cell(column=2, row=irow + 6).value,
        ) = ("mae", FT_BOLD, "Средняя абсолютная ошибка")
        (
            ws.cell(column=1, row=irow + 7).value,
            ws.cell(column=1, row=irow + 7).font,
            ws.cell(column=2, row=irow + 7).value,
        ) = ("rmse", FT_BOLD, "Среднеквадратическая ошибка")
        (
            ws.cell(column=1, row=irow + 8).value,
            ws.cell(column=1, row=irow + 8).font,
            ws.cell(column=2, row=irow + 8).value,
        ) = ("r2", FT_BOLD, "Коэффициент детерминации")
        (
            ws.cell(column=1, row=irow + 9).value,
            ws.cell(column=1, row=irow + 9).font,
            ws.cell(column=2, row=irow + 9).value,
        ) = ("mre", FT_BOLD, "Средняя относительная ошибка (она же MAPE)")
        (
            ws.cell(column=1, row=irow + 10).value,
            ws.cell(column=1, row=irow + 10).font,
            ws.cell(column=2, row=irow + 10).value,
        ) = ("nse", FT_BOLD, "Коэффициент эффективности Нэша-Сатклиффа")
        (
            ws.cell(column=1, row=irow + 11).value,
            ws.cell(column=1, row=irow + 11).font,
            ws.cell(column=2, row=irow + 11).value,
        ) = ("kge", FT_BOLD, "Коэффициент эффективности Клинга-Гупты")

        irow = irow + 13
        ws.cell(column=1, row=irow).value = "Данные"
        ws.cell(column=1, row=irow).font = FT_BOLD_BLUE
        (
            ws.cell(column=1, row=irow + 1).value,
            ws.cell(column=1, row=irow + 1).font,
            ws.cell(column=2, row=irow + 1).value,
        ) = ("obs", FT_BOLD, "Наблюдения из БД ИМКЭС")
        (
            ws.cell(column=1, row=irow + 2).value,
            ws.cell(column=1, row=irow + 2).font,
            ws.cell(column=2, row=irow + 2).value,
        ) = (
            "loc_td<X>d",
            FT_BOLD,
            "Локальный прогноз на периоде обучения из <X> дней (time-depth=<X>d)",
        )
        (
            ws.cell(column=1, row=irow + 3).value,
            ws.cell(column=1, row=irow + 3).font,
            ws.cell(column=2, row=irow + 3).value,
        ) = (
            "glob_td<X>d",
            FT_BOLD,
            "Глобальный прогноз на периоде обучения из <X> дней (time-depth=<X>d)",
        )
        (
            ws.cell(column=1, row=irow + 4).value,
            ws.cell(column=1, row=irow + 4).font,
            ws.cell(column=2, row=irow + 4).value,
        ) = (
            "loc_tf<Y>d",
            FT_BOLD,
            "Локальный прогноз вперед от текущей даты из <Y> дней (time-forecast=<Y>d)",
        )
        (
            ws.cell(column=1, row=irow + 5).value,
            ws.cell(column=1, row=irow + 5).font,
            ws.cell(column=2, row=irow + 5).value,
        ) = (
            "glob_tf<Y>d",
            FT_BOLD,
            "Глобальный прогноз вперед от текущей даты из <Y> дней (time-forecast=<Y>d)",
        )

    def _write_info_sheet_to_parameter_file(self, wb, info, par_name):
        logging.info(
            "Запись информации о расчетах в файл с метриками для параметра %s", par_name
        )

        ws = wb.create_sheet(title="Info", index=0)

        ws.column_dimensions["A"].width = COL_WIDHT
        ws.column_dimensions["B"].width = COL_WIDHT
        ws.column_dimensions["C"].width = COL_WIDHT
        ws.column_dimensions["D"].width = COL_WIDHT
        ws.column_dimensions["E"].width = COL_WIDHT
        ws.column_dimensions["F"].width = COL_WIDHT_2X
        ws.column_dimensions["G"].width = COL_WIDHT_2X
        # ws.column_dimensions["H"].width = COL_WIDHT
        # ws.column_dimensions["I"].width = COL_WIDHT

        ws["A1"] = "QC-отчет для периода:"
        ws["A1"].font = FT_BOLD_BLUE

        ws["A2"], ws["B2"], ws["C2"] = "Начало", "Конец", "Шаг"
        ws["A2"].font, ws["B2"].font, ws["C2"].font = FT_BOLD, FT_BOLD, FT_BOLD

        ws["A3"], ws["B3"], ws["C3"] = (
            self.start_date_str,
            self.end_date_str,
            self.step_date_str,
        )

        ws["A5"] = "Параметр"
        ws["A5"].font = FT_BOLD_BLUE

        (
            ws["A6"],
            ws["B6"],
            ws["C6"],
            ws["D6"],
            ws["E6"],
            ws["F6"],
            ws["G6"],
            # ws["H6"],
            # ws["I6"],
        ) = (
            "Коды",
            "Суффикс",
            "Название",
            "Минимум",
            "Максимум",
            "Предикторы",
            "ОМ-соответствие",
            # "Кол-во ML-моделей",
            # "Список ML-моделей (<конфигурация>)[тип конфигурации]",
        )
        (
            ws["A6"].font,
            ws["B6"].font,
            ws["C6"].font,
            ws["D6"].font,
            ws["E6"].font,
            ws["F6"].font,
            ws["G6"].font,
            # ws["H6"].font,
            # ws["I6"].font,
        ) = (
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            # FT_BOLD,
            # FT_BOLD,
        )
        # Строка 7: заполняется ниже

        ws["A9"] = "Станции"
        ws["A9"].font = FT_BOLD_BLUE

        ws["A10"], ws["B10"], ws["C10"], ws["D10"] = (
            "Код",
            "Название",
            "Широта",
            "Долгота",
        )
        ws["A10"].font, ws["B10"].font, ws["C10"].font, ws["D10"].font = (
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
        )

        irow = 11
        par_codes = set()
        # par_models = set()
        for st_code, station in info.items():
            if st_code != "config":
                if par_name in station["parameters"]:
                    any_st_code = st_code
                    par_codes.add(station["parameters"][par_name]["code"])
                    # par_models.add(station["parameters"][par_name]["ml_models"])

                    ws.cell(column=1, row=irow).value = st_code  # A
                    ws.cell(column=2, row=irow).value = station["station"][
                        "full_name"
                    ]  # B
                    ws.cell(column=3, row=irow).value = station["station"]["lat"]  # C
                    ws.cell(column=4, row=irow).value = station["station"]["lon"]  # D

                    irow = irow + 1

        (
            ws["A7"],
            ws["B7"],
            ws["C7"],
            ws["D7"],
            ws["E7"],
            ws["F7"],
            ws["G7"],
            # ws["H7"],
            # ws["I7"],
        ) = (
            "; ".join(list(par_codes)),
            par_name,
            info[any_st_code]["parameters"][par_name]["name"],
            info[any_st_code]["parameters"][par_name]["min"],
            info[any_st_code]["parameters"][par_name]["max"],
            "; ".join(info[any_st_code]["parameters"][par_name]["predictors"]),
            info[any_st_code]["parameters"][par_name]["om_parameter"],
            # len(info[any_st_code]["parameters"][par_name]["ml_models"]),
            # "; ".join(list(par_models)),
        )

        irow = irow + 1
        ws.cell(column=1, row=irow).value = "Параметры расчета"
        ws.cell(column=1, row=irow).font = FT_BOLD_BLUE

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
            ws.cell(column=1, row=irow + 1).font,
            ws.cell(column=2, row=irow + 1).font,
            ws.cell(column=3, row=irow + 1).font,
            ws.cell(column=4, row=irow + 1).font,
            ws.cell(column=5, row=irow + 1).font,
        ) = (
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
            FT_BOLD,
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

        irow = irow + 4
        ws.cell(column=1, row=irow).value = "Метрики"
        ws.cell(column=1, row=irow).font = FT_BOLD_BLUE

        (
            ws.cell(column=1, row=irow + 1).value,
            ws.cell(column=1, row=irow + 1).font,
            ws.cell(column=2, row=irow + 1).value,
        ) = ("min", FT_BOLD, "Минимальное значение")
        (
            ws.cell(column=1, row=irow + 2).value,
            ws.cell(column=1, row=irow + 2).font,
            ws.cell(column=2, row=irow + 2).value,
        ) = ("max", FT_BOLD, "Максимальное значение")
        (
            ws.cell(column=1, row=irow + 3).value,
            ws.cell(column=1, row=irow + 3).font,
            ws.cell(column=2, row=irow + 3).value,
        ) = ("mean", FT_BOLD, "Среднее значение")
        (
            ws.cell(column=1, row=irow + 4).value,
            ws.cell(column=1, row=irow + 4).font,
            ws.cell(column=2, row=irow + 4).value,
        ) = ("med", FT_BOLD, "Медианное значение")

        (
            ws.cell(column=1, row=irow + 5).value,
            ws.cell(column=1, row=irow + 5).font,
            ws.cell(column=2, row=irow + 5).value,
        ) = ("me", FT_BOLD, "Средняя ошибка")
        (
            ws.cell(column=1, row=irow + 6).value,
            ws.cell(column=1, row=irow + 6).font,
            ws.cell(column=2, row=irow + 6).value,
        ) = ("mae", FT_BOLD, "Средняя абсолютная ошибка")
        (
            ws.cell(column=1, row=irow + 7).value,
            ws.cell(column=1, row=irow + 7).font,
            ws.cell(column=2, row=irow + 7).value,
        ) = ("rmse", FT_BOLD, "Среднеквадратическая ошибка")
        (
            ws.cell(column=1, row=irow + 8).value,
            ws.cell(column=1, row=irow + 8).font,
            ws.cell(column=2, row=irow + 8).value,
        ) = ("r2", FT_BOLD, "Коэффициент детерминации")
        (
            ws.cell(column=1, row=irow + 9).value,
            ws.cell(column=1, row=irow + 9).font,
            ws.cell(column=2, row=irow + 9).value,
        ) = ("mre", FT_BOLD, "Средняя относительная ошибка (она же MAPE)")
        (
            ws.cell(column=1, row=irow + 10).value,
            ws.cell(column=1, row=irow + 10).font,
            ws.cell(column=2, row=irow + 10).value,
        ) = ("nse", FT_BOLD, "Коэффициент эффективности Нэша-Сатклиффа")
        (
            ws.cell(column=1, row=irow + 11).value,
            ws.cell(column=1, row=irow + 11).font,
            ws.cell(column=2, row=irow + 11).value,
        ) = ("kge", FT_BOLD, "Коэффициент эффективности Клинга-Гупты")

        irow = irow + 13
        ws.cell(column=1, row=irow).value = "Данные"
        ws.cell(column=1, row=irow).font = FT_BOLD_BLUE
        (
            ws.cell(column=1, row=irow + 1).value,
            ws.cell(column=1, row=irow + 1).font,
            ws.cell(column=2, row=irow + 1).value,
        ) = ("obs", FT_BOLD, "Наблюдения из БД ИМКЭС")
        (
            ws.cell(column=1, row=irow + 2).value,
            ws.cell(column=1, row=irow + 2).font,
            ws.cell(column=2, row=irow + 2).value,
        ) = (
            "loc_td<X>d",
            FT_BOLD,
            "Локальный прогноз на периоде обучения из <X> дней (time-depth=<X>d)",
        )
        (
            ws.cell(column=1, row=irow + 3).value,
            ws.cell(column=1, row=irow + 3).font,
            ws.cell(column=2, row=irow + 3).value,
        ) = (
            "glob_td<X>d",
            FT_BOLD,
            "Глобальный прогноз на периоде обучения из <X> дней (time-depth=<X>d)",
        )
        (
            ws.cell(column=1, row=irow + 4).value,
            ws.cell(column=1, row=irow + 4).font,
            ws.cell(column=2, row=irow + 4).value,
        ) = (
            "loc_tf<Y>d",
            FT_BOLD,
            "Локальный прогноз вперед от текущей даты из <Y> дней (time-forecast=<Y>d)",
        )
        (
            ws.cell(column=1, row=irow + 5).value,
            ws.cell(column=1, row=irow + 5).font,
            ws.cell(column=2, row=irow + 5).value,
        ) = (
            "glob_tf<Y>d",
            FT_BOLD,
            "Глобальный прогноз вперед от текущей даты из <Y> дней (time-forecast=<Y>d)",
        )

    def _write_ml_models_sheet_to_station_file(self, wb, dict_ml_models, st_code):
        logging.info(
            "Запись информации о ML-моделях в файл с метриками для станции %s",
            st_code,
        )

        ws = wb.create_sheet(title="ML-models", index=0)

        now_dates = sorted(list(dict_ml_models.keys()))

        columns = sorted(
            [par_name for par_name in dict_ml_models[now_dates[0]][st_code].keys()]
        )
        for idx, col_name in enumerate(columns):
            ws.cell(row=1, column=idx + 2).value = col_name
            ws.cell(row=1, column=idx + 2).font = FT_BOLD

        for idx in range(len(columns) + 1):
            ws.column_dimensions[get_column_letter(idx + 1)].width = COL_WIDHT_2X

        for idx_row, now_date in enumerate(now_dates):
            ws.cell(row=idx_row + 2, column=1).value = now_date
            for idx_col, par_name in enumerate(columns):
                ws.cell(row=idx_row + 2, column=idx_col + 2).value = dict_ml_models[
                    now_date
                ][st_code][par_name]

    def _write_ml_models_sheet_to_parameter_file(self, wb, dict_ml_models, par_name):
        logging.info(
            "Запись информации о ML-моделях в файл с метриками для параметра %s",
            par_name,
        )

        ws = wb.create_sheet(title="ML-models", index=0)

        now_dates = sorted(list(dict_ml_models.keys()))

        columns = sorted([st_code for st_code in dict_ml_models[now_dates[0]].keys()])

        for idx, col_name in enumerate(columns):
            ws.cell(row=1, column=idx + 2).value = col_name
            ws.cell(row=1, column=idx + 2).font = FT_BOLD

        for idx in range(len(columns) + 1):
            ws.column_dimensions[get_column_letter(idx + 1)].width = COL_WIDHT_2X

        for idx_row, now_date in enumerate(now_dates):
            ws.cell(row=idx_row + 2, column=1).value = now_date
            for idx_col, st_code in enumerate(columns):
                if par_name in dict_ml_models[now_date][st_code]:
                    ws.cell(row=idx_row + 2, column=idx_col + 2).value = dict_ml_models[
                        now_date
                    ][st_code][par_name]

    def _write_1_file_is_1_station_all_parameters(
        self, fname_prefix: str, info: dict, dfs: dict, dict_ml_models: dict
    ) -> None:
        logging.info(
            "Формирование серии файлов: 1 файл = 1 станция с метриками по всем метео-параметрам"
        )

        # Цикл по станциям:
        for station_code in dfs.keys():
            fname = fname_prefix + "_station_" + station_code + ".xlsx"
            logging.info("[%s] Запись файла %s", station_code, fname)

            out_file = os.path.join(self.output_folder, fname)

            # Создать файл и записать все датафреймы
            with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
                # Цикл по метео-параметрам:
                for par_name in dfs[station_code].keys():
                    # Запись датафрейма dfs[station_code][par_name] на отдельный лист с именем par_name
                    dfs[station_code][par_name].to_excel(writer, sheet_name=par_name)

            #  Открыть файл для дозаписи листа Info
            wb = load_workbook(out_file)

            # Сформировать 1-й лист (ML-models), на основе словаря dict_ml_models (для записи используется openpyxl)
            self._write_ml_models_sheet_to_station_file(
                wb, dict_ml_models, station_code
            )

            # Сформировать 1-й лист (Info), на основе словаря info (для записи используется openpyxl)
            self._write_info_sheet_to_station_file(wb, info, station_code)

            wb.save(out_file)

    def _write_1_file_is_1_parameter_all_stations(
        self, fname_prefix: str, info: dict, dfs: dict, dict_ml_models: dict
    ) -> None:
        logging.info(
            "Формирование серии файлов: 1 файл = 1 метео-параметр (по имени) с метриками по станциям"
        )

        # Получить список всех метео-параметров из словаря dfs
        par_names = set()
        for station_code in dfs.keys():
            par_names.update(dfs[station_code].keys())
        par_names = sorted(list(par_names))

        # Цикл по именам метео-параметров из par_names:
        for par_name in par_names:
            fname = fname_prefix + "_parameter_" + par_name + ".xlsx"
            logging.info("[%s] Запись файла %s", par_name, fname)

            out_file = os.path.join(self.output_folder, fname)

            # Открыть файл с помощью pandas.ExcelWriter
            with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
                # Цикл по станциям:
                for station_code in dfs.keys():
                    if par_name in dfs[station_code]:

                        # Запись датафрейма dfs[station_code][par_name] на отдельный лист с именем station_code
                        dfs[station_code][par_name].to_excel(
                            writer, sheet_name=station_code
                        )

            #  Открыть файл для дозаписи листа Info
            wb = load_workbook(out_file)

            # Сформировать 1-й лист (ML-models), на основе словаря dict_ml_models (для записи используется openpyxl)
            self._write_ml_models_sheet_to_parameter_file(wb, dict_ml_models, par_name)

            #   Сформировать 1-й лист (Info), на основе словаря info (для записи используется openpyxl)
            self._write_info_sheet_to_parameter_file(wb, info, par_name)

            wb.save(out_file)

    def write_metrics(self, in_data: dict, metrics: dict) -> None:
        logging.info("Запись вычисленных метрик в файлы")

        now_dates_list = list(metrics.keys())

        info = self._collect_info(in_data[list(in_data.keys())[0]])
        dict_ml_models = self._collect_ml_models_info(in_data, now_dates_list)

        dfs_metrics = self._gen_dfs_metrics(metrics)

        self._write_1_file_is_1_station_all_parameters(
            self.metrics_filename_prefix, info, dfs_metrics, dict_ml_models
        )
        self._write_1_file_is_1_parameter_all_stations(
            self.metrics_filename_prefix, info, dfs_metrics, dict_ml_models
        )

    def write_data(self, in_data: dict, exp_data: dict, now_dates: list) -> None:
        logging.info("Запись данных в файлы")

        info = self._collect_info(in_data[list(in_data.keys())[0]])
        dict_ml_models = self._collect_ml_models_info(in_data, now_dates)

        dfs_data = self._gen_dfs_data(exp_data, now_dates)

        self._write_1_file_is_1_station_all_parameters(
            self.data_filename_prefix, info, dfs_data, dict_ml_models
        )
        self._write_1_file_is_1_parameter_all_stations(
            self.data_filename_prefix, info, dfs_data, dict_ml_models
        )
