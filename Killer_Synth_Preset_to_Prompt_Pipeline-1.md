# Killer Synth Emulation and the Preset-to-Prompt Pipeline

*A technical paper on a software emulation of a patchable vintage synthesizer and the pipeline that turns its presets into prompts for AI music generators*

October 2026

## Abstract

This paper documents a two-branch software system built around a software emulation of a vintage, patchable analog synthesizer called "Killer" (referred to in the source material as the Ionic Performer, with a design in the style of EMS Synthi-type instruments). A single preset file acts as a shared data contract. One branch renders it to audio with a sample-by-sample DSP engine. The other branch classifies it into a semantic sonic profile and converts that profile into Suno-style text prompts (title, style tags, description, optional lyric seed) for prompt-driven AI music services such as Suno or Udio.

The central design decision is that the preset is the fork point: everything upstream describes how a sound is produced, everything downstream describes what that sound means to a listener. A deterministic rule-based classifier carries the meaning across. This paper describes each layer, the signal flow, the routing math, the classifier, the vocabulary banks, the export formats, and the known limitations of the design, including several defects found when the published rules are traced by hand.

## 1. Scope and provenance

This paper is derived from a saved design conversation about the system. It is important to be precise about what that source contains.

- **Included in the source:** the full Python code for the prompt-generation branch (`descriptor_banks.py`, `killer_bridge.py`, `suno_generator.py`, README) and detailed architecture diagrams of the whole system.
- **Described but not included:** the synth branch (`killer_panel.py`, `killer_matrix.py`, `killer_engine.py`, `killer_presets.py`, `render_presets.py`, `killer_gui.py`). Its behavior is documented here from the architecture diagrams only, so those sections describe intended design rather than verified code.
- **Not executed:** the source states that the code was produced by design reasoning and domain knowledge, not by running it. Nothing in this paper has been tested, and the demo-bank classifications in Section 6 come from tracing the rules by hand.
- **No AI audio is produced by this codebase.** The "AI synthesized sound" step happens inside an external service (Suno, Udio, or similar). This system produces the text that steers that service, plus its own locally rendered DSP audio.

## 2. System overview

The system has three layers and two output branches.

| Layer | Modules | Responsibility |
|---|---|---|
| Interfaces | `killer_main.py` (Tkinter GUI), `render_presets.py` (CLI), `suno_generator.py` (CLI) | Entry points for performing, batch rendering, and prompt generation |
| Core model | `killer_panel.py`, `killer_matrix.py`, `killer_engine.py` | State of every control, the patch matrix, and the audio engine |
| Output branches | Audio: `killer_presets.py`, `render_presets.py`. Semantic: `killer_bridge.py`, `descriptor_banks.py`, `suno_generator.py` | Two independent consumers of the same preset data |

```
USER INTERFACES  (GUI / render CLI / prompt CLI)
        |
CORE MODEL:  Panel  <-->  Switch Matrix
                \          /
                  Engine (reads both every block, emits stereo PCM)
        |
   PRESET  (panel state + matrix pins)   <-- the fork point
     /                                \
AUDIO BRANCH                      SEMANTIC BRANCH
render_sequence -> save_wav       build_profile -> vocabulary banks
   -> *.wav                          -> prompt generator
                                     -> suno_prompts.{json,txt,csv}
```

The two branches are deliberately independent. `render_presets.py` and `suno_generator.py` are leaves that never import each other. They share only the preset data format, which keeps each testable in isolation.

## 3. The synthesizer emulation

### 3.1 Panel model

`IonicPerformerPanel` holds the value of every knob, switch, button, and wheel as a named parameter. The preset format stores these as a flat dictionary of panel keys, for example `Osc1 Wave`, `Osc1 Level`, `Filter Cutoff`, `Filter Resonance`, `Env Attack`, `Env Decay`, `Env Sustain`, `Env Release`, `Noise Level`, `LFO Rate`, `LFO Wave`, `Reverb Amount`, `Osc Drift`, and `Killer Mode`. Keeping all state in one place is what makes presets trivial to serialize and lets the classifier read them without touching the engine.

### 3.2 Switch matrix

The patching system is a 16 x 16 pin matrix. Rows are signal sources, columns are destinations, and each cell holds a pin level in the range 0.0 to 1.0. The routing equation is a weighted sum:

```
dst[j][t] = sum over i of ( src[i][t] * pins[i][j] )
```

Each destination is the sum of every source pinned to it, scaled by the pin level, so a pin acts as an attenuator. The same set of sources can therefore produce very different instruments depending on which pins are present. This is the property that makes a Synthi-style instrument a programmable patch bay rather than a fixed-architecture synth.

**Sources (the diagram's bus):** OSC1, OSC2, OSC3, NOISE, ENV, LFO, RING (ring modulator), S&H (sample and hold), JOY_X, JOY_Y, MOD_WHEEL, PITCH_WHEEL, KEY_CV, TRIGGER, FILTER, REVERB.

**Destinations:** oscillator frequencies, noise level, FILTER_FREQ, FILTER_RES, VCA1, VCA2, REVERB_IN, REVERB_MIX, OUT_L, OUT_R, PAN, ENV_TRIG, ENV_GATE, LFO_RESET.

Presets store matrix pins as triples such as `["ENV", "FILTER_FREQ", 0.6]` (source, destination, level).

### 3.3 Engine signal flow

`Engine.render_note` processes one note through the following stages. The engine reads the panel and matrix at each audio block.

1. **Keyboard CV.** MIDI note to frequency, plus keyboard octave offset (up to 24 semitones), master tune (up to 100 cents), and a per-note tracking error that models imperfect keyboard scaling.
2. **Glide.** Off, auto, or on, with portamento time of 0 to 2 seconds, starting from the previous note's frequency.
3. **Pitch modulation.** Pitch wheel scaled by bend range, joystick assignments, and vibrato derived from mod wheel times LFO.
4. **Drift.** An analog instability model: the drift amount times a slow sine (about 0.3 Hz) with a random phase, applied to oscillator pitch.
5. **Oscillators.** Three oscillators with selectable waveform (sine, saw, square, triangle), a fine-tune "vernier", level, and pulse-width modulation by LFO.
6. **Noise and ring modulation.** White, pink, or red noise source, and a ring modulator multiplying oscillator 1 by oscillator 2.
7. **Source bus.** All sources collected into one dictionary for the matrix.
8. **Matrix routing.** The weighted-sum equation above produces the destination bus.
9. **Pre-filter mix.** Oscillators and noise summed, plus the VCA1 and VCA2 contributions at 0.5 each.
10. **Cutoff modulation.** The effective cutoff is the panel base multiplied by joystick filter scaling, envelope amount, mod-wheel LFO depth, a matrix term, and keyboard tracking:

```
cutoff = base * joy_filter_mul
              * (1 + env_amount * env)
              * (1 + 0.5 * mod_wheel * LFO)
              * (1 + 0.8 * tanh(FILTER_FREQ))
              * kbd_track_mul
```

11. **State-variable filter.** Low-pass, band-pass, high-pass, and notch outputs, with resonance equal to the panel value plus the matrix FILTER_RES term. An SVF is a natural choice because one structure gives all four responses and tolerates audio-rate modulation.
12. **VCA.** `out = filtered * env * (1 + 0.8*VCA1) * (1 + 0.8*VCA2)`.
13. **Reverb.** A Schroeder-style reverb (parallel comb filters into series all-pass filters). Tone controls damping, decay controls comb feedback, and the output is `dry*(1-mix) + wet*mix`, where mix is the panel amount plus the matrix REVERB_MIX term. The input comes from the REVERB_IN pin, or the dry signal if nothing is pinned.
14. **Killer Mode.** An imperfection stage that is the signature of the instrument: crosstalk (`+0.1 * roll(out, 100)`, a delayed bleed of the signal into itself), slow amplitude wobble (`* (1 + 0.05*sin(0.5 Hz))`), and random jitter (`* (1 + 0.02*randn)`).
15. **Output stage.** Balance or pan (a PAN pin overrides balance), matrix OUT_L and OUT_R terms, then master volume. The result is stereo PCM.

The design choice worth noting is that imperfections (drift, tracking error, crosstalk, wobble, jitter) are modeled as first-class, explicit stages instead of being left as numerical accident. That is what makes the emulation read as vintage, and it also gives the semantic branch something to detect (see `Osc Drift` and `Killer Mode` in Section 5.2).

### 3.4 Audio branch

`killer_presets.py` applies a preset to the panel and matrix. `render_presets.py` then calls `render_sequence` to play a note sequence through the engine and `save_wav` to write the result, giving one WAV per preset for audition or for use as reference audio elsewhere.

## 4. The preset as a data contract

A preset is a name, a panel dictionary, and a list of matrix pins.

```
{
  "name": "Killer Bass",
  "panel": {
    "Osc1 Wave": "saw", "Osc1 Level": 1.0,
    "Filter Cutoff": 400, "Filter Resonance": 0.9,
    "Env Attack": 0.01, "Env Sustain": 0.2,
    "Killer Mode": 1.0, "Osc Drift": 0.01
  },
  "matrix": [["ENV", "FILTER_FREQ", 0.6]]
}
```

This single structure is the interface between the two branches. The audio branch uses all of it. The semantic branch reads only a subset: oscillator waves and levels, filter cutoff and resonance, the four envelope stages, noise level, LFO rate and wave, mod wheel, reverb amount, drift, and Killer Mode. Notably, the classifier ignores the matrix entirely, which is a limitation discussed in Section 8.

The loader in `suno_generator.py` tries to import `PRESETS` from `killer_presets.py` and flattens each entry's `panel` dictionary next to its `name`. If the import fails for any reason, it falls back to a built-in bank of six archetype presets (Killer Bass, Drift Pad, Novelty Lead, Noise Perc, Resonant Drone, Glitch) so the tool always runs standalone.

## 5. The semantic pipeline: preset to Suno prompt

### 5.1 Why text

Prompt-driven music generators such as Suno accept a style prompt (genre, mood, instrumentation, tempo, production descriptors), a title, and optionally lyrics. They do not accept patch data. The pipeline therefore has to translate physical synthesis parameters into the vocabulary a text-to-music model was trained to respond to.

### 5.2 Stage 1: classification (`killer_bridge.py`)

`build_profile(preset)` produces a profile with four categorical labels and a few passthrough numbers.

| Field | Classes |
|---|---|
| `character` | bass, acid, perc, glitch, ambient, pad, drone, bell, theremin, formant, strings, brass, pluck, sub, arp, lead |
| `envelope` | padded, percussive, plucky, droning, stabbing, sustained |
| `wave` | the dominant oscillator waveform, or noise if noise level exceeds 0.4 |
| `era` | lo-fi analog, acid analog, analog |

Passthrough fields: cutoff, resonance, attack, release, reverb, LFO rate, and a Boolean `killer_mode`.

**Character classification** is a priority chain in which the first matching rule wins:

| # | Class | Condition |
|---|---|---|
| 1 | bass | cutoff < 500 and Osc2 level > 0.2 and Osc1 level > 0.8 |
| 2 | acid | cutoff < 800 and resonance > 0.85 |
| 3 | perc | noise level > 0.5 and attack < 0.01 and release < 0.2 |
| 4 | glitch | LFO rate > 15 and LFO wave is S&H |
| 5 | ambient or pad | attack > 0.5 and release > 1.0; ambient if cutoff < 1200, else pad |
| 6 | drone | attack > 1.0 and sustain > 0.9 |
| 7 | bell | Osc1 and Osc2 both sine and release > 0.8 |
| 8 | theremin | Osc1 sine and LFO rate > 4 and mod wheel > 0.2 |
| 9 | formant | Osc1 saw and Osc2 square and resonance > 0.8 |
| 10 | strings | Osc1 and Osc2 both saw and attack > 0.3 |
| 11 | brass | Osc1 and Osc2 both saw and 0.05 < attack < 0.3 |
| 12 | pluck | attack < 0.01 and sustain < 0.1 |
| 13 | sub | cutoff < 300 and Osc1 sine |
| 14 | arp | Osc1 square and attack < 0.01 and sustain == 0 |
| 15 | lead | fallback |

**Envelope classification** is likewise ordered: padded if attack > 0.8; percussive if attack < 0.01, decay < 0.15, sustain < 0.1; plucky if attack < 0.02 and sustain < 0.3; droning if sustain > 0.9 and release > 1.0; stabbing if attack < 0.05 and sustain > 0.6; otherwise sustained.

**Era classification:** lo-fi analog if Killer Mode > 0.5 or drift > 0.01; acid analog if resonance > 0.85; otherwise analog.

The author chose a priority chain over a statistical classifier on purpose: the preset set is small and hand-authored, and the output needs to be deterministic and explainable. If a preset is misclassified, the offending rule is visible by inspection and can be reordered.

### 5.3 Stage 2: vocabulary banks (`descriptor_banks.py`)

All words live in data tables, separate from logic, so taste can be tuned without touching code.

| Table | Keyed by | Content |
|---|---|---|
| `GENRE_BY_CHARACTER` | character | 5 to 10 genres each (bass: synthwave, darkwave, EBM, deep house, trap, drill and others) |
| `MOOD_BY_ENV` | envelope | mood words (plucky: punchy, tight, crisp, snappy, staccato) |
| `TEXTURE_BY_WAVE` | wave | timbre words (saw: buzzing, rich, harmonic, fat, analog) |
| `TEMPO_BY_CHARACTER` | character | BPM range (bass: 95 to 140, drone: 40 to 70, hoover: 150 to 180) |
| `ERA_TAGS`, `PRODUCTION_TAGS`, `INSTRUMENT_FLAVOURS`, `STRUCTURE_HINTS` | none (global pools) | era, mix, drum, and form tags |
| `TITLE_*` pools and `TITLE_TEMPLATES` | none | title generation |
| `LYRIC_FRAGMENTS`, `LYRIC_CHORUSES` | none | optional lyric seeds |

### 5.4 Stage 3: prompt assembly (`suno_generator.py`)

For each preset and each requested variant, `make_prompt` draws from the banks using a seeded random number generator:

1. Two genres sampled from the character's genre list.
2. Two moods from the envelope's mood list.
3. Two textures from the wave's texture list.
4. One era tag, two production tags, one drum or instrument flavour.
5. A BPM drawn uniformly from the character's tempo range.
6. Conditional additions: if reverb > 0.3, append "cavernous reverb"; if Killer Mode is on, append "raw analog imperfection". These are the points where the DSP-side design (reverb amount, imperfection stage) visibly reaches the text.
7. A title from a randomly chosen template filled with adjective, noun, place, time, verb, abstract, and number pools.
8. A one-line description string built from the profile fields (era, character, envelope, wave, cutoff in Hz, resonance percentage, and a structure hint).
9. Optionally, a lyric seed of two verse lines and one chorus.

The style string is the comma-joined list in this order: genres, era, moods, textures, drum flavour, BPM, production tags. A sample output for the Killer Bass preset in the source is:

```
TITLE: Molten Circuit #4
STYLE: synthwave, darkwave, 1970s, punchy, aggressive, buzzing, fat,
       with TR-808 drums, 118 BPM, tape-saturated, glued,
       raw analog imperfection
SOURCE PRESET: Killer Bass
```

### 5.5 Stage 4: export

The CLI writes three formats. JSON (`suno_prompts.json`) preserves every field. Text (`suno_prompts.txt`) is a copy-paste layout with ruled separators. CSV (`suno_prompts.csv`) has the columns title, style, source_preset, character, envelope, era, and description. Flags are `--variants N` (default 3), `--out DIR`, `--with-lyrics`, `--format {all,json,txt,csv}`, and `--seed N` for reproducibility.

## 6. Worked example: tracing the demo bank

Tracing the published rules by hand against the six built-in demo presets gives the following results. These were derived by reading the code, not by running it.

| Preset | Character | Envelope | Era | Matches intent? |
|---|---|---|---|---|
| Killer Bass | bass | plucky | lo-fi analog | Yes |
| Drift Pad | ambient | sustained | analog | Partly |
| Novelty Lead | lead | sustained | lo-fi analog | Yes |
| Noise Perc | perc | percussive | analog | Yes |
| Resonant Drone | acid | padded | acid analog | No, intended as a drone |
| Glitch | glitch | percussive | lo-fi analog | Yes |

Drift Pad's drift value of 0.01 does not exceed the 0.01 threshold and the preset has no Killer Mode key, so its era resolves to plain analog.

## 7. Design rationale

- **Layered architecture.** Physical model, DSP, preset, semantics, output. Each layer can be tested alone, and a change in one rarely forces a change in another.
- **Shared data contract.** One preset format serves audio and text consumers, so a new consumer (for example a reverse mapper) needs no engine changes.
- **Deterministic, explainable classification.** For a small hand-authored library this beats a learned model on transparency and maintenance.
- **Data-driven vocabulary.** Taste is a data problem. Editing a Python dictionary is cheaper than editing control flow.
- **Seeded randomness.** The same seed yields the same prompt set, which matters when comparing how a generator responds to prompt changes.

## 8. Limitations and defects found

Reading the rules closely surfaces several issues. None are fatal, but they affect output quality.

1. **Unreachable classes.** The banks define `hoover` and `fx` characters, but the classifier never returns them, so their genre and tempo entries are dead data.
2. **Shadowed rules.** The drone rule (attack > 1.0, sustain > 0.9) sits after the ambient and pad rule (attack > 0.5, release > 1.0), so most drones are captured earlier. The envelope "droning" class is likewise unreachable when attack exceeds 0.8, because the padded rule fires first. The demo's Resonant Drone becomes "acid" because the acid rule (cutoff < 800, resonance > 0.85) precedes everything but bass and perc.
3. **Brittle boundary conditions.** Strict inequalities mean values exactly on a threshold fall through (an attack of exactly 0.01 is not percussive, an attack of exactly 0.8 is not padded).
4. **Documentation drift.** The architecture diagrams describe the bass rule as "cutoff < 500 and Osc2 level > 0.2" and list pad and ambient as separate steps, while the code also requires Osc1 level > 0.8 and merges them. The code is authoritative.
5. **Dominant-wave collision.** `classify_wave` builds a dictionary keyed by waveform name, so two oscillators sharing a waveform overwrite one another instead of summing their levels (Drift Pad's two saws count once).
6. **Matrix blindness.** Routing is ignored, though it carries much of a patch's character (for example filter modulation by an LFO or sample-and-hold). Two presets with the same panel but different pins classify identically.
7. **Static, non-musical mapping.** Words are drawn independently, so combinations can be incoherent (a drone with a 1970s tag and TR-808 drums, or a no-drums flavour alongside a driving mood). There is no musical constraint solver.
8. **No feedback from the generator.** Nothing measures how well Suno's output matches the source patch. The mapping is a hypothesis about what the service responds to, not a validated one.
9. **Unverified code.** Per the source, the code was written, not executed.

## 9. Extensions proposed in the source

- A Flask or single-page web UI that renders a preset, plays it, and shows its generated prompt beside it.
- A reverse bridge that takes a Suno prompt and returns the nearest Killer preset as a starting patch.
- A batch tool that clusters thousands of prompts into preset families.

The conversation ends with a request for a further emulation (the "Juncture", for novelty sounds and voicing). That work is not part of the supplied material and is not covered here.

## 10. Recommended next steps

1. Execute the prompt generator and the demo bank to confirm Section 6 empirically.
2. Fix the unreachable classes and rule ordering, and add unit tests that pin the expected class for each demo preset.
3. Extend the profile with matrix-derived features such as modulation depth and modulation targets.
4. Add coherence constraints to prompt assembly (era-compatible drums, tempo-compatible moods).
5. Close the loop: generate audio from each prompt, compare it against the locally rendered WAV using spectral or embedding metrics, and use the scores to tune the vocabulary banks.

## Appendix A: File map

| File | Role |
|---|---|
| `killer_main.py`, `killer_gui.py` | Tkinter application entry and interface |
| `killer_panel.py` | `IonicPerformerPanel` control state |
| `killer_matrix.py` | 16 x 16 `SwitchMatrix` |
| `killer_engine.py` | Audio engine (`render_note`) |
| `killer_presets.py` | Preset bank (panel plus matrix) |
| `render_presets.py` | Audio branch CLI, writes WAV files |
| `killer_bridge.py` | Preset to sonic profile classifier |
| `descriptor_banks.py` | Vocabulary tables |
| `suno_generator.py` | Prompt assembly and export CLI |
