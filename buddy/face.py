"""face.py — rendering parametrico del buddy.

Niente sprite, niente GIF: la faccia e' disegnata a runtime con primitive
vettoriali (cerchi, archi, poligoni). I parametri arrivano dal reaction vector
(campo ``face`` + ``mood``) e dallo stato di animazione.

Il buddy in idle e' vivo: respira, sbatte le palpebre, si guarda intorno e,
dopo molto tempo senza eventi, si addormenta ("z"). Su un evento fa un
"bounce" e assume l'espressione della reazione per ``ttl_s`` secondi.

Questo modulo importa pygame (e' rendering), ma NON contiene logica di regole
o sintesi: quelle stanno in brain.py / synth.py, testabili senza pygame.
"""

from __future__ import annotations

import colorsys
import math
import random
from typing import Any, Dict, Tuple

import pygame

# soglia (s) di inattivita' oltre la quale il buddy si addormenta
SLEEP_AFTER_S = 90.0


def _hsv(h: float, s: float, v: float) -> Tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


class Face:
    """Disegna il buddy. Mantiene lo stato di animazione internamente."""

    def __init__(self, size: Tuple[int, int], palette: Dict[str, Any]) -> None:
        self.w, self.h = size
        self.cx, self.cy = self.w // 2, self.h // 2
        self.base_hue = float(palette.get("body_hue", 200))
        self.bg = tuple(palette.get("bg", [18, 18, 26]))
        self.accent = tuple(palette.get("accent", [255, 170, 60]))

        self.t = 0.0                    # tempo totale (s)
        self.idle_t = 0.0               # tempo dall'ultimo evento (s)
        self._blink = 0.0               # 0 aperto .. 1 chiuso
        self._next_blink = 2.0
        self._look = [0.0, 0.0]         # offset sguardo target
        self._look_cur = [0.0, 0.0]
        self._next_look = 3.0
        self._bounce_v = 0.0            # velocita' verticale del bounce
        self._bounce_y = 0.0

        # stato di reazione corrente (None = idle)
        self.reaction: Dict[str, Any] | None = None
        self.reaction_ttl = 0.0
        self._rng = random.Random()

    # ---- API usata da main.py -------------------------------------------
    def set_reaction(self, reaction: Dict[str, Any]) -> None:
        """Applica un reaction vector; parte anche il bounce."""
        self.reaction = reaction
        self.reaction_ttl = float(reaction.get("ttl_s", 8.0))
        self.idle_t = 0.0
        strength = float(reaction.get("face", {}).get("bounce", 0.6))
        self._bounce_v = -220.0 * (0.4 + strength)  # spinta verso l'alto

    @property
    def mood(self) -> str:
        if self.reaction:
            return str(self.reaction.get("mood", "curious"))
        if self.idle_t > SLEEP_AFTER_S:
            return "sleepy"
        return "curious"

    def update(self, dt: float) -> None:
        self.t += dt
        self.idle_t += dt

        # scadenza reazione
        if self.reaction is not None:
            self.reaction_ttl -= dt
            if self.reaction_ttl <= 0:
                self.reaction = None

        # blink
        self._next_blink -= dt
        if self._next_blink <= 0 and self._blink == 0.0:
            self._blink = 1e-3
        if self._blink > 0:
            self._blink += dt * 12.0
            if self._blink >= 2.0:       # ciclo chiudi+apri
                self._blink = 0.0
                self._next_blink = self._rng.uniform(1.8, 5.0)

        # sguardo che vaga (piu' lento se assonnato)
        self._next_look -= dt
        if self._next_look <= 0:
            reach = 0.1 if self.mood == "sleepy" else 0.35
            self._look = [self._rng.uniform(-reach, reach),
                          self._rng.uniform(-reach * 0.5, reach * 0.5)]
            self._next_look = self._rng.uniform(1.5, 4.5)
        # easing verso il target
        for i in range(2):
            self._look_cur[i] += (self._look[i] - self._look_cur[i]) * min(1.0, dt * 4)

        # fisica del bounce (molla verso y=0)
        self._bounce_v += (-self._bounce_y * 45.0) * dt   # richiamo elastico
        self._bounce_v *= (1.0 - min(1.0, dt * 4.0))      # smorzamento
        self._bounce_y += self._bounce_v * dt

    # ---- rendering -------------------------------------------------------
    def _eye_openness(self) -> float:
        """0 = chiuso, 1 = spalancato. Combina stile occhi + blink + respiro."""
        style = "wide"
        if self.reaction:
            style = str(self.reaction.get("face", {}).get("eyes", "wide"))
        elif self.mood == "sleepy":
            style = "closed"

        base = {"wide": 1.0, "half": 0.5, "squint": 0.35,
                "closed": 0.08, "spiral": 0.9}.get(style, 1.0)
        # respiro leggero
        base *= 0.92 + 0.08 * math.sin(self.t * 2.0)
        # blink: la funzione triangolare 0->1->0 chiude gli occhi
        blink = 1.0 - abs(self._blink - 1.0) if self._blink > 0 else 0.0
        return max(0.03, base * (1.0 - blink)), style

    def draw(self, surf: pygame.Surface, unseen: int = 0, muted: bool = False,
             text: str | None = None, font: pygame.font.Font | None = None) -> None:
        surf.fill(self.bg)

        breathe = 1.0 + 0.03 * math.sin(self.t * 2.0)
        r = int(min(self.w, self.h) * 0.28 * breathe)

        hue = self.base_hue
        sat, val = 0.45, 0.85
        if self.reaction:
            hue = float(self.reaction.get("face", {}).get("hue_shift", hue))
            urg = float(self.reaction.get("urgency", 0.4))
            sat = 0.4 + 0.4 * urg
        elif self.mood == "sleepy":
            sat, val = 0.25, 0.55

        body_col = _hsv(hue, sat, val)
        cy = self.cy + int(self._bounce_y)

        # ombra morbida
        shadow = pygame.Surface((r * 2, r), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
        surf.blit(shadow, (self.cx - r, self.cy + r - 6))

        # corpo/blob
        pygame.draw.circle(surf, body_col, (self.cx, cy), r)
        pygame.draw.circle(surf, _hsv(hue, sat, min(1.0, val + 0.15)),
                           (self.cx, cy), r, width=max(2, r // 14))

        # occhi
        openness, style = self._eye_openness()
        eye_dx = int(r * 0.42)
        eye_r = int(r * 0.20)
        lx = int(self._look_cur[0] * eye_r)
        ly = int(self._look_cur[1] * eye_r)
        for sx in (-1, 1):
            ex, ey = self.cx + sx * eye_dx, cy - int(r * 0.12)
            eh = max(2, int(eye_r * openness))
            # bianco dell'occhio (una capsula che si schiaccia col blink)
            pygame.draw.ellipse(surf, (245, 245, 250),
                                (ex - eye_r, ey - eh, eye_r * 2, eh * 2))
            if style == "spiral":
                self._draw_spiral(surf, ex, ey, eye_r)
            elif openness > 0.2:
                pygame.draw.circle(surf, (25, 25, 35),
                                   (ex + lx, ey + ly), max(2, int(eye_r * 0.5)))

        # bocca
        self._draw_mouth(surf, self.cx, cy + int(r * 0.35), r)

        # "z" da dormiente
        if self.mood == "sleepy" and font is not None:
            zz = "z" * (1 + int(self.t) % 3)
            zsurf = font.render(zz, True, (200, 200, 220))
            surf.blit(zsurf, (self.cx + r - 6, cy - r - 10))

        # HUD: badge non visti + mute + testo evento
        self._draw_hud(surf, unseen, muted, text, font)

    def _draw_spiral(self, surf, ex, ey, eye_r):
        pts = []
        for i in range(24):
            a = i * 0.9 + self.t * 3
            rad = eye_r * (i / 24.0)
            pts.append((ex + math.cos(a) * rad, ey + math.sin(a) * rad))
        if len(pts) > 1:
            pygame.draw.lines(surf, (25, 25, 35), False, pts, 2)

    def _draw_mouth(self, surf, mx, my, r):
        style = "smile"
        if self.reaction:
            style = str(self.reaction.get("face", {}).get("mouth", "smile"))
        elif self.mood == "sleepy":
            style = "flat"
        w = int(r * 0.6)
        col = (30, 25, 35)
        if style == "smile":
            rect = pygame.Rect(mx - w, my - w // 2, w * 2, w)
            pygame.draw.arc(surf, col, rect, math.pi, 2 * math.pi, 4)
        elif style == "flat":
            pygame.draw.line(surf, col, (mx - w, my), (mx + w, my), 4)
        elif style == "o":
            pygame.draw.circle(surf, col, (mx, my), max(4, w // 3), 4)
        elif style == "wave":
            pts = [(mx - w + i, my + int(math.sin(i * 0.4 + self.t * 4) * 4))
                   for i in range(0, w * 2, 4)]
            if len(pts) > 1:
                pygame.draw.lines(surf, col, False, pts, 3)

    def _draw_hud(self, surf, unseen, muted, text, font):
        if font is None:
            return
        if unseen > 0:
            badge = font.render(str(unseen), True, (255, 255, 255))
            bx, by = self.w - 34, 14
            pygame.draw.circle(surf, self.accent, (bx, by), 16)
            surf.blit(badge, badge.get_rect(center=(bx, by)))
        if muted:
            m = font.render("MUTE", True, (200, 120, 120))
            surf.blit(m, (14, 14))
        if text:
            t = font.render(text[:40], True, (230, 230, 240))
            bar = pygame.Surface((self.w, t.get_height() + 12), pygame.SRCALPHA)
            bar.fill((0, 0, 0, 130))
            surf.blit(bar, (0, self.h - bar.get_height()))
            surf.blit(t, (12, self.h - t.get_height() - 6))
