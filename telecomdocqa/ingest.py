"""Step 1a: read PDF specs, clean the text and split it into sections.

3GPP specs have numbered headings like "5.2.1 General" and annexes like
"Annex A (informative): ..." or "A.1 General". We use those headings to
split each document into sections, and remember the page each line came
from so answers can cite "TS 38.300, section 5.2.1, page 23" later.
"""

import re
from collections import Counter

from pypdf import PdfReader

from telecomdocqa import config

# "5", "5.2", "5.2.1.3" or "A.1", "B.2.3" followed by a title starting with a capital letter
HEADING_RE = re.compile(r"^(\d{1,2}(?:\.\d+){0,5}|[A-Z](?:\.\d+){1,5})\s+([A-Z].{1,100})$")
# "Annex A (informative): Deployment scenarios". Real annex headings always
# say (normative) or (informative); a sentence like "Annex C describes ..." doesn't.
ANNEX_RE = re.compile(r"^Annex ([A-Z]{1,2})\s*\((?:normative|informative)\)\s*:?\s*(.*)$")
# Table-of-contents lines end with dot leaders and a page number: "5.2 General ........ 25"
TOC_RE = re.compile(r"\.{4,}\s*\d+\s*$")
# A line that is only a page number
PAGE_NUMBER_RE = re.compile(r"^\d{1,4}$")
# The section number at the start of a contents line: "5.2.1", "A.3" or "Annex B"
TOC_NUMBER_RE = re.compile(r"^(?:Annex ([A-Z]{1,2})\b|(\d{1,2}(?:\.\d+)*|[A-Z]{1,2}(?:\.\d+)+)\s)")


def load_pdf_pages(pdf_path):
    """Return a list with the text of each page of the PDF."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return pages


def line_pattern(line):
    """Replace every number with '#', so headers that differ only by page
    number look the same.

    Example: "ETSI TS 138 300 V18.6.0 (2025-07)63GPP TS 38.300" and
             "ETSI TS 138 300 V18.6.0 (2025-07)64GPP TS 38.300"
    both become "ETSI TS # # V#.#.# (#-#)#GPP TS #.#".
    """
    return re.sub(r"\d+", "#", " ".join(line.split()))


def find_repeated_patterns(pages):
    """Find header/footer patterns that repeat on most pages."""
    counts = Counter()
    for page_text in pages:
        # use a set so a pattern is counted once per page
        patterns = set(line_pattern(line) for line in page_text.splitlines() if line.strip())
        counts.update(patterns)

    if len(pages) < 4:  # too few pages to tell what repeats
        return set()

    min_pages = len(pages) * config.HEADER_FOOTER_THRESHOLD
    return {pattern for pattern, count in counts.items() if count >= min_pages}


def first_word(text):
    """Lowercase first word, used to compare a heading with its contents entry."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return words[0] if words else ""


def read_toc(pages):
    """Read the table of contents: {section number: first word of its title}.

    Contents lines end with dot leaders and a page number:
        "5.2.1 General .................. 25"
    Long entries wrap, so the number is sometimes on the line before:
        "4.2.9.3 AAA Server triggered Network Slice-Specific"
        "Re-authentication procedure ........ 105"
    """
    toc = {}
    for page_text in pages:
        lines = [" ".join(l.split()) for l in page_text.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            if not TOC_RE.search(line):
                continue
            entry = line
            match = TOC_NUMBER_RE.match(line)
            if not match and i > 0:
                entry = lines[i - 1]  # wrapped entry: the number is on the line before
                match = TOC_NUMBER_RE.match(entry)
            if match:
                number = match.group(1) or match.group(2)
                toc[number] = first_word(entry[match.end():])
    return toc


def matches_toc(number, title, toc):
    """True if this heading is listed in the contents with the same first word.
    Annex headings ("Annex B: ...") only need their letter to be listed."""
    if not toc:
        return True  # no contents found: accept every heading-like line
    if number not in toc:
        return False
    if not number[0].isdigit() and "." not in number:
        return True
    return first_word(title) == toc[number]


def clean_pages(pages):
    """Remove headers, footers, page numbers and table-of-contents lines.

    Returns a list of (page_number, line) pairs. Page numbers start at 1.
    """
    repeated = find_repeated_patterns(pages)
    cleaned = []
    for page_number, page_text in enumerate(pages, start=1):
        for line in page_text.splitlines():
            line = " ".join(line.split())  # collapse tabs and double spaces
            if not line:
                continue
            if line_pattern(line) in repeated:
                continue
            if PAGE_NUMBER_RE.match(line):
                continue
            if TOC_RE.search(line):
                continue
            cleaned.append((page_number, line))
    return cleaned


def parse_heading(line):
    """If the line is a section heading, return (number, title). Otherwise None."""
    annex = ANNEX_RE.match(line)
    if annex:
        letter, title = annex.groups()
        return letter, ("Annex " + letter + ": " + title).strip(": ")

    match = HEADING_RE.match(line)
    if not match:
        return None

    number, title = match.groups()
    title = title.strip()

    # Filter out normal sentences that happen to start with a number,
    # e.g. "5 UEs are connected to the gNB." Real headings are short and
    # don't end with sentence punctuation.
    if title.endswith((".", ",", ";", ":")):
        return None
    if len(title.split()) > 15:
        return None
    if number[0].isdigit() and int(number.split(".")[0]) > 30:
        return None  # 3GPP specs never have more than ~30 top-level clauses
    return number, title


def split_into_sections(lines, toc=None):
    """Group (page_number, line) pairs into sections using the headings.

    Numbered table rows ("5 Non-GBR 10 100 ms") and procedure steps
    ("4 Namf_Communication_UEContextTransfer") can look like headings, so a
    heading only counts if the spec's table of contents lists the same
    number with a title starting with the same word.

    Every 3GPP spec starts its real content with "1 Scope". Everything
    before that (cover page, contents pages, foreword) goes into a
    "front matter" section with number "0". We don't look for headings
    there, because wrapped contents-page lines look like headings.
    """
    # find where the real content starts
    start = 0
    for i, (_, line) in enumerate(lines):
        if parse_heading(line) == ("1", "Scope"):
            start = i
            break

    sections = []
    current = {"section_number": "0", "section_title": "Front matter", "lines": list(lines[:start])}
    for page_number, line in lines[start:]:
        heading = parse_heading(line)
        if heading and not matches_toc(heading[0], heading[1], toc):
            heading = None  # looks like a heading but isn't in the contents
        if heading:
            sections.append(current)
            number, title = heading
            current = {"section_number": number, "section_title": title, "lines": []}
        else:
            current["lines"].append((page_number, line))

    sections.append(current)
    # drop sections with no body text (e.g. a heading followed directly by a sub-heading)
    return [s for s in sections if s["lines"]]


def load_document_sections(pdf_path):
    """Full pipeline for one PDF: pages -> cleaned lines -> sections."""
    pages = load_pdf_pages(pdf_path)
    toc = read_toc(pages)
    lines = clean_pages(pages)
    sections = split_into_sections(lines, toc)
    return pages, sections
