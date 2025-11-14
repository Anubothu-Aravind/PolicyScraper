# parser/pdf_parser.py
# Purpose:
#   - Extract text from a PDF file with a fallback OCR pass for pages that appear to be scanned
#   - Split a full document text into heuristic "sections" based on heading patterns
#
# Dependencies:
#   - fitz (PyMuPDF) for PDF text and rasterization
#   - pytesseract + Pillow (PIL.Image) for OCR
#   - io for in‑memory byte buffers
#   - re for regular expressions
#
# Notes:
#   - OCR is only invoked if a page's extracted text length is below a threshold (likely scanned)
#   - Section splitting relies on a regex capturing ALL CAPS headings OR numbered headings (e.g. "1. Introduction")
#   - The logic is heuristic; may be refined or replaced with a more robust structure parser later.

import fitz  # PyMuPDF: open PDFs and extract text / render pages
import pytesseract  # Tesseract OCR engine wrapper
from PIL import Image  # Image object for OCR processing
import io  # In‑memory bytes buffer for pixmap data
import os  # Filesystem operations (not heavily used here but imported)
import re  # Regular expressions for heading detection

def extract_text_from_pdf(path):
    """
    Extract text from every page of a PDF.
    Fallback to OCR for pages that yield very little textual content (suggesting scanned images).
    Args:
        path (str): Filesystem path to the PDF.
    Returns:
        tuple[str, bool]:
            - Concatenated text across all pages separated by newline.
            - Boolean flag indicating whether at least one page required OCR (scanned).
    """
    doc = fitz.open(path)          # Open PDF document
    full_text = []                 # Accumulate page texts (native or OCR)
    is_scanned = False             # Track if any page required OCR fallback

    for page_num in range(len(doc)):  # Iterate over each page index
        page = doc[page_num]          # Retrieve page object
        text = page.get_text("text")  # Native text extraction (layout‑aware mode omitted)

        if len(text.strip()) < 50:    # Heuristic: too little text → likely scanned image page
            # Invoke OCR fallback:
            is_scanned = True
            pix = page.get_pixmap(dpi=200)           # Render page as raster image at higher DPI for OCR clarity
            img = Image.open(io.BytesIO(pix.tobytes()))  # Build PIL Image from pixmap bytes
            ocr_text = pytesseract.image_to_string(img)  # OCR extract textual content
            full_text.append(ocr_text)               # Append OCR result
        else:
            full_text.append(text)                   # Append native extraction

    return "\n".join(full_text), is_scanned          # Join all page texts with newlines

# basic section splitter
def split_into_sections(text):
    """
    Split raw document text into sections using heading detection heuristics.
    Heuristic definition:
        - A heading is a line either:
            * In ALL CAPS (≥4 characters allowing spaces, hyphens, apostrophes)
            * Starts with digits + '.' (e.g. '2. Scope', '10. TERMS')
    Args:
        text (str): Full document text.
    Returns:
        list[dict]: Each dict has keys:
            - 'title': heading/title string
            - 'text': content accumulated under that heading
    """
    # heuristic: headings are lines in ALL CAPS or lines that start with numbers + dot
    lines = text.splitlines()  # Split document into individual lines
    sections = []              # Output list of section dicts
    current_title = "start"    # Default initial section title
    current_buf = []           # Buffer for lines belonging to current section

    # Regex: start of line followed by:
    #   - ALL CAPS segment (letters/spaces/hyphen/apostrophe, ≥4 chars)
    #   - OR digits + '.' + whitespace (numbered heading)
    heading_pattern = re.compile(r"^([A-Z][A-Z\s\-']{3,}|[0-9]+.\s+)")

    for line in lines:
        if heading_pattern.match(line.strip()):  # Detected heading line
            if current_buf:  # Flush previous section if buffer has content
                sections.append({
                    "title": current_title.strip(),
                    "text": "\n".join(current_buf).strip()
                })
            current_title = line.strip()  # Start new section title
            current_buf = []              # Reset buffer for new section
        else:
            current_buf.append(line)      # Accumulate line under current section

    # Flush final buffered section (if any)
    if current_buf:
        sections.append({
            "title": current_title.strip(),
            "text": "\n".join(current_buf).strip()
        })

    return sections  # Return list of structured sections

if __name__ == "__main__":
    # Quick manual test when executing this module directly:
    p = "../data/raw_pdfs/example.pdf"   # Example path (adjust as needed)
    text, scanned = extract_text_from_pdf(p)
    print("scanned?", scanned)
    sections = split_into_sections(text)

    # Print first 10 sections for inspection
    for i, s in enumerate(sections[:10]):
        print("SECTION", i, "TITLE:", s["title"][:120])
        print(s["text"][:300])
        print("----")