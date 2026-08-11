"""brain.py — dalla notifica al "reaction vector".

Il brain non produce mai audio o immagini: produce SOLO il dict del reaction
vector (schema nel README). synth.py e face.py lo interpretano.

Due implementazioni dietro la stessa interfaccia ``Brain.react(notif) -> dict``:

  * ``RuleBrain``  deterministico-con-jitter, offline, DEFAULT.
  * ``LLMBrain``   stub: per ora chiama semplicemente il fallback RuleBrain.
                   In Fase 4 chiamera' un'API con timeout aggressivo.

Ogni sorgente ha una "firma" (profilo base) presa da config; sopra ci mettiamo
un jitter controllato, cosi' la reazione e' riconoscibile ma mai identica.

Funzioni PURE, nessun import di pygame: testabile a mano (criterio Fase 1).
"""

from __future__ import annotations

import random
from typing import Any, Dict, Optional

# Profili di default se config.toml non li definisce. Chiave = sorgente.
DEFAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    "claude_code": {
        "mood": "happy", "urgency": 0.35, "valence": 0.8,
        "engine": "chime", "root_hz": 587.33, "scales": [[0, 4, 7, 12], [0, 5, 7, 12]],
        "decay": 0.6, "brightness": 0.75, "density": 4,
        "eyes": "wide", "mouth": "smile", "bounce": 0.8, "hue": 140,
        "text": "fatto! ho finito",
    },
    "teams": {
        "mood": "alert", "urgency": 0.7, "valence": -0.1,
        "engine": "pluck", "root_hz": 392.0, "scales": [[0, 3, 7], [0, 2, 7]],
        "decay": 0.35, "brightness": 0.6, "density": 2,
        "eyes": "squint", "mouth": "o", "bounce": 0.5, "hue": 30,
        "text": "ping da Teams",
    },
    "default": {
        "mood": "curious", "urgency": 0.45, "valence": 0.2,
        "engine": "fm", "root_hz": 440.0, "scales": [[0, 7], [0, 5], [0, 7, 12]],
        "decay": 0.4, "brightness": 0.55, "density": 2,
        "eyes": "wide", "mouth": "flat", "bounce": 0.6, "hue": 200,
        "text": "nuova notifica",
    },
}

_MOOD_EYES = {
    "happy": "wide", "curious": "wide", "alert": "squint",
    "annoyed": "half", "focused": "half", "sleepy": "closed",
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _jitter(rng: random.Random, base: float, amt: float, lo: float, hi: float) -> float:
    return round(_clamp(base + (rng.random() * 2 - 1) * amt, lo, hi), 3)


class Brain:
    """Interfaccia comune."""

    def react(self, notif: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError


class RuleBrain(Brain):
    """Regole + jitter controllato. Deterministico a parita' di ``seed``."""

    def __init__(self, profiles: Optional[Dict[str, Dict[str, Any]]] = None,
                 seed: Optional[int] = None) -> None:
        self.profiles = profiles or DEFAULT_PROFILES
        self._rng = random.Random(seed)

    def profile_for(self, source: str) -> Dict[str, Any]:
        return self.profiles.get(source, self.profiles.get("default", DEFAULT_PROFILES["default"]))

    def react(self, notif: Dict[str, Any]) -> Dict[str, Any]:
        source = str(notif.get("source", "default"))
        prio = float(notif.get("priority", 0.0))  # 0..1 spinta extra di urgenza
        p = self.profile_for(source)
        rng = self._rng

        urgency = _jitter(rng, p["urgency"] + prio * 0.3, 0.08, 0.0, 1.0)
        valence = _jitter(rng, p["valence"], 0.15, -1.0, 1.0)

        scales = p.get("scales", [[0, 7]])
        intervals = list(rng.choice(scales))
        # una nota fondamentale che oscilla leggermente
        root = round(p["root_hz"] * (2.0 ** (rng.uniform(-1, 1) / 12.0)), 2)

        mood = p["mood"]
        # se molto urgente, l'umore vira su "alert" a prescindere dalla sorgente
        if urgency > 0.8 and mood not in ("alert", "annoyed"):
            mood = "alert"

        title = str(notif.get("title") or notif.get("body") or p["text"])
        text = title[:40]

        # ttl: piu' urgente = resta un filo di piu' a schermo
        ttl = round(6.0 + urgency * 6.0, 1)

        return {
            "urgency": urgency,
            "valence": valence,
            "mood": mood,
            "sound": {
                "engine": p["engine"],
                "root_hz": root,
                "intervals": intervals,
                "decay": _jitter(rng, p["decay"], 0.1, 0.05, 1.5),
                "brightness": _jitter(rng, p["brightness"], 0.15, 0.0, 1.0),
                "density": int(p["density"]),
                "detune": _jitter(rng, 0.02, 0.02, 0.0, 0.08),
            },
            "face": {
                "eyes": _MOOD_EYES.get(mood, p["eyes"]),
                "mouth": p["mouth"],
                "bounce": _jitter(rng, p["bounce"], 0.15, 0.0, 1.0),
                "hue_shift": int(round(p["hue"] + (rng.random() * 2 - 1) * 20)),
            },
            "text": text,
            "ttl_s": ttl,
            "source": source,
        }


class LLMBrain(Brain):
    """Stub. Stessa interfaccia; per ora delega al RuleBrain (fallback).

    In Fase 4: chiamata API con timeout ~2s -> se non risponde, ``fallback.react``.
    """

    def __init__(self, fallback: RuleBrain, timeout_s: float = 2.0) -> None:
        self.fallback = fallback
        self.timeout_s = timeout_s

    def react(self, notif: Dict[str, Any]) -> Dict[str, Any]:
        # TODO Fase 4: chiamata API, parsing JSON, validazione schema.
        return self.fallback.react(notif)


if __name__ == "__main__":  # smoke test manuale, senza pygame
    b = RuleBrain(seed=0)
    for src in ("claude_code", "teams", "qualcos_altro"):
        rv = b.react({"source": src, "title": f"test {src}"})
        print(src, "->", rv["mood"], rv["sound"]["engine"],
              "u=%.2f" % rv["urgency"], rv["sound"]["intervals"])
