# lop_audited.py  — Quiet Storm bed, rendered by Killer Synth, audited by London Fog
import json, hashlib, time, os
from datetime import datetime, timezone

import numpy as np

from killer_synth import KillerSynth, Preset, save_wav
from killer_presets import PRESETS

# ── Minimal London Fog–style audit log ──────────────────────────
# Full London Fog needs TSA endpoints + Rekor v2 + Ed25519 keys.
# This local stand-in keeps the same contract: every edit is hashed,
# chained, and timestamped before the render is allowed to proceed.
class AuditLog:
    def __init__(self, path="audit/lop_chain.jsonl"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.prev = "0" * 64
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    self.prev = json.loads(line)["hash"]

    def record(self, kind: str, payload: dict) -> str:
        body = {
            "kind": kind,
            "utc": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "prev": self.prev,
        }
        h = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        body["hash"] = h
        with open(self.path, "a") as f:
            f.write(json.dumps(body) + "\n")
        self.prev = h
        return h

audit = AuditLog()

# ── Quiet Storm presets on Killer ──────────────────────────────
lop = {
    "LoP Soft Bass": Preset("LoP Soft Bass", {
        "Osc1 Wave": "sine", "Osc1 Level": 1.0,
        "Osc2 Wave": "saw", "Osc2 Level": 0.25, "Osc2 Detune": 0.04,
        "Filter Mode": "lp", "Filter Cutoff": 280, "Filter Resonance": 0.15,
        "Env Attack": 0.08, "Env Decay": 0.35, "Env Sustain": 0.55, "Env Release": 0.6,
        "Reverb Amount": 0.18, "Osc Drift": 0.008, "Killer Mode": 0.4,
        "Master Volume": 0.75,
    }, [["ENV", "FILTER_FREQ", 0.25]]),

    "LoP Rhodes": Preset("LoP Rhodes", {
        "Osc1 Wave": "sine", "Osc1 Level": 0.85,
        "Osc2 Wave": "tri", "Osc2 Level": 0.45, "Osc2 Detune": 0.07,
        "Osc3 Wave": "sine", "Osc3 Level": 0.15,
        "Filter Mode": "lp", "Filter Cutoff": 3200, "Filter Resonance": 0.22,
        "Env Attack": 0.012, "Env Decay": 0.45, "Env Sustain": 0.35, "Env Release": 0.9,
        "LFO Rate": 5.2, "LFO Wave": "sine", "Mod Wheel": 0.15,
        "Reverb Amount": 0.28, "Osc Drift": 0.006, "Killer Mode": 0.3,
        "Master Volume": 0.7,
    }, [["LFO", "FILTER_FREQ", 0.12], ["ENV", "FILTER_FREQ", 0.2]]),

    "LoP Flute": Preset("LoP Flute", {
        "Osc1 Wave": "sine", "Osc1 Level": 1.0,
        "Osc2 Wave": "sine", "Osc2 Level": 0.18, "Osc2 Detune": 0.03,
        "Filter Mode": "lp", "Filter Cutoff": 4800, "Filter Resonance": 0.12,
        "Env Attack": 0.09, "Env Decay": 0.4, "Env Sustain": 0.65, "Env Release": 0.7,
        "LFO Rate": 5.4, "LFO Wave": "sine", "Mod Wheel": 0.35,
        "Noise Level": 0.04,
        "Reverb Amount": 0.32, "Osc Drift": 0.004, "Killer Mode": 0.2,
        "Master Volume": 0.65,
    }, [["LFO", "OSC1_FREQ", 0.08]]),

    "LoP Warm Pad": Preset("LoP Warm Pad", {
        "Osc1 Wave": "saw", "Osc1 Level": 0.7,
        "Osc2 Wave": "saw", "Osc2 Level": 0.65, "Osc2 Detune": 0.11,
        "Filter Mode": "lp", "Filter Cutoff": 1800, "Filter Resonance": 0.18,
        "Env Attack": 1.1, "Env Decay": 0.8, "Env Sustain": 0.85, "Env Release": 2.2,
        "LFO Rate": 0.35, "LFO Wave": "sine", "Mod Wheel": 0.1,
        "Reverb Amount": 0.45, "Osc Drift": 0.015, "Killer Mode": 0.5,
        "Master Volume": 0.55,
    }, [["LFO", "FILTER_FREQ", 0.18], ["ENV", "FILTER_FREQ", 0.15]]),
}
PRESETS.update(lop)

# ── Log every preset before it is allowed to render ────────────
for name, p in lop.items():
    audit.record("preset_define", p.to_dict())

synth = KillerSynth(seed=1979)
RNG = np.random.default_rng(1979)
BPM = 84.0; BEAT = 60.0 / BPM; BAR = 4 * BEAT; SWING = 0.56

# ── Harmony: full voicings, rootless Rhodes ────────────────────
chords = [
    (36, 8, [36, 43], [51, 55, 58, 62], [67, 63]),   # Cm9
    (41, 8, [41, 48], [56, 60, 63, 67], [68, 65]),   # Fm9
    (38, 4, [38, 45], [53, 56, 60],     [62]),       # Dm7b5
    (43, 4, [43, 50], [59, 62, 65, 68], [67]),       # G7b9
    (36, 8, [36, 43], [51, 55, 58, 62], [63, 67]),   # Cm9
]

def h(sec, ms=5.0):
    return sec + RNG.uniform(-ms, ms) / 1000.0

notes = {"bass": [], "rhodes": [], "flute": [], "pad": []}
t = 0.0
for _, beats, bass, rhodes, flute in chords:
    dur = beats * BEAT
    notes["bass"].append((bass[0], h(t, 2), dur * 0.95))
    if len(bass) > 1:
        notes["bass"].append((bass[1], h(t + 2 * BEAT, 3), dur * 0.45))
    for i, m in enumerate(rhodes):
        notes["rhodes"].append((m, h(t + 0.04 * i, 6), min(1.6, dur * 0.7)))
    for i, m in enumerate(flute):
        notes["flute"].append((m, h(t + i * 1.5 * BEAT, 8), 1.8 * BEAT))
    for m in rhodes[:3]:
        notes["pad"].append((m, h(t, 10), dur * 0.98))
    t += dur

TOTAL_BEATS = sum(b for _, b, *_ in chords)
TOTAL_SEC = TOTAL_BEATS * BEAT

# ── Render layers ──────────────────────────────────────────────
print("Rendering…")
layers = {
    "bass":   synth.render_sequence(lop["LoP Soft Bass"],  notes["bass"]),
    "rhodes": synth.render_sequence(lop["LoP Rhodes"],     notes["rhodes"]),
    "flute":  synth.render_sequence(lop["LoP Flute"],      notes["flute"]),
    "pad":    synth.render_sequence(lop["LoP Warm Pad"],   notes["pad"]),
}

# ── Drums (same as previous version; synth layer) ─────────────
SR = 44100
def fft_hp(x, cutoff):
    n = len(x); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(X / (1 + (cutoff / np.maximum(f, 1e-6)) ** 2), n).astype(np.float32)

def make_kick(dur=0.22):
    n = int(dur * SR); t = np.arange(n) / SR
    pitch = 45 + 85 * np.exp(-55 * t)
    body = np.sin(2 * np.pi * np.cumsum(pitch) / SR)
    click = np.exp(-400 * t) * RNG.standard_normal(n) * 0.15
    return ((body + click) * np.exp(-9 * t) * (1 - np.exp(-200 * t))).astype(np.float32)

def make_snare(dur=0.16):
    n = int(dur * SR); t = np.arange(n) / SR
    body = (0.55 * np.sin(2 * np.pi * 185 * t) + 0.35 * np.sin(2 * np.pi * 340 * t)) * np.exp(-28 * t)
    noise = fft_hp(RNG.standard_normal(n).astype(np.float32), 900) * np.exp(-20 * t)
    return (body + 0.75 * noise).astype(np.float32)

def make_hat(dur=0.045):
    n = int(dur * SR); t = np.arange(n) / SR
    return (fft_hp(RNG.standard_normal(n).astype(np.float32), 6000) * np.exp(-95 * t)).astype(np.float32)

def swing_time(bar, slot):
    beat = slot // 2; off = (slot % 2) * SWING
    return bar * BAR + (beat + off) * BEAT

NUM_BARS = TOTAL_BEATS // 4
drum_len = int((TOTAL_SEC + 1.0) * SR)
drums = np.zeros((drum_len, 2), np.float32)

def place(buf, sig, start_s, gain, pan):
    s = int(start_s * SR); e = min(s + len(sig), len(buf))
    if s >= len(buf) or e <= s: return
    lg, rg = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
    buf[s:e, 0] += sig[: e - s] * gain * lg
    buf[s:e, 1] += sig[: e - s] * gain * rg

KICK, SNARE, HAT = make_kick(), make_snare(), make_hat()
for bar in range(NUM_BARS):
    place(drums, KICK,  bar * BAR,               0.62, 0.00)
    place(drums, KICK,  bar * BAR + 2 * BEAT,    0.55, 0.00)
    place(drums, SNARE, bar * BAR + 1 * BEAT + h(0, 4), 0.40, 0.08)
    place(drums, SNARE, bar * BAR + 3 * BEAT + h(0, 4), 0.38, 0.08)
    for slot in range(8):
        v = 0.13 if slot % 2 == 0 else 0.09
        place(drums, HAT, swing_time(bar, slot) + h(0, 3), v, 0.35)

# ── Mix + master ──────────────────────────────────────────────
maxlen = max([len(x) for x in layers.values()] + [len(drums)])
mix = np.zeros((maxlen, 2), np.float32)
for src, gain in [("bass", 0.55), ("rhodes", 0.40), ("flute", 0.32), ("pad", 0.20)]:
    mix[: len(layers[src])] += layers[src] * gain
mix[: len(drums)] += drums

# Glue reverb (simple)
ir_len = int(1.8 * SR)
t_ir = np.arange(ir_len) / SR
ir = RNG.standard_normal(ir_len).astype(np.float32) * np.exp(-6.9 * t_ir / 1.8)
ir[0] = 0.0; ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
def conv(x, kernel):
    nf = 1 << (len(x) + len(kernel) - 2).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(kernel, nf), nf)[: len(x)]
    return y.astype(np.float32)
mix[:, 0] = 0.82 * mix[:, 0] + 0.18 * conv(mix[:, 0], ir)
mix[:, 1] = 0.82 * mix[:, 1] + 0.18 * conv(mix[:, 1], np.roll(ir, 271))

peak = np.abs(mix).max()
if peak > 0: mix *= 0.92 / peak
mix = np.tanh(mix * 1.05) * 0.95

# ── Log the render, then write ────────────────────────────────
out_path = "/home/workdir/artifacts/land_of_passion_audited.wav"
save_wav(out_path, mix)

with open(out_path, "rb") as f:
    wav_hash = hashlib.sha256(f.read()).hexdigest()

audit.record("render_finalize", {
    "wav": out_path,
    "sha256": wav_hash,
    "bpm": BPM,
    "bars": NUM_BARS,
    "duration_s": round(len(mix) / SR, 3),
    "presets": list(lop.keys()),
})
print(f"Wrote {out_path}  ({len(mix)/SR:.1f}s, peak {np.abs(mix).max():.3f})")
print(f"Audit chain tail: {audit.prev}")
