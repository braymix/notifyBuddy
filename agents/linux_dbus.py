"""agents/linux_dbus.py — agente PC (Linux): notifiche desktop -> MQTT.

Ascolta il bus D-Bus di sessione (org.freedesktop.Notifications) e ripubblica
ogni notifica sul topic MQTT del buddy. Cosi' tutto cio' che fa "toast" sul PC
(Teams, browser, ecc.) arriva alla console.

Dipendenze (solo sul PC, non sulla console):
    pip install dbus-python paho-mqtt
Su Debian/Ubuntu: sudo apt install python3-dbus

Uso:
    python linux_dbus.py --host <ip-console> --port 1883 --topic buddy/notify

Nota: intercetta le notifiche col metodo "monitor" di D-Bus. Il mapping
app-name -> source e' grezzo e si affina in Fase 3.
"""

from __future__ import annotations

import argparse
import json
import sys

# mapping app D-Bus -> sorgente riconosciuta dal brain
APP_TO_SOURCE = {
    "microsoft teams": "teams",
    "teams": "teams",
    "teams for linux": "teams",
}


def app_to_source(app_name: str) -> str:
    return APP_TO_SOURCE.get((app_name or "").strip().lower(), "default")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="IP della console (broker MQTT)")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--topic", default="buddy/notify")
    args = ap.parse_args()

    try:
        import dbus
        from dbus.mainloop.glib import DBusGMainLoop
        from gi.repository import GLib
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        print(f"dipendenze mancanti: {exc}\n"
              "  pip install dbus-python paho-mqtt  (+ python3-gi, python3-dbus)",
              file=sys.stderr)
        return 2

    client = mqtt.Client()
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(args.host, args.port, keepalive=30)
    client.loop_start()
    print(f"[linux_dbus] pubblico su {args.host}:{args.port} topic={args.topic}")

    def on_notification(bus, message):
        if message.get_member() != "Notify":
            return
        a = message.get_args_list()
        # firma Notify: app_name, id, icon, summary, body, actions, hints, timeout
        app_name = str(a[0]) if len(a) > 0 else ""
        summary = str(a[3]) if len(a) > 3 else ""
        body = str(a[4]) if len(a) > 4 else ""
        notif = {
            "source": app_to_source(app_name),
            "title": summary or body,
            "body": body,
            "app": app_name,
        }
        client.publish(args.topic, json.dumps(notif))
        print(f"[linux_dbus] -> {notif['source']}: {notif['title']!r}")

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    bus.add_match_string(
        "eavesdrop=true, interface='org.freedesktop.Notifications', member='Notify'")
    bus.add_message_filter(on_notification)

    print("[linux_dbus] in ascolto sulle notifiche desktop (Ctrl-C per uscire)")
    try:
        GLib.MainLoop().run()
    except KeyboardInterrupt:
        print("\n[linux_dbus] stop")
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
