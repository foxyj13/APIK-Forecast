import logging

import math
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

        data_nan = [
            (x is None) or (isinstance(x, float) and math.isnan(x)) for x in data
        ]

        if sum(data_nan) / len(data) < 0.1:
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
    def _get_mutual_metrics(data_obs: list, data_mod: list) -> dict:

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

        obs_nan = [
            (x is None) or (isinstance(x, float) and math.isnan(x)) for x in data_obs
        ]
        mod_nan = [
            (x is None) or (isinstance(x, float) and math.isnan(x)) for x in data_mod
        ]

        if (sum(obs_nan) / len(data_obs) < 0.1) and (
            sum(mod_nan) / len(data_mod) < 0.1
        ):
            nse = get_nse(data_obs, data_mod)

            pearsonr = get_pearsonr(data_obs, data_mod)
            alpha = variation(data_mod, nan_policy="omit") / variation(
                data_obs, nan_policy="omit"
            )
            betta = np.nanmean(data_mod) / np.nanmean(data_obs)
            kge = 1 - ((pearsonr - 1) ** 2 + (betta - 1) ** 2 + (alpha - 1) ** 2) ** 0.5

            idx_notnan = ~np.array(obs_nan) * ~np.array(mod_nan)
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

        return result

    def get_metrics(self, station_now: dict, station_next: dict) -> dict:

        def _get_obs_future_idx(
            now_timeline_future: list, next_timeline_past: list
        ) -> tuple:
            idx_start = next_timeline_past.index(now_timeline_future[0])
            idx_end = next_timeline_past.index(now_timeline_future[-1])

            return idx_start, idx_end

        logging.info(
            "Расчет метрик для станции %s (%s)",
            station_now["code"],
            station_now["full_name"],
        )

        obs_future_start, obs_future_end = _get_obs_future_idx(
            station_now["timeline"]["future"][self.time_forecast],
            station_next["timeline"]["past"][self.time_depth],
        )

        metrics = {}

        for par_name, parameter in station_now["parameters"].items():
            metrics[par_name] = {}
            # parameter["metrics"] = {}

            # Расчет метрик для наблюдений
            if ("data" in parameter) and (parameter["data"][self.time_depth]):
                metrics[par_name]["obs"] = self._get_self_metrics(
                    parameter["data"][self.time_depth]
                )

                # Расчет метрик для локального прогноза
                metrics[par_name]["local"] = {}
                if "data_local" in parameter:
                    # Индивидуальные метрики
                    if ("past" in parameter["data_local"]) and (
                        parameter["data_local"]["past"][self.time_depth]
                    ):
                        metrics[par_name]["local"]["past"] = self._get_self_metrics(
                            parameter["data_local"]["past"][self.time_depth]
                        )

                        metrics[par_name]["local"]["past"].update(
                            self._get_mutual_metrics(
                                parameter["data"][self.time_depth],
                                parameter["data_local"]["past"][self.time_depth],
                            )
                        )
                    else:
                        metrics[par_name]["local"]["past"] = {}

                    if ("future" in parameter["data_local"]) and (
                        parameter["data_local"]["future"][self.time_forecast]
                    ):
                        metrics[par_name]["local"]["future"] = self._get_self_metrics(
                            parameter["data_local"]["future"][self.time_forecast]
                        )

                        if (
                            "data" in station_next["parameters"][par_name]
                        ) and station_next["parameters"][par_name]["data"][
                            self.time_depth
                        ]:
                            metrics[par_name]["local"]["future"].update(
                                self._get_mutual_metrics(
                                    station_next["parameters"][par_name]["data"][
                                        self.time_depth
                                    ][obs_future_start:obs_future_end],
                                    parameter["data_local"]["future"][
                                        self.time_forecast
                                    ],
                                )
                            )
                    else:
                        metrics[par_name]["local"]["future"] = {}

                else:
                    metrics[par_name]["local"]["past"] = {}
                    metrics[par_name]["local"]["future"] = {}

                # расчет метрик для глобального прогноза
                if ("om_parameter" in parameter) and (parameter["om_parameter"] != ""):
                    om_par_name = parameter["om_parameter"]

                    if om_par_name in station_now["predictors_data"]:
                        # Индивидуальные метрики
                        if "past" in station_now["predictors_data"][om_par_name] and (
                            station_now["predictors_data"][om_par_name]["past"][
                                self.time_depth
                            ]
                        ):
                            metrics[par_name]["global"]["past"] = (
                                self._get_self_metrics(
                                    station_now["predictors_data"][om_par_name]["past"][
                                        self.time_depth
                                    ]
                                )
                            )

                            metrics[par_name]["global"]["past"].update(
                                self._get_mutual_metrics(
                                    parameter["data"][self.time_depth],
                                    station_now["predictors_data"][om_par_name]["past"][
                                        self.time_depth
                                    ],
                                )
                            )
                        else:
                            metrics[par_name]["global"]["past"] = {}

                        if "future" in station_now["predictors_data"][om_par_name] and (
                            station_now["predictors_data"][om_par_name]["future"][
                                self.time_forecast
                            ]
                        ):
                            metrics[par_name]["global"]["future"] = (
                                self._get_self_metrics(
                                    station_now["predictors_data"][om_par_name][
                                        "future"
                                    ][self.time_forecast]
                                )
                            )

                            if (
                                "data" in station_next["parameters"][par_name]
                            ) and station_next["parameters"][par_name]["data"][
                                self.time_depth
                            ]:
                                metrics[par_name]["global"]["future"].update(
                                    self._get_mutual_metrics(
                                        station_next["parameters"][par_name]["data"][
                                            self.time_depth
                                        ][obs_future_start:obs_future_end],
                                        station_now["predictors_data"][om_par_name][
                                            "future"
                                        ][self.time_forecast],
                                    )
                                )
                        else:
                            metrics[par_name]["global"]["future"] = {}

                    else:
                        metrics[par_name]["global"]["past"] = {}
                        metrics[par_name]["global"]["future"] = {}
                else:
                    metrics[par_name]["global"]["past"] = {}
                    metrics[par_name]["global"]["future"] = {}
            else:
                metrics[par_name]["obs"] = {}
                metrics[par_name]["local"]["past"] = {}
                metrics[par_name]["local"]["future"] = {}
                metrics[par_name]["global"]["past"] = {}
                metrics[par_name]["global"]["future"] = {}

        return metrics  # station
