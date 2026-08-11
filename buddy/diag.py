"""diag.py — sonda diagnostica. SOLO libreria standard: non importa pygame ne'
numpy, quindi non puo' crashare per dipendenze mancanti. Raccoglie i fatti che
servono a capire perche' il buddy non parte e li scrive su file + a schermo.

Uso:  python3 diag.py /percorso/BUDDY-DIAGNOSI.txt
"""

import sys
import os
import platform
import importlib.util
import ctypes.util
import socket
import subprocess


def line(s=""):
    print(s)
    _buf.append(s)


_buf = []


def can_import(name):
    try:
        spec = importlib.util.find_spec(name)
    except Exception as exc:  # noqa: BLE001
        return f"ERRORE ricerca: {exc}"
    if spec is None:
        return "ASSENTE"
    try:
        mod = __import__(name)
        ver = getattr(mod, "__version__", "?")
        return f"OK (versione {ver})"
    except Exception as exc:  # noqa: BLE001
        return f"PRESENTE ma import fallito: {exc}"


def check_network():
    try:
        s = socket.create_connection(("8.8.8.8", 53), timeout=4)
        s.close()
        return "OK (rete raggiungibile)"
    except Exception as exc:  # noqa: BLE001
        return f"NO ({exc})"


def check_pip():
    try:
        out = subprocess.run([sys.executable, "-m", "pip", "--version"],
                             capture_output=True, text=True, timeout=20)
        if out.returncode == 0:
            return "OK: " + out.stdout.strip()
        return "ASSENTE: " + (out.stderr.strip() or "rc!=0")
    except Exception as exc:  # noqa: BLE001
        return f"ERRORE: {exc}"


def try_pygame_display():
    """Se pygame c'e', prova ad aprire un display coi vari driver."""
    if importlib.util.find_spec("pygame") is None:
        return "saltato (pygame assente)"
    results = []
    import pygame  # noqa: E402
    for drv in ("kmsdrm", "fbcon", "x11", "directfb", "wayland"):
        os.environ["SDL_VIDEODRIVER"] = drv
        try:
            pygame.display.quit()
            pygame.display.init()
            pygame.display.set_mode((640, 480))
            results.append(f"{drv}=OK")
            pygame.display.quit()
        except Exception as exc:  # noqa: BLE001
            results.append(f"{drv}=NO({str(exc)[:40]})")
    os.environ.pop("SDL_VIDEODRIVER", None)
    return " | ".join(results)


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "BUDDY-DIAGNOSI.txt"

    line("================= BUDDY — DIAGNOSTICA =================")
    line(f"data: {__import__('datetime').datetime.now()}")
    line(f"python: {sys.version.split()[0]}  ({sys.executable})")
    line(f"piattaforma: {platform.platform()}")
    line(f"macchina: {platform.machine()}")
    line("")
    line("--- dipendenze python ---")
    line(f"numpy    : {can_import('numpy')}")
    line(f"pygame   : {can_import('pygame')}")
    line(f"paho.mqtt: {can_import('paho.mqtt.client')}")
    line(f"pip      : {check_pip()}")
    line("")
    line("--- sistema grafico / SDL ---")
    line(f"libSDL2  : {ctypes.util.find_library('SDL2') or 'non trovata'}")
    fbs = [d for d in os.listdir("/dev") if d.startswith("fb")] if os.path.isdir("/dev") else []
    line(f"framebuffer /dev/fb*: {fbs or 'nessuno'}")
    line(f"SDL_VIDEODRIVER (env): {os.environ.get('SDL_VIDEODRIVER', 'non impostato')}")
    line(f"prova display pygame : {try_pygame_display()}")
    line("")
    line("--- rete ---")
    line(f"internet : {check_network()}")
    line("")
    line("--- cartella corrente ---")
    line(f"cwd: {os.getcwd()}")
    try:
        line("file: " + ", ".join(sorted(os.listdir("."))))
    except Exception as exc:  # noqa: BLE001
        line(f"listdir errore: {exc}")
    line("======================================================")

    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(_buf) + "\n")
        line(f"\n>> diagnosi salvata in: {out_path}")
    except Exception as exc:  # noqa: BLE001
        line(f"\n!! impossibile scrivere {out_path}: {exc}")


if __name__ == "__main__":
    main()
