# buddy — assistente notifiche per handheld R36XX

Un compagno digitale che vive su una console R36XX (Rockchip RK3326, 1 GB RAM,
640×480, no touch) e **reagisce** alle notifiche del PC/telefono/API con
**suoni e animazioni generati proceduralmente a runtime** — mai file audio,
mai GIF. Il brain produce solo un piccolo JSON ("reaction vector"); synth e
face lo trasformano in suono e video.

Stato: **Fase 1** — scheletro minimo funzionante, sviluppabile su PC.

## Prova su PC (30 secondi)

```bash
pip install -r requirements.txt
cd buddy
python main.py --sim
```

Genera notifiche finte a intervalli casuali: ogni notifica produce un **suono
diverso** e un'**animazione diversa**. In idle il buddy respira, sbatte le
palpebre, si guarda intorno e dopo un po' si addormenta.

Comandi (tastiera):

| Tasto | Azione |
|---|---|
| `A` / `Invio` | "ho visto" (azzera badge e testo) |
| `B` / `R` | ripeti l'ultima reazione |
| `X` / `M` | muto on/off |
| `Esc` | chiusura pulita (= START sul gamepad) |

## Test delle parti pure (senza pygame)

`brain.py` e `synth.py` sono funzioni pure (dict/array in uscita), testabili
senza audio né video:

```bash
python tests/test_pure.py        # oppure: python -m pytest tests/ -q
```

## Architettura

```
PC / telefono / API  --MQTT topic buddy/notify-->  R36XX (buddy)
                                                     bus  -> notifiche
                                                     brain-> reaction vector
                                                     synth-> suono (numpy)
                                                     face -> animazione
                                                     main -> loop 30fps
```

Il broker MQTT (mosquitto) gira **sulla console stessa**, così il buddy è
autosufficiente e funziona anche a PC spento. PC e telefono sono solo publisher.

### Reaction vector (unico output del brain)

```json
{
  "urgency": 0.0, "valence": -1.0,
  "mood": "curious|alert|sleepy|happy|annoyed|focused",
  "sound": {"engine": "fm|pluck|chime|noise", "root_hz": 440.0,
            "intervals": [0,7,12], "decay": 0.4, "brightness": 0.6,
            "density": 3, "detune": 0.02},
  "face": {"eyes": "wide|half|closed|spiral|squint",
           "mouth": "smile|flat|o|wave", "bounce": 0.7, "hue_shift": 30},
  "text": "riga breve, max 40 caratteri", "ttl_s": 8
}
```

Due brain intercambiabili: **`RuleBrain`** (deterministico + jitter, offline,
default) e **`LLMBrain`** (stub: per ora delega al RuleBrain; Fase 4 → API con
timeout e fallback).

## File

```
buddy/
  main.py        loop pygame + macchina a stati + input + logging
  bus.py         sorgente MQTT (thread) + SimSource finta per i test
  brain.py       RuleBrain / LLMBrain -> reaction vector   (puro, no pygame)
  synth.py       sintesi numpy -> pygame.Sound             (puro, no pygame)
  face.py        rendering vettoriale parametrico del buddy
  config.toml    broker, palette, filtri, pulsanti, profili per-sorgente
  run.sh         launcher (menu Ports di ArkOS)
agents/
  linux_dbus.py  PC Linux: notifiche desktop D-Bus -> MQTT
  publish.py     publisher one-shot (es. hook "Claude Code ha finito")
tests/
  test_pure.py   test di brain e synth senza pygame
```

## Sorgenti configurate

- **`claude_code`** — es. hook "Claude Code ha finito" via `agents/publish.py`.
- **`teams`** — notifiche desktop via `agents/linux_dbus.py`.
- **`default`** — tutto il resto.

Firma sonora/visiva per-sorgente e filtri ("cosa non mostrare mai") in
`config.toml`.

## Fasi successive (non ancora fatte)

2. deploy su ArkOS in `/roms/ports/`, mappatura gamepad reale, tuning perf
3. agente Android (app di forwarding → MQTT) + agente Windows
4. `LLMBrain` con API + cache
5. memoria e stati a lungo termine
6. eventuale modello locale
