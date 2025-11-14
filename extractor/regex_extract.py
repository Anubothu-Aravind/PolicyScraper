# extractor/regex_extract.py
# Purpose:
#   - Provide regex-based feature extraction utilities for insurance / policy documents:
#       * Deductible (a.k.a. excess)
#       * Waiting period durations
#       * Exclusion section detection
#   - Lightweight, heuristic layer prior to advanced NLP models.
#
# Notes:
#   - Regex patterns are intentionally broad; refine as corpus evolves.
#   - Currency detection pattern CURRENCY_RE is currently unused but may assist in future value normalization.

import re  # Regular expression engine

# Compile regex patterns once at module import for efficiency.

# DEDUCTIBLE_RE:
#   Matches terms like "deductible", "excess", or phrases indicating responsibility
#   Captures up to ~40 characters of descriptive content following the keyword(s).
#   Case-insensitive (re.I).
DEDUCTIBLE_RE = re.compile(
    r'(?:deductible|excess|you will bear up to|you are liable for)\s*[:\-]?\s*([A-Za-z0-9,\. ]{1,40})',
    re.I
)

# WAITING_RE:
#   Identifies phrases such as "waiting period of 24 months" or "waiting periods 12 months"
#   Captures numeric duration + unit (months/years).
WAITING_RE = re.compile(
    r'waiting period[s]?\s*(?:of\s*)?(\d+\s*(?:months|years))',
    re.I
)

# EXCLUSION_HEADINGS:
#   Detects presence of exclusion sections either by heading or phrase start.
#   Examples: "Exclusions", "What is not covered", "We will not pay"
EXCLUSION_HEADINGS = re.compile(
    r'\b(exclusions?|what (?:is )?not covered|we will not pay)\b',
    re.I
)

# CURRENCY_RE:
#   Matches currency codes/symbols followed by numeric amounts
#   Examples: "INR 50,000", "Rs. 10,000", "$250", "€1,200", "USD 300"
CURRENCY_RE = re.compile(
    r'(?:INR|Rs\.?|₹|\$|USD|EUR)\s*[0-9,\.]+'
)

def find_deductible(text):
    """
    Extract deductible/excess information from a block of text.
    Returns:
        str | None: Captured detail (e.g. 'Rs 5,000 per claim') if found; otherwise None.
    """
    m = DEDUCTIBLE_RE.search(text)
    return m.group(1).strip() if m else None

def find_waiting(text):
    """
    Extract waiting period duration (e.g. '24 months', '2 years').
    Returns:
        str | None: The captured duration string if present.
    """
    m = WAITING_RE.search(text)
    return m.group(1).strip() if m else None

def contains_exclusions_section(title, text):
    """
    Determine whether a section should be flagged as an exclusion.
    Checks regex against:
        - The section title
        - First 2000 characters of the section body (performance vs. coverage tradeoff)
    Returns:
        bool: True if exclusion-related phrase detected.
    """
    return bool(EXCLUSION_HEADINGS.search(title)) or bool(EXCLUSION_HEADINGS.search(text[:2000]))

# Example usage block for quick manual testing.
if __name__ == "__main__":
    sample = "This policy has a waiting period of 24 months for pre-existing conditions. Deductible: ₹5,000 per claim."
    print("deductible:", find_deductible(sample))
    print("waiting:", find_waiting(sample))