"""UK-specific validators. Runs on the IR (numbering) and on raw XML vs rendered
Markdown (round-trip). Deliberately NOT a parameterisation of Israel's numbering
validator -- UK's legitimate gaps (repealed sections, alphanumeric suffixes like
19A) would false-positive-flood a dense-sequence checker (research PITFALLS.md
Pitfall 9). Built fresh for UK's rules.
"""
from __future__ import annotations

import re

from lxml import etree

from ir import LegalDoc, Provision

NS = {"leg": "http://www.legislation.gov.uk/namespaces/legislation"}

# Bare alphanumeric ("19A"), Roman numeral ("iv"), lower-case letter ("a"), or a
# dash-joined range of any of those ("II–VI") -- CLML uses ranges to label a
# single consolidated block of repealed provisions.
_ALNUM_NUMBER_RE = re.compile(
    r"^([0-9]+[A-Z]*|[ivxlcdm]+|[a-z]+)([–—-]([0-9]+[A-Z]*|[ivxlcdm]+|[a-z]+))?$",
    re.IGNORECASE,
)


class ValidationError:
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def __repr__(self) -> str:
        return f"{self.code}: {self.message}"


# ---------------------------------------------------------------------------
# UKVALID-01 -- round-trip losslessness
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return " ".join(text.split())


_FOOTNOTE_REF_RE = re.compile(r"\[\^[^\]]+\]")
_SPAN_RE = re.compile(r'<span id="[^"]*" */>')
_REPEAL_NOTE_RE = re.compile(r" \(repealed(?: for [^)]+)?\)")
_STATUS_MARKER_RE = re.compile(r" \[(REPEALED|NOT YET IN FORCE — prospective)\]")


def _normalize_rendered(markdown: str) -> str:
    """Strip renderer-added decoration (bracket-and-footnote markup per UKCONV-06,
    anchors, heading marks, extent/status annotations) before substring-matching
    against source <Text> nodes. The bracket/footnote convention is a REQUIRED
    typographic decoration (matches legislation.gov.uk's own page convention), not
    text loss -- a byte-exact substring check against undecorated markdown would
    fail by design on every amended provision. Strip the decoration -- and the
    renderer's own synthetic annotations, which are never sourced from a <Text>
    node -- keep the underlying words."""
    text = _FOOTNOTE_REF_RE.sub("", markdown)
    text = _SPAN_RE.sub("", text)
    text = _REPEAL_NOTE_RE.sub("", text)
    text = _STATUS_MARKER_RE.sub("", text)
    text = text.replace("[", "").replace("]", "").replace("**", "")
    return _normalize(text)


def extract_source_text_nodes(xml_bytes: bytes) -> list[str]:
    """Every <Text> element's normalized full text (itertext, mixed content included)."""
    root = etree.fromstring(xml_bytes)
    out = []
    for el in root.iter("{http://www.legislation.gov.uk/namespaces/legislation}Text"):
        text = _normalize("".join(el.itertext()))
        if text:
            out.append(text)
    return out


def check_round_trip(xml_bytes: bytes, rendered_markdown: str) -> list[ValidationError]:
    """UKVALID-01: every source <Text> node's content appears verbatim (after
    whitespace normalization) somewhere in the rendered output."""
    errors: list[ValidationError] = []
    haystack = _normalize_rendered(rendered_markdown)
    for text in extract_source_text_nodes(xml_bytes):
        # Strip the same decoration characters from the source needle too: some very
        # old Acts carry literal square brackets in their own text (editorially supplied
        # words), which would otherwise collide with the renderer's own Addition/
        # Substitution bracket convention when comparing.
        needle = text.replace("[", "").replace("]", "").replace("**", "")
        needle = _normalize(needle)
        if needle not in haystack:
            snippet = text[:80] + ("..." if len(text) > 80 else "")
            errors.append(ValidationError("ROUND_TRIP_MISSING", f"source text not found in output: {snippet!r}"))
    return errors


# ---------------------------------------------------------------------------
# UKVALID-02 -- UK numbering validator (alphanumeric-aware, gap-tolerant)
# ---------------------------------------------------------------------------

def _is_valid_uk_number(number: str | None) -> bool:
    if not number:
        return False
    return bool(_ALNUM_NUMBER_RE.match(number.strip()))


def _check_numbering(provisions: list[Provision], errors: list[ValidationError], context: str) -> None:
    """Cross-checks numbering FORMAT (must be a recognised alphanumeric/Roman
    provision number) and duplicate-heading detection at each sibling level.
    Does NOT flag gaps -- UK gaps are legitimate (repealed sections, inserted
    19A-style numbers) per PITFALLS.md Pitfall 9. BlockAmendment/uncertain/table
    content is already excluded (never enters this walk -- see caller)."""
    seen_ids: set[str] = set()
    for p in provisions:
        if p.kind in ("block_quote", "uncertain", "table"):
            continue  # never validated -- Pitfall 6 / Pitfall 9
        # Containers (Part/Chapter/Schedule) carry a free-text label ("SCHEDULE 1",
        # "PART I"), not an alphanumeric provision number -- only leaf provisions
        # (section/subsection/para/subpara) are format-checked.
        if p.number and p.kind not in ("part", "chapter", "schedule") and not _is_valid_uk_number(p.number):
            errors.append(ValidationError(
                "MALFORMED_NUMBER", f"{context}: provision number {p.number!r} is not a recognised UK format"))
        if p.id:
            if p.id in seen_ids:
                errors.append(ValidationError("DUPLICATE_ID", f"{context}: duplicate provision id {p.id!r}"))
            seen_ids.add(p.id)
        _check_numbering(p.children, errors, context=p.id or context)


def check_numbering(doc: LegalDoc) -> list[ValidationError]:
    errors: list[ValidationError] = []
    _check_numbering(doc.body, errors, context="body")
    _check_numbering(doc.schedules, errors, context="schedules")
    return errors


def check_number_of_provisions_oracle(doc: LegalDoc, actual_leaf_count: int) -> list[ValidationError]:
    """Cross-check against /Legislation/@NumberOfProvisions as a count oracle
    (Pitfall 9's recommendation) -- informational, not a hard failure, since the
    source's own count includes provisions this parser may bucket differently
    (e.g. schedule paragraphs)."""
    errors: list[ValidationError] = []
    if doc.meta.number_of_provisions is not None and actual_leaf_count == 0:
        errors.append(ValidationError(
            "EMPTY_BODY", f"source declares {doc.meta.number_of_provisions} provisions but 0 were parsed"))
    return errors


def _count_leaves(provisions: list[Provision]) -> int:
    count = 0
    for p in provisions:
        if p.kind in ("block_quote", "uncertain", "table", "part", "chapter", "crossheading"):
            count += _count_leaves(p.children)
        else:
            count += 1
            count += _count_leaves(p.children)
    return count


def validate(doc: LegalDoc, xml_bytes: bytes, rendered_markdown: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    errors.extend(check_round_trip(xml_bytes, rendered_markdown))
    errors.extend(check_numbering(doc))
    errors.extend(check_number_of_provisions_oracle(doc, _count_leaves(doc.body) + _count_leaves(doc.schedules)))
    return errors
