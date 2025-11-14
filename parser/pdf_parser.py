# parser/pdf_parser.py
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
import re

def extract_text_from_pdf(path):
    doc = fitz.open(path)
    full_text = []
    is_scanned = False
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if len(text.strip()) < 50:
            # likely scanned page; fallback to OCR
            is_scanned = True
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes()))
            ocr_text = pytesseract.image_to_string(img)
            full_text.append(ocr_text)
        else:
            full_text.append(text)
    return "\n".join(full_text), is_scanned

# basic section splitter
def split_into_sections(text):
    # heuristic: headings are lines in ALL CAPS or lines that start with numbers + dot
    lines = text.splitlines()
    sections = []
    current_title = "start"
    current_buf = []
    heading_pattern = re.compile(r"^([A-Z][A-Z\s\-\']{3,}|[0-9]+\.\s+)")
    for line in lines:
        if heading_pattern.match(line.strip()):
            if current_buf:
                sections.append({"title": current_title.strip(), "text": "\n".join(current_buf).strip()})
            current_title = line.strip()
            current_buf = []
        else:
            current_buf.append(line)
    if current_buf:
        sections.append({"title": current_title.strip(), "text": "\n".join(current_buf).strip()})
    return sections

if __name__ == "__main__":
    p = "../data/raw_pdfs/example.pdf"
    text, scanned = extract_text_from_pdf(p)
    print("scanned?", scanned)
    sections = split_into_sections(text)
    for i, s in enumerate(sections[:10]):
        print("SECTION", i, "TITLE:", s["title"][:120])
        print(s["text"][:300])
        print("----")
