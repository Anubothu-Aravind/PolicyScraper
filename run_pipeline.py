"""
Pipeline script:
- Reads all PDF files from data/raw_pdfs
- Extracts text and splits into sections using parser.pdf_parser utilities
- Applies regex-based feature extraction (deductible, waiting period, exclusions)
- Writes a JSON summary per source PDF into data/parsed

Assumptions:
- parser/pdf_parser.py provides: extract_text_from_pdf(path) -> (text, scanned_flag)
                                split_into_sections(text) -> iterable of {"title": ..., "text": ...}
- extractor/regex_extract.py provides: find_deductible(text), find_waiting(text),
                                       contains_exclusions_section(title, text)
Directories:
  IN_DIR = data/raw_pdfs (must exist and contain PDFs)
  OUT_DIR = data/parsed (auto-created)
"""

import os, json  # Standard libraries for filesystem and JSON serialization
from parser.pdf_parser import extract_text_from_pdf, split_into_sections  # PDF parsing & sectioning
from extractor.regex_extract import find_deductible, find_waiting, contains_exclusions_section  # Feature extraction functions

IN_DIR, OUT_DIR = "data/raw_pdfs", "data/parsed"  # Input (PDF source) and output (parsed JSON) directories
os.makedirs(OUT_DIR, exist_ok=True)  # Ensure output directory exists; no error if already present

# Iterate over every file in the input directory
for pdf in os.listdir(IN_DIR):
    if not pdf.lower().endswith(".pdf"):  # Skip non-PDF files (case-insensitive)
        continue
    path = os.path.join(IN_DIR, pdf)  # Full filesystem path to the PDF
    print("Processing", pdf)  # Basic progress feedback

    text, scanned = extract_text_from_pdf(path)  # Extract full text; scanned flag could indicate OCR fallback
    sections = split_into_sections(text)  # Break document into logical sections with titles

    out = []  # Collect per-section feature dictionaries
    for s in sections:
        t = s["text"]  # Raw section text
        out.append({
            "title": s["title"],  # Section title/header
            "deductible": find_deductible(t),  # Extraction of deductible info (truthy/structured)
            "waiting_period": find_waiting(t),  # Extraction of waiting period
            "is_exclusion": contains_exclusions_section(s["title"], t),  # Flag if exclusion-related
            "sample_text": t[:600]  # Truncated preview for dataset creation / inspection
        })

    # Write JSON output named after the original PDF (with .json suffix appended)
    with open(os.path.join(OUT_DIR, pdf + ".json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("✅ Saved", pdf + ".json")  # Confirmation message