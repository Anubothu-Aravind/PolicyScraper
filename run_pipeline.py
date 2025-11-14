import os, json
from parser.pdf_parser import extract_text_from_pdf, split_into_sections
from extractor.regex_extract import find_deductible, find_waiting, contains_exclusions_section

IN_DIR, OUT_DIR = "data/raw_pdfs", "data/parsed"
os.makedirs(OUT_DIR, exist_ok=True)

for pdf in os.listdir(IN_DIR):
    if not pdf.lower().endswith(".pdf"): continue
    path = os.path.join(IN_DIR, pdf)
    print("Processing", pdf)
    text, scanned = extract_text_from_pdf(path)
    sections = split_into_sections(text)
    out = []
    for s in sections:
        t = s["text"]
        out.append({
            "title": s["title"],
            "deductible": find_deductible(t),
            "waiting_period": find_waiting(t),
            "is_exclusion": contains_exclusions_section(s["title"], t),
            "sample_text": t[:600]
        })
    with open(os.path.join(OUT_DIR, pdf + ".json"),"w",encoding="utf-8") as f:
        json.dump(out,f,indent=2)
    print("✅ Saved", pdf+".json")
