"""Test delle parti PURE: brain e synth senza pygame (criterio Fase 1).

Eseguibili con:  python -m pytest tests/ -q   oppure   python tests/test_pure.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "buddy"))

from brain import RuleBrain            # noqa: E402
import synth                            # noqa: E402

REQUIRED_KEYS = {"urgency", "valence", "mood", "sound", "face", "text", "ttl_s"}


def test_reaction_vector_schema():
    b = RuleBrain(seed=1)
    rv = b.react({"source": "teams", "title": "ciao"})
    assert REQUIRED_KEYS <= set(rv), "manca una chiave nel reaction vector"
    assert -1.0 <= rv["valence"] <= 1.0
    assert 0.0 <= rv["urgency"] <= 1.0
    assert len(rv["text"]) <= 40
    assert set(rv["sound"]) >= {"engine", "root_hz", "intervals", "decay"}


def test_reactions_vary():
    """Due notifiche uguali NON devono produrre lo stesso suono/faccia."""
    b = RuleBrain(seed=7)
    a = b.react({"source": "claude_code", "title": "x"})
    c = b.react({"source": "claude_code", "title": "x"})
    assert (a["sound"], a["face"]) != (c["sound"], c["face"]), \
        "le reazioni devono variare (jitter)"


def test_priority_raises_urgency():
    b = RuleBrain(seed=3)
    lows = [b.react({"source": "teams", "title": "t"})["urgency"] for _ in range(8)]
    highs = [b.react({"source": "teams", "title": "t", "priority": 1.0})["urgency"]
             for _ in range(8)]
    assert np.mean(highs) > np.mean(lows)


def test_synth_is_pure_array():
    a = synth.render({"engine": "chime", "root_hz": 440, "intervals": [0, 7],
                      "decay": 0.4, "brightness": 0.6, "density": 2, "detune": 0.02})
    assert isinstance(a, np.ndarray)
    assert a.dtype == np.float32
    assert a.size > 0
    assert np.max(np.abs(a)) <= 1.0 + 1e-6


def test_all_engines_render():
    for eng in ("fm", "pluck", "chime", "noise"):
        a = synth.render({"engine": eng, "root_hz": 330, "intervals": [0, 4, 7],
                          "decay": 0.3, "brightness": 0.5, "density": 3})
        assert a.size > 0 and np.isfinite(a).all(), f"engine {eng} rotto"


def test_different_params_different_sound():
    a = synth.render({"engine": "fm", "root_hz": 220, "intervals": [0],
                      "decay": 0.3, "brightness": 0.2}, seed=1)
    b = synth.render({"engine": "fm", "root_hz": 660, "intervals": [0, 12],
                      "decay": 0.3, "brightness": 0.9}, seed=1)
    n = min(a.size, b.size)
    assert not np.allclose(a[:n], b[:n]), "parametri diversi -> suono diverso"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} test passati")
