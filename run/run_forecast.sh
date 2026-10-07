#!/bin/bash

CFG_FILENAME="run_forecast.cfg"

# 1. Specify the script directory (works reliably in Bash)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CFG_FILE="$PROJECT_ROOT/config/$CFG_FILENAME"

# Add python path to the environment variable
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 2. Check whether the configuration file exists
if [[ ! -f "$CFG_FILE" ]]; then
    echo "[ERROR] The file with arguments for starting the forecast was not found: $CFG_FILE" >&2
    exit 1
fi

# 3. Read the file line by line using Bash
while IFS='=' read -r key val || [[ -n "$key" ]]; do
    # Remove spaces at the beginning and end of the key
    key="${key##*( )}"
    key="${key%%*( )}"
    
    # Skip empty lines and comments starting with #
    [[ -z "$key" || "$key" =~ ^# ]] && continue

    # Remove spaces at the beginning and end of the value
    val="${val##*( )}"
    val="${val%%*( )}"

    # Optionally: strip surrounding quotes, if they exist (e.g., "value" -> value)
    val="${val#\"}"
    val="${val%\"}"
    val="${val#\'}"
    val="${val%\'}"

    # Dynamically declare a variable in the current Bash environment
    printf -v "$key" "%s" "$val"

done < "$CFG_FILE"

# 4. Check the work of the loaded variables
echo "Argument loading completed."
echo "-----------------------------------"
echo "Calculation mode : ${MODE:-Not specified}"
echo "Global forecast plot flag : ${ADD_GLOBFORECAST_PLOT:-Not specified}"
echo "Training period : ${TIME_DEPTH:-Not specified}"
echo "Forecast period : ${TIME_FORECAST:-Not specified}"
echo "Maximum number of missing values : ${DATA_MISSINGS_PERCENT:-Not specified}"
echo "Global forecast type : ${FORECAST_TYPE:-Not specified}"
echo "Current date : ${NOW_DATE:-Not specified}"
echo "Configuration file : ${CONFIG_FILE:-Not specified}"
echo "-----------------------------------"

cd $PROJECT_ROOT
"$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/src/forecast/main.py" --mode=$MODE --add-globforecast-plot=$ADD_GLOBFORECAST_PLOT --time-depth=$TIME_DEPTH --time-forecast=$TIME_FORECAST --data-missings-percent=$DATA_MISSINGS_PERCENT --forecast-type=$FORECAST_TYPE --now-date=$NOW_DATE --config=$CONFIG_FILE
