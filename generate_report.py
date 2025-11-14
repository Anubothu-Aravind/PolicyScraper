import json, os
IN_DIR, OUT_DIR = "data/parsed", "data/reports"
os.makedirs(OUT_DIR, exist_ok=True)

for f in os.listdir(IN_DIR):
    data = json.load(open(os.path.join(IN_DIR,f),encoding="utf-8"))
    risky = [d for d in data if d["deductible"] or d["waiting_period"] or d["is_exclusion"]]
    json.dump(risky, open(os.path.join(OUT_DIR,f.replace(".json",".report.json")),"w"), indent=2)
    print("⚠️", f, "->", len(risky), "flags")
