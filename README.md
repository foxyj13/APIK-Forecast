# APIK-Forecast

Software suite, designed for calculating and visualizing forecasts of key meteorological parameters, evaluating the quality of the resulting forecasts, and exporting the observational data, global forecasts, and generated local forecasts. 

## Overview

APIK-Forecast is a modular system for forecasting meteorological parameters that delivers enhanced accuracy for specific observation sites by correcting global forecasts using machine learning methods. 

## Features

- Calculation/refinement, visualization of a single forecast;
- Quality control and consolidated visualization of a forecast series;
- Export of observation and forecast data.

## Installation

```bash
git clone https://github.com/foxyj13/APIK-Forecast.git
cd APIK-Forecast
pip install -r requirements.txt
```

## Dependencies

- Python >= 3.8
- NumPy
- Pandas
- Matplotlib
- SQLAlchemy
- OpenPyXL 
- Open-Meteo Weather API
- Scikit-learn
- LightGBM
- XGBoost
- statsmodels

*See `requirements.txt` for the full list.*

## ML-models available to use

1. Baseline models: 
    - `BiasModel` (y = x + b),
    - `ScalingModel` (y = a * x);

2. Simple regressors:
    - `LinearRegression` (https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html),
    - `Ridge` (https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html),
    - `Lasso` (https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Lasso.html),
    - `ElasticNet` (https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.ElasticNet.html),
    - `KNeighborsRegressor` (https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KNeighborsRegressor.html),
    - `DecisionTreeRegressor` (https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeRegressor.html);

3. Ensemble models: 
    - `RandomForestRegressor` (https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html), 
    - `GradientBoostingRegressor` (https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingRegressor.html), 
    - `LGBMRegressor` (https://lightgbm.readthedocs.io/en/latest/index.html), 
    - `XGBRegressor` (https://xgboost.readthedocs.io/en/latest/index.html);
    
4. Exponential smoothing models: 
    - `SimpleExpSmoothing` (https://www.statsmodels.org/dev/generated/statsmodels.tsa.holtwinters.SimpleExpSmoothing.html), 
    - `Holt` (https://www.statsmodels.org/dev/generated/statsmodels.tsa.holtwinters.Holt.html), 
    - `ExponentialSmoothing` (https://www.statsmodels.org/dev/generated/statsmodels.tsa.holtwinters.ExponentialSmoothing.html).

## Quick Start
See the documentation for a detailed description (*Russian*): 
`./doc/APIK-Forecast_UserGuide_ru.pdf`

### Single forecast
1. Check for the existence of the following files and their settings: ​​`run_forecast.cgf`, `config.ini`, and `config_ml.ini`.
2. Verify the presence and correctness of the `xlsx-file` with the list of stations and meteorological parameters for which the forecast will be calculated.
3. Run the `run_forecast.bat` script (if on Windows) or `run_forecast.sh` (if on Linux).

### Forecast series and Quality control
1. Check for the existence of the following files and their settings: `​​run_qc.cgf`, `args_qc.ini`, `config.ini` (and `config_ml.ini` if it is necessary to calculate a series of forecasts).
2. Verify the presence and correctness of the `xlsx-file` with the list of stations and meteorological parameters for which the forecast will be calculated.
3. Run the `run_qc.bat` script (if on Windows) or `run_qc.sh` (if on Linux).

### Export data
1. Check for the existence of the following files and their settings: `​​run_export.cgf`, `args_export.ini` and `config.ini`.
2. Verify the presence of the `pkl-files` with the calculation information, forecasting results, and the data used.
3. Run the `run_export.bat` script (if on Windows) or `run_export.sh` (if on Linux).

## License

This project is licensed under the terms of the LICENSE.txt file.

## References

This work was supported by Grant No. 075-15-2024-533 from the Ministry of Science and Higher Education of the Russian Federation for the implementation of a major scientific project in priority areas of scientific and technological development (project title: "Fundamental research on the Baikal natural territory based on a system of interconnected fundamental methods, models, neural networks, and a digital platform for environmental monitoring"; reg. no. 124052100088-3).

## Citation

If you use this code in your research, please cite it:

```bibtex
@software{apik-forecast,
    title = {APIK-Forecast: Python project for calculation of forecasts for key meteorological parameters, quality control, and visualization},
    author = {Yuliya Martynova},
    year = {2026},
    url = {https://github.com/foxyj13/APIK-Forecast.git}
}
```

## Contact

For questions and support, please open an issue on the GitHub repository.

