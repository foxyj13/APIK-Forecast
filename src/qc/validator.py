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
        # logging.info("self_metrics")

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

        # def get_pearsonr(data_obs: list, data_mod: list) -> float:

        #     np_data_obs = np.asarray(data_obs)
        #     np_data_mod = np.asarray(data_mod)

        #     mask = ~np.isnan(np_data_obs) & ~np.isnan(np_data_mod)
        #     matrix = np.corrcoef(np_data_obs[mask], np_data_mod[mask])
        #     pearson_coef = matrix[0, 1]

        #     return pearson_coef

        def get_nse(data_obs: list, data_mod: list, eps=1e-7) -> float:
            """Получение значения коэффициента эффективности Нэша-Сатклиффа (NSE)

            Интерпретация значений:
                NSE = 1: Идеальное совпадение модели с реальностью.
                    Смоделированные данные полностью повторяют фактические.
                0 < NSE < 1: Модель считается приемлемой. Чем ближе к 1, тем выше качество прогноза.
                    Значения выше 0.5–0.6 в гидрологии обычно трактуются как удовлетворительные или хорошие.
                NSE = 0: Прогнозы модели имеют точность на уровне простого среднего значения от исторических данных.
                NSE < 0: Модель работает хуже, чем простое среднее арифметическое наблюдений.
                    Моделирование в данном виде не имеет практического смысла.
            """

            # logging.info("NSE")

            np_data_obs = np.asarray(data_obs)
            np_data_mod = np.asarray(data_mod)

            top = np.nansum(np.power(np_data_mod - np_data_obs, 2))
            bot = np.nansum(np.power(np_data_obs - np.nanmean(data_obs), 2))

            if np.isclose(bot, 0.0, atol=eps):
                if np.isclose(top, 0.0, atol=eps) == 0:
                    return 1.0
                else:
                    return np.nan

            return 1 - top / bot

        def get_kge(data_obs: list, data_mod: list, eps=1e-7) -> float:
            """Получение значения коэффициента эффективности Клинга-Гупты (KGE)

            Интерпретация значений:
                KGE = 1: Идеальное совпадение модели с реальностью по всем трем параметрам.
                KGE > 0: Модель считается относительно хорошей и применимой на практике.
                KGE ≈ -0.41: Критическая отметка.
                    При этом значении точность модели эквивалентна использованию константного среднего исторического значения.
                KGE < -0.41: Качество модели крайне низкое; ее прогнозы хуже простого угадывания по среднему значению
            """

            # logging.info("KGE")

            obs = np.asarray(data_obs)
            sim = np.asarray(data_mod)

            # 1. Расчет средних и стандартных отклонений
            mu_obs = np.mean(obs)
            mu_sim = np.mean(sim)
            sigma_obs = np.std(obs)
            sigma_sim = np.std(sim)

            # 2. Безопасный расчет Beta
            if np.isclose(mu_obs, 0.0, atol=eps):
                beta = 1.0 if np.isclose(mu_sim, 0.0, atol=eps) else 1e5
            else:
                beta = mu_sim / mu_obs

            # 3. Безопасный расчет Alpha и Корреляции (r)
            if np.isclose(sigma_obs, 0.0, atol=eps):
                alpha = 1.0 if np.isclose(sigma_sim, 0.0, atol=eps) else 1e5
                r = 1.0 if np.isclose(mu_obs, mu_sim, atol=eps) else 0.0
            else:
                alpha = sigma_sim / sigma_obs
                # Безопасный коэффициент Пирсона
                if np.isclose(sigma_sim, 0.0, atol=eps):
                    r = 0.0
                else:
                    r = np.corrcoef(obs, sim)[0, 1]
                    if np.isnan(r):
                        r = 0.0

            # 4. Сборка KGE
            kge = 1.0 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)
            return float(kge)  # , {"r": r, "alpha": alpha, "beta": beta}

        # logging.info("mutual_metrics")

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
            kge = get_kge(data_obs, data_mod)

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
            logging.info("[%s]", par_name)

            metrics[par_name] = {}
            metrics[par_name]["obs"] = {}
            metrics[par_name]["local"] = {}
            metrics[par_name]["global"] = {}

            # parameter["metrics"] = {}

            # Расчет метрик для наблюдений
            if ("data" in parameter) and (parameter["data"][self.time_depth]):
                metrics[par_name]["obs"]["past"] = self._get_self_metrics(
                    parameter["data"][self.time_depth]
                )

                metrics[par_name]["obs"]["future"] = self._get_self_metrics(
                    station_next["parameters"][par_name]["data"][self.time_depth][
                        obs_future_start : obs_future_end + 1
                    ]
                )

                # Расчет метрик для локального прогноза
                if "data_local" in parameter:
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
                                    ][obs_future_start : obs_future_end + 1],
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
                                        ][obs_future_start : obs_future_end + 1],
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
