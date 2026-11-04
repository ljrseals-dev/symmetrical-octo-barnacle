Here's the full preset logic — not just the dictionaries, but the entire system: velocity layers, release articulation, mechanical noise, honest provenance, serializable bank, and a proper renderer. This is the answer to every criticism the Critic Harness raised about the preset layer.

```python
# lop_presets_full.py
"""
Land of Passion / Quiet Storm preset bank for symmetrical-octo-barnacle.

PROVENANCE
----------
These presets are AUTHORED for the KillerSynth engine. They are NOT
imported from any hardware emulation bank (Korg, Roland, Yamaha, Nord).
KillerSynth does not ship a factory preset bank, and no .fxp / .vstpreset
loader exists in the repo. The "analog" character comes from the engine's
Osc Drift, Filter, and Killer Mode parameters — not from sampled hardware.

If you want emulation-sourced presets, you must supply a .fxp/.vstpreset
bank AND a parameter mapper. That is out of scope for this module; see
the README's "importing external presets" section for the bridge.

VERSION: 2.0.0
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List

# ── Import the real Preset if available, else a compatible stand-in ──
try:
    from killer_synth import Preset  # type: ignore
except ImportError:
    @dataclass
    class Preset:
        name: str
        params: Dict[str, Any]
        mod: List[List[Any]] = field(default_factory=list)

        def to_dict(self) -> Dict[str, Any]:
            return {"name": self.name, "params": dict(self.params), "mod": list(self.mod)}


# ── Velocity bucket centres (0.0–1.0) ───────────────────────────
VELOCITY_BUCKETS = {"soft": 0.28, "med": 0.62, "hard": 0.92}


def _preset(name: str, params: Dict[str, Any],
            mod: List[List[Any]] | None = None) -> Preset:
    return Preset(name, params, mod or [])


# ── Shared mod routes (KillerSynth mod syntax) ──────────────────
# NOTE: KillerSynth exposes LFO→FILTER_FREQ, not LFO→AMPLITUDE, so a
# Rhodes tremolo cannot be reproduced exactly. The compromise below
# uses a low-amount filter LFO, which gives a slow "wah" rather than
# a true tremolo. Document this in the preset metadata.
RHODES_MOD = [["ENV", "FILTER_FREQ", 0.20],
              ["LFO", "FILTER_FREQ", 0.08]]


def build_preset_bank() -> Dict[str, Dict[str, Preset]]:
    """Return {instrument: {velocity_bucket: Preset}} + 'release' keys."""
    bank: Dict[str, Dict[str, Preset]] = {}

    # ── BASS: three velocity layers ─────────────────────────────
    bank["bass"] = {
        "soft": _preset("LoP Bass soft", {
            "Osc1 Wave": "sine", "Osc1 Level": 1.0,
            "Osc2 Wave": "saw",  "Osc2 Level": 0.15, "Osc2 Detune": 0.02,
            "Filter Mode": "lp", "Filter Cutoff": 200, "Filter Resonance": 0.10,
            "Env Attack": 0.12, "Env Decay": 0.35,
            "Env Sustain": 0.60, "Env Release": 0.70,
            "Reverb Amount": 0.15, "Osc Drift": 0.006,
            "Killer Mode": 0.35, "Master Volume": 0.70,
        }, [["ENV", "FILTER_FREQ", 0.20]]),

        "med": _preset("LoP Bass med", {
            "Osc1 Wave": "sine", "Osc1 Level": 1.0,
            "Osc2 Wave": "saw",  "Osc2 Level": 0.25, "Osc2 Detune": 0.04,
            "Filter Mode": "lp", "Filter Cutoff": 280, "Filter Resonance": 0.15,
            "Env Attack": 0.08, "Env Decay": 0.35,
            "Env Sustain": 0.55, "Env Release": 0.60,
            "Reverb Amount": 0.18, "Osc Drift": 0.008,
            "Killer Mode": 0.40, "Master Volume": 0.75,
        }, [["ENV", "FILTER_FREQ", 0.25]]),

        "hard": _preset("LoP Bass hard", {
            "Osc1 Wave": "sine", "Osc1 Level": 0.95,
            "Osc2 Wave": "saw",  "Osc2 Level": 0.40, "Osc2 Detune": 0.05,
            "Filter Mode": "lp", "Filter Cutoff": 420, "Filter Resonance": 0.22,
            "Env Attack": 0.05, "Env Decay": 0.30,
            "Env Sustain": 0.50, "Env Release": 0.55,
            "Reverb Amount": 0.15, "Osc Drift": 0.010,
            "Killer Mode": 0.45, "Master Volume": 0.80,
        }, [["ENV", "FILTER_FREQ", 0.30]]),
    }

    # ── RHODES: three velocity layers + release ─────────────────
    bank["rhodes"] = {
        "soft": _preset("LoP Rhodes soft", {
            "Osc1 Wave": "sine", "Osc1 Level": 1.00,
            "Osc2 Wave": "tri",  "Osc2 Level": 0.25, "Osc2 Detune": 0.05,
            "Osc3 Wave": "sine", "Osc3 Level": 0.08,
            "Filter Mode": "lp", "Filter Cutoff": 2200, "Filter Resonance": 0.18,
            "Env Attack": 0.020, "Env Decay": 0.50,
            "Env Sustain": 0.30, "Env Release": 0.85,
            "LFO Rate": 5.2, "LFO Wave": "sine", "Mod Wheel": 0.12,
            "Reverb Amount": 0.25, "Osc Drift": 0.005,
            "Killer Mode": 0.25, "Master Volume": 0.65,
        }, RHODES_MOD),

        "med": _preset("LoP Rhodes med", {
            "Osc1 Wave": "sine", "Osc1 Level": 0.85,
            "Osc2 Wave": "tri",  "Osc2 Level": 0.45, "Osc2 Detune": 0.07,
            "Osc3 Wave": "sine", "Osc3 Level": 0.15,
            "Filter Mode": "lp", "Filter Cutoff": 3200, "Filter Resonance": 0.22,
            "Env Attack": 0.012, "Env Decay": 0.45,
            "Env Sustain": 0.35, "Env Release": 0.90,
            "LFO Rate": 5.2, "LFO Wave": "sine", "Mod Wheel": 0.15,
            "Reverb Amount": 0.28, "Osc Drift": 0.006,
            "Killer Mode": 0.30, "Master Volume": 0.70,
        }, RHODES_MOD),

        "hard": _preset("LoP Rhodes hard", {
            "Osc1 Wave": "sine", "Osc1 Level": 0.78,
            "Osc2 Wave": "tri",  "Osc2 Level": 0.65, "Osc2 Detune": 0.08,
            "Osc3 Wave": "sine", "Osc3 Level": 0.30,
            "Filter Mode": "lp", "Filter Cutoff": 4200, "Filter Resonance": 0.30,
            "Env Attack": 0.008, "Env Decay": 0.40,
            "Env Sustain": 0.38, "Env Release": 0.85,
            "LFO Rate": 5.4, "LFO Wave": "sine", "Mod Wheel": 0.18,
            "Reverb Amount": 0.30, "Osc Drift": 0.007,
            "Killer Mode": 0.35, "Master Volume": 0.75,
        }, RHODES_MOD),

        # Release: short damped thump at note-off
        "release": _preset("LoP Rhodes release", {
            "Osc1 Wave": "sine", "Osc1 Level": 1.00,
            "Osc2 Wave": "tri",  "Osc2 Level": 0.30, "Osc2 Detune": 0.04,
            "Osc3 Wave": "sine", "Osc3 Level": 0.05,
            "Filter Mode": "lp", "Filter Cutoff": 1800, "Filter Resonance": 0.15,
            "Env Attack": 0.002, "Env Decay": 0.15,
            "Env Sustain": 0.00, "Env Release": 0.20,
            "Reverb Amount": 0.10, "Osc Drift": 0.003,
            "Killer Mode": 0.10, "Master Volume": 0.45,
        }),
    }

    # ── FLUTE: three velocity layers (noise handled in renderer) ─
    # We set Noise Level to 0 here; breath attack is synthesized
    # separately in the renderer and bandpassed 2–6 kHz, which is the
    # fix for the earlier criticism that lowpassing at 4.8 kHz turned
    # breath into hiss.
    bank["flute"] = {
        "soft": _preset("LoP Flute soft", {
            "Osc1 Wave": "sine", "Osc1 Level": 1.0,
            "Osc2 Wave": "sine", "Osc2 Level": 0.12, "Osc2 Detune": 0.02,
            "Filter Mode": "lp", "Filter Cutoff": 3800, "Filter Resonance": 0.10,
            "Env Attack": 0.12, "Env Decay": 0.40,
            "Env Sustain": 0.70, "Env Release": 0.80,
            "LFO Rate": 5.2, "LFO Wave": "sine", "Mod Wheel": 0.25,
            "Noise Level": 0.0,
            "Reverb Amount": 0.35, "Osc Drift": 0.003,
            "Killer Mode": 0.15, "Master Volume": 0.60,
        }, [["LFO", "OSC1_FREQ", 0.06]]),

        "med": _preset("LoP Flute med", {
            "Osc1 Wave": "sine", "Osc1 Level": 1.0,
            "Osc2 Wave": "sine", "Osc2 Level": 0.18, "Osc2 Detune": 0.03,
            "Filter Mode": "lp", "Filter Cutoff": 4800, "Filter Resonance": 0.12,
            "Env Attack": 0.09, "Env Decay": 0.40,
            "Env Sustain": 0.65, "Env Release": 0.70,
            "LFO Rate": 5.4, "LFO Wave": "sine", "Mod Wheel": 0.35,
            "Noise Level": 0.0,
            "Reverb Amount": 0.32, "Osc Drift": 0.004,
            "Killer Mode": 0.20, "Master Volume": 0.65,
        }, [["LFO", "OSC1_FREQ", 0.08]]),

        "hard": _preset("LoP Flute hard", {
            "Osc1 Wave": "sine", "Osc1 Level": 1.0,
            "Osc2 Wave": "tri",  "Osc2 Level": 0.25, "Osc2 Detune": 0.03,
            "Filter Mode": "lp", "Filter Cutoff": 6000, "Filter Resonance": 0.14,
            "Env Attack": 0.05, "Env Decay": 0.35,
            "Env Sustain": 0.60, "Env Release": 0.65,
            "LFO Rate": 5.6, "LFO Wave": "sine", "Mod Wheel": 0.40,
            "Noise Level": 0.0,
            "Reverb Amount": 0.30, "Osc Drift": 0.005,
            "Killer Mode": 0.25, "Master Volume": 0.70,
        }, [["LFO", "OSC1_FREQ", 0.10]]),
    }

    # ── PAD: one preset (pads don't get velocity layers) ────────
    bank["pad"] = {
        "med": _preset("LoP Warm Pad", {
            "Osc1 Wave": "saw", "Osc1 Level": 0.70,
            "Osc2 Wave": "saw", "Osc2 Level": 0.65, "Osc2 Detune": 0.11,
            "Filter Mode": "lp", "Filter Cutoff": 1800, "Filter Resonance": 0.18,
            "Env Attack": 1.10, "Env Decay": 0.80,
            "Env Sustain": 0.85, "Env Release": 2.20,
            "LFO Rate": 0.35, "LFO Wave": "sine", "Mod Wheel": 0.10,
            "Reverb Amount": 0.45, "Osc Drift": 0.015,
            "Killer Mode": 0.50, "Master Volume": 0.55,
        }, [["LFO", "FILTER_FREQ", 0.18], ["ENV", "FILTER_FREQ", 0.15]]),
    }

    return bank


# ── Serializable bank ────────────────────────────────────────────
class PresetBank:
    """A versioned, JSON-serializable collection of presets."""

    def __init__(self, data: Dict[str, Dict[str, Preset]],
                 version: str = "2.0.0",
                 provenance: str = "authored-for-killer-synth"):
        self.data = data
        self.version = version
        self.provenance = provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "provenance": self.provenance,
            "bank": {
                inst: {bucket: p.to_dict() for bucket, p in buckets.items()}
                for inst, buckets in self.data.items()
            },
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "PresetBank":
        blob = json.loads(Path(path).read_text())
        data = {
            inst: {
                bucket: _preset(p["name"], p["params"], p.get("mod", []))
                for bucket, p in buckets.items()
            }
            for inst, buckets in blob["bank"].items()
        }
        return cls(data, blob["version"], blob["provenance"])

    def __getitem__(self, instrument: str) -> Dict[str, Preset]:
        return self.data[instrument]


# ── Demo / self-test ────────────────────────────────────────────
if __name__ == "__main__":
    bank = PresetBank(build_preset_bank())
    out = Path("lop_preset_bank.json")
    bank.save(out)
    total = sum(len(buckets) for buckets in bank.data.values())
    print(f"Wrote {out}  ({total} presets, {len(bank.data)} instruments)")
    print(f"Provenance: {bank.provenance}")
    for inst, buckets in bank.data.items():
        names = ", ".join(f"{k}={p.name}" for k, p in buckets.items())
        print(f"  {inst:8s}: {names}")
```

```python
# lop_render.py
"""
Renderer for the Land of Passion bed.

Uses the full preset bank from lop_presets_full.py, with:
  • velocity bucketing + within-bucket gain scaling
  • release articulation (Rhodes damped thump at note-off)
  • mechanical noise (key click, breath attack, finger noise)
  • honest local hash chain (NOT London Fog — see README)
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from killer_synth import KillerSynth, save_wav
from lop_presets_full import PresetBank, VELOCITY_BUCKETS, build_preset_bank


SR = 44100
BPM = 84.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
SWING = 0.56
RNG = np.random.default_rng(1979)


# ── Utility ─────────────────────────────────────────────────────
def _hp(x: np.ndarray, cutoff: float) -> np.ndarray:
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    return np.fft.irfft(X / (1.0 + (cutoff / np.maximum(f, 1e-6)) ** 2), n).astype(np.float32)


def _bp(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    lo_mask = 1.0 / (1.0 + (lo / np.maximum(f, 1e-6)) ** 2)
    hi_mask = 1.0 / (1.0 + (f / hi) ** 2)
    return np.fft.irfft(X * lo_mask * hi_mask, n).astype(np.float32)


def bucket_velocity(vel: float) -> str:
    """Map a velocity in [0, 1] to the nearest bucket by centre distance."""
    return min(VELOCITY_BUCKETS, key=lambda k: abs(VELOCITY_BUCKETS[k] - vel))


def within_bucket_gain(vel: float, bucket: str) -> float:
    """Small gain trim so notes in the same bucket still vary."""
    centre = VELOCITY_BUCKETS[bucket]
    return float(np.clip(0.85 + 0.30 * (vel - centre), 0.75, 1.00))


# ── Mechanical noise (synthesized, not preset-based) ────────────
def rhodes_key_click(dur: float = 0.008) -> np.ndarray:
    n = int(dur * SR)
    noise = RNG.standard_normal(n).astype(np.float32)
    noise = _hp(noise, 1800.0)
    env = np.exp(-np.linspace(0, 6, n))
    return (noise * env * 0.55).astype(np.float32)


def flute_breath_attack(dur: float = 0.060) -> np.ndarray:
    n = int(dur * SR)
    noise = RNG.standard_normal(n).astype(np.float32)
    noise = _bp(noise, 2000.0, 6000.0)  # FIX: bandpass, not lowpass
    t = np.arange(n) / n
    env = np.sin(np.pi * t) ** 0.6        # soft in, soft out
    return (noise * env * 0.30).astype(np.float32)


def bass_finger_noise(dur: float = 0.020) -> np.ndarray:
    n = int(dur * SR)
    noise = RNG.standard_normal(n).astype(np.float32)
    noise = _hp(_bp(noise, 150.0, 900.0), 120.0)
    env = np.exp(-np.linspace(0, 5, n))
    return (noise * env * 0.22).astype(np.float32)


# ── Layer renderer with velocity + release + noise ──────────────
def render_layer(synth: KillerSynth, bank: PresetBank, instrument: str,
                 notes: List[Tuple[int, float, float, float]],
                 noise_fn=None, noise_offset_s: float = 0.0,
                 total_len: int | None = None) -> np.ndarray:
    """
    notes: list of (midi, start_s, dur_s, velocity) where velocity ∈ [0, 1]
    """
    buckets = bank[instrument]
    # Group by bucket
    groups: Dict[str, List[Tuple[int, float, float, float]]] = {k: [] for k in buckets}
    for midi, start, dur, vel in notes:
        groups[bucket_velocity(vel)].append((midi, start, dur, vel))

    # Determine output length from the last note
    if total_len is None:
        total_len = max(
            int((s + d) * SR) for _, s, d, _ in notes
        ) if notes else SR
        total_len += int(2.0 * SR)   # room for release tails

    # Render main layers
    out = np.zeros((total_len, 2), np.float32)
    for bucket, bucket_notes in groups.items():
        if not bucket_notes or bucket not in buckets:
            continue
        render_notes = [(m, s, d) for m, s, d, _ in bucket_notes]
        audio = synth.render_sequence(buckets[bucket], render_notes)
        # Apply within-bucket gain scaling
        for i, (_, s, _, vel) in enumerate(bucket_notes):
            g = within_bucket_gain(vel, bucket)
            e = min(int((s + 2.0) * SR), len(audio))
            b = int(s * SR)
            if b < len(audio):
                audio[b:e] *= g
        out[:len(audio)] += audio

    # Rhodes release articulation
    if instrument == "rhodes" and "release" in buckets:
        rel_notes = [(m, s + d, 0.20) for m, s, d, _ in notes]
        rel_audio = synth.render_sequence(buckets["release"], rel_notes)
        out[:len(rel_audio)] += rel_audio * 0.35

    # Mechanical noise
    if noise_fn is not None:
        for m, s, d, _ in notes:
            burst = noise_fn()
            b = int((s + noise_offset_s) * SR)
            e = min(b + len(burst), len(out))
            if b < len(out):
                out[b:e] += burst[:e - b, None] * 0.5

    return out


# ── Arrangement ────────────────────────────────────────────────
CHORDS = [
    (36, 8, [36, 43], [51, 55, 58, 62], [67, 63]),   # Cm9
    (41, 8, [41, 48], [56, 60, 63, 67], [68, 65]),   # Fm9
    (38, 4, [38, 45], [53, 56, 60],     [62]),       # Dm7b5
    (43, 4, [43, 50], [59, 62, 65, 68], [67]),       # G7b9
    (36, 8, [36, 43], [51, 55, 58, 62], [63, 67]),   # Cm9
]


def h(sec: float, ms: float = 5.0) -> float:
    return sec + RNG.uniform(-ms, ms) / 1000.0


def build_note_lists():
    bass, rhodes, flute, pad = [], [], [], []
    t = 0.0
    for _, beats, b_notes, r_notes, f_notes in CHORDS:
        dur = beats * BEAT
        # bass: root at full, fifth at 0.7
        bass.append((b_notes[0], h(t, 2), dur * 0.95, 0.75))
        if len(b_notes) > 1:
            bass.append((b_notes[1], h(t + 2 * BEAT, 3), dur * 0.45, 0.55))
        # rhodes: staggered block, descending velocity on inner voices
        for i, m in enumerate(r_notes):
            vel = 0.75 - 0.05 * i
            rhodes.append((m, h(t + 0.04 * i, 6), min(1.6, dur * 0.7), vel))
        # flute: long tones
        for i, m in enumerate(f_notes):
            vel = 0.70 + 0.10 * (i % 2)
            flute.append((m, h(t + i * 1.5 * BEAT, 8), 1.8 * BEAT, vel))
        # pad: sustained
        for m in r_notes[:3]:
            pad.append((m, h(t, 10), dur * 0.98, 0.60))
        t += dur
    return bass, rhodes, flute, pad


# ── Drums ──────────────────────────────────────────────────────
def make_kick() -> np.ndarray:
    dur = 0.22; n = int(dur * SR); t = np.arange(n) / SR
    pitch = 45 + 85 * np.exp(-55 * t)
    body = np.sin(2 * np.pi * np.cumsum(pitch) / SR)
    click = np.exp(-400 * t) * RNG.standard_normal(n).astype(np.float32) * 0.15
    return ((body + click) * np.exp(-9 * t) * (1 - np.exp(-200 * t))).astype(np.float32)


def make_snare() -> np.ndarray:
    dur = 0.16; n = int(dur * SR); t = np.arange(n) / SR
    body = (0.55 * np.sin(2 * np.pi * 185 * t)
            + 0.35 * np.sin(2 * np.pi * 340 * t)) * np.exp(-28 * t)
    noise = _hp(RNG.standard_normal(n).astype(np.float32), 900) * np.exp(-20 * t)
    return (body + 0.75 * noise).astype(np.float32)


def make_hat() -> np.ndarray:
    dur = 0.045; n = int(dur * SR); t = np.arange(n) / SR
    return (_hp(RNG.standard_normal(n).astype(np.float32), 6000)
            * np.exp(-95 * t)).astype(np.float32)


def swing_time(bar: int, slot: int) -> float:
    beat = slot // 2
    off = (slot % 2) * SWING
    return bar * BAR + (beat + off) * BEAT


def render_drums(num_bars: int, total_len: int) -> np.ndarray:
    out = np.zeros((total_len, 2), np.float32)
    kick, snare, hat = make_kick(), make_snare(), make_hat()

    def place(sig, start_s, gain, pan):
        s = int(start_s * SR); e = min(s + len(sig), len(out))
        if s >= len(out) or e <= s:
            return
        lg, rg = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
        out[s:e, 0] += sig[:e - s] * gain * lg
        out[s:e, 1] += sig[:e - s] * gain * rg

    for bar in range(num_bars):
        place(kick,  bar * BAR,             0.62, 0.00)
        place(kick,  bar * BAR + 2 * BEAT,  0.55, 0.00)
        place(snare, bar * BAR + 1 * BEAT + h(0, 4), 0.40, 0.08)
        place(snare, bar * BAR + 3 * BEAT + h(0, 4), 0.38, 0.08)
        for slot in range(8):
            v = 0.13 if slot % 2 == 0 else 0.09
            place(hat, swing_time(bar, slot) + h(0, 3), v, 0.35)
    return out


# ── Master chain ──────────────────────────────────────────────
def glue_reverb(mix: np.ndarray, decay_s: float = 1.8) -> np.ndarray:
    ir_len = int(decay_s * SR)
    t = np.arange(ir_len) / SR
    ir = RNG.standard_normal(ir_len).astype(np.float32) * np.exp(-6.9 * t / decay_s)
    ir[0] = 0.0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9

    def conv(x, kernel):
        nf = 1 << (len(x) + len(kernel) - 2).bit_length()
        y = np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(kernel, nf), nf)[:len(x)]
        return y.astype(np.float32)

    out = mix.copy()
    out[:, 0] = 0.82 * mix[:, 0] + 0.18 * conv(mix[:, 0], ir)
    out[:, 1] = 0.82 * mix[:, 1] + 0.18 * conv(mix[:, 1], np.roll(ir, 271))
    return out


def master(mix: np.ndarray) -> np.ndarray:
    peak = float(np.abs(mix).max())
    if peak > 0:
        mix = mix * (0.92 / peak)
    return (np.tanh(mix * 1.05) * 0.95).astype(np.float32)


# ── Hash-chained audit log (honest naming) ─────────────────────
class HashChain:
    """A local hash chain. NOT tamper-evident against deletion.
    For real tamper-evidence, wire fictional-winner's run_ceremony."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prev = "0" * 64
        if path.exists():
            with path.open() as f:
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
        with self.path.open("a") as f:
            f.write(json.dumps(body) + "\n")
        self.prev = h
        return h


# ── Main ──────────────────────────────────────────────────────
def main(out_dir: Path = Path(".")) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    bank = PresetBank(build_preset_bank())
    bank.save(out_dir / "lop_preset_bank.json")

    chain = HashChain(out_dir / "lop_chain.jsonl")
    for inst, buckets in bank.data.items():
        for bucket, p in buckets.items():
            chain.record("preset_define", {
                "instrument": inst, "bucket": bucket, "preset": p.to_dict(),
            })

    synth = KillerSynth(seed=1979)
    bass, rhodes, flute, pad = build_note_lists()
    total_beats = sum(b for _, b, *_ in CHORDS)
    total_len = int((total_beats * BEAT + 3.0) * SR)

    print("Rendering bass…")
    bass_audio = render_layer(synth, bank, "bass", bass,
                              noise_fn=bass_finger_noise, total_len=total_len)
    print("Rendering rhodes…")
    rhodes_audio = render_layer(synth, bank, "rhodes", rhodes,
                                noise_fn=rhodes_key_click, total_len=total_len)
    print("Rendering flute…")
    flute_audio = render_layer(synth, bank, "flute", flute,
                               noise_fn=flute_breath_attack, total_len=total_len)
    print("Rendering pad…")
    pad_audio = render_layer(synth, bank, "pad", pad, total_len=total_len)

    num_bars = total_beats // 4
    drums = render_drums(num_bars, total_len)

    mix = np.zeros((total_len, 2), np.float32)
    for src, gain in [(bass_audio, 0.55), (rhodes_audio, 0.40),
                      (flute_audio, 0.32), (pad_audio, 0.20)]:
        mix += src * gain
    mix += drums

    mix = master(glue_reverb(mix))

    out_path = out_dir / "land_of_passion_full.wav"
    save_wav(str(out_path), mix)

    with out_path.open("rb") as f:
        wav_hash = hashlib.sha256(f.read()).hexdigest()

    chain.record("render_finalize", {
        "wav": str(out_path),
        "sha256": wav_hash,
        "bpm": BPM,
        "bars": num_bars,
        "duration_s": round(len(mix) / SR, 3),
        "preset_bank_version": bank.version,
        "provenance": bank.provenance,
    })

    print(f"\nWrote {out_path}  ({len(mix)/SR:.1f}s, peak {np.abs(mix).max():.3f})")
    print(f"Preset bank: {out_dir/'lop_preset_bank.json'}")
    print(f"Hash chain tail: {chain.prev[:16]}…")


if __name__ == "__main__":
    main(Path(os.environ.get("LOP_OUT", ".")))
```

What this fixes, one-by-one, from the Critic Harness review

Critic flag Fix
"Presets don't take from emulation" PROVENANCE docstring says plainly: authored, not imported. No fake emulation claim.
Rhodes LFO targets filter, not amplitude Documented in RHODES_MOD comment: "KillerSynth exposes LFO→FILTER_FREQ, not amplitude. Compromise, not tremolo."
Flute noise lowpassed into hiss Noise Level: 0.0 in the preset; breath attack synthesized separately with _bp(2000, 6000) in flute_breath_attack()
No velocity layers Three presets per instrument (soft/med/hard), bucket_velocity() + within_bucket_gain()
No release articulation bank["rhodes"]["release"] rendered at every note-off
No mechanical noise rhodes_key_click, flute_breath_attack, bass_finger_noise — synthesized, layered
No main guard if __name__ == "__main__": main()
Hardcoded paths out_dir param, LOP_OUT env var
Global PRESETS.update() Isolated PresetBank class with save/load
Fake "London Fog" claim Renamed AuditLog → HashChain with an honest docstring: "NOT tamper-evident against deletion."
No versioning PresetBank.version = "2.0.0", written into JSON and hash log

Running it

```bash
cd /home/workdir/artifacts/killer_synth/sardine_killer
LOP_OUT=/home/workdir/artifacts python3 lop_presets_full.py   # writes lop_preset_bank.json
LOP_OUT=/home/workdir/artifacts python3 lop_render.py          # writes WAV + chain
```

What you get

· lop_preset_bank.json — versioned, human-readable, auditable preset bank (11 presets across 4 instruments)
· lop_chain.jsonl — hash-chained provenance (11 preset hashes + 1 render hash)
· land_of_passion_full.wav — the render

Honest remaining gaps (unchanged)

The Rhodes tremolo is still filter-based, not amplitude-based — KillerSynth can't fix that from the preset layer. The oscillators still alias above ~2 kHz. And for genuine "professional record" timbre, you still need sample-based instruments. What this gives you is the best preset logic the engine can support, with every limitation documented rather than hidden. That's the difference between a prototype and something you can hand to another engineer.
