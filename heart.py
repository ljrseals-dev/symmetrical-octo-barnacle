"""heart.py - the inner heart.

One place that holds the meaning of a sound:
    intent text / preset  ->  Profile (character, envelope, wave, era)
                          ->  Suno/Udio prompt (title, style, description, lyric seed)
                          ->  audio (via killer_synth)
Deterministic and rule-based on purpose: every decision can be traced by hand.
"""
from __future__ import annotations
import json, os, random
from dataclasses import dataclass, asdict
from killer_synth import Preset, KillerSynth, save_wav
from killer_presets import PRESETS

# ---------------------------------------------------------------- classification
@dataclass
class Profile:
    character: str; envelope: str; wave: str; era: str
    cutoff: float; resonance: float; attack: float; release: float
    reverb: float; lfo_rate: float; killer_mode: bool


def classify(preset: Preset) -> Profile:
    p = preset.full_panel()
    o1, o2 = p["Osc1 Wave"], p["Osc2 Wave"]
    cut, res, a, d, s, r = (p["Filter Cutoff"], p["Filter Resonance"], p["Env Attack"],
                            p["Env Decay"], p["Env Sustain"], p["Env Release"])
    noise, lfo, lw, mw = p["Noise Level"], p["LFO Rate"], p["LFO Wave"], p["Mod Wheel"]
    if cut < 500 and p["Osc2 Level"] > 0.2 and p["Osc1 Level"] > 0.8: ch = "bass"
    elif cut < 800 and res > 0.85: ch = "acid"
    elif noise > 0.5 and a < 0.01 and r < 0.2: ch = "perc"
    elif lfo > 15 and lw in ("S&H", "sh"): ch = "glitch"
    elif a > 1.0 and s > 0.9: ch = "drone"      # moved ahead of ambient/pad: the paper's order made it unreachable
    elif a > 0.5 and r > 1.0: ch = "ambient" if cut < 1200 else "pad"
    elif o1 == o2 == "sine" and r > 0.8: ch = "bell"
    elif o1 == "sine" and lfo > 4 and mw > 0.2: ch = "theremin"
    elif o1 == "saw" and o2 == "square" and res > 0.8: ch = "formant"
    elif o1 == o2 == "saw" and a > 0.3: ch = "strings"
    elif o1 == o2 == "saw" and 0.05 < a <= 0.3: ch = "brass"
    elif a < 0.01 and s < 0.1: ch = "pluck"
    elif cut < 300 and o1 == "sine": ch = "sub"
    elif o1 == "square" and a < 0.01 and s == 0: ch = "arp"
    else: ch = "lead"
    if a > 0.8: env = "padded"
    elif a < 0.01 and d < 0.15 and s < 0.1: env = "percussive"
    elif a < 0.02 and s < 0.3: env = "plucky"
    elif s > 0.9 and r > 1.0: env = "droning"
    elif a < 0.05 and s > 0.6: env = "stabbing"
    else: env = "sustained"
    wave = "noise" if noise > 0.4 else o1
    km = p["Killer Mode"] > 0.5
    era = "lo-fi analog" if (km or p["Osc Drift"] > 0.01) else ("acid analog" if res > 0.85 else "analog")
    return Profile(ch, env, wave, era, cut, res, a, r, p["Reverb Amount"], lfo, km)

# ---------------------------------------------------------------- vocabulary banks
GENRES = {
    "bass": ["synthwave", "darkwave", "EBM", "deep house", "trap", "drill"],
    "acid": ["acid house", "acid techno", "electro", "trance"],
    "perc": ["industrial", "IDM", "breakbeat", "minimal techno"],
    "glitch": ["glitch", "IDM", "experimental electronic", "clicks and cuts"],
    "ambient": ["ambient", "dark ambient", "drone ambient", "cinematic"],
    "pad": ["synthwave", "dream pop", "ambient", "new age", "cinematic"],
    "drone": ["drone", "dark ambient", "space music", "kosmische"],
    "bell": ["ambient", "minimal", "new age", "cinematic"],
    "theremin": ["sci-fi soundtrack", "psychedelic", "retro-futurism"],
    "formant": ["vocoder electro", "synth-funk", "robotic pop"],
    "strings": ["cinematic", "italo disco", "synth-pop", "orchestral synth"],
    "brass": ["synth-funk", "80s pop", "fanfare synth", "boogie"],
    "pluck": ["future bass", "synth-pop", "chillwave", "house"],
    "sub": ["dub", "dubstep", "deep house", "808 trap"],
    "arp": ["trance", "synthwave", "krautrock", "electro"],
    "lead": ["synthwave", "prog electronic", "synth-pop", "outrun"],
}
MOODS = {"padded": ["hazy", "expansive", "floating"], "percussive": ["punchy", "tight", "aggressive"],
         "plucky": ["crisp", "snappy", "staccato"], "droning": ["hypnotic", "brooding", "vast"],
         "stabbing": ["urgent", "bold", "driving"], "sustained": ["warm", "singing", "glowing"]}
TEXTURES = {"saw": ["buzzing", "rich", "fat", "harmonic"], "square": ["hollow", "reedy", "nasal", "chiptune-like"],
            "sine": ["pure", "round", "glassy", "soft"], "tri": ["mellow", "woody"],
            "noise": ["breathy", "gritty", "hissing", "airy"]}
TEMPO = {"bass": (95, 140), "acid": (125, 140), "perc": (110, 150), "glitch": (90, 160), "ambient": (50, 80),
         "pad": (70, 110), "drone": (40, 70), "bell": (60, 90), "theremin": (70, 100), "formant": (100, 125),
         "strings": (80, 120), "brass": (100, 125), "pluck": (100, 130), "sub": (65, 140), "arp": (120, 145),
         "lead": (100, 135)}
ERA = {"lo-fi analog": ["1970s", "worn tape", "vintage hardware"], "acid analog": ["1980s", "TB-style", "squelchy"],
       "analog": ["1980s", "warm analog", "classic synth"]}
PRODUCTION = ["tape-saturated", "glued", "wide stereo", "dry and close", "sidechained", "analog warmth", "lo-fi grit"]
DRUMS = ["with TR-808 drums", "with live-feel drums", "with sparse percussion", "no drums", "with LinnDrum"]
ADJ = ["Molten", "Velvet", "Copper", "Hollow", "Neon", "Quiet", "Burning"]
NOUN = ["Circuit", "Cathedral", "Signal", "Garden", "Engine", "Lantern", "Key"]

# ---------------------------------------------------------------- intent -> preset
# (keyword -> panel patch). First hits merge in order; later keywords override.
INTENT = [
    ("bass", {"Osc1 Level": 1.0, "Osc2 Level": 0.5, "Filter Cutoff": 400, "Filter Resonance": 0.6, "Env Sustain": 0.3}),
    ("acid", {"Filter Cutoff": 600, "Filter Resonance": 0.9, "Env Amount": 3.0}),
    ("pad", {"Osc2 Level": 0.8, "Osc2 Detune": 0.12, "Env Attack": 1.0, "Env Release": 2.0, "Filter Cutoff": 2400, "Reverb Amount": 0.4}),
    ("warm", {"Filter Cutoff": 1400, "Osc Drift": 0.015}),
    ("bright", {"Filter Cutoff": 6000}),
    ("dark", {"Filter Cutoff": 500}),
    ("drone", {"Env Attack": 1.5, "Env Sustain": 1.0, "Env Release": 2.5, "Reverb Amount": 0.4}),
    ("pluck", {"Env Attack": 0.003, "Env Decay": 0.25, "Env Sustain": 0.0, "Env Release": 0.2}),
    ("bell", {"Osc1 Wave": "sine", "Osc2 Wave": "sine", "Osc2 Level": 0.5, "Osc2 Detune": 7.02, "Env Release": 1.5}),
    ("lead", {"Osc1 Wave": "square", "Env Attack": 0.02, "Mod Wheel": 0.4}),
    ("perc", {"Osc1 Level": 0.0, "Noise Level": 0.9, "Env Attack": 0.002, "Env Sustain": 0.0, "Env Release": 0.1}),
    ("glitch", {"LFO Wave": "S&H", "LFO Rate": 18.0, "Osc1 Wave": "square"}),
    ("vintage", {"Killer Mode": 1.0, "Osc Drift": 0.015}),
    ("grit", {"Killer Mode": 1.0}),
    ("space", {"Reverb Amount": 0.6}),
]


def intent_to_preset(text: str, name: str | None = None) -> Preset:
    t = text.lower()
    panel: dict = {}
    for kw, patch in INTENT:
        if kw in t:
            panel.update(patch)
    return Preset(name or text.strip().title()[:32] or "Untitled", panel,
                  [["ENV", "FILTER_FREQ", 0.5]] if "acid" in t or "bass" in t else [])

# ---------------------------------------------------------------- prompt assembly
def make_prompt(preset: Preset, seed: int = 0, lyrics: bool = False) -> dict:
    prof = classify(preset)
    rng = random.Random(f"{preset.name}:{seed}")
    pick = lambda pool, k=1: rng.sample(pool, min(k, len(pool)))
    lo, hi = TEMPO[prof.character]
    tags = (pick(GENRES[prof.character], 2) + pick(ERA[prof.era]) + pick(MOODS[prof.envelope], 2)
            + pick(TEXTURES.get(prof.wave, ["analog"]), 2) + pick(DRUMS) + [f"{rng.randint(lo, hi)} BPM"]
            + pick(PRODUCTION, 2))
    if prof.reverb > 0.3: tags.append("cavernous reverb")
    if prof.killer_mode: tags.append("raw analog imperfection")
    out = {"title": f"{rng.choice(ADJ)} {rng.choice(NOUN)} #{rng.randint(1, 99)}",
           "style": ", ".join(tags),
           "description": (f"{prof.era} {prof.character}, {prof.envelope} envelope, {prof.wave} wave, "
                           f"cutoff {prof.cutoff:.0f} Hz, resonance {prof.resonance * 100:.0f}%"),
           "source_preset": preset.name, "profile": asdict(prof)}
    if lyrics:
        out["lyrics"] = "[Verse]\nSignals bloom in copper light\nEvery wire remembers night\n[Chorus]\nHold the key, hold the key"
    return out

# ---------------------------------------------------------------- the orchestrator
class Heart:
    """Intent in -> {preset, profile, prompt, wav} out. Plug any AIGenerator into `generators`."""
    def __init__(self, out_dir: str = "out", seed: int = 0):
        self.out_dir, self.seed = out_dir, seed
        self.synth = KillerSynth(seed=seed)
        self.presets = dict(PRESETS)
        self.generators: list = []
        os.makedirs(out_dir, exist_ok=True)

    def add_preset(self, preset: Preset) -> Preset:
        self.presets[preset.name] = preset
        return preset

    def resolve(self, what) -> Preset:
        if isinstance(what, Preset): return what
        if what in self.presets: return self.presets[what]
        return self.add_preset(intent_to_preset(str(what)))

    def create(self, what, notes=None, variants: int = 3, lyrics: bool = False, render: bool = True) -> dict:
        preset = self.resolve(what)
        notes = notes or [(48, 0.0, 1.0), (55, 1.0, 1.0), (60, 2.0, 1.5)]
        prompts = [make_prompt(preset, self.seed + i, lyrics) for i in range(variants)]
        slug = "".join(c if c.isalnum() else "_" for c in preset.name)
        wav = save_wav(os.path.join(self.out_dir, slug + ".wav"), self.synth.render_sequence(preset, notes)) if render else None
        with open(os.path.join(self.out_dir, slug + ".prompts.json"), "w") as f:
            json.dump({"preset": preset.to_dict(), "prompts": prompts}, f, indent=2)
        results = [g.submit(p, reference_wav=wav) for g in self.generators for p in prompts[:1]]
        return {"preset": preset, "prompts": prompts, "wav": wav, "generator_results": results}
