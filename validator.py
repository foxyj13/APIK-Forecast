import logging

# from statistics import mean, median

import numpy as np
from scipy.stats import variation
from sklearn.metrics import (
    root_mean_squared_error,
    r2_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
)


class Validator:
    def __init__(self, time_depth: str, time_forecast: str):
        self.time_depth = time_depth
        self.time_forecast = time_forecast

    @staticmethod
    def _get_self_metrics(data: list) -> dict:

        if sum(np.isnan(data)) / len(data) < 0.1:
            result = {
                "mean": np.nanmean(data),
                "med": np.nanmedian(data),
                "max": max(data),
                "min": min(data),
            }
        else:
            result = {
                "mean": None,
                "med": None,
                "max": None,
                "min": None,
            }

        return result

    @staticmethod
    def _get_mutual_metrics(
        time_obs: list, data_obs: list, time_mod: list, data_mod: list
    ) -> dict:

        def get_pearsonr(data_obs: list, data_mod: list) -> float:

            mean_obs = np.nanmean(data_obs)
            mean_mod = np.nanmean(data_mod)

            np_data_obs = np.asarray(data_obs)
            np_data_mod = np.asarray(data_mod)

            top = np.nansum((np_data_obs - mean_obs) * (np_data_mod - mean_mod))

            bot = (
                np.nansum(np.power(np_data_obs - mean_obs, 2))
                * np.nansum(np.power(np_data_mod - mean_mod, 2))
            ) ** 0.5

            return top / bot

        def get_nse(data_obs: list, data_mod: list) -> float:
            np_data_obs = np.asarray(data_obs)
            np_data_mod = np.asarray(data_mod)

            top = np.nansum(np.power(np_data_mod - np_data_obs, 2))
            bot = np.nansum(np.power(np_data_obs - np.nanmean(data_obs), 2))

            return 1 - top / bot

        if time_obs == time_mod:
            if (sum(np.isnan(data_obs)) / len(data_obs) < 0.1) and (
                sum(np.isnan(data_mod)) / len(data_mod) < 0.1
            ):

                nse = get_nse(data_obs, data_mod)

                pearsonr = get_pearsonr(data_obs, data_mod)
                alpha = variation(data_mod, nan_policy="omit") / variation(
                    data_obs, nan_policy="omit"
                )
                betta = np.nanmean(data_mod) / np.nanmean(data_obs)
                kge = (
                    1
                    - ((pearsonr - 1) ** 2 + (betta - 1) ** 2 + (alpha - 1) ** 2) ** 0.5
                )

                idx_notnan = ~np.isnan(data_obs) * ~np.isnan(data_mod)
                data_obs_np = np.array(data_obs)[idx_notnan]
                data_mod_np = np.array(data_mod)[idx_notnan]
                result = {
                    "rmse": root_mean_squared_error(data_obs_np, data_mod_np),
                    "r2": r2_score(data_obs_np, data_mod_np),
                    "me": np.nanmean(
                        [data_mod[idx] - data_obs[idx] for idx in range(len(data_obs))]
                    ),
                    "mae": mean_absolute_error(data_obs_np, data_mod_np),
                    "mre": mean_absolute_percentage_error(data_obs_np, data_mod_np),
                    "nse": nse,
                    "kge": kge,
                }
            else:
                result = {
                    "rmse": None,
                    "r2": None,
                    "me": None,
                    "mae": None,
                    "mre": None,
                    "nse": None,
                    "kge": None,
                }
        else:
            # Возможно, потом нужно будет как-то попробовать состыковать временные оси и посчитать метрики,
            #   но пока так:
            result = {
                "rmse": None,
                "r2": None,
                "me": None,
                "mae": None,
                "mre": None,
                "nse": None,
                "kge": None,
            }

        return result

    def get_metrics(self, station: dict) -> dict:

        logging.info(
            "Расчет метрик для станции %s (%s)", station["code"], station["full_name"]
        )

        for _, parameter in station["parameters"].items():
            parameter["metrics"] = {}

            # Расчет метрик для наблюдений
            if ("data" in parameter) and (parameter["data"][self.time_depth]):
                parameter["metrics"]["obs"] = self._get_self_metrics(
                    parameter["data"][self.time_depth]
                )

            # Расчет метрик для прогноза
            if ("om_data_glob" in parameter) and (
                parameter["om_data_glob"]["past"][self.time_depth]
            ):
                parameter["metrics"]["glob_past"] = self._get_self_metrics(
                    parameter["om_data_glob"]["past"][self.time_depth]
                )

                if ("om_data_glob" in parameter) and (
                    parameter["om_data_glob"]["future"][self.time_forecast]
                ):
                    parameter["metrics"]["glob_future"] = self._get_self_metrics(
                        parameter["om_data_glob"]["future"][self.time_forecast]
                    )

                if ("om_data_local" in parameter) and (
                    parameter["om_data_local"]["past"][self.time_depth]
                ):
                    parameter["metrics"]["local_past"] = self._get_self_metrics(
                        parameter["om_data_local"]["past"][self.time_depth]
                    )

                if ("om_data_local" in parameter) and (
                    parameter["om_data_local"]["future"][self.time_forecast]
                ):
                    parameter["metrics"]["local_future"] = self._get_self_metrics(
                        parameter["om_data_local"]["future"][self.time_forecast]
                    )

            # Расчет совместных метрик наблюдения vs глобальный прогноз
            if (
                ("om_data_glob" in parameter)
                and (parameter["om_data_glob"]["past"][self.time_depth])
                and (parameter["data"][self.time_depth])
            ):
                parameter["metrics"]["obs_glob"] = self._get_mutual_metrics(
                    station["db_time_past"][self.time_depth],
                    parameter["data"][self.time_depth],
                    station["om_time_past"][self.time_depth],
                    parameter["om_data_glob"]["past"][self.time_depth],
                )

            # Расчет совместных метрик наблюдения vs локальный прогноз
            if (
                ("om_data_local" in parameter)
                and (parameter["om_data_local"]["past"][self.time_depth])
                and (parameter["data"][self.time_depth])
            ):
                parameter["metrics"]["obs_local"] = self._get_mutual_metrics(
                    station["db_time_past"][self.time_depth],
                    parameter["data"][self.time_depth],
                    station["om_time_past"][self.time_depth],
                    parameter["om_data_local"]["past"][self.time_depth],
                )

        return station
