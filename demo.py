from sardine_bridge import SardineKiller
k = SardineKiller("out")
for name in ["Killer Bass", "Drift Pad", "Resonant Drone", "Glitch"]:
    r = k.heart.create(name, variants=2)
    print(name, "->", r["prompts"][0]["profile"]["character"], "|", r["prompts"][0]["style"], "|", r["wav"])
k.auto_instrument("warm dark vintage pad with space")
print(k.prompt("Warm Dark Vintage Pad With Space")["style"])
