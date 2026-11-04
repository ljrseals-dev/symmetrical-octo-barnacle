"""sardine_bridge.py - the Sardine wiring.

Exposes the Heart to a Sardine live-coding session (or any Python REPL) as plain functions:
    auto_instrument("warm dark pad")   -> builds a Killer preset from words
    play("Killer Bass", [36, 43, 48])  -> renders audio, returns path (and optionally sends MIDI)
    prompt("Drift Pad")                -> Suno/Udio prompt dict
    wire_generator(gen)                -> attach an AI generator (anything with .submit(prompt, reference_wav=))
Sardine's exact API was not available to me, so registration is namespace-based: pass the
dict you want the functions in (e.g. globals() inside a Sardine session).
"""
from __future__ import annotations
import json, os
from heart import Heart, make_prompt


class FilePromptGenerator:
    """Default AI-generator adapter: writes a copy-paste Suno/Udio prompt file. Calls no external API."""
    def __init__(self, out_dir: str = "out/ai_queue"):
        self.out_dir = out_dir; os.makedirs(out_dir, exist_ok=True)

    def submit(self, prompt: dict, reference_wav: str | None = None) -> str:
        path = os.path.join(self.out_dir, prompt["title"].replace(" ", "_").replace("#", "") + ".txt")
        with open(path, "w") as f:
            f.write(f"TITLE: {prompt['title']}\nSTYLE: {prompt['style']}\n"
                    f"SOURCE PRESET: {prompt['source_preset']}\nREFERENCE AUDIO: {reference_wav}\n")
            if prompt.get("lyrics"): f.write("\nLYRICS:\n" + prompt["lyrics"] + "\n")
        return path


class HttpGenerator:
    """Template for a real service. Fill in url/headers for whichever provider you have access to."""
    def __init__(self, url: str, headers: dict | None = None):
        self.url, self.headers = url, headers or {}

    def submit(self, prompt: dict, reference_wav: str | None = None):
        import urllib.request
        req = urllib.request.Request(self.url, json.dumps(prompt).encode(),
                                     {"Content-Type": "application/json", **self.headers})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())


class SardineKiller:
    def __init__(self, out_dir: str = "out", midi_port: str | None = None):
        self.heart = Heart(out_dir)
        self.heart.generators.append(FilePromptGenerator(os.path.join(out_dir, "ai_queue")))
        self.midi = None
        if midi_port:
            try:
                import mido
                self.midi = mido.open_output(midi_port)
            except Exception as e:  # MIDI is optional
                print("MIDI disabled:", e)

    def auto_instrument(self, text: str):
        return self.heart.add_preset(self.heart.resolve(text))

    def play(self, what, midi_notes=(48, 55, 60), step: float = 0.5, dur: float = 0.5, send_midi: bool = False):
        notes = [(n, i * step, dur) for i, n in enumerate(midi_notes)]
        res = self.heart.create(what, notes=notes, variants=1)
        if send_midi and self.midi:
            import mido, time
            for n in midi_notes:
                self.midi.send(mido.Message("note_on", note=n, velocity=96)); time.sleep(dur)
                self.midi.send(mido.Message("note_off", note=n))
        return res["wav"]

    def prompt(self, what, seed: int = 0, lyrics: bool = False):
        return make_prompt(self.heart.resolve(what), seed, lyrics)

    def wire_generator(self, gen):
        self.heart.generators.append(gen); return gen

    def register(self, namespace: dict) -> None:
        """Inject live-coding helpers into a Sardine session: register(globals())."""
        namespace.update(auto_instrument=self.auto_instrument, play_killer=self.play,
                         killer_prompt=self.prompt, wire_generator=self.wire_generator, killer=self)
