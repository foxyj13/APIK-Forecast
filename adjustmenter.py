import inspect
import logging
import sys

import numpy as np
import pandas as pd

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
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.holtwinters import Holt
from baselinmodels import BiasModel
from baselinmodels import ScalingModel

from sklearn.metrics import root_mean_squared_error, r2_score, mean_absolute_error
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
        self.exp_models = {"Holt", "ExponentialSmoothing", "SimpleExpSmoothing"}
        self.base_models = {"BiasModel", "ScalingModel"}

        self.inner_metrics = {"r2", "rmse", "mae"}

        self.config_keys_system = [
            "model",
            "model-set",
            "grid-search",
            "get-result",
            "best-result-metrics",
        ]
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
            # Будут ли все веса модели строго неотрицательными
            "positive": [True, False],
        }
        ml_models["LinearRegression"]["default_params"] = {}

        ml_models["Ridge"] = {}
        ml_models["Ridge"]["cls"] = Ridge
        ml_models["Ridge"]["param_grid"] = {
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
        ml_models["Ridge"]["default_params"] = {}

        ml_models["Lasso"] = {}
        ml_models["Lasso"]["cls"] = Lasso
        ml_models["Lasso"]["param_grid"] = {
            # Коэффициент силы регуляризации (от слабой к сильной)
            "alpha": np.logspace(
                -4, 2, 7
            ),  # [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
            # Нужно ли рассчитывать свободный коэффициент
            "fit_intercept": [True, False],
            # Максимальное число итераций (для Lasso важно, так как оно сходится дольше)
            "max_iter": [1000, 5000],
        }  # Для подбора alpha лучше использовать LassoCV вместо стандартного GridSearchCV
        ml_models["Lasso"]["default_params"] = {}

        ml_models["ElasticNet"] = {}
        ml_models["ElasticNet"]["cls"] = ElasticNet
        ml_models["ElasticNet"]["param_grid"] = {
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
        ml_models["ElasticNet"]["default_params"] = {}

        ml_models["KNeighborsRegressor"] = {}
        ml_models["KNeighborsRegressor"]["cls"] = KNeighborsRegressor
        ml_models["KNeighborsRegressor"]["param_grid"] = {
            # Количество соседей
            "n_neighbors": [5, 7, 10, 13, 15],
            # Весовая функция
            "weights": ["uniform", "distance"],
            # Метрика расстояния
            "metric": ["euclidean", "manhattan", "minkowski"],
            # Степенной параметр для метрики Минковского
            "p": [1, 2],
        }
        ml_models["KNeighborsRegressor"]["default_params"] = {}

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
        ml_models["DecisionTreeRegressor"]["default_params"] = {}

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
        ml_models["RandomForestRegressor"]["default_params"] = {}

        ml_models["GradientBoostingRegressor"] = {}
        ml_models["GradientBoostingRegressor"]["cls"] = GradientBoostingRegressor
        ml_models["GradientBoostingRegressor"]["param_grid"] = {
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
        ml_models["GradientBoostingRegressor"]["default_params"] = {}

        ml_models["LGBMRegressor"] = {}
        ml_models["LGBMRegressor"]["cls"] = LGBMRegressor
        ml_models["LGBMRegressor"]["param_grid"] = {
            # Количество деревьев
            "n_estimators": [10, 50, 100, 200, 500],
            # Скорость обучения
            "learning_rate": [0.01, 0.05, 0.1, 0.2],
            # Максимальная глубина каждого дерева
            "max_depth": [None, 2, 5, 10],
            # Коэффициент случайной субвыборки признаков
            "colsample_bytree": [0.8, 1.0],
        }
        ml_models["LGBMRegressor"]["default_params"] = {}

        ml_models["XGBRegressor"] = {}
        ml_models["XGBRegressor"]["cls"] = XGBRegressor
        ml_models["XGBRegressor"]["param_grid"] = {
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
        ml_models["XGBRegressor"]["default_params"] = {}

        ml_models["SimpleExpSmoothing"] = {}
        ml_models["SimpleExpSmoothing"]["cls"] = SimpleExpSmoothing
        ml_models["SimpleExpSmoothing"]["param_grid"] = {}
        # ml_models["SimpleExpSmoothing"]["param_grid"] = {
        #     # Определяет способ выбора стартового значения уровня (с чего начнется сглаживание).
        #     "initialization_method": ["estimated", "heuristic"],
        #     # Преобразование Бокса-Кокса. Помогает стабилизировать дисперсию (разброс) данных перед прогнозированием.
        #     # 'log' полезен, если ночью дисперсия падает, а днем растет
        #     "use_boxcox": [False, "log"],
        # }
        ml_models["SimpleExpSmoothing"]["default_params"] = {}

        ml_models["ExponentialSmoothing"] = {}
        ml_models["ExponentialSmoothing"]["cls"] = ExponentialSmoothing
        ml_models["ExponentialSmoothing"]["param_grid"] = {}
        # ml_models["ExponentialSmoothing"]["param_grid"] = {
        #     # Характер тренда. Может быть отсутствующим (только суточный цикл) (None), аддитивным ('add') или мультипликативным ('mul')
        #     "trend": ["add", None, "mul"],
        #     # Характер сезонных колебаний. Может быть отсутствующим (None), аддитивным ('add') или мультипликативным ('mul')
        #     # 'mul' идеален, если дневные пики пропорциональны общему росту ряда
        #     "seasonal": ["add", "mul", None],
        #     # Включение затухания тренда. На часовых данных затухание (True) почти всегда повышает точность, так как тренд не может расти бесконечно.
        #     "damped_trend": [True, False],
        #     # Фиксируем суточный цикл (при желании можно протестировать недельную сезонность - 168 часав, но она может не работать из-за недостатка данных для обучения модели)
        #     "seasonal_periods": [24],
        # }
        ml_models["ExponentialSmoothing"]["default_params"] = {
            "seasonal_periods": 24,
            "seasonal": "add",
            "trend": "add",
            "damped_trend": True,
        }

        ml_models["Holt"] = {}
        ml_models["Holt"]["cls"] = Holt
        ml_models["Holt"]["param_grid"] = {}
        # ml_models["Holt"]["param_grid"] = {
        #     "initialization_method": ["estimated"],
        #     # Тип тренда (линейный или экспоненциальный). Линейный тренд обычно более устойчивый, в то время как экспоненциальный может улетать в бесконечность при прогнозировании на дальнюю перспективу.
        #     "exponential": [False],
        #     # Включение затухания тренда. На часовых данных затухание (True) почти всегда повышает точность, так как тренд не может расти бесконечно.
        #     "damped_trend": [True, False],
        # }
        ml_models["Holt"]["default_params"] = {}

        ml_models["BiasModel"] = {}
        ml_models["BiasModel"]["cls"] = BiasModel
        ml_models["BiasModel"]["param_grid"] = {}
        ml_models["BiasModel"]["default_params"] = {}

        ml_models["ScalingModel"] = {}
        ml_models["ScalingModel"]["cls"] = ScalingModel
        ml_models["ScalingModel"]["param_grid"] = {}
        ml_models["ScalingModel"]["default_params"] = {}

        return ml_models

    def _check_config_models(self, config) -> dict:

        def get_user_model_params(model_cfg) -> dict:
            model_params = {}
            for par_name, value in model_cfg.items():
                if par_name not in self.config_keys_system:
                    model_params[par_name] = corr_type(value)

            return model_params

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

        logging.info("Проверка заданных ML-настроек")

        cfg_dict = {s: dict(config.items(s)) for s in config.sections()}

        for par_model_key, par_model_cfg in cfg_dict.items():
            logging.info("Проверка раздела [%s]", par_model_key)

            # Определить набор моделей для перебора в зависимости от значения ключа "model"
            # (auto - все доступные модели, autoset - модели из набора, указанных в "model-set", конкретная модель - только она)
            logging.info("[%s] Определение набора моделей для расчетов", par_model_key)
            if par_model_cfg["model"].lower() == "auto":
                model_set = self.ml_models_list
                logging.info(
                    "[%s] Для расчетов будут использованы все доступные модели: %s",
                    par_model_key,
                    model_set,
                )
            elif par_model_cfg["model"].lower() == "autoset":
                if "model-set" not in par_model_cfg:
                    logging.error(
                        "[%s] В файле с ML-настройками в разделе [%s] указано значение 'autoset' для ключа 'model', но не указан ключ 'model-set' с перечнем моделей для перебора. Необходимо указать 'model-set' с перечнем моделей из доступных: %s",
                        par_model_key,
                        par_model_key,
                        self.ml_models_list,
                    )
                    return {}
                else:
                    model_set = [
                        model.strip() for model in par_model_cfg["model-set"].split(",")
                    ]
                    logging.info(
                        "[%s] Для расчетов будет использован следующий поднабор моделей: %s",
                        par_model_key,
                        model_set,
                    )
            else:
                model_set = [par_model_cfg["model"]]
                logging.info(
                    "[%s] Для расчетов будет использована только одна модель: %s",
                    par_model_key,
                    model_set,
                )

            par_model_cfg["model-set"] = model_set

            if par_model_cfg["model"].lower() != "auto":
                logging.info(
                    "[%s] Проверка наличия указанных в конфигурации моделей в списке доступных моделей для построения прогноза",
                    par_model_key,
                )
                for model_name in model_set:
                    if model_name not in self.ml_models_list:
                        logging.error(
                            "[%s] В файле с ML-настройками в разделе [%s] модель %s не входят в список доступных ML-моделей. Доступные модели: %s",
                            par_model_key,
                            par_model_key,
                            model_name,
                            self.ml_models_list,
                        )
                        return {}

            logging.info(
                "[%s] Проверка указания кастомного набора предикторов", par_model_key
            )

            # Определяем метрику для внутренней оценки качества прогноза и по которой будет выбираться наилучший результат
            if "best-result-metrics" not in par_model_cfg:
                par_model_cfg["best-result-metrics"] = "r2"
                logging.info(
                    "[%s] Для внутренней оценки качества прогноза на тренировочном наборе будет использована метрика %s",
                    par_model_key,
                    par_model_cfg["best-result-metrics"],
                )
            else:
                par_model_cfg["best-result-metrics"] = par_model_cfg[
                    "best-result-metrics"
                ].lower()
                if par_model_cfg["best-result-metrics"] in self.inner_metrics:
                    logging.info(
                        "[%s] Для внутренней оценки качества прогноза на тренировочном наборе будет использована метрика %s",
                        par_model_key,
                        par_model_cfg["best-result-metrics"],
                    )
                else:
                    logging.info(
                        "[%s] Указанная недопустимая метрика для внутренней оценки качества (%s). Вместо нее будет использована метрика по умолчанию (r2)",
                        par_model_key,
                        par_model_cfg["best-result-metrics"],
                    )
                    par_model_cfg["best-result-metrics"] = "r2"

            # Определить, что результат перебора по моделям нужно брать "best" (т.е. модель с наилучшим R2 на тренировочных данных)
            # или "mean" (т.е. усреднение прогнозов всех моделей)
            if ("get-result" not in par_model_cfg) or (
                par_model_cfg["get-result"] not in {"best", "mean"}
            ):
                par_model_cfg["get-result"] = "best"
                logging.info(
                    "[%s] При использовании для расчетов набора моделей в качестве результата будет использован наилучший по метрике %s",
                    par_model_key,
                    par_model_cfg["best-result-metrics"],
                )
            else:
                if par_model_cfg["get-result"] == "mean":
                    logging.info(
                        "[%s] При использовании для расчетов набора моделей в качестве результата будет использовано среднее по расчетам всех моделей набора",
                        par_model_key,
                    )
                else:
                    logging.info(
                        "[%s] При использовании для расчетов набора моделей в качестве результата будет использован наилучший по метрике %s",
                        par_model_key,
                        par_model_cfg["best-result-metrics"],
                    )

            # Если явно не указано использовать или нет GridSearchCV для подбора гиперпараметров, то использовать значение по умолчанию (False)
            if "grid-search" not in par_model_cfg:
                par_model_cfg["grid-search"] = False
                logging.info(
                    "[%s] Использование GridSearchCV по умолчанию отключено. В расчете использовано не будет",
                    par_model_key,
                )
            else:
                par_model_cfg["grid-search"] = corr_type(par_model_cfg["grid-search"])
                if par_model_cfg["grid-search"]:
                    logging.info(
                        "[%s] Подключено использование GridSearchCV", par_model_key
                    )
                else:
                    logging.info(
                        "[%s] Отключено использование GridSearchCV", par_model_key
                    )

            # GridSearchCV нельзя использовать для моделей  Holt, ExponentialSmoothing, SimpleExpSmoothing, BiasModel, ScalingModel
            if set(model_set) & (self.exp_models | self.base_models):
                par_model_cfg["grid-search"] = False
                logging.info(
                    "[%s] Использование GridSearchCV невозможно с базовыми и экспоненциальными моделями (%s; %s). В расчете GridSearchCV использован не будет",
                    par_model_key,
                    self.exp_models,
                    self.base_models,
                )

            model_params_user = {}
            if not par_model_cfg["grid-search"]:
                logging.info(
                    "[%s] Получение списка гиперпараметров, заданных пользователем",
                    par_model_key,
                )
                model_params_user = get_user_model_params(par_model_cfg)

                if model_params_user:
                    if set(model_set) & self.base_models:
                        logging.info(
                            "[%s] В списке моделей есть базовая. Пользовательские гиперпараметры игнорируются",
                            par_model_key,
                        )
                        model_params_user = {}
                    else:
                        logging.info(
                            "[%s] Проверка допустимости имен указанных пользователем гиперпараметров для каждой модели в наборе",
                            par_model_key,
                        )
                        for model_name in model_set:
                            # Получаем объект сигнатуры
                            sig = inspect.signature(self.ml_models[model_name]["cls"])
                            allowed_params = list(sig.parameters.keys())

                            for par_name in model_params_user:
                                if par_name not in allowed_params:
                                    logging.error(
                                        "[%s] В файле с ML-настройками для модели %s использовано недопустимое имя гиперпараметра: %s. Доступные гиперпараметры: %s",
                                        par_model_key,
                                        model_name,
                                        par_name,
                                        allowed_params,
                                    )
                                    return {}
                else:
                    logging.info(
                        "[%s] Дополнительных гиперпараметров не задано", par_model_key
                    )
            else:
                logging.info(
                    "[%s] При использовании GridSearchCV пользовательские гиперпараметры игнорируются",
                    par_model_key,
                )

            par_model_cfg["model-params-user"] = model_params_user

            if par_model_cfg["model-params-user"]:
                logging.info(
                    "[%s] Для моделей будут использованы следующие гиперпараметры, заданные пользователем: %s",
                    par_model_key,
                    par_model_cfg["model-params-user"],
                )

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
    def _get_train_predict_sets_common(
        forecast_type: str,
        len_past: int,
        len_future: int,
        target: list,
        idx_target_none: list,
        predictor_default_names: list,
        predictor_data: dict,
        time_depth: str,
        time_forecast: str,
    ) -> dict:
        """Формирование набора данных для работы со всеми моделями кроме базовых и экспоненциальных"""

        def collect_predictors(
            list_names: list, dict_data: dict, time_type: str, time_period: str
        ) -> list[list]:
            predictor_list = []
            for pr_name in list_names:
                predictor_list.append(dict_data[pr_name][time_type][time_period])

            return [list(pr) for pr in zip(*predictor_list)]

        def check_names(some_names: list, all_names: list) -> bool:
            wrong_some_names = set(some_names) - set(all_names)
            if len(wrong_some_names) == 0:
                return True
            else:
                logging.error(
                    "Ошибка: некорректно заданы имена предикторов %s", wrong_some_names
                )
                return False

        if predictor_default_names and check_names(
            predictor_default_names, list(predictor_data.keys())
        ):
            predictor_names = predictor_default_names
        else:
            predictor_names = []

        if predictor_names:
            if forecast_type == "mod":
                predictor_past = collect_predictors(
                    predictor_names, predictor_data, "past", time_depth
                )
                predictor_future = collect_predictors(
                    predictor_names, predictor_data, "future", time_forecast
                )
            elif forecast_type == "stat":
                predictor_past = collect_predictors(
                    predictor_names, predictor_data, "prepast", time_depth
                )
                predictor_future = collect_predictors(
                    predictor_names, predictor_data, "past", time_depth
                )
                predictor_future = predictor_future[-len_future:]
            else:
                return {
                    "status": -1,
                    "x_train": [],
                    "y_train": [],
                    "predictors_past": [],
                    "idx_predictor_past_none": [],
                    "predictors_future": [],
                    "idx_predictor_future_none": [],
                }

            idx_predictor_past_none = [
                idx
                for idx, val_list in enumerate(predictor_past)
                if (None in val_list) or (np.any(np.isnan(val_list)))
            ]
            idx_predictor_future_none = [
                idx
                for idx, val_list in enumerate(predictor_future)
                if (None in val_list) or (np.any(np.isnan(val_list)))
            ]

            idx_none_past = set(idx_target_none) | set(idx_predictor_past_none)

            if len(idx_none_past) > (len(target) / 10.0):
                return {
                    "status": 0,
                    "x_train": [],
                    "y_train": [],
                    "predictors_past": [],
                    "idx_predictor_past_none": [],
                    "predictors_future": [],
                    "idx_predictor_future_none": [],
                }
            else:
                x_train = [
                    val
                    for idx, val in enumerate(predictor_past)
                    if idx not in idx_none_past  # | idx_del_time)
                ]
                y_train = [
                    val
                    for idx, val in enumerate(target)
                    if idx not in idx_none_past  # | idx_del_time)
                ]
                predictors_past_no_none = [
                    val
                    for idx, val in enumerate(predictor_past)
                    if idx not in idx_predictor_past_none
                ]
                predictors_future_no_none = [
                    val
                    for idx, val in enumerate(predictor_future)
                    if idx not in idx_predictor_future_none
                ]

                return {
                    "status": 1,
                    "x_train": x_train,
                    "y_train": y_train,
                    "predictors_past": predictors_past_no_none,
                    "idx_predictor_past_none": idx_predictor_past_none,
                    "predictors_future": predictors_future_no_none,
                    "idx_predictor_future_none": idx_predictor_future_none,
                }
        else:
            return {
                "status": -1,
                "x_train": [],
                "y_train": [],
                "predictors_past": [],
                "idx_predictor_past_none": [],
                "predictors_future": [],
                "idx_predictor_future_none": [],
            }

    @staticmethod
    def _get_train_predict_sets_basemodels(
        forecast_type: str,
        len_past: int,
        len_future: int,
        target: list,
        idx_target_none: list,
        predictor_default_names: list,
        predictor_data: dict,
        time_depth: str,
        time_forecast: str,
    ) -> dict:
        """Получение наборов данных для работы с базовыми моделями (может быть только 1 предиктор)"""

        if predictor_default_names:
            if len(predictor_default_names) == 1:
                predictor_name = predictor_default_names[0]
            else:
                return {
                    "status": -2,
                    "x_train": [],
                    "y_train": [],
                    "predictors_past": [],
                    "idx_predictor_past_none": [],
                    "predictors_future": [],
                    "idx_predictor_future_none": [],
                }
        else:
            return {
                "status": -1,
                "x_train": [],
                "y_train": [],
                "predictors_past": [],
                "idx_predictor_past_none": [],
                "predictors_future": [],
                "idx_predictor_future_none": [],
            }

        if forecast_type == "mod":
            predictor_past = predictor_data[predictor_name]["past"][time_depth]
            predictor_future = predictor_data[predictor_name]["future"][time_forecast]
        elif forecast_type == "stat":
            predictor_past = predictor_data[predictor_name]["prepast"][time_depth]
            predictor_future = predictor_data[predictor_name]["past"][time_depth]
            predictor_future = predictor_future[-len_future:]
        else:
            return {
                "status": -1,
                "x_train": [],
                "y_train": [],
                "predictors_past": [],
                "idx_predictor_past_none": [],
                "predictors_future": [],
                "idx_predictor_future_none": [],
            }

        idx_predictor_past_none = [
            idx
            for idx, val in enumerate(predictor_past)
            if (val is None) or (np.isnan(val))
        ]
        idx_predictor_future_none = [
            idx
            for idx, val in enumerate(predictor_future)
            if (val is None) or (np.isnan(val))
        ]

        idx_none_past = set(idx_target_none) | set(idx_predictor_past_none)

        if len(idx_none_past) > (len(target) / 10.0):
            return {
                "status": 0,
                "x_train": [],
                "y_train": [],
                "predictors_past": [],
                "idx_predictor_past_none": [],
                "predictors_future": [],
                "idx_predictor_future_none": [],
            }
        else:
            x_train = [
                val
                for idx, val in enumerate(predictor_past)
                if idx not in idx_none_past  # | idx_del_time)
            ]
            y_train = [
                val
                for idx, val in enumerate(target)
                if idx not in idx_none_past  # | idx_del_time)
            ]
            predictors_past_no_none = [
                val
                for idx, val in enumerate(predictor_past)
                if idx not in idx_predictor_past_none
            ]
            predictors_future_no_none = [
                val
                for idx, val in enumerate(predictor_future)
                if idx not in idx_predictor_future_none
            ]

            return {
                "status": 1,
                "x_train": x_train,
                "y_train": y_train,
                "predictors_past": predictors_past_no_none,
                "idx_predictor_past_none": idx_predictor_past_none,
                "predictors_future": predictors_future_no_none,
                "idx_predictor_future_none": idx_predictor_future_none,
            }

    @staticmethod
    def _get_train_predict_sets_expmodels(
        len_past: int, len_future: int, obs: list, idx_none: list
    ) -> dict:
        """Получение обучающего ряда для экспоненциальных моделей (сам ряд наблюдений является предиктором)"""

        if idx_none:
            # Заполнить None
            obs_series = pd.Series(obs, dtype=float)
            filled_obs_series = obs_series.interpolate(method="linear").ffill().bfill()
            return {
                "status": 1,
                "train": filled_obs_series.tolist(),
                "len_future": len_future,
            }
        else:
            return {"status": 1, "train": obs, "len_future": len_future}

    def _get_train_predict_sets(
        self,
        forecast_type: str,
        len_past: int,
        len_future: int,
        target: list,
        predictor_names: list,
        predictor_data: dict,
    ) -> dict:
        # status = 1: все ОК
        # status = 0: пропусктов > 10 %
        # status = -1: не указаны предикторы
        # status = -2: предикторов более, чем 1

        idx_target_none = [
            idx for idx, val in enumerate(target) if (val is None) or (np.isnan(val))
        ]

        if idx_target_none and len(idx_target_none) > len(target) / 10:
            common_models_set = {
                "status": 0,
                "x_train": [],
                "y_train": [],
                "predictors_past": [],
                "idx_predictor_past_none": [],
                "predictors_future": [],
                "idx_predictor_future_none": [],
            }
            base_models_set = {
                "status": 0,
                "x_train": [],
                "y_train": [],
                "predictors_past": [],
                "idx_predictor_past_none": [],
                "predictors_future": [],
                "idx_predictor_future_none": [],
            }
            exp_models_set = {"status": 0, "train": []}

            prepared_sets = {
                "common": common_models_set,
                "base": base_models_set,
                "exp": exp_models_set,
            }
        else:
            common_models = self._get_train_predict_sets_common(
                forecast_type,
                len_past,
                len_future,
                target,
                idx_target_none,
                predictor_names,
                predictor_data,
                self.time_depth,
                self.time_forecast,
            )

            base_models = self._get_train_predict_sets_basemodels(
                forecast_type,
                len_past,
                len_future,
                target,
                idx_target_none,
                predictor_names,
                predictor_data,
                self.time_depth,
                self.time_forecast,
            )

            exp_models = self._get_train_predict_sets_expmodels(
                len_past, len_future, target, idx_target_none
            )

            prepared_sets = {
                "common": common_models,
                "base": base_models,
                "exp": exp_models,
            }

        return prepared_sets

    def _get_ml_forecast(
        self,
        forecast_type: str,
        parameter_key: str,
        train_predict_sets: dict,
    ) -> tuple[list, list]:

        def logging_err_status(model_type: str) -> None:
            if train_predict_sets[model_type]["status"] == 0:
                logging.error(
                    "Слишком много пропусков в обучающих данных (более 10 %). Пропуск обучения модели. Пропуск расчета прогноза на ней."
                )
            elif train_predict_sets[model_type]["status"] == -1:
                logging.error(
                    "Не задано ни одного предиктора. Обучение модели невозможно. Пропуск расчета прогноза на этой модели."
                )
            elif train_predict_sets[model_type]["status"] == -2:
                logging.error(
                    "Задано более 1 предиктора (но допустим только 1). Пропуск обучения модели. Пропуск расчета прогноза на этой модели."
                )
            else:
                logging.error(
                    "Некорректный обучающий набор данных. Пропуск обучения модели. Пропуск расчета прогноза на этой модели."
                )

        model_cfg = self.config[parameter_key]

        model_set = model_cfg["model-set"]
        model_params_user = model_cfg["model-params-user"]
        grid_search_flag = model_cfg["grid-search"]
        get_result_way = model_cfg["get-result"]
        if "best-result-metrics" in model_cfg:
            best_result_metrics = model_cfg["best-result-metrics"].lower()
        else:
            best_result_metrics = "r2"

        # Информирование об используемом наборе моделей
        if model_cfg["model"] == "auto":
            logging.info(
                "Автоматический перебор всех доступных моделей машинного обучения для получения прогноза: %s",
                model_set,
            )
        elif model_cfg["model"] == "autoset":
            logging.info(
                "Автоматический перебор выбранных моделей машинного обучения для получения прогноза: %s",
                model_set,
            )
        else:
            logging.info(
                "Использование модели машинного обучения %s для получения прогноза",
                model_set,
            )

        # Информирование об использовании GridSearchCV и пользовательских гиперпараметрах
        if grid_search_flag:
            logging.info(
                "Использование GridSearchCV для подбора наилучшей конфигурации гиперпараметров"
            )
        else:
            if model_params_user:
                logging.info(
                    "Использование пользовательских гиперпараметров для выбранных моделей машинного обучения: %s",
                    model_params_user,
                )
            else:
                logging.info(
                    "Использование стандартных гиперпараметров для выбранных моделей машинного обучения"
                )

        # Далее: расчетная часть
        result_predict = {}
        for model_idx, model_name in enumerate(model_set):
            logging.info(
                "Построение прогноза с помощью модели машинного обучения %s",
                model_name,
            )

            try:
                model_cls = self.ml_models[model_name]["cls"]

                if grid_search_flag and self.ml_models[model_name]["param_grid"]:
                    if model_name in self.exp_models | self.base_models:
                        logging.warning(
                            "Модель %s относится к классу базовых или экспеоненциальных, к которым не может быть применен GridSearchCV. Пропускаю расчет на этой модели",
                            model_name,
                        )
                    else:
                        model_type = "common"

                        if train_predict_sets[model_type]["status"]:  # т.е. status == 1
                            x_train = train_predict_sets[model_type]["x_train"]
                            y_train = train_predict_sets[model_type]["y_train"]
                            x_past_predict = train_predict_sets[model_type][
                                "predictors_past"
                            ]
                            x_future_predict = train_predict_sets[model_type][
                                "predictors_future"
                            ]

                            param_grid = self.ml_models[model_name]["param_grid"]

                            model = GridSearchCV(model_cls(), param_grid, cv=5)
                            model.fit(np.array(x_train), y_train)

                            # TODO: later out model.best_params_ to log and verbose-file
                            result_predict[model_idx] = {}

                            y_test = model.best_estimator_.predict(np.array(x_train))
                            # !!! TODO:
                            # Диагностический вывод будет всех метрик
                            result_predict[model_idx]["r2"] = r2_score(y_train, y_test)
                            result_predict[model_idx]["rmse"] = root_mean_squared_error(
                                y_train, y_test
                            )
                            result_predict[model_idx]["mae"] = mean_absolute_error(
                                y_train, y_test
                            )

                            result_predict[model_idx]["y_past_predict"] = list(
                                model.best_estimator_.predict(np.array(x_past_predict))
                            )
                            result_predict[model_idx]["y_future_predict"] = list(
                                model.best_estimator_.predict(
                                    np.array(x_future_predict)
                                )
                            )

                            # Возвращение None на место, если они были
                            for idx in train_predict_sets[model_type][
                                "idx_predictor_past_none"
                            ]:
                                result_predict[model_idx]["y_past_predict"].insert(
                                    idx, np.nan
                                )

                            for idx in train_predict_sets[model_type][
                                "idx_predictor_future_none"
                            ]:
                                result_predict[model_idx]["y_future_predict"].insert(
                                    idx, np.nan
                                )

                        else:
                            logging_err_status(model_type)
                else:
                    result_predict[model_idx] = {}

                    if model_name in self.exp_models:
                        model_type = "exp"
                        if train_predict_sets[model_type]["status"]:  # т.е. status == 1
                            x_train = train_predict_sets[model_type]["train"]

                            if model_params_user:
                                model = model_cls(
                                    x_train,
                                    **(
                                        self.ml_models[model_name]["default_params"]
                                        | model_params_user
                                    )
                                ).fit()
                            else:
                                model = model_cls(
                                    x_train,
                                    **self.ml_models[model_name]["default_params"]
                                ).fit()

                            x_test = model.fittedvalues

                            # TODO: later out model.params to log and verbose-file

                            # !!! TODO:
                            # Диагностический вывод будет всех метрик
                            result_predict[model_idx]["r2"] = r2_score(x_train, x_test)
                            result_predict[model_idx]["rmse"] = root_mean_squared_error(
                                x_train, x_test
                            )
                            result_predict[model_idx]["mae"] = mean_absolute_error(
                                x_train, x_test
                            )

                            result_predict[model_idx]["y_past_predict"] = list(x_test)
                            result_predict[model_idx]["y_future_predict"] = list(
                                model.forecast(
                                    steps=train_predict_sets[model_type]["len_future"]
                                )
                            )
                        else:
                            logging_err_status(model_type)

                    else:
                        if model_name in self.base_models:
                            model_type = "base"
                            model = model_cls()
                        else:
                            model_type = "common"

                            if model_params_user:
                                model = model_cls(**model_params_user)
                            else:
                                model = model_cls()

                        if (
                            model_type == "base"
                            and train_predict_sets["base"]["status"]
                        ) or (
                            model_type == "common"
                            and train_predict_sets["common"]["status"]
                        ):
                            x_train = train_predict_sets[model_type]["x_train"]
                            y_train = train_predict_sets[model_type]["y_train"]
                            x_past_predict = train_predict_sets[model_type][
                                "predictors_past"
                            ]
                            x_future_predict = train_predict_sets[model_type][
                                "predictors_future"
                            ]

                            model.fit(np.array(x_train), y_train)

                            # TODO: later out model.params_ to log and verbose-file

                            y_test = model.predict(np.array(x_train))
                            # !!! TODO:
                            # Диагностический вывод будет всех метрик
                            result_predict[model_idx]["r2"] = r2_score(y_train, y_test)
                            result_predict[model_idx]["rmse"] = root_mean_squared_error(
                                y_train, y_test
                            )
                            result_predict[model_idx]["mae"] = mean_absolute_error(
                                y_train, y_test
                            )

                            result_predict[model_idx]["y_past_predict"] = list(
                                model.predict(np.array(x_past_predict))
                            )
                            result_predict[model_idx]["y_future_predict"] = list(
                                model.predict(np.array(x_future_predict))
                            )

                            # Возвращение None на место, если они были
                            for idx in train_predict_sets[model_type][
                                "idx_predictor_past_none"
                            ]:
                                result_predict[model_idx]["y_past_predict"].insert(
                                    idx, np.nan
                                )

                            for idx in train_predict_sets[model_type][
                                "idx_predictor_future_none"
                            ]:
                                result_predict[model_idx]["y_future_predict"].insert(
                                    idx, np.nan
                                )

                        else:
                            logging_err_status(model_type)
            except Exception as e:
                logging.error(
                    "Ошибка при построении прогноза с помощью модели машинного обучения %s: %s",
                    model_name,
                    str(e),
                )
                logging.info("Переход к следующей модели (если есть)")
                continue

        if result_predict and result_predict[0]:
            if len(model_set) == 1:
                y_past_predict = result_predict[0]["y_past_predict"]
                y_future_predict = result_predict[0]["y_future_predict"]
            else:
                if get_result_way == "best":
                    # См. по какой метрике лучшая (best_result_metrics). М.б. другая из self.inner_metrics
                    best_model_idx = max(
                        result_predict,
                        key=lambda idx: result_predict[idx][best_result_metrics],
                    )

                    y_past_predict = result_predict[best_model_idx]["y_past_predict"]
                    y_future_predict = result_predict[best_model_idx][
                        "y_future_predict"
                    ]

                elif get_result_way == "mean":
                    y_past_predict = np.mean(
                        [
                            result_predict[idx]["y_past_predict"]
                            for idx in result_predict
                        ],
                        axis=0,
                    )
                    y_future_predict = np.mean(
                        [
                            result_predict[idx]["y_future_predict"]
                            for idx in result_predict
                        ],
                        axis=0,
                    )
                else:
                    logging.error(
                        "Недопустимое значение для ключа 'get-result' в ML-конфигурации: %s. Допустимые значения: 'best', 'mean'",
                        get_result_way,
                    )
                    logging.info("Остановка программы")
                    sys.exit(1)
        else:
            logging.error(
                "Не удалось построить прогноз ни с одной из моделей машинного обучения. Будет возвращен прогноз без коррекции (т.е. глобальный прогноз)."
            )
            y_past_predict = []  # x_past_predict
            y_future_predict = []  # x_future_predict

        return list(y_past_predict), list(y_future_predict)

    def get_local_forecast(self, station: dict) -> dict:
        logging.info(
            "Формирование локального прогноза для станции %s (%s)",
            station["code"],
            station["full_name"],
        )

        if "om_time_past" in station:
            time_past = station["om_time_past"][self.time_depth]
            mod_time_future = station["om_time_future"][self.time_forecast]

            time_recent = station["om_time_past"]["recent"]
            idx_recent = time_past.index(time_recent)

            # len_prepast = len(station["om_time_prepast"][self.time_depth])
            len_past = len(station["om_time_past"][self.time_depth])
            len_future = len(station["om_time_future"][self.time_forecast])

            for par_short_name, parameter in station["parameters"].items():
                logging.info(
                    "Получение локального прогноза для параметра %s (код: %s)",
                    parameter["name"],
                    parameter["code"],
                )

                predictors_list = []

                if "om_time_prepast" in station:
                    logging.info("Расчет статистического прогноза")

                    forecast_type = "stat"

                    if parameter["db_predictors"]:
                        predictors_list = list(parameter["db_predictors"].keys())
                    else:
                        logging.info(
                            "Невозможно получить локальный прогноз для параметра %s (код: %s), т.к. отсутствуют предикторы",
                            parameter["name"],
                            parameter["code"],
                        )
                else:
                    logging.info("Расчет прогноза на основе глобального от Open-Meteo")

                    forecast_type = "mod"

                    if (
                        parameter["om_predictors"]
                        and parameter["om_predictors"][0] is not None
                        and parameter["om_predictors"][0].lower() != "none"
                    ):
                        predictors_list = parameter["om_predictors"]
                    else:
                        logging.info(
                            "Невозможно получить локальный прогноз для параметра %s (код: %s), т.к. отсутствуют предикторы",
                            parameter["name"],
                            parameter["code"],
                        )

                if predictors_list:
                    logging.info("Используемые предикторы: %s", predictors_list)

                    obs_data = parameter["data"][self.time_depth]
                    train_predict_sets = self._get_train_predict_sets(
                        forecast_type,
                        len_past,
                        len_future,
                        obs_data,
                        predictors_list,
                        station["om_parameters"],
                    )

                    if par_short_name in self.cfg_sections:
                        par_key = par_short_name
                    else:
                        par_key = "default"

                    mod_local_past, mod_local_future = self._get_ml_forecast(
                        forecast_type, par_key, train_predict_sets
                    )

                    parameter["om_data_local"] = {}
                    parameter["om_data_local"]["past"] = {}
                    parameter["om_data_local"]["future"] = {}

                    parameter["om_data_local_no_corr"] = {}
                    parameter["om_data_local_no_corr"]["past"] = {}
                    parameter["om_data_local_no_corr"]["future"] = {}

                    if mod_local_past:
                        parameter["om_data_local_no_corr"]["past"][
                            self.time_depth
                        ] = mod_local_past

                        mod_local_past_corr, corr_past_percent = (
                            self._check_corr_data_bounds(
                                data=mod_local_past,
                                min_val=parameter["min_value"],
                                max_val=parameter["max_value"],
                            )
                        )
                        parameter["om_data_local"]["past"][
                            self.time_depth
                        ] = mod_local_past_corr

                        logging.info(
                            "Скорректировано под допустимый диапазон %.2f %% значений прогноза на историческом периоде",
                            corr_past_percent,
                        )
                    else:
                        none_arr = [None for idx in range(len(time_past))]

                        parameter["om_data_local_no_corr"]["past"][
                            self.time_depth
                        ] = none_arr

                        parameter["om_data_local"]["past"][self.time_depth] = none_arr

                        logging.info(
                            "Локальный прогноз на исторический период отсутствует"
                        )

                    if mod_local_future:
                        parameter["om_data_local_no_corr"]["future"][
                            self.time_forecast
                        ] = mod_local_future

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
                            "Скорректировано под допустимый диапазон %.2f %% значений прогноза в будущее",
                            corr_future_percent,
                        )
                    else:
                        none_arr = [None for idx in range(len(mod_time_future))]

                        parameter["om_data_local_no_corr"]["future"][
                            self.time_forecast
                        ] = none_arr

                        parameter["om_data_local"]["future"][
                            self.time_forecast
                        ] = none_arr

                        logging.info("Локальный прогноз в будущее отсутствует")

                    if idx_recent:
                        parameter["om_data_local_no_corr"]["past"]["recent"] = (
                            parameter["om_data_local_no_corr"]["past"][self.time_depth][
                                idx_recent
                            ]
                        )
                        parameter["om_data_local"]["past"]["recent"] = parameter[
                            "om_data_local"
                        ]["past"][self.time_depth][idx_recent]
                    else:
                        parameter["om_data_local_no_corr"]["past"]["recent"] = (
                            parameter["om_data_local_no_corr"]["past"][self.time_depth][
                                -1
                            ]
                        )
                        parameter["om_data_local"]["past"]["recent"] = parameter[
                            "om_data_local"
                        ]["past"][self.time_depth][-1]

                    # TODO: если включен verbose, то записать в verbose-файл в формате JSON информацию о построенных прогнозах
                    # (какие модели были использованы, какие гиперпараметры были заданы, R2 на тренировочных данных, процент скорректированных значений прогноза и т.д.)
                    # 1 станция, 1 параметр - 1 файл с именем, например, "verbose_station{station_code}_par-{parameter_code}.json" в папке verbose_dir
                else:
                    logging.info(
                        "Невозможно получить локальный прогноз для параметра %s (код: %s), т.к. отсутствуют предикторы",
                        parameter["name"],
                        parameter["code"],
                    )

        else:
            logging.warning(
                "Отсутствуют данные для обучения модели. Невозможно построить локальный прогноз."
            )

        return station
