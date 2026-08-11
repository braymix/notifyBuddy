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
for f in main.py bus.py brain.py synth.py face.py config.toml diag.py; do
  cp "$ROOT/buddy/$f" "$OUT/buddy/$f"
done

# launcher del menu Ports + bootstrap + diagnostica
cp "$ROOT/deploy/Buddy.sh" "$OUT/Buddy.sh"
cp "$ROOT/deploy/Diagnostica.sh" "$OUT/Diagnostica.sh"
cp "$ROOT/deploy/bootstrap.sh" "$OUT/buddy/bootstrap.sh"
chmod +x "$OUT/Buddy.sh" "$OUT/Diagnostica.sh" "$OUT/buddy/bootstrap.sh"
touch "$OUT/buddy/logs/.gitkeep"

# pacchetti ARM64 gia' pronti per l'installazione OFFLINE sulla console
if ls "$ROOT/deploy/wheels/"*.whl >/dev/null 2>&1; then
  mkdir -p "$OUT/buddy/wheels"
  cp "$ROOT/deploy/wheels/"*.whl "$OUT/buddy/wheels/"
  echo "inclusi wheel offline: $(ls -1 "$OUT/buddy/wheels" | wc -l)"
fi

# zip: estraendolo dentro /roms/ports/ crea Buddy.sh + Diagnostica.sh + buddy/
cd "$OUT"
rm -f "$ROOT/deploy/buddy-port.zip"
zip -r -q "$ROOT/deploy/buddy-port.zip" Buddy.sh Diagnostica.sh buddy
echo "creato: deploy/buddy-port.zip"
unzip -l "$ROOT/deploy/buddy-port.zip"
