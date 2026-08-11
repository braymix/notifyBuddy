#!/bin/bash
# bootstrap.sh — installa le dipendenze Python UNA volta sola.
# Scrive un marcatore .deps_ok cosi' gli avvii successivi sono immediati.
# Non tocca nulla fuori da qui e da ~/.local (pip --user).

MARK=".deps_ok"
[ -f "$MARK" ] && exit 0

echo "[bootstrap] prima configurazione: installo numpy pygame paho-mqtt"
echo "[bootstrap] serve il Wi-Fi attivo, puo' richiedere 1-2 minuti..."

# assicurati che pip esista
python3 -m pip --version >/dev/null 2>&1 || python3 -m ensurepip --user >/dev/null 2>&1

if python3 -m pip install --user --no-input numpy pygame paho-mqtt; then
  touch "$MARK"
  echo "[bootstrap] dipendenze installate. Al prossimo avvio parte subito."
else
  echo "[bootstrap] ATTENZIONE: installazione fallita."
  echo "[bootstrap] Controlla il Wi-Fi e riavvia il port. Log in logs/run.out"
fi
