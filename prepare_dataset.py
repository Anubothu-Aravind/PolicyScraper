"""
Dataset preparation script:
- Reads per-PDF section JSON files from data/parsed
- Applies heuristic labeling rules:
    is_exclusion -> "Exclusion"
    deductible -> "Deductible"
    waiting_period -> "WaitingPeriod"
    else -> "Other"
- Filters out very short samples (<30 chars)
- Writes a CSV suitable for text classification: columns [text, label]

Assumptions:
- Each JSON file is a list of dicts with keys created by run_pipeline.py.
"""

import json, csv, os  # Standard libraries for serialization, CSV writing, and filesystem

IN_DIR = "data/parsed"  # Directory containing section JSON files
OUT_FILE = "data/training_dataset.csv"  # Target CSV dataset path

rows = []  # Accumulator for (text, label) pairs

# Iterate through parsed JSON outputs
for fname in os.listdir(IN_DIR):
    if not fname.endswith(".json"):  # Skip non-JSON artifacts
        continue
    data = json.load(open(os.path.join(IN_DIR, fname), encoding="utf-8"))  # Load list of section dicts

    for sec in data:
        text = sec.get("sample_text", "").strip()  # Retrieve truncated text; ensure whitespace trimmed
        if not text or len(text) < 30:  # Filter out empty / too-short snippets to reduce noise
            continue

        # Heuristic labeling precedence order: exclusion > deductible > waiting_period > other
        if sec.get("is_exclusion"):
            label = "Exclusion"
        elif sec.get("deductible"):
            label = "Deductible"
        elif sec.get("waiting_period"):
            label = "WaitingPeriod"
        else:
            label = "Other"

        rows.append([text, label])  # Append row for CSV writing

# Write final dataset with header row
with open(OUT_FILE, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["text", "label"])  # Column headers
    writer.writerows(rows)  # Bulk write all samples

print(f"✅ Created dataset: {OUT_FILE}, samples: {len(rows)}")  # Summary output