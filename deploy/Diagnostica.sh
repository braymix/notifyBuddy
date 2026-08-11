#!/bin/sh
# =============================================================================
#  Buddy — DIAGNOSTICA. Voce del menu Ports. POSIX sh, nessuna dipendenza.
#  Non usa pygame: non puo' crashare. Scrive BUDDY-DIAGNOSI.txt nella cartella
#  ports (facile da trovare) e resta a schermo finche' non spegni.
# =============================================================================

for base in /roms/ports /roms2/ports; do
  if [ -d "$base/buddy" ]; then DIR="$base/buddy"; PORTS="$base"; break; fi
done

if [ -z "$DIR" ]; then
  echo "ERRORE: cartella 'buddy' non trovata in /roms/ports ne' /roms2/ports"
  echo "Hai estratto lo zip dentro la cartella ports? Spegni per uscire."
  while true; do sleep 5; done
fi

cd "$DIR" || exit 1
mkdir -p logs
OUT="$PORTS/BUDDY-DIAGNOSI.txt"

# se python3 manca del tutto, dillo chiaro
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 NON presente sul sistema (finding importante!)" | tee "$OUT"
else
  python3 diag.py "$OUT" 2>&1 | tee logs/diag_screen.txt
fi

echo ""
echo "=========================================================="
echo " Diagnosi salvata nel file:"
echo "   $OUT"
echo " Mandalo allo sviluppatore, o FOTOGRAFA questa schermata."
echo " Spegni la console per uscire."
echo "=========================================================="
# tieni la schermata visibile
while true; do sleep 5; done
