# Sardine + Killer Synth + Inner Heart

1. killer_synth.py + killer_presets.py  - the Killer synthesizer (panel, 16x16 pin matrix, SVF, reverb, Killer Mode)
2. heart.py                              - the inner heart (classifier, vocabulary banks, intent->preset, prompt maker, orchestrator)
3. sardine_bridge.py                     - the Sardine wiring + AI-generator adapters

## Use
    from sardine_bridge import SardineKiller
    k = SardineKiller("out"); k.register(globals())     # inside a Sardine session
    auto_instrument("warm dark vintage pad with space")
    play_killer("Killer Bass", [36, 43, 48])             # renders WAV
    killer_prompt("Drift Pad")                           # Suno/Udio title + style
    wire_generator(HttpGenerator(url, headers))          # attach a real AI service

Requires numpy and scipy. Run `python demo.py`.

## Honest limits
- Oscillators are naive (no band-limiting), so high notes alias. Not the ymfm/ROM engine from the Sardine master prompt.
- The Sardine registration is namespace-based; I could not check Sardine's real API.
- HttpGenerator is a template; no Suno/Udio API is called by default (FilePromptGenerator writes prompt files).
- DRONE rule moved ahead of AMBIENT/PAD in heart.py; in the paper's order it was unreachable.
