"""main.py — loop principale del buddy.

Loop pygame 640x480 @30fps con una piccola macchina a stati (IDLE / REACTING).
Collega bus (notifiche) -> brain (reaction vector) -> synth (suono) + face (video).

Uso:
    python main.py --sim     # sviluppo su PC, notifiche finte, tastiera
    python main.py           # console: si collega al broker MQTT di config.toml

Comandi (tastiera su PC / gamepad su console, mappa in config.toml):
    A / Invio     -> "ho visto" (azzera badge e testo)
    B / R         -> ripeti l'ultima reazione
    X / M         -> muto on/off
    START / Esc   -> chiusura pulita
"""

from __future__ import annotations

import argparse
import logging
import queue
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

# tomllib e' in stdlib da 3.11; fallback a tomli se serve
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

HERE = Path(__file__).resolve().parent

import bus as bus_mod
import synth as synth_mod
from brain import RuleBrain, LLMBrain, DEFAULT_PROFILES

FPS = 30
SIZE = (640, 480)


def load_config(path: Path) -> Dict[str, Any]:
    if path.exists():
        with path.open("rb") as fh:
            return tomllib.load(fh)
    return {}


def setup_logging() -> logging.Logger:
    """Log su file DENTRO la cartella del buddy (mai fuori)."""
    log_dir = HERE / "logs"
    log_dir.mkdir(exist_ok=True)
    logger = logging.getLogger("buddy")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_dir / "buddy.log", maxBytes=512_000,
                                  backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    return logger


def build_profiles(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Unisce i profili di default con eventuali override da config."""
    profiles = {k: dict(v) for k, v in DEFAULT_PROFILES.items()}
    for name, prof in (cfg.get("profiles") or {}).items():
        profiles[name] = {**profiles.get(name, {}), **prof}
    return profiles


def is_blocked(notif: Dict[str, Any], filt: Dict[str, Any]) -> bool:
    """Filtri di config: sorgenti bandite o parole chiave da ignorare."""
    source = str(notif.get("source", "default"))
    if source in (filt.get("block_sources") or []):
        return True
    text = f"{notif.get('title', '')} {notif.get('body', '')}".lower()
    for kw in (filt.get("block_keywords") or []):
        if str(kw).lower() in text:
            return True
    return False


class App:
    def __init__(self, sim: bool, cfg: Dict[str, Any], logger: logging.Logger) -> None:
        import pygame  # import qui: main e' l'unico modulo che richiede pygame
        self.pygame = pygame
        self.cfg = cfg
        self.log = logger
        self.sim = sim
        self.running = True
        self.muted = bool(cfg.get("muted", False))
        self.unseen = 0
        self.last_reaction: Dict[str, Any] | None = None
        self.last_sound = None

        pygame.init()
        try:
            pygame.mixer.init(frequency=synth_mod.SAMPLE_RATE, size=-16,
                              channels=2, buffer=512)
        except Exception as exc:  # noqa: BLE001
            self.log.warning(f"mixer non disponibile: {exc} (audio off)")

        pygame.display.set_caption("buddy")
        self.screen = pygame.display.set_mode(SIZE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("dejavusans", 20)

        from face import Face
        self.face = Face(SIZE, cfg.get("palette", {}))

        # brain
        profiles = build_profiles(cfg)
        rule = RuleBrain(profiles=profiles, seed=cfg.get("seed"))
        self.brain = LLMBrain(rule) if cfg.get("use_llm") else rule

        # bus
        self.queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.source = bus_mod.make_source(sim, self.queue, cfg, logger)
        self.source.start()

        # gamepad (console) se presente
        self.joy = None
        if pygame.joystick.get_count() > 0:
            self.joy = pygame.joystick.Joystick(0)
            self.joy.init()
            self.log.info(f"gamepad: {self.joy.get_name()}")

        self.filt = cfg.get("filters", {})
        self.btn = cfg.get("buttons", {"ack": 0, "replay": 1, "mute": 2, "quit": 7})
        self.log.info(f"avviato (sim={sim}, muted={self.muted})")

    # ---- eventi ----------------------------------------------------------
    def _on_notification(self, notif: Dict[str, Any]) -> None:
        if is_blocked(notif, self.filt):
            self.log.info(f"filtrata: {notif}")
            return
        reaction = self.brain.react(notif)
        self.last_reaction = reaction
        self.log.info(f"reazione {reaction['source']} mood={reaction['mood']} "
                      f"u={reaction['urgency']:.2f} text={reaction['text']!r}")
        self.face.set_reaction(reaction)
        self.unseen += 1
        self._play(reaction["sound"])

    def _play(self, sound_params: Dict[str, Any]) -> None:
        if self.muted or not self.pygame.mixer.get_init():
            return
        try:
            arr = synth_mod.render(sound_params)
            self.last_sound = synth_mod.to_sound(arr)
            self.last_sound.play()
        except Exception as exc:  # noqa: BLE001
            self.log.error(f"synth/play errore: {exc}")

    def _acknowledge(self) -> None:
        self.unseen = 0
        self.face.reaction = None
        self.log.info("ack: badge azzerato")

    def _replay(self) -> None:
        if self.last_reaction:
            self.face.set_reaction(self.last_reaction)
            self._play(self.last_reaction["sound"])

    def _toggle_mute(self) -> None:
        self.muted = not self.muted
        self.log.info(f"muted={self.muted}")

    def _handle_input(self) -> None:
        pygame = self.pygame
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE,):
                    self.running = False              # START
                elif ev.key in (pygame.K_RETURN, pygame.K_a):
                    self._acknowledge()               # A
                elif ev.key in (pygame.K_b, pygame.K_r):
                    self._replay()                    # B
                elif ev.key in (pygame.K_x, pygame.K_m):
                    self._toggle_mute()               # X
            elif ev.type == pygame.JOYBUTTONDOWN:
                if ev.button == self.btn.get("quit"):
                    self.running = False
                elif ev.button == self.btn.get("ack"):
                    self._acknowledge()
                elif ev.button == self.btn.get("replay"):
                    self._replay()
                elif ev.button == self.btn.get("mute"):
                    self._toggle_mute()

    # ---- loop ------------------------------------------------------------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_input()

            # svuota la coda notifiche del frame
            try:
                while True:
                    self._on_notification(self.queue.get_nowait())
            except queue.Empty:
                pass

            self.face.update(dt)
            text = self.last_reaction["text"] if (self.face.reaction and
                                                  self.last_reaction) else None
            self.face.draw(self.screen, unseen=self.unseen, muted=self.muted,
                           text=text, font=self.font)
            self.pygame.display.flip()

        self.shutdown()

    def shutdown(self) -> None:
        self.log.info("chiusura pulita")
        try:
            self.source.stop()
        except Exception:  # noqa: BLE001
            pass
        self.pygame.quit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="buddy — assistente notifiche")
    parser.add_argument("--sim", action="store_true",
                        help="sorgente finta, per sviluppo su PC")
    parser.add_argument("--config", default=str(HERE / "config.toml"))
    args = parser.parse_args(argv)

    logger = setup_logging()
    cfg = load_config(Path(args.config))
    try:
        App(args.sim, cfg, logger).run()
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"crash: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
