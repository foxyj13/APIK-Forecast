@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

set "CFG_FILENAME=run_qc.cfg"

:: 1. Указываем путь к файлу конфигурации
set "cfg_file=%~dp0..\config\%CFG_FILENAME%"

:: 2. Проверяем, существует ли файл
if not exist "%cfg_file%" (
    echo [ОШИБКА] Файл с аргументами для запуска прогноза не найден: %cfg_file%
    pause
    exit /b
)

:: 3. Читаем файл, игнорируя пустые строки и комментарии с #
:: eol=#     - пропускает строки, начинающиеся с #
:: tokens=1* - делит строку на две части (до первого знака "=" и после него)
:: delims==  - использует знак "=" как разделитель
for /f "usebackq eol=# tokens=1* delims==" %%A in ("!cfg_file!") do (
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
echo Конфигурационный файл: %FARGS%

echo Запуск расчета прогноза

python ..\src\qc\main.py --fargs=%FARGS%

pause