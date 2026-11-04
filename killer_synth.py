"""killer_synth.py - the Killer synthesizer (Ionic Performer / Synthi-style).

Panel + 16x16 pin matrix + SVF + Schroeder reverb + "Killer Mode" imperfections.
Pure numpy/scipy. Deterministic when a seed is given.
Matrix rule:  dst[j] = sum_i src[i] * pins[i, j]
"""
from __future__ import annotations
import wave
from dataclasses import dataclass, field
import numpy as np
from scipy.signal import lfilter

SR = 44100
SOURCES = ["OSC1", "OSC2", "OSC3", "NOISE", "ENV", "LFO", "RING", "S&H",
           "JOY_X", "JOY_Y", "MOD_W", "PITCH_W", "KEY_CV", "TRIGGER", "FILTER", "REVERB"]
DESTS = ["OSC1_FREQ", "OSC2_FREQ", "OSC3_FREQ", "NOISE_LVL", "FILTER_FREQ", "FILTER_RES",
         "VCA1", "VCA2", "REVERB_IN", "REVERB_MIX", "OUT_L", "OUT_R", "PAN"]

DEFAULT_PANEL = {
    "Osc1 Wave": "saw", "Osc1 Level": 1.0, "Osc2 Wave": "saw", "Osc2 Level": 0.0,
    "Osc3 Wave": "sine", "Osc3 Level": 0.0, "Osc2 Detune": 0.0,
    "Filter Mode": "lp", "Filter Cutoff": 2000.0, "Filter Resonance": 0.2, "Env Amount": 0.0,
    "Env Attack": 0.01, "Env Decay": 0.2, "Env Sustain": 0.7, "Env Release": 0.3,
    "Noise Level": 0.0, "LFO Rate": 5.0, "LFO Wave": "sine", "Mod Wheel": 0.0,
    "Reverb Amount": 0.0, "Osc Drift": 0.0, "Killer Mode": 0.0,
    "Balance": 0.5, "Master Volume": 0.7,
}


@dataclass
class Preset:
    name: str
    panel: dict = field(default_factory=dict)
    matrix: list = field(default_factory=list)  # [source, dest, level]

    def full_panel(self) -> dict:
        return {**DEFAULT_PANEL, **self.panel}

    def to_dict(self) -> dict:
        return {"name": self.name, "panel": self.panel, "matrix": self.matrix}

    @staticmethod
    def from_dict(d: dict) -> "Preset":
        return Preset(d["name"], dict(d.get("panel", {})), [list(m) for m in d.get("matrix", [])])


def _osc(kind: str, freq: np.ndarray, sr: int) -> np.ndarray:
    ph = np.cumsum(freq) / sr
    p = ph - np.floor(ph)
    if kind == "sine":
        return np.sin(2 * np.pi * p)
    if kind == "square":
        return np.where(p < 0.5, 1.0, -1.0)
    if kind == "tri":
        return 4 * np.abs(p - 0.5) - 1
    return 2 * p - 1  # saw


def _env(n_gate: int, n_total: int, a, d, s, r, sr) -> np.ndarray:
    a, d, r = max(a, 1e-3), max(d, 1e-3), max(r, 1e-3)
    na, nd, nr = int(a * sr), int(d * sr), int(r * sr)
    e = np.zeros(n_total)
    t = np.arange(n_gate)
    att = np.minimum(t / na, 1.0)
    dec = np.where(t >= na, np.maximum(1 - (1 - s) * np.minimum((t - na) / nd, 1.0), s), 1.0)
    g = att * np.where(t >= na, dec, 1.0)
    e[:n_gate] = g
    last = g[-1] if n_gate else 0.0
    nrel = min(nr, n_total - n_gate)
    if nrel > 0:
        e[n_gate:n_gate + nrel] = last * (1 - np.arange(nrel) / nr)
    return e


def _svf(x, cutoff, res, mode, sr):
    out = np.zeros_like(x)
    low = band = 0.0
    q = 2.0 - 1.95 * np.clip(res, 0, 0.98)
    f = 2 * np.sin(np.pi * np.clip(cutoff, 20, sr * 0.45) / sr)
    for i in range(len(x)):
        low += f[i] * band
        high = x[i] - low - q[i] * band
        band += f[i] * high
        out[i] = {"lp": low, "bp": band, "hp": high}.get(mode, high + low)
    return out


def _reverb(x, amount, sr):
    wet = np.zeros_like(x)
    for d in (1557, 1617, 1491, 1422):
        b = np.zeros(d + 1); b[d] = 1
        a = np.zeros(d + 1); a[0] = 1; a[d] = -0.84
        wet += lfilter(b, a, x) * 0.25
    for d, g in ((225, 0.5), (556, 0.5)):
        b = np.zeros(d + 1); b[0] = -g; b[d] = 1
        a = np.zeros(d + 1); a[0] = 1; a[d] = -g
        wet = lfilter(b, a, wet)
    return x * (1 - amount) + wet * amount * 1.5


class KillerSynth:
    def __init__(self, sr: int = SR, seed: int | None = 0):
        self.sr = sr
        self.rng = np.random.default_rng(seed)

    def _pins(self, preset: Preset) -> np.ndarray:
        pins = np.zeros((len(SOURCES), len(DESTS)))
        for s, d, lvl in preset.matrix:
            if s in SOURCES and d in DESTS:
                pins[SOURCES.index(s), DESTS.index(d)] = float(lvl)
        return pins

    def render_note(self, preset: Preset, midi: int, dur: float = 1.0, vel: float = 0.8) -> np.ndarray:
        sr, P = self.sr, preset.full_panel()
        n_gate = int(dur * sr)
        n = n_gate + int(max(P["Env Release"], 0.01) * sr)
        t = np.arange(n) / sr
        base = 440.0 * 2 ** ((midi - 69) / 12)
        if P["Killer Mode"] > 0.5:  # per-note tracking error
            base *= 2 ** (self.rng.normal(0, 0.004) / 12)
        drift = P["Osc Drift"] * np.sin(2 * np.pi * 0.3 * t + self.rng.uniform(0, 6.28))
        freq = base * (1 + drift)

        lfo = _osc(P["LFO Wave"] if P["LFO Wave"] in ("sine", "square", "tri", "saw") else "sine",
                   np.full(n, P["LFO Rate"]), sr)
        if P["LFO Wave"] in ("S&H", "sh"):
            step = max(int(sr / max(P["LFO Rate"], 0.1)), 1)
            lfo = np.repeat(self.rng.uniform(-1, 1, n // step + 1), step)[:n]
        env = _env(n_gate, n, P["Env Attack"], P["Env Decay"], P["Env Sustain"], P["Env Release"], sr)
        vib = 1 + 0.01 * P["Mod Wheel"] * lfo

        o1 = _osc(P["Osc1 Wave"], freq * vib, sr) * P["Osc1 Level"]
        o2 = _osc(P["Osc2 Wave"], freq * vib * 2 ** (P["Osc2 Detune"] / 12), sr) * P["Osc2 Level"]
        o3 = _osc(P["Osc3 Wave"], freq * vib, sr) * P["Osc3 Level"]
        noise = self.rng.uniform(-1, 1, n) * P["Noise Level"]
        ring = o1 * o2
        src = {"OSC1": o1, "OSC2": o2, "OSC3": o3, "NOISE": noise, "ENV": env, "LFO": lfo, "RING": ring,
               "MOD_W": np.full(n, P["Mod Wheel"]), "KEY_CV": np.full(n, (midi - 60) / 60.0),
               "TRIGGER": (np.arange(n) < n_gate).astype(float)}
        pins = self._pins(preset)
        dst = {d: np.zeros(n) for d in DESTS}
        for i, s in enumerate(SOURCES):
            if s in src:
                for j, d in enumerate(DESTS):
                    if pins[i, j]:
                        dst[d] += src[s] * pins[i, j]

        mix = (o1 + o2 + o3 + noise) + 0.5 * dst["VCA1"] + 0.5 * dst["VCA2"]
        cutoff = (P["Filter Cutoff"] * (1 + P["Env Amount"] * env) * (1 + 0.5 * P["Mod Wheel"] * lfo)
                  * (1 + 0.8 * np.tanh(dst["FILTER_FREQ"])))
        res = np.clip(P["Filter Resonance"] + dst["FILTER_RES"], 0, 0.98)
        y = _svf(mix, cutoff, res, P["Filter Mode"], sr)
        y = y * env * (1 + 0.8 * dst["VCA1"]) * (1 + 0.8 * dst["VCA2"])
        y = np.tanh(y * 0.9)

        amt = float(np.clip(P["Reverb Amount"] + dst["REVERB_MIX"].mean(), 0, 1))
        if amt > 0:
            y = _reverb(y, amt, sr)
        if P["Killer Mode"] > 0.5:  # crosstalk, wobble, jitter
            y = y + 0.1 * np.roll(y, 100)
            y = y * (1 + 0.05 * np.sin(2 * np.pi * 0.5 * t)) * (1 + 0.02 * self.rng.standard_normal(n))
        bal = np.clip(P["Balance"], 0, 1)
        L = (y * (1 - bal) + dst["OUT_L"]) * P["Master Volume"] * vel
        R = (y * bal + dst["OUT_R"]) * P["Master Volume"] * vel
        # Balance 0.5 => equal power-ish centre
        if "PAN" not in [m[1] for m in preset.matrix] and abs(bal - 0.5) < 1e-9:
            L = R = y * 0.7071 * P["Master Volume"] * vel
        return np.stack([L, R], axis=1).astype(np.float32)

    def render_sequence(self, preset: Preset, notes: list[tuple[int, float, float]]) -> np.ndarray:
        """notes = [(midi, start_sec, dur_sec)] -> stereo float32 array."""
        if not notes:
            return np.zeros((1, 2), np.float32)
        tail = int(preset.full_panel()["Env Release"] * self.sr) + int(self.sr * 2)
        total = int(max(s + d for _, s, d in notes) * self.sr) + tail
        out = np.zeros((total, 2), np.float32)
        for midi, start, dur in notes:
            chunk = self.render_note(preset, midi, dur)
            i = int(start * self.sr)
            out[i:i + len(chunk)] += chunk[: total - i]
        peak = np.abs(out).max()
        return out / peak * 0.89 if peak > 0.89 else out


def save_wav(path: str, audio: np.ndarray, sr: int = SR) -> str:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path
