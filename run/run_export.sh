#!/bin/bash

CFG_FILENAME="run_export.cfg"

# 1. Specify the script directory (works reliably in Bash)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CFG_FILE="$PROJECT_ROOT/config/$CFG_FILENAME"

# 2. Check whether the configuration file exists
if [[ ! -f "$CFG_FILE" ]]; then
    echo "[ERROR] The file with arguments for starting the export was not found: $CFG_FILE" >&2
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
echo "Configuration file : ${FARGS:-Not specified}"
echo "-----------------------------------"

"$PROJECT_ROOT/.venv/Scripts/python.exe" "$PROJECT_ROOT/src/qc/main.py" --fargs=$FARGS
