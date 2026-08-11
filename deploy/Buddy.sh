#!/bin/bash
# =============================================================================
#  Buddy — voce del menu "Ports" di ArkOS.
#  Questo file va in /roms/ports/  (o /roms2/ports/), l'app in .../ports/buddy/
#  Isolato: non tocca nulla del sistema. Cancellalo e ArkOS resta identico.
# =============================================================================

# trova la cartella dell'app su prima o seconda SD
for base in /roms/ports /roms2/ports; do
  if [ -d "$base/buddy" ]; then DIR="$base/buddy"; break; fi
done
[ -z "$DIR" ] && exit 1
cd "$DIR" || exit 1

mkdir -p logs
{
  echo "=================== avvio $(date) ==================="
  # 1) installa le dipendenze la prima volta (serve Wi-Fi, ~1-2 min)
  bash ./bootstrap.sh
  # 2) lancia il buddy in modalita' demo (eventi finti, nessun broker richiesto)
  #    per le notifiche vere si toglie --sim dopo aver messo mosquitto sulla console
  python3 main.py --sim
  echo "=================== uscita $(date) ==================="
} >> logs/run.out 2>&1
