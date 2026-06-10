import logging

import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Ridge
from sklearn.linear_model import Lasso
from sklearn.linear_model import ElasticNet
from sklearn.tree import DecisionTreeRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import GradientBoostingRegressor
from lightgbm import LGBMRegressor
from xgboost import XGBRegressor


from sklearn.model_selection import GridSearchCV


class Adjustmenter:
    def __init__(
        self,
        config,
        now_date,
        time_depth: str,
        time_forecast: str,
        verbose: str,
        verbose_dir: str,
    ):
        self.config = config
        # добавить проверку правильности названий модели и указанных гиперпараметров (сверка со словарем ml_models)

        self.now_date = now_date
        self.time_depth = time_depth
        self.time_forecast = time_forecast

        self.verbose = verbose.lower() == "true"
        self.verbose_dir = verbose_dir
        if self.verbose:
            # добавить создание и открытие файла для вербоза + вписать туда стартовые данные
            ...

        ml_models = {}
        ml_models[LinearRegression] = {}
        ml_models[LinearRegression]["param_grid"] = {
            # Нужно ли рассчитывать свободный коэффициент
            "fit_intercept": [True, False],
            # Будут ли все веса моедли строго неотрицательными
            "positive": [True, False],
        }

        ml_models[Ridge] = {}
        ml_models[Ridge]["param_grid"] = {
            # Сила регуляризации: от очень слабой (0.01) до экстремально сильной (1000)
            "alpha": np.logspace(
                -3, 3, 7
            ),  # [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
            # Расчет свободного коэффициента
            "fit_intercept": [True, False],
            # Алгоритм решения оптимизационной задачи.
            # 'auto' выберет лучший метод сам, но можно протестировать конкретные:
            # 'cholesky' хорош для плотных матриц, 'sag'/'saga' — для больших датасетов
            "solver": ["auto", "cholesky", "svd", "sag"],
        }  # Для подбора alpha лучше использовать RidgeCV вместо стандартного GridSearchCV

        ml_models[Lasso] = {}
        ml_models[Lasso]["param_grid"] = {
            # Коэффициент силы регуляризации (от слабой к сильной)
            "alpha": np.logspace(
                -4, 2, 7
            ),  # [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
            # Нужно ли рассчитывать свободный коэффициент
            "fit_intercept": [True, False],
            # Максимальное число итераций (для Lasso важно, так как оно сходится дольше)
            "max_iter": [1000, 5000],
        }  # Для подбора alpha лучше использовать LassoCV вместо стандартного GridSearchCV

        ml_models[ElasticNet] = {}
        ml_models[ElasticNet]["param_grid"] = {
            # Общая сила штрафа
            "alpha": np.logspace(
                -4, 2, 7
            ),  # [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
            # Доля L1 (Lasso) штрафа.
            # При 0.0 — это чистый Ridge, при 1.0 — чистый Lasso.
            "l1_ratio": [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99],
            # Нужно ли рассчитывать свободный коэффициент
            "fit_intercept": [True, False],
            # Максимальное число итераци
            "max_iter": [1000, 5000],
        }

        ml_models[KNeighborsRegressor] = {}
        ml_models[KNeighborsRegressor]["param_grid"] = {
            # Количество соседей
            "n_neighbors": [5, 7, 10, 13, 15],
            # Весовая функция
            "weights": ["uniform", "distance"],
            # Метрика расстояния
            "metric": ["euclidean", "manhattan", "minkowski"],
            # Степенной параметр для метрики Минковского
            "p": [1, 2],
        }

        ml_models[DecisionTreeRegressor] = {}
        ml_models[DecisionTreeRegressor]["param_grid"] = {
            # Максимальная глубина дерева
            "max_depth": [None, 3, 5, 10],
            # Максимальное количество признаков для поиска разбиения
            "max_features": [None, "auto", "sqrt", "log2", 0.5],
            # Критерий качества расщепления
            "criterion": ["squared_error", "friedman_mse", "absolute_error"],
        }

        ml_models[RandomForestRegressor] = {}
        ml_models[RandomForestRegressor]["param_grid"] = {
            # Количество генерируемых деревьев
            "n_estimators": [10, 50, 100, 200, 500],
            # Максимальная глубина дерева
            "max_depth": [None, 2, 5, 10],
            # Максимальное количество признаков для поиска разбиения
            "max_features": [None, "auto", "sqrt", "log2"],
        }

        ml_models[GradientBoostingRegressor] = {}
        ml_models[GradientBoostingRegressor]["param_grid"] = {
            # Количество деревьев
            "n_estimators": [10, 50, 100, 200, 500],
            # Скорость обучения
            "learning_rate": [0.01, 0.05, 0.1, 0.2],
            # Максимальная глубина каждого дерева
            "max_depth": [None, 2, 5, 10],
            # Доля выборки для обучения одного дерева
            "subsample": [0.7, 0.8, 0.9, 1.0],
            # Ограничение признаков
            "max_features": [None, "sqrt", 0.8],
        }

        ml_models[LGBMRegressor] = {}
        ml_models[LGBMRegressor]["param_grid"] = {
            # Количество деревьев
            "n_estimators": [10, 50, 100, 200, 500],
            # Скорость обучения
            "learning_rate": [0.01, 0.05, 0.1, 0.2],
            # Максимальная глубина каждого дерева
            "max_depth": [None, 2, 5, 10],
            # Коэффициент случайной субвыборки признаков
            "colsample_bytree": [0.8, 1.0],
        }

        ml_models[XGBRegressor] = {}
        ml_models[XGBRegressor]["param_grid"] = {
            # Количество деревьев
            "n_estimators": [10, 50, 100, 200, 500],
            # Скорость обучения
            "learning_rate": [0.01, 0.05, 0.1, 0.2],
            # Максимальная глубина каждого дерева
            "max_depth": [None, 2, 5, 10],
            # Минимальное снижение ошибки для создания нового расщепления (регуляризация)
            "gamma": [0, 0.1, 0.2],
            # Доля строк (данных) для обучения одного дерева
            "subsample": [0.8, 1.0],
            # Коэффициент случайной субвыборки признаков
            "colsample_bytree": [0.8, 1.0],
        }

        # Еще добавить нужно будет:
        # - Базовая модель: прогноз средним значением (среднее по тренировочной далее принимается за прогнозное)
        # - Наивный прогноз (последнее значение тренировочной далее принимается за прогнозное)
        # - Суточный наивный прогноз (выбираются последние сутки и далее принимается за прогнозное)
        # - Модель смещения (y = x + b)
        # - Модель масштабирования (y = a * x)
        # - Модели экспоненциального сглаживания (statsmodels.tsa.holtwinters (модель Холта-Винтерса)): SimpleExpSmoothing; ExponentialSmoothing; Holt

        self.ml_models = ml_models

    @staticmethod
    def _check_corr_data_bounds(
        data: list, min_val: float, max_val: float
    ) -> tuple[list, float]:

        corr_cnt = 0
        for idx, val in enumerate(data):
            if val:
                if val < min_val:
                    data[idx] = min_val
                    corr_cnt += 1
                if val > max_val:
                    data[idx] = max_val
                    corr_cnt += 1

        return data, 100.0 * corr_cnt / len(data)

    @staticmethod
    def _get_train_sets(x_data: list, y_data: list) -> tuple[bool, list, list]:

        idx_x_none = [idx for idx, val in enumerate(x_data) if val is None]
        idx_y_none = [idx for idx, val in enumerate(y_data) if val is None]

        idx_none = set(idx_x_none) | set(idx_y_none)

        if len(idx_none) > (len(x_data) / 10.0):
            status = False
            x_data_no_none = []
            y_data_no_none = []
        else:
            status = True
            x_data_no_none = [
                val for idx, val in enumerate(x_data) if idx not in idx_none
            ]
            y_data_no_none = [
                val for idx, val in enumerate(y_data) if idx not in idx_none
            ]

        return status, x_data_no_none, y_data_no_none

    def _get_ml_forecast(
        self,
        model_cfg,  # конкретная модель или auto (т.е. перебор по всем доступным для построения наилучшей)
        # или autoset и дальше указать model-set=[..., ..., ...] (перебор по моделям только из этого набора)
        x_train: list,
        y_train: list,
        x_past_predict: list,
        x_future_predict: list,
    ) -> tuple[list, list]:

        return [], []

    # mod_local_past, mod_local_future = self._get_local_forecast(
    #                    par_short_name, x_train, y_train, mod_data_past, mod_data_future
    #                )
    def _get_local_forecast(
        self,
        par_short_name: str,
        x_train: list,
        y_train: list,
        x_past_predict: list,
        x_future_predict: list,
    ) -> tuple[list, list]:

        if par_short_name in self.config.keys():
            # use specific ml-model
            par_model_key = par_short_name
        else:
            # use default ml-model (under "default" key in config_ml.ini)
            par_model_key = "default"

        y_past_predict, y_future_predict = self._get_ml_forecast(
            self.config[par_model_key],
            x_train,
            y_train,
            x_past_predict,
            x_future_predict,
        )

        return y_past_predict, y_future_predict

    def get_local_forecast(self, station: dict) -> dict:
        logging.info(
            "Формирование локального прогноза для станции %s (%s)",
            station["code"],
            station["full_name"],
        )

        # self.obs_time_past = station["db_time_past"][self.time_depth]
        # self.mod_time_past = station["om_time_past"][self.time_depth]
        # self.mod_time_future = station["om_time_future"][self.time_forecast]

        for par_short_name, parameter in station["parameters"].items():
            logging.info(
                "Получение локального прогноза для параметра %s (код: %s)",
                parameter["name"],
                parameter["code"],
            )

            parameter["om_data_local"] = {}
            parameter["om_data_local"]["past"] = {}
            parameter["om_data_local"]["future"] = {}

            parameter["om_data_local_no_corr"] = {}
            parameter["om_data_local_no_corr"]["past"] = {}
            parameter["om_data_local_no_corr"]["future"] = {}

            obs_data = parameter["data"][self.time_depth]
            mod_data_past = parameter["om_data_glob"]["past"][self.time_depth]
            mod_data_future = parameter["om_data_glob"]["future"][self.time_forecast]

            status, x_train, y_train = self._get_train_sets(mod_data_past, obs_data)

            if status:
                mod_local_past, mod_local_future = self._get_local_forecast(
                    par_short_name, x_train, y_train, mod_data_past, mod_data_future
                )

                parameter["om_data_local_no_corr"]["past"][
                    self.time_depth
                ] = mod_local_past
                parameter["om_data_local_no_corr"]["future"][
                    self.time_forecast
                ] = mod_local_future

                mod_local_past_corr, corr_past_percent = self._check_corr_data_bounds(
                    data=mod_local_past,
                    min_val=parameter["min_value"],
                    max_val=parameter["max_value"],
                )
                parameter["om_data_local"]["past"][
                    self.time_depth
                ] = mod_local_past_corr

                mod_local_future_corr, corr_future_percent = (
                    self._check_corr_data_bounds(
                        data=mod_local_future,
                        min_val=parameter["min_value"],
                        max_val=parameter["max_value"],
                    )
                )
                parameter["om_data_local"]["future"][
                    self.time_forecast
                ] = mod_local_future_corr

                logging.info(
                    "Скорректировано под допустимый диапазон %.2f %% значений прогноза на историческом периоде и %.2f %% значений прогноза в будущее",
                    corr_past_percent,
                    corr_future_percent,
                )
            else:
                logging.error(
                    "Пропуск получения локального прогноза: большие пропуски в данных (> 10 %)"
                )

                parameter["om_data_local"]["past"][self.time_depth] = [
                    None for _ in mod_data_past
                ]
                parameter["om_data_local"]["future"][self.time_forecast] = [
                    None for _ in mod_data_past
                ]

        return station
