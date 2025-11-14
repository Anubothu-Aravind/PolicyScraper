# extractor/regex_extract.py
import re

DEDUCTIBLE_RE = re.compile(r'(?:deductible|excess|you will bear up to|you are liable for)\s*[:\-]?\s*([A-Za-z0-9,\. ]{1,40})', re.I)
WAITING_RE = re.compile(r'waiting period[s]?\s*(?:of\s*)?(\d+\s*(?:months|years))', re.I)
EXCLUSION_HEADINGS = re.compile(r'\b(exclusions?|what (?:is )?not covered|we will not pay)\b', re.I)
CURRENCY_RE = re.compile(r'(?:INR|Rs\.?|₹|\$|USD|EUR)\s*[0-9,\.]+')

def find_deductible(text):
    m = DEDUCTIBLE_RE.search(text)
    return m.group(1).strip() if m else None

def find_waiting(text):
    m = WAITING_RE.search(text)
    return m.group(1).strip() if m else None

def contains_exclusions_section(title, text):
    return bool(EXCLUSION_HEADINGS.search(title)) or bool(EXCLUSION_HEADINGS.search(text[:2000]))

# Example usage:
if __name__ == "__main__":
    sample = "This policy has a waiting period of 24 months for pre-existing conditions. Deductible: ₹5,000 per claim."
    print("deductible:", find_deductible(sample))
    print("waiting:", find_waiting(sample))
