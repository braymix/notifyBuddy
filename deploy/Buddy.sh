#!/bin/bash
# =============================================================================
#  Buddy — voce del menu "Ports" di ArkOS.
#  Robusto: cattura TUTTO in un log con redirezione semplice (niente trucchi),
#  copia il log accanto a Buddy.sh (facile da trovare) e RESTA a schermo.
# =============================================================================

# trova la cartella dell'app su prima o seconda SD
DIR=""
for base in /roms/ports /roms2/ports; do
  if [ -d "$base/buddy" ]; then DIR="$base/buddy"; PORTS="$base"; break; fi
done
if [ -z "$DIR" ]; then
  clear 2>/dev/null
  echo "ERRORE: cartella 'buddy' non trovata in /roms/ports ne' /roms2/ports"
  echo "Spegni per uscire."
  while true; do sleep 5; done
fi
cd "$DIR" || exit 1
mkdir -p logs
LOG="logs/run.out"

# --- tutto quello che segue va nel LOG (redirezione semplice, POSIX) ---------
{
  echo "==================== AVVIO $(date) ===================="
  echo "[buddy] cartella: $DIR"
  echo "[buddy] python: $(python3 --version 2>&1)  ($(command -v python3))"
  echo "[buddy] arch:   $(python3 -c 'import platform;print(platform.machine())' 2>&1)"

  echo "[buddy] --- passo 1: installazione dipendenze ---"
  bash ./bootstrap.sh

  echo "[buddy] --- passo 2: verifica import ---"
  python3 -c "import numpy, pygame; print('[buddy] import numpy+pygame OK')"
  IMP=$?

  if [ "$IMP" -ne 0 ]; then
    echo "[buddy] STOP: numpy/pygame non importabili. Vedi errori sopra."
  else
    echo "[buddy] --- passo 3: avvio applicazione ---"
    python3 main.py --sim
    echo "[buddy] applicazione uscita con codice $?"
  fi
  echo "==================== FINE $(date) ===================="
} > "$LOG" 2>&1

# --- copia il log dove e' facilissimo trovarlo e mostralo a schermo ----------
cp "$LOG" "$PORTS/BUDDY-LOG.txt" 2>/dev/null
clear 2>/dev/null
echo "=================== BUDDY: RISULTATO ==================="
tail -n 40 "$LOG"
echo "======================================================="
echo ">> Log salvato anche in:  $PORTS/BUDDY-LOG.txt"
echo ">> FOTOGRAFA questa schermata o mandami quel file."
echo ">> Per uscire: SELECT+START, oppure spegni la console."
echo "======================================================="
# resta fisso a schermo
while true; do sleep 5; done
