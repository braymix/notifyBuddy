"""bus.py — sorgente delle notifiche.

Espone una coda unica (``queue.Queue``) da cui main.py preleva le notifiche.
Due modi di riempirla:

  * ``MqttSource``  client paho-mqtt in un thread, si iscrive a ``buddy/notify``.
                    Riconnessione automatica. Import di paho in ritardo, cosi'
                    il resto gira anche senza la libreria (es. in --sim).
  * ``SimSource``   genera notifiche FINTE a intervalli casuali, per sviluppare
                    sul PC senza broker (criterio Fase 1: ``python main.py --sim``).

Formato notifica (dict):
    {"source": "claude_code", "title": "build ok", "body": "...", "priority": 0.0}

Il payload MQTT atteso e' lo stesso dict in JSON. Payload non-JSON viene
incapsulato come notifica generica, cosi' non si perde nulla.
"""

from __future__ import annotations

import json
import queue
import random
import threading
import time
from typing import Any, Dict, Optional

# esempi usati dalla sorgente finta
_SIM_SAMPLES = [
    {"source": "claude_code", "title": "task completato", "priority": 0.2},
    {"source": "claude_code", "title": "build fallita", "priority": 0.6},
    {"source": "teams", "title": "messaggio da Anna"},
    {"source": "teams", "title": "riunione fra 5 min", "priority": 0.8},
    {"source": "default", "title": "nuova email"},
    {"source": "default", "title": "meteo: pioggia in arrivo"},
]


class SimSource:
    """Immette notifiche finte nella coda a intervalli casuali."""

    def __init__(self, out: "queue.Queue[Dict[str, Any]]",
                 min_s: float = 4.0, max_s: float = 12.0,
                 seed: Optional[int] = None) -> None:
        self.out = out
        self.min_s, self.max_s = min_s, max_s
        self._rng = random.Random(seed)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            wait = self._rng.uniform(self.min_s, self.max_s)
            if self._stop.wait(wait):
                break
            notif = dict(self._rng.choice(_SIM_SAMPLES))
            self.out.put(notif)

    def stop(self) -> None:
        self._stop.set()


class MqttSource:
    """Client MQTT in thread. Mette i messaggi decodificati nella coda."""

    def __init__(self, out: "queue.Queue[Dict[str, Any]]", host: str, port: int,
                 topic: str, username: str = "", password: str = "") -> None:
        self.out = out
        self.host, self.port, self.topic = host, port, topic
        self.username, self.password = username, password
        self._client = None
        self._log = None  # impostato da main via attach_logger

    def attach_logger(self, logger) -> None:
        self._log = logger

    def _emit(self, level: str, msg: str) -> None:
        if self._log:
            getattr(self._log, level)(msg)

    def start(self) -> None:
        import paho.mqtt.client as mqtt  # import lazy

        client = mqtt.Client()
        if self.username:
            client.username_pw_set(self.username, self.password)

        def on_connect(cli, userdata, flags, rc, *args):
            self._emit("info", f"MQTT connesso rc={rc}, iscrizione a {self.topic}")
            cli.subscribe(self.topic)

        def on_message(cli, userdata, message):
            self.out.put(self._decode(message.payload))

        def on_disconnect(cli, userdata, rc, *args):
            self._emit("warning", f"MQTT disconnesso rc={rc}, riconnessione automatica")

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        client.reconnect_delay_set(min_delay=1, max_delay=30)

        self._client = client
        try:
            client.connect_async(self.host, self.port, keepalive=30)
            client.loop_start()   # gestisce (ri)connessioni in un thread proprio
            self._emit("info", f"MQTT avvio verso {self.host}:{self.port}")
        except Exception as exc:  # noqa: BLE001
            self._emit("error", f"MQTT connessione fallita: {exc}")

    @staticmethod
    def _decode(payload: bytes) -> Dict[str, Any]:
        try:
            data = json.loads(payload.decode("utf-8"))
            if isinstance(data, dict):
                data.setdefault("source", "default")
                return data
        except Exception:  # noqa: BLE001
            pass
        return {"source": "default", "title": payload.decode("utf-8", "replace")[:40]}

    def stop(self) -> None:
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass


def make_source(sim: bool, out: "queue.Queue[Dict[str, Any]]",
                cfg: Dict[str, Any], logger=None):
    """Fabbrica la sorgente giusta in base alla modalita'."""
    if sim:
        return SimSource(out, seed=cfg.get("sim_seed"))
    broker = cfg.get("broker", {})
    src = MqttSource(
        out,
        host=broker.get("host", "127.0.0.1"),
        port=int(broker.get("port", 1883)),
        topic=broker.get("topic", "buddy/notify"),
        username=broker.get("username", ""),
        password=broker.get("password", ""),
    )
    if logger:
        src.attach_logger(logger)
    return src


if __name__ == "__main__":  # smoke test della sorgente finta
    q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
    s = SimSource(q, min_s=0.2, max_s=0.5, seed=1)
    s.start()
    for _ in range(3):
        print(q.get(timeout=2))
    s.stop()
