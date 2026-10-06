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

    @staticmethod
    def _get_mutual_daily_metrics(data_obs: list, data_mod: list) -> dict:
        n_days = len(data_obs) // 24

        result = {
            "rmse_day": [],
            "r2_day": [],
            "me_day": [],
            "mae_day": [],
            "mre_day": [],
            "nse_day": [],
            "kge_day": [],
        }

        for day in range(n_days):
            day_obs = data_obs[day * 24 : (day + 1) * 24]
            day_mod = data_mod[day * 24 : (day + 1) * 24]

            daily_metrics = Validator._get_mutual_metrics(day_obs, day_mod)

            for key in daily_metrics:
                result[key + "_day"].append(daily_metrics[key])

        return result

    def get_metrics(self, obs_data: dict, local_data: dict, glob_data: dict) -> dict:
        metrics = {
            "obs": {"past": {}, "future": {}},
            "local": {"past": {}, "future": {}},
            "global": {"past": {}, "future": {}},
        }

        # Расчет метрик для наблюдений
        if obs_data["past"]:
            metrics["obs"]["past"] = self._get_self_metrics(obs_data["past"])

        if obs_data["future"]:
            metrics["obs"]["future"] = self._get_self_metrics(obs_data["future"])

        # Расчет метрик для локального прогноза
        if local_data["past"]:
            metrics["local"]["past"] = self._get_self_metrics(local_data["past"])
            if obs_data["past"]:
                metrics["local"]["past"].update(
                    self._get_mutual_metrics(obs_data["past"], local_data["past"])
                )

        if local_data["future"]:
            metrics["local"]["future"] = self._get_self_metrics(local_data["future"])
            if obs_data["future"]:
                metrics["local"]["future"].update(
                    self._get_mutual_metrics(obs_data["future"], local_data["future"])
                )
                metrics["local"]["future"].update(
                    self._get_mutual_daily_metrics(
                        obs_data["future"], local_data["future"]
                    )
                )

        # Расчет метрик для глобального прогноза
        if glob_data["past"]:
            metrics["global"]["past"] = self._get_self_metrics(glob_data["past"])
            if obs_data["past"]:
                metrics["global"]["past"].update(
                    self._get_mutual_metrics(obs_data["past"], glob_data["past"])
                )

        if glob_data["future"]:
            metrics["global"]["future"] = self._get_self_metrics(glob_data["future"])
            if obs_data["future"]:
                metrics["global"]["future"].update(
                    self._get_mutual_metrics(obs_data["future"], glob_data["future"])
                )
                metrics["global"]["future"].update(
                    self._get_mutual_daily_metrics(
                        obs_data["future"], glob_data["future"]
                    )
                )

        return metrics
