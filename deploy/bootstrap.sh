#!/bin/bash
# bootstrap.sh — installa numpy/pygame/paho UNA volta sola.
# Prima prova OFFLINE dai pacchetti gia' pronti in ./wheels (nessuna rete,
# nessuna compilazione). Se non bastano, tenta online come ripiego.
# Scrive .deps_ok cosi' gli avvii successivi sono immediati. Non tocca nulla
# fuori da qui e da ~/.local (pip --user).

MARK=".deps_ok"
[ -f "$MARK" ] && exit 0

echo "[bootstrap] prima configurazione delle dipendenze..."

# pip deve esistere
python3 -m pip --version >/dev/null 2>&1 || python3 -m ensurepip --user >/dev/null 2>&1

# tomli serve solo su Python < 3.11 (dove manca tomllib); innocuo altrove
PKGS="numpy pygame paho-mqtt tomli"

# 1) OFFLINE dai wheel inclusi (il caso normale su questa console)
if [ -d wheels ] && ls wheels/*.whl >/dev/null 2>&1; then
  echo "[bootstrap] pip attuale: $(python3 -m pip --version 2>&1)"
  # IMPORTANTISSIMO su Debian buster: il pip di sistema (18.x) NON sa leggere
  # i pacchetti manylinux2014. Installo prima un pip moderno (offline) e uso
  # quello per tutto il resto.
  echo "[bootstrap] aggiorno pip/setuptools/wheel OFFLINE (necessario per Python 3.7)..."
  python3 -m pip install --user --no-index --find-links wheels --upgrade pip setuptools wheel
  echo "[bootstrap] pip aggiornato: $(python3 -m pip --version 2>&1)"

  echo "[bootstrap] installo OFFLINE numpy/pygame/paho/tomli (~1 min)..."
  if python3 -m pip install --user --no-index --find-links wheels $PKGS; then
    if python3 -c "import numpy, pygame" 2>&1; then
      touch "$MARK"
      echo "[bootstrap] OK (offline). Al prossimo avvio parte subito."
      exit 0
    fi
    echo "[bootstrap] installati ma non importabili (?)."
  fi
  echo "[bootstrap] installazione offline non riuscita."
  echo "[bootstrap] Python: $(python3 --version 2>&1) / $(python3 -c 'import platform;print(platform.machine())' 2>&1)"
  echo "[bootstrap] Wheel disponibili:"; ls -1 wheels
fi

# 2) ONLINE come ripiego (serve Wi-Fi + pip recente)
echo "[bootstrap] provo online (serve Wi-Fi)..."
python3 -m pip install --user --upgrade pip >/dev/null 2>&1
if python3 -m pip install --user --no-input $PKGS; then
  touch "$MARK"
  echo "[bootstrap] OK (online)."
else
  echo "[bootstrap] ATTENZIONE: installazione fallita (offline e online)."
  echo "[bootstrap] Manda allo sviluppatore le righe qui sopra."
fi
