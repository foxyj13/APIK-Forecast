"""Базовые модели для сравнения с ML-моделями."""


class BiasModel:
    """Модель смещения (y = x + b)"""

    def __init__(self):
        pass

    def fit(self, X, y):
        self.bias_ = (y - X).mean()

    def predict(self, X):
        return X + self.bias_


class ScalingModel:
    """Модель масштабирования (y = a * x)"""

    def __init__(self):
        pass

    def fit(self, X, y):
        self.scale_ = (y / X).mean()

    def predict(self, X):
        return X * self.scale_


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
