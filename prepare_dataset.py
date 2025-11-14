import json, csv, os

IN_DIR = "data/parsed"
OUT_FILE = "data/training_dataset.csv"

rows = []
for fname in os.listdir(IN_DIR):
    if not fname.endswith(".json"):
        continue
    data = json.load(open(os.path.join(IN_DIR, fname), encoding="utf-8"))
    for sec in data:
        text = sec.get("sample_text", "").strip()
        if not text or len(text) < 30:
            continue
        if sec.get("is_exclusion"):
            label = "Exclusion"
        elif sec.get("deductible"):
            label = "Deductible"
        elif sec.get("waiting_period"):
            label = "WaitingPeriod"
        else:
            label = "Other"
        rows.append([text, label])

with open(OUT_FILE, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["text", "label"])
    writer.writerows(rows)

print(f"✅ Created dataset: {OUT_FILE}, samples: {len(rows)}")
