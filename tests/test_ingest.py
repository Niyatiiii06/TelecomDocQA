"""Step 1: PDF text cleaning and section detection.

These functions work on page TEXT, so we can test them with small strings
that copy the quirks of real ETSI PDFs, without needing a PDF file.
"""

from telecomdocqa.ingest import (
    clean_pages,
    line_pattern,
    matches_toc,
    parse_heading,
    read_toc,
    split_into_sections,
)

HEADER = "ETSI TS 138 300 V18.6.0 (2025-07)"


def page(number, *lines):
    """A fake page: the ETSI header with the page number glued on (as pypdf
    really extracts it), then the body lines."""
    return "\n".join([f"{HEADER}{number}3GPP TS 38.300 version 18.6.0 Release 18", *lines])


def test_line_pattern_ignores_numbers():
    assert line_pattern(f"{HEADER}63GPP TS") == line_pattern(f"{HEADER}643GPP TS")


BODY = ["The gNB serves the UE.", "The AMF handles mobility.", "The SMF manages sessions.",
        "The UPF forwards packets.", "The NRF stores NF profiles."]


def test_clean_pages_removes_headers_page_numbers_and_toc():
    pages = [page(n, BODY[n - 1]) for n in range(1, 6)]
    pages[0] += "\n5.2 General ........................ 25\n17"
    lines = [line for _, line in clean_pages(pages)]
    assert lines == BODY  # no header, no TOC line, no page number


def test_clean_pages_keeps_page_numbers_of_lines():
    pages = [page(n, BODY[n - 1]) for n in range(1, 6)]
    assert clean_pages(pages)[2] == (3, "The SMF manages sessions.")


def test_text_repeated_on_most_pages_counts_as_a_header():
    # The rule that removes headers also removes ANY line that repeats on at
    # least half the pages, even if it's body text. That's the trade-off.
    pages = [page(n, "Same line everywhere.", BODY[n - 1]) for n in range(1, 6)]
    assert [line for _, line in clean_pages(pages)] == BODY


def test_parse_heading_accepts_real_headings():
    assert parse_heading("6.2.1 AMF") == ("6.2.1", "AMF")
    assert parse_heading("5 Physical Layer") == ("5", "Physical Layer")
    assert parse_heading("A.1 General") == ("A.1", "General")
    assert parse_heading("Annex B (informative): Deployment scenarios") == ("B", "Annex B: Deployment scenarios")


def test_parse_heading_rejects_sentences_and_noise():
    assert parse_heading("5 UEs are connected to the gNB.") is None    # ends like a sentence
    assert parse_heading("The AMF handles registration") is None       # no number
    assert parse_heading("99 Something") is None                       # no spec has clause 99
    assert parse_heading("Annex C describes the details") is None      # not (normative)/(informative)


def test_read_toc_handles_wrapped_entries():
    pages = [
        "Contents\n"
        "4.2.1 General ........................ 20\n"
        "4.2.9.3 AAA Server triggered Network Slice-Specific\n"
        "Re-authentication procedure ........ 105\n"
        "Annex A (informative): Examples ..... 300"
    ]
    assert read_toc(pages) == {"4.2.1": "general", "4.2.9.3": "aaa", "A": "informative"}


def test_matches_toc():
    toc = {"5.7.4": "standardized", "B": "informative"}
    assert matches_toc("5.7.4", "Standardized 5QI to QoS mapping", toc)
    assert not matches_toc("5", "Non-GBR 10 100 ms", toc)          # a table row, not in the contents
    assert not matches_toc("5.7.4", "Something else", toc)          # number listed, title differs
    assert matches_toc("B", "Annex B: Anything", toc)               # annex letters only need to be listed
    assert matches_toc("5", "Anything", {})                         # no contents found: accept


def test_split_into_sections():
    lines = [
        (1, "Foreword text before the scope."),
        (2, "1 Scope"),
        (2, "This document describes NR."),
        (3, "5 Non-GBR 10 100 ms"),            # table row that looks like a heading
        (3, "6.2.1 AMF"),
        (4, "The AMF terminates N2."),
    ]
    toc = {"1": "scope", "6.2.1": "amf"}
    sections = split_into_sections(lines, toc)

    assert [s["section_number"] for s in sections] == ["0", "1", "6.2.1"]
    assert sections[0]["section_title"] == "Front matter"
    assert (3, "5 Non-GBR 10 100 ms") in sections[1]["lines"]   # kept as body text, not a heading
    assert sections[2]["lines"] == [(4, "The AMF terminates N2.")]
