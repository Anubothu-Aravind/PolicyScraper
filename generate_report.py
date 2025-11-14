"""
Report generation script:
- Scans parsed JSON files in data/parsed
- Filters sections that contain any "flag" features:
    deductible OR waiting_period OR is_exclusion
- Writes a simplified JSON report per source file into data/reports
  with only flagged sections retained
- Prints summary line with count of flagged sections per file

Potential extensions:
- Aggregate statistics across all reports
- Produce CSV or Markdown summaries
- Add severity scoring

Assumptions:
- Input JSON file structure matches output of run_pipeline.py.
"""

import json, os  # Standard libraries for filesystem operations and JSON handling

IN_DIR, OUT_DIR = "data/parsed", "data/reports"  # Source of parsed sections & destination for reports
os.makedirs(OUT_DIR, exist_ok=True)  # Ensure reports directory exists

# Iterate over every file in the parsed directory
for f in os.listdir(IN_DIR):
    data = json.load(open(os.path.join(IN_DIR, f), encoding="utf-8"))  # Load list of section dicts

    # Filter sections that have at least one of the "risk" features
    risky = [d for d in data if d["deductible"] or d["waiting_period"] or d["is_exclusion"]]

    # Write filtered list to a .report.json file (mirrors original name)
    json.dump(risky, open(os.path.join(OUT_DIR, f.replace(".json", ".report.json")), "w"), indent=2)

    print("⚠️", f, "->", len(risky), "flags")  # Console summary with count of flagged sections