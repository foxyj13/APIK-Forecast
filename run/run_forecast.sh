#!/bin/bash

CFG_FILENAME="run_forecast.cfg"

# 1. Находим директорию скрипта (работает надежно в Bash)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG_FILE="$SCRIPT_DIR/../config/$CFG_FILENAME"

# 2. Проверяем, существует ли файл конфигурации
if [[ ! -f "$CFG_FILE" ]]; then
    echo "[ОШИБКА] Файл с аргументами для запуска прогноза не найден: $CFG_FILE" >&2
    exit 1
fi

# 3. Читаем файл построчно средствами Bash
while IFS='=' read -r key val || [[ -n "$key" ]]; do
    # Удаляем пробелы в начале и конце ключа
    key="${key##*( )}"
    key="${key%%*( )}"
    
    # Пропускаем пустые строки и комментарии, начинающиеся с #
    [[ -z "$key" || "$key" =~ ^# ]] && continue

    # Удаляем пробелы в начале и конце значения
    val="${val##*( )}"
    val="${val%%*( )}"

    # Опционально: очищаем окружающие кавычки, если они есть (например, "value" -> value)
    val="${val#\"}"
    val="${val%\"}"
    val="${val#\'}"
    val="${val%\'}"

    # Динамически объявляем переменную в текущем окружении Bash
    printf -v "$key" "%s" "$val"

done < "$CFG_FILE"

# 4. Проверяем работу загруженных переменных
echo "Загрузка аргументов завершена."
echo "-----------------------------------"
echo "Режим расчета : ${MODE:-Не задан}"
echo "Ключ отрисовки глобального прогноза : ${ADD_GLOBFORECAST_PLOT:-Не задан}"
echo "Период обучения : ${TIME_DEPTH:-Не задан}"
echo "Период прогноза : ${TIME_FORECAST:-Не задан}"
echo "Максимальное кол-во пропусков : ${DATA_MISSINGS_PERCENT:-Не задан}"
echo "Тип глобального прогноза : ${FORECAST_TYPE:-Не задан}"
echo "Текущая дата : ${NOW_DATE:-Не задан}"
echo "Конфигурационный файл : ${CONFIG_FILE:-Не задан}"
echo "-----------------------------------"

python ../src/forecast/main.py --mode=$MODE --add-globforecast-plot=$ADD_GLOBFORECAST_PLOT --time-depth=$TIME_DEPTH --time-forecast=$TIME_FORECAST --data-missings-percent=$DATA_MISSINGS_PERCENT --forecast-type=$FORECAST_TYPE --now-date=$NOW_DATE --config=$CONFIG_FILE
