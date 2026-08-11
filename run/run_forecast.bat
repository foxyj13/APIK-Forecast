@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

set "CFG_FILENAME=run_forecast.cfg"

:: 1. Указываем путь к файлу конфигурации
set "config_file=%~dp0..\config\%CFG_FILENAME%"

:: 2. Проверяем, существует ли файл
if not exist "%config_file%" (
    echo [ОШИБКА] Файл с аргументами для запуска прогноза не найден: %config_file%
    pause
    exit /b
)

:: 3. Читаем файл, игнорируя пустые строки и комментарии с #
:: eol=#     - пропускает строки, начинающиеся с #
:: tokens=1* - делит строку на две части (до первого знака "=" и после него)
:: delims==  - использует знак "=" как разделитель
for /f "usebackq eol=# tokens=1* delims==" %%A in ("!config_file!") do (
    :: Удаляем возможные пробелы вокруг имени аргумента и значения
    set "key=%%A"
    set "val=%%B"
    
    :: Очищаем имя от пробелов на конце (если они есть)
    for /f "tokens=1" %%X in ("!key!") do set "key=%%X"
    
    :: Сохраняем аргумент, если имя не оказалось пустым
    if not "!key!"=="" (
        set "!key!=!val!"
    )
)

:: 4. Проверяем, как загрузились наши аргументы
echo Загрузка аргументов завершена.
echo Режим расчета: %MODE%
echo Ключ отрисовки глобального прогноза: %ADD_GLOBFORECAST_PLOT%
echo Период обучения: %TIME_DEPTH%
echo Период прогноза: %TIME_FORECAST%
echo Тип глобального прогноза: %FORECAST_TYPE%
echo Текущая дата: %NOW_DATE%
echo Конфигурационный файл: %CONFIG_FILE%

echo Запуск расчета прогноза

python ..\src\forecast\main.py --mode=%MODE% --add-globforecast-plot=%ADD_GLOBFORECAST_PLOT% --time-depth=%TIME_DEPTH% --time-forecast=%TIME_FORECAST% --forecast-type=%FORECAST_TYPE% --now-date=%NOW_DATE% --config=%CONFIG_FILE%

pause