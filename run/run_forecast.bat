@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

set "CFG_FILENAME=run_forecast.cfg"

:: 0. Specify the project root directory
set "PROJECT_ROOT=%~dp0.."

:: Add python path to the environment variable
set "PYTHONPATH=%PYTHONPATH%;%PROJECT_ROOT%"

:: 1. Specify the path to the configuration file
set "cfg_file=%~dp0..\config\%CFG_FILENAME%"

:: 2. Check whether the file exists
if not exist "%cfg_file%" (
    echo [ERROR] The file with arguments for starting the forecast was not found: %cfg_file%
    pause
    exit /b
)

:: 3. Read the file, ignoring empty lines and comments with #
:: eol=#     - skips lines starting with #
:: tokens=1* - splits the line into two parts (before the first "=" and after it)
:: delims==  - uses the "=" sign as a delimiter
for /f "usebackq eol=# tokens=1* delims==" %%A in ("!cfg_file!") do (
    :: Remove possible spaces around the argument name and value
    set "key=%%A"
    set "val=%%B"
    
    :: Trim trailing spaces from the name (if any)
    for /f "tokens=1" %%X in ("!key!") do set "key=%%X"
    
    :: Save the argument if the name is not empty
    if not "!key!"=="" (
        set "!key!=!val!"
    )
)

:: 4. Check how our arguments were loaded
echo Argument loading completed.
echo Calculation mode: %MODE%
echo Global forecast plot flag: %ADD_GLOBFORECAST_PLOT%
echo Training period: %TIME_DEPTH%
echo Forecast period: %TIME_FORECAST%
echo Maximum number of missing values: %DATA_MISSINGS_PERCENT%
echo Global forecast type: %FORECAST_TYPE%
echo Current date: %NOW_DATE%
echo Configuration file: %CONFIG_FILE%

echo Starting forecast calculation

cd "%PROJECT_ROOT%"
"%PROJECT_ROOT%\.venv\Scripts\python.exe" "%PROJECT_ROOT%\src\forecast\main.py" --mode=%MODE% --add-globforecast-plot=%ADD_GLOBFORECAST_PLOT% --time-depth=%TIME_DEPTH% --time-forecast=%TIME_FORECAST% --data-missings-percent=%DATA_MISSINGS_PERCENT% --forecast-type=%FORECAST_TYPE% --now-date=%NOW_DATE% --config=%CONFIG_FILE%

pause