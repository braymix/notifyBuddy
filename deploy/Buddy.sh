#!/bin/bash
# =============================================================================
#  Buddy — voce del menu "Ports" di ArkOS.
#  Mostra tutto a schermo e, in caso di errore, TIENE l'errore visibile 60s
#  cosi' lo puoi fotografare. Isolato: non tocca nulla del sistema.
# =============================================================================

# trova la cartella dell'app su prima o seconda SD
for base in /roms/ports /roms2/ports; do
  if [ -d "$base/buddy" ]; then DIR="$base/buddy"; break; fi
done
if [ -z "$DIR" ]; then
  echo "ERRORE: cartella 'buddy' non trovata in /roms/ports ne' /roms2/ports"
  sleep 20; exit 1
fi
cd "$DIR" || exit 1
mkdir -p logs
LOG="logs/run.out"

# stampa a SCHERMO e salva su file contemporaneamente
exec > >(tee -a "$LOG") 2>&1

echo "=================== avvio $(date) ==================="
echo "[buddy] cartella: $DIR"
echo "[buddy] python: $(python3 --version 2>&1)"

# 1) installa le dipendenze la prima volta (serve Wi-Fi)
bash ./bootstrap.sh

# 2) preflight: se mancano numpy/pygame, fermati con un messaggio chiaro
echo "[buddy] controllo dipendenze..."
if ! python3 -c "import numpy, pygame" 2>&1; then
  echo ""
  echo "############################################################"
  echo "# ERRORE: numpy o pygame NON disponibili."
  echo "# L'installazione automatica non e' riuscita."
  echo "# Cause tipiche: Wi-Fi assente, oppure pygame non installabile"
  echo "# via pip su questo sistema (serve il piano B)."
  echo "# Fotografa questa schermata e mandala allo sviluppatore."
  echo "############################################################"
  sleep 60
  exit 1
fi

# 3) lancia il buddy in demo (--sim: eventi finti, nessun broker richiesto)
echo "[buddy] avvio applicazione..."
python3 main.py --sim
CODE=$?
echo "[buddy] applicazione terminata con codice $CODE"

# 4) se e' crashata, mostra le ultime righe e tieni la schermata
if [ "$CODE" -ne 0 ]; then
  echo ""
  echo "############################################################"
  echo "# CRASH (codice $CODE). Ultime righe del log:"
  echo "############################################################"
  tail -n 30 "$LOG"
  echo "############################################################"
  echo "# Fotografa questa schermata e mandala allo sviluppatore."
  echo "############################################################"
  sleep 60
fi
