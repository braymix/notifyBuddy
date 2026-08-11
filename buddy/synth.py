"""synth.py — sintesi audio procedurale.

Nessun file audio. Ogni suono e' generato a runtime dai parametri del
"reaction vector" (campo ``sound``). Il cuore e' ``render()``, una funzione
PURA che ritorna un ``numpy.ndarray`` mono float32 in [-1, 1]: NON importa
pygame ed e' quindi testabile a mano (criterio Fase 1).

La conversione in ``pygame.Sound`` sta in ``to_sound()``, che importa pygame
solo quando serve, cosi' il core resta indipendente dalla UI.

Parametri di ``sound`` (dal reaction vector):
    engine:     "fm" | "pluck" | "chime" | "noise"
    root_hz:    frequenza fondamentale
    intervals:  offset in semitoni rispetto alla fondamentale (una "voce" ognuno)
    decay:      durata/coda della nota in secondi (~0.05..1.5)
    brightness: 0..1  quantita' di armoniche/timbro brillante
    density:    1..N  quante voci suonano davvero + arpeggio
    detune:     0..~0.1  stonatura relativa fra le voci (spessore)
"""

from __future__ import annotations

from typing import Any, Dict, Sequence

import numpy as np

SAMPLE_RATE = 22050  # mono, leggero per Cortex-A35
MAX_SECONDS = 1.6    # cap di sicurezza: i suoni restano corti e reattivi


def _semitone(root_hz: float, semi: float) -> float:
    """Frequenza di ``semi`` semitoni sopra ``root_hz``."""
    return float(root_hz) * (2.0 ** (semi / 12.0))


def _adsr(n: int, decay: float, sr: int) -> np.ndarray:
    """Inviluppo semplice attacco-veloce / decadimento esponenziale."""
    env = np.ones(n, dtype=np.float32)
    attack = max(1, int(sr * 0.005))          # 5 ms di attacco: niente click
    attack = min(attack, n)
    env[:attack] = np.linspace(0.0, 1.0, attack, dtype=np.float32)
    # decadimento esponenziale sul resto
    tau = max(decay, 1e-3)
    t = np.arange(n, dtype=np.float32) / sr
    env *= np.exp(-t / tau).astype(np.float32)
    # micro-fade finale per evitare click al taglio
    fade = min(int(sr * 0.005), n)
    if fade > 0:
        env[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    return env


def _voice(engine: str, freq: float, dur_s: float, brightness: float,
           detune: float, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Genera una singola voce col motore scelto."""
    n = max(1, int(sr * dur_s))
    t = np.arange(n, dtype=np.float32) / sr
    b = float(np.clip(brightness, 0.0, 1.0))
    det = 1.0 + float(detune) * (rng.random() - 0.5) * 2.0
    f = freq * det

    if engine == "fm":
        # FM: indice di modulazione guidato da brightness
        ratio = 2.0
        index = 0.5 + b * 6.0
        env_mod = np.exp(-t / max(dur_s * 0.5, 1e-3))
        mod = np.sin(2 * np.pi * f * ratio * t) * index * env_mod
        wave = np.sin(2 * np.pi * f * t + mod)

    elif engine == "pluck":
        # corda pizzicata: armoniche che si spengono in fretta, piu' brillante = piu' armoniche
        wave = np.zeros(n, dtype=np.float32)
        n_harm = 1 + int(b * 6)
        for h in range(1, n_harm + 1):
            wave += (1.0 / h) * np.sin(2 * np.pi * f * h * t)
        wave *= np.exp(-t * (6.0 + (1.0 - b) * 10.0))

    elif engine == "chime":
        # campana: parziali inarmonici, coda lunga e cristallina
        partials = [1.0, 2.76, 5.40, 8.93]
        gains = [1.0, 0.6, 0.4 * (0.3 + b), 0.25 * b]
        wave = np.zeros(n, dtype=np.float32)
        for p, g in zip(partials, gains):
            wave += g * np.sin(2 * np.pi * f * p * t)

    elif engine == "noise":
        # rumore filtrato: allerta / percussivo
        raw = rng.standard_normal(n).astype(np.float32)
        # filtro passa-basso a un polo, cutoff da brightness
        alpha = 0.05 + b * 0.6
        filtered = np.empty(n, dtype=np.float32)
        acc = 0.0
        for i in range(n):
            acc = acc + alpha * (raw[i] - acc)
            filtered[i] = acc
        # un pizzico di tono per dargli un'intonazione
        wave = 0.7 * filtered + 0.3 * np.sin(2 * np.pi * f * t)

    else:  # fallback: seno puro
        wave = np.sin(2 * np.pi * f * t)

    return wave.astype(np.float32)


def render(sound: Dict[str, Any], sr: int = SAMPLE_RATE,
           seed: int | None = None) -> np.ndarray:
    """Renderizza i parametri ``sound`` in un array mono float32 in [-1, 1].

    Funzione PURA: input dict -> output ndarray. Nessun side effect, niente pygame.
    """
    engine = str(sound.get("engine", "chime"))
    root = float(sound.get("root_hz", 440.0))
    intervals: Sequence[float] = list(sound.get("intervals", [0])) or [0]
    decay = float(sound.get("decay", 0.4))
    brightness = float(sound.get("brightness", 0.6))
    density = max(1, int(sound.get("density", len(intervals))))
    detune = float(sound.get("detune", 0.0))

    rng = np.random.default_rng(seed)

    # quante voci: min fra density e intervalli disponibili
    voices = intervals[:density] if density <= len(intervals) else intervals
    if not voices:
        voices = [0]

    dur_s = float(np.clip(decay, 0.03, MAX_SECONDS))
    # arpeggio: le voci partono leggermente sfalsate se sono piu' d'una
    spread = min(0.06, dur_s * 0.25)
    total_n = int(sr * (dur_s + spread * max(0, len(voices) - 1))) + 1
    out = np.zeros(total_n, dtype=np.float32)

    for k, semi in enumerate(voices):
        freq = _semitone(root, float(semi))
        v = _voice(engine, freq, dur_s, brightness, detune, sr, rng)
        env = _adsr(len(v), dur_s, sr)
        v = v * env
        start = int(k * spread * sr)
        end = start + len(v)
        if end > len(out):
            v = v[: len(out) - start]
            end = len(out)
        out[start:end] += v

    # normalizzazione morbida
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if peak > 1e-6:
        out = out / peak * 0.9
    return out.astype(np.float32)


def to_sound(array: np.ndarray):
    """Converte un array mono float32 in ``pygame.Sound`` (stereo int16).

    Importa pygame in ritardo: chi testa il synth non deve avere pygame.
    Richiede che il mixer sia gia' inizializzato con ``SAMPLE_RATE``.
    """
    import pygame  # import lazy, di proposito

    clipped = np.clip(array, -1.0, 1.0)
    int16 = (clipped * 32767.0).astype(np.int16)
    stereo = np.repeat(int16[:, None], 2, axis=1)  # mono -> due canali uguali
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


if __name__ == "__main__":  # smoke test manuale, senza pygame
    demo = {
        "engine": "chime", "root_hz": 523.25, "intervals": [0, 4, 7, 12],
        "decay": 0.6, "brightness": 0.7, "density": 4, "detune": 0.02,
    }
    a = render(demo, seed=1)
    print(f"engine={demo['engine']} campioni={a.size} "
          f"durata={a.size / SAMPLE_RATE:.2f}s picco={np.max(np.abs(a)):.3f}")
