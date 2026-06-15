import inspect
import logging
import sys

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
        self.now_date = now_date
        self.time_depth = time_depth
        self.time_forecast = time_forecast

        self.verbose = verbose.lower() == "true"
        self.verbose_dir = verbose_dir
        if self.verbose:
            # добавить создание и открытие файла для вербоза + вписать туда стартовые данные
            ...

        self.ml_models = self._set_available_models()
        self.ml_models_list = list(self.ml_models.keys())
        logging.info(
            "Для использования доступны следующие модели машинного обучения: %s",
            self.ml_models_list,
        )

        # self.config = config
        # self.cfg_sections = self.config.sections()
        self.config = self._check_config_models(config)
        if not self.config:
            logging.error(
                "Ошибка ML-конфигурации. Возможные причины: 1) В конфигурации указаны ML-модели, которые не входят в список доступных моделей. Доступные модели: %s; 2) Указаны неверные наименования гиперпараметров (указаны параметры, которые не существуют для этих моделей)",
                self.ml_models_list,
            )
            logging.info("Остановка программы")
            sys.exit(1)
        else:
            self.cfg_sections = list(self.config.keys())

    @staticmethod
    def _set_available_models() -> dict:
        logging.info(
            "Инициализация доступных моделей машинного обучения и их гиперпараметров для перебора"
        )

        ml_models = {}
        ml_models["LinearRegression"] = {}
        ml_models["LinearRegression"]["cls"] = LinearRegression
        ml_models["LinearRegression"]["param_grid"] = {
            # Нужно ли рассчитывать свободный коэффициент
            "fit_intercept": [True, False],
            # Будут ли все веса моедли строго неотрицательными
            "positive": [True, False],
        }

        # ml_models["Ridge"] = {}
        # ml_models["Ridge"]["cls"] = Ridge
        # ml_models["Ridge"]["param_grid"] = {
        #     # Сила регуляризации: от очень слабой (0.01) до экстремально сильной (1000)
        #     "alpha": np.logspace(
        #         -3, 3, 7
        #     ),  # [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
        #     # Расчет свободного коэффициента
        #     "fit_intercept": [True, False],
        #     # Алгоритм решения оптимизационной задачи.
        #     # 'auto' выберет лучший метод сам, но можно протестировать конкретные:
        #     # 'cholesky' хорош для плотных матриц, 'sag'/'saga' — для больших датасетов
        #     "solver": ["auto", "cholesky", "svd", "sag"],
        # }  # Для подбора alpha лучше использовать RidgeCV вместо стандартного GridSearchCV

        # ml_models["Lasso"] = {}
        # ml_models["Lasso"]["cls"] = Lasso
        # ml_models["Lasso"]["param_grid"] = {
        #     # Коэффициент силы регуляризации (от слабой к сильной)
        #     "alpha": np.logspace(
        #         -4, 2, 7
        #     ),  # [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
        #     # Нужно ли рассчитывать свободный коэффициент
        #     "fit_intercept": [True, False],
        #     # Максимальное число итераций (для Lasso важно, так как оно сходится дольше)
        #     "max_iter": [1000, 5000],
        # }  # Для подбора alpha лучше использовать LassoCV вместо стандартного GridSearchCV

        # ml_models["ElasticNet"] = {}
        # ml_models["ElasticNet"]["cls"] = ElasticNet
        # ml_models["ElasticNet"]["param_grid"] = {
        #     # Общая сила штрафа
        #     "alpha": np.logspace(
        #         -4, 2, 7
        #     ),  # [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
        #     # Доля L1 (Lasso) штрафа.
        #     # При 0.0 — это чистый Ridge, при 1.0 — чистый Lasso.
        #     "l1_ratio": [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99],
        #     # Нужно ли рассчитывать свободный коэффициент
        #     "fit_intercept": [True, False],
        #     # Максимальное число итераци
        #     "max_iter": [1000, 5000],
        # }

        # ml_models["KNeighborsRegressor"] = {}
        # ml_models["KNeighborsRegressor"]["cls"] = KNeighborsRegressor
        # ml_models["KNeighborsRegressor"]["param_grid"] = {
        #     # Количество соседей
        #     "n_neighbors": [5, 7, 10, 13, 15],
        #     # Весовая функция
        #     "weights": ["uniform", "distance"],
        #     # Метрика расстояния
        #     "metric": ["euclidean", "manhattan", "minkowski"],
        #     # Степенной параметр для метрики Минковского
        #     "p": [1, 2],
        # }

        ml_models["DecisionTreeRegressor"] = {}
        ml_models["DecisionTreeRegressor"]["cls"] = DecisionTreeRegressor
        ml_models["DecisionTreeRegressor"]["param_grid"] = {
            # Максимальная глубина дерева
            "max_depth": [None, 3, 5, 10],
            # Максимальное количество признаков для поиска разбиения
            "max_features": [None, "auto", "sqrt", "log2", 0.5],
            # Критерий качества расщепления
            "criterion": ["squared_error", "friedman_mse", "absolute_error"],
        }

        ml_models["RandomForestRegressor"] = {}
        ml_models["RandomForestRegressor"]["cls"] = RandomForestRegressor
        ml_models["RandomForestRegressor"]["param_grid"] = {
            # Количество генерируемых деревьев
            "n_estimators": [10, 50, 100, 200, 500],
            # Максимальная глубина дерева
            "max_depth": [None, 2, 5, 10],
            # Максимальное количество признаков для поиска разбиения
            "max_features": [None, "auto", "sqrt", "log2"],
        }

        # ml_models["GradientBoostingRegressor"] = {}
        # ml_models["GradientBoostingRegressor"]["cls"] = GradientBoostingRegressor
        # ml_models["GradientBoostingRegressor"]["param_grid"] = {
        #     # Количество деревьев
        #     "n_estimators": [10, 50, 100, 200, 500],
        #     # Скорость обучения
        #     "learning_rate": [0.01, 0.05, 0.1, 0.2],
        #     # Максимальная глубина каждого дерева
        #     "max_depth": [None, 2, 5, 10],
        #     # Доля выборки для обучения одного дерева
        #     "subsample": [0.7, 0.8, 0.9, 1.0],
        #     # Ограничение признаков
        #     "max_features": [None, "sqrt", 0.8],
        # }

        # ml_models["LGBMRegressor"] = {}
        # ml_models["LGBMRegressor"]["cls"] = LGBMRegressor
        # ml_models["LGBMRegressor"]["param_grid"] = {
        #     # Количество деревьев
        #     "n_estimators": [10, 50, 100, 200, 500],
        #     # Скорость обучения
        #     "learning_rate": [0.01, 0.05, 0.1, 0.2],
        #     # Максимальная глубина каждого дерева
        #     "max_depth": [None, 2, 5, 10],
        #     # Коэффициент случайной субвыборки признаков
        #     "colsample_bytree": [0.8, 1.0],
        # }

        # ml_models["XGBRegressor"] = {}
        # ml_models["XGBRegressor"]["cls"] = XGBRegressor
        # ml_models["XGBRegressor"]["param_grid"] = {
        #     # Количество деревьев
        #     "n_estimators": [10, 50, 100, 200, 500],
        #     # Скорость обучения
        #     "learning_rate": [0.01, 0.05, 0.1, 0.2],
        #     # Максимальная глубина каждого дерева
        #     "max_depth": [None, 2, 5, 10],
        #     # Минимальное снижение ошибки для создания нового расщепления (регуляризация)
        #     "gamma": [0, 0.1, 0.2],
        #     # Доля строк (данных) для обучения одного дерева
        #     "subsample": [0.8, 1.0],
        #     # Коэффициент случайной субвыборки признаков
        #     "colsample_bytree": [0.8, 1.0],
        # }

        # Еще добавить нужно будет:
        # - Базовая модель: прогноз средним значением (среднее по тренировочной далее принимается за прогнозное)
        # - Наивный прогноз (последнее значение тренировочной далее принимается за прогнозное)
        # - Суточный наивный прогноз (выбираются последние сутки и далее принимается за прогнозное)
        # - Модель смещения (y = x + b)
        # - Модель масштабирования (y = a * x)
        # - Модели экспоненциального сглаживания (statsmodels.tsa.holtwinters (модель Холта-Винтерса)): SimpleExpSmoothing; ExponentialSmoothing; Holt

        return ml_models

    def _check_config_models(self, config) -> dict:

        def corr_type(s: str):
            try:
                num = int(s)
                return num
            except ValueError:
                try:
                    num = float(s)
                    return num
                except ValueError:
                    if s.lower() == "true":
                        return True
                    elif s.lower() == "false":
                        return False
                    else:
                        return s

        cfg_dict = {s: dict(config.items(s)) for s in config.sections()}

        for par_model_key, par_model_cfg in cfg_dict.items():
            if par_model_cfg["model"] == "auto":
                model_set = self.ml_models_list

                if ("get-result" not in par_model_cfg) or (
                    par_model_cfg["get-result"] not in ["best", "mean"]
                ):
                    par_model_cfg["get-result"] = "best"

            elif par_model_cfg["model"] == "autoset":
                if "model-set" not in par_model_cfg:
                    logging.error(
                        "В файле с ML-настройками в разделе [%s] указано значение 'autoset' для ключа 'model', но не указан ключ 'model-set' с перечнем моделей для перебора. Необходимо указать 'model-set' с перечнем моделей из доступных: %s",
                        par_model_key,
                        self.ml_models_list,
                    )
                    return {}
                else:
                    model_set = [
                        model.strip() for model in par_model_cfg["model-set"].split(",")
                    ]
                    par_model_cfg["model-set"] = model_set

                if ("get-result" not in par_model_cfg) or (
                    par_model_cfg["get-result"] not in ["best", "mean"]
                ):
                    par_model_cfg["get-result"] = "best"
            else:
                model_set = [par_model_cfg["model"]]

            if "grid-search" not in par_model_cfg:
                par_model_cfg["grid-search"] = False
            else:
                par_model_cfg[par_name] = corr_type(value)

            if par_model_cfg["model"] != "auto":
                for model_name in model_set:
                    if model_name not in self.ml_models_list:
                        logging.error(
                            "В файле с ML-настройками в разделе [%s] модель %s не входят в список доступных ML-моделей. Доступные модели: %s",
                            par_model_key,
                            model_name,
                            self.ml_models_list,
                        )
                        return {}

            model_params_user = {}
            for par_name, value in par_model_cfg.items():
                if (
                    par_name != "model"
                    and par_name != "grid-search"
                    and par_name != "model-set"
                    and par_name != "get-result"
                ):
                    model_params_user[par_name] = value

            for model_name in model_set:
                # Получаем объект сигнатуры
                sig = inspect.signature(self.ml_models[model_name]["cls"])
                allowed_params = list(sig.parameters.keys())

                for par_name, par_value in model_params_user.items():
                    if par_name not in allowed_params:
                        logging.error(
                            "В файле с ML-настройками в разделе [%s] для модели %s использовано недопустимое имя гиперпараметра: %s. Доступные гиперпараметры: %s",
                            par_model_key,
                            model_name,
                            par_name,
                            allowed_params,
                        )
                        return {}
                    else:
                        par_model_cfg[par_name] = corr_type(par_value)

        return cfg_dict

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

    @staticmethod
    def _get_user_model_params(model_cfg) -> dict:

        model_params = {}
        for par_name, value in model_cfg.items():
            if (
                par_name != "model"
                and par_name != "grid-search"
                and par_name != "model-set"
            ):
                model_params[par_name] = value

        return model_params

    def _get_ml_forecast(
        self,
        model_cfg,  # конкретная модель или auto (т.е. перебор по всем доступным для построения наилучшей)
        # или autoset и дальше указать model-set=[..., ..., ...] (перебор по моделям только из этого набора)
        x_train: list,
        y_train: list,
        x_past_predict: list,
        x_future_predict: list,
    ) -> tuple[list, list]:

        if model_cfg["model"] == "auto":
            logging.info(
                "Автоматический перебор всех доступных моделей машинного обучения для получения прогноза"
            )
            model_set = self.ml_models_list

            if model_cfg["grid-search"]:
                logging.info(
                    "Использование GridSearchCV для подбора гиперпараметров для всех моделей машинного обучения"
                )
            else:
                model_params_user = self._get_user_model_params(model_cfg)

                if model_params_user:
                    logging.info(
                        "Использование пользовательских гиперпараметров для всех моделей машинного обучения: %s",
                        model_params_user,
                    )
                else:
                    logging.info(
                        "Использование стандартных гиперпараметров для всех моделей машинного обучения"
                    )

        elif model_cfg["model"] == "autoset":
            logging.info(
                "Автоматический перебор выбранных моделей машинного обучения для получения прогноза: %s",
                model_cfg["model-set"],
            )
            model_set = model_cfg["model-set"]

            if model_cfg["grid-search"]:
                logging.info(
                    "Использование GridSearchCV для подбора гиперпараметров для всех моделей машинного обучения"
                )
            else:
                model_params_user = self._get_user_model_params(model_cfg)

                if model_params_user:
                    logging.info(
                        "Использование пользовательских гиперпараметров для всех моделей машинного обучения: %s",
                        model_params_user,
                    )
                else:
                    logging.info(
                        "Использование стандартных гиперпараметров для всех моделей машинного обучения"
                    )
        else:
            logging.info(
                "Использование модели машинного обучения %s для получения прогноза",
                model_cfg["model"],
            )
            model_set = [model_cfg["model"]]

            if model_cfg["grid-search"]:
                logging.info(
                    "Использование GridSearchCV для подбора гиперпараметров модели машинного обучения"
                )
            else:
                model_params_user = self._get_user_model_params(model_cfg)

                if model_params_user:
                    logging.info(
                        "Использование пользовательских гиперпараметров для модели машинного обучения: %s",
                        model_params_user,
                    )
                else:
                    logging.info(
                        "Использование стандартных гиперпараметров для модели машинного обучения"
                    )

        for model_name in model_set:
            logging.info(
                "Построение прогноза с помощью модели машинного обучения %s",
                model_name,
            )

            model_cls = self.ml_models[model_name]["cls"]

            if model_cfg["grid-search"]:
                param_grid = self.ml_models[model_name]["param_grid"]

                model = GridSearchCV(model_cls(), param_grid, cv=5)
                model.fit(np.array(x_train).reshape(-1, 1), y_train)

                # later out model.best_params_ to log and verbose-file
                # r2_score(y_train, y_test)
                # y_test = model.best_estimator_.predict(
                #     np.array(x_train).reshape(-1, 1)
                # )

                y_past_predict = model.best_estimator_.predict(
                    np.array(x_past_predict).reshape(-1, 1)
                )
                y_future_predict = model.best_estimator_.predict(
                    np.array(x_future_predict).reshape(-1, 1)
                )
            else:
                if model_params_user:
                    model = model_cls(**model_params_user)
                else:
                    model = model_cls()

                model.fit(np.array(x_train).reshape(-1, 1), y_train)

                # later out model.params_ to log and verbose-file
                # r2_score(y_train, y_test)
                # y_test = model.best_estimator_.predict(
                #     np.array(x_train).reshape(-1, 1)
                # )

                y_past_predict = model.predict(np.array(x_past_predict).reshape(-1, 1))
                y_future_predict = model.predict(
                    np.array(x_future_predict).reshape(-1, 1)
                )

        return list(y_past_predict), list(y_future_predict)

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

        if par_short_name in self.cfg_sections:
            # use specific ml-model
            logging.info(
                "Установка специальных настроек модели машинного обучения для параметра %s",
                par_short_name,
            )
            par_model_key = par_short_name
        else:
            # use default ml-model (under "default" key in config_ml.ini)
            logging.info(
                "Установка модели машинного обучения по умолчанию ([default]) для параметра %s",
                par_short_name,
            )
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
