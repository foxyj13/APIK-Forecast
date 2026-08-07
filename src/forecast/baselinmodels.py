"""Базовые модели для сравнения с ML-моделями."""

import numpy as np


class BiasModel:
    """Модель смещения (y = x + b)"""

    def __init__(self):
        self.bias_ = 0.0

    def fit(self, x_arr, y_arr):
        self.bias_ = (np.array(y_arr) - np.array(x_arr)).mean()

    def predict(self, x_arr):
        return list(np.array(x_arr) + self.bias_)


class ScalingModel:
    """Модель масштабирования (y = a * x)"""

    def __init__(self):
        self.scale_ = 1.0

    def fit(self, x_arr, y_arr):
        x = np.array(x_arr)
        y = np.array(y_arr)

        x[x == 0] = np.nan

        self.scale_ = np.nanmean(y / x)

    def predict(self, x_arr):
        return list(np.array(x_arr) * self.scale_)


# class NaiveMean:
#     """Базовая модель: прогноз средним значением (среднее по тренировочной далее принимается за прогнозное)"""

#     def __init__(self):
#         pass

#     def fit(self, X, y):
#         self.mean_ = y.mean()

#     def predict(self, X):
#         return [self.mean_] * len(X)


# class NaiveLast:
#     """Наивный прогноз (последнее значение тренировочной далее принимается за прогнозное)"""

#     def __init__(self):
#         pass

#     def fit(self, X, y):
#         self.last_ = y.iloc[-1]

#     def predict(self, X):
#         return [self.last_] * len(X)


# class NaiveSeasonal:
#     """Суточный наивный прогноз (выбираются последние сутки и далее принимается за прогнозное)"""

#     def __init__(self):
#         pass
