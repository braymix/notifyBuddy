#!/bin/bash
# build_port.sh — assembla la cartella-port pronta da copiare + lo zip.
# Uscita: deploy/out/  (struttura da estrarre dentro /roms/ports/)
#         deploy/buddy-port.zip
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/deploy/out"

rm -rf "$OUT"
mkdir -p "$OUT/buddy/logs"

# file dell'app (niente logs, niente __pycache__, niente file audio)
for f in main.py bus.py brain.py synth.py face.py config.toml; do
  cp "$ROOT/buddy/$f" "$OUT/buddy/$f"
done

# launcher del menu Ports + bootstrap
cp "$ROOT/deploy/Buddy.sh" "$OUT/Buddy.sh"
cp "$ROOT/deploy/bootstrap.sh" "$OUT/buddy/bootstrap.sh"
chmod +x "$OUT/Buddy.sh" "$OUT/buddy/bootstrap.sh"
touch "$OUT/buddy/logs/.gitkeep"

# zip: estraendolo dentro /roms/ports/ crea Buddy.sh + buddy/
cd "$OUT"
rm -f "$ROOT/deploy/buddy-port.zip"
zip -r -q "$ROOT/deploy/buddy-port.zip" Buddy.sh buddy
echo "creato: deploy/buddy-port.zip"
unzip -l "$ROOT/deploy/buddy-port.zip"
