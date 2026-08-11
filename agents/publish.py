"""agents/publish.py — publisher MQTT "one-shot" per hook e test.

Pubblica una singola notifica sul topic del buddy e termina. Utile per
agganciare eventi custom, in particolare l'hook "Claude Code ha finito".

Uso:
    python publish.py --host <ip-console> --source claude_code \
        --title "task completato" --priority 0.2

Esempio di hook Claude Code (Stop hook): richiama questo script quando finisce.
Non richiede un broker locale sul PC: pubblica direttamente sulla console.
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="IP della console (broker MQTT)")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--topic", default="buddy/notify")
    ap.add_argument("--source", default="claude_code")
    ap.add_argument("--title", default="evento")
    ap.add_argument("--body", default="")
    ap.add_argument("--priority", type=float, default=0.0)
    args = ap.parse_args()

    try:
        import paho.mqtt.publish as publish
    except ImportError:
        print("manca paho-mqtt: pip install paho-mqtt", file=sys.stderr)
        return 2

    payload = json.dumps({
        "source": args.source, "title": args.title,
        "body": args.body, "priority": args.priority,
    })
    publish.single(args.topic, payload, hostname=args.host, port=args.port)
    print(f"pubblicato su {args.host}:{args.port}/{args.topic}: {payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
