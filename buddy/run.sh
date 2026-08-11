#!/bin/bash
# run.sh — launcher per ArkOS (menu Ports) e per test rapido su PC.
# L'app vive interamente nella sua cartella e non scrive altrove.

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1

# su console: assicurati che python veda numpy/pygame/paho installati via pip --user
export PYTHONUNBUFFERED=1

# --sim se passato come primo argomento (utile anche sulla console per provare)
exec python3 main.py "$@" >> "$DIR/logs/run.out" 2>&1
