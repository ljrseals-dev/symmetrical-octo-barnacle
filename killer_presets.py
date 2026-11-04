"""killer_presets.py - the six archetype presets from the paper."""
from killer_synth import Preset

PRESETS = {p.name: p for p in [
    Preset("Killer Bass", {"Osc1 Wave": "saw", "Osc1 Level": 1.0, "Osc2 Wave": "saw", "Osc2 Level": 0.5,
          "Filter Cutoff": 400, "Filter Resonance": 0.9, "Env Attack": 0.01, "Env Sustain": 0.2,
          "Killer Mode": 1.0, "Osc Drift": 0.01}, [["ENV", "FILTER_FREQ", 0.6]]),
    Preset("Drift Pad", {"Osc1 Wave": "saw", "Osc2 Wave": "saw", "Osc2 Level": 0.8, "Osc2 Detune": 0.12,
          "Filter Cutoff": 2400, "Env Attack": 1.2, "Env Release": 2.0, "Env Sustain": 0.8,
          "Reverb Amount": 0.5, "Osc Drift": 0.02}, [["LFO", "FILTER_FREQ", 0.2]]),
    Preset("Novelty Lead", {"Osc1 Wave": "sine", "LFO Rate": 6.0, "Mod Wheel": 0.6, "Filter Cutoff": 5000,
          "Env Attack": 0.05, "Env Release": 0.4}, []),
    Preset("Noise Perc", {"Osc1 Level": 0.0, "Noise Level": 0.9, "Filter Cutoff": 3000, "Filter Mode": "bp",
          "Filter Resonance": 0.5, "Env Attack": 0.002, "Env Decay": 0.1, "Env Sustain": 0.0,
          "Env Release": 0.1}, []),
    Preset("Resonant Drone", {"Osc1 Wave": "square", "Osc2 Wave": "saw", "Osc2 Level": 0.6, "Filter Cutoff": 700,
          "Filter Resonance": 0.7, "Env Attack": 1.5, "Env Sustain": 1.0, "Env Release": 2.5,
          "Reverb Amount": 0.4}, [["LFO", "FILTER_FREQ", 0.4]]),
    Preset("Glitch", {"Osc1 Wave": "square", "LFO Wave": "S&H", "LFO Rate": 18.0, "Filter Cutoff": 1500,
          "Filter Resonance": 0.6, "Env Attack": 0.005, "Env Release": 0.15, "Killer Mode": 1.0},
           [["LFO", "FILTER_FREQ", 0.9]]),
]}
