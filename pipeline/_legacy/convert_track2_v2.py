#!/usr/bin/env python3
"""Track 2 v2 — Docling + Tesseract heb OCR pipeline.

Stage 1 of the conjecture path per CLAUDE.md, expanded to:
  Docling + Tesseract heb OCR (force_full_page_ocr=True)
              → structural elements with bboxes (section_header, list_item,
                footnote, page_footer, text). OCR text is already in Hebrew
                logical reading order.
  margin     → right-margin <text> elements collected as annotations
  prefix     → margin-annotation prefixes detected & stripped from list_items
  AST        → JSON intermediate (sections + signatures + footnotes + margins)
  renderer   → predictable markdown

Output:
  laws/israel/track2/<bill_id>.md          — rendered markdown
  laws/israel/track2/<bill_id>.ast.json    — canonical AST for downstream use

Stages 5 (LLM cleanup) and 8 (validator) are deferred.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

DEFAULT_MANIFEST = Path(__file__).parent.parent / "data" / "raw" / "israel" / "manifest.json"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "laws" / "israel" / "track2"

# Docling outputs <loc_X> coordinates normalized to a 0..500 grid by default.
DOCLING_GRID = 500
RIGHT_MARGIN_X_FRAC = 0.82  # right-margin column starts at this fraction of grid width


def build_converter() -> DocumentConverter:
    """Docling converter configured for Hebrew OCR via Tesseract CLI."""
    opts = PdfPipelineOptions()
    opts.do_ocr = True
    opts.ocr_options = TesseractCliOcrOptions(
        lang=["heb"],
        force_full_page_ocr=True,
    )
    opts.do_table_structure = False
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )


def parse_doctags(doctags: str) -> list[dict]:
    """Parse Docling's doctag string into a list of structural elements.

    Each element has keys: kind (str), text (str), bbox_grid (x0,y0,x1,y1).
    """
    pattern = re.compile(
        r"<(?P<kind>section_header_level_\d+|list_item|text|footnote|page_footer|caption|title)>"
        r"<loc_(?P<x0>\d+)><loc_(?P<y0>\d+)><loc_(?P<x1>\d+)><loc_(?P<y1>\d+)>"
        r"(?P<text>.*?)"
        r"</(?P=kind)>",
        re.DOTALL,
    )
    elements = []
    for m in pattern.finditer(doctags):
        elements.append({
            "kind": m.group("kind"),
            "text": m.group("text"),
            "bbox_grid": (
                int(m.group("x0")), int(m.group("y0")),
                int(m.group("x1")), int(m.group("y1")),
            ),
        })
    return elements


# ---------- Cleanup ----------------------------------------------------------

# Stray glyphs OCR introduces around margin/section markers.
_OCR_STRAY_GLYPHS = re.compile(r"[|\[\]]")
# Hebrew currency in parens often misread as section marker — drop entirely.
_OCR_CURRENCY_PARENS = re.compile(r"\(\s*[₪$€£]\s*\)")
# Bare currency glyphs leaked from typography (footnote markers, page artifacts).
_OCR_CURRENCY_BARE = re.compile(r"(?<!\w)[₪](?!\w)")
# RTL/LTR/RLM/LRM marks
_BIDI_MARKS = re.compile(r"[‎‏‪-‮⁦-⁩]")
# Double dashes that OCR introduces around margin notes
_DOUBLE_DASH = re.compile(r"\s--\s?")
# Stray spaced commas at line ends and double commas
_TRAILING_COMMA = re.compile(r"\s+,\s*$", re.MULTILINE)
_DOUBLE_COMMA = re.compile(r",\s*,")
# Backslash-escaped punctuation (\, \; \,) that OCR emits when fonts confuse it.
_ESCAPED_PUNCT = re.compile(r"\\([,;.])")
# Lone backslash on its own line (or surrounded by whitespace).
_LONE_BACKSLASH = re.compile(r"(?:^|\s)\\(?=\s|$)", re.MULTILINE)
# Punctuation-only string (used to filter false-positive margin notes).
_PUNCT_ONLY = re.compile(r"^[\s\W_]+$")


def clean_ocr_text(text: str) -> str:
    """Strip OCR-introduced artifacts. Keep Hebrew + section markers intact."""
    text = _BIDI_MARKS.sub("", text)
    text = _OCR_CURRENCY_PARENS.sub("", text)
    text = _OCR_CURRENCY_BARE.sub("", text)
    text = _OCR_STRAY_GLYPHS.sub("", text)
    text = _DOUBLE_DASH.sub(" ", text)
    text = _ESCAPED_PUNCT.sub(r"\1", text)
    text = _LONE_BACKSLASH.sub("", text)
    text = _TRAILING_COMMA.sub("", text)
    text = _DOUBLE_COMMA.sub(",", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def is_meaningful_text(text: str, min_hebrew_chars: int = 2) -> bool:
    """True if text has enough Hebrew letters to count as content (not just punctuation)."""
    if not text or _PUNCT_ONLY.match(text):
        return False
    hebrew_chars = sum(1 for c in text if "א" <= c <= "ת")
    return hebrew_chars >= min_hebrew_chars


# ---------- Margin-prefix stripping -----------------------------------------

# Section anchor pattern: a small integer (1-99) sitting between Hebrew words
# OR opening the body. Used to find where the body actually begins on a
# list_item line whose OCR captured the margin annotation as a prefix.
_SECTION_ANCHOR = re.compile(
    r"(?<![\d.])(\d{1,2})(?:\s*\.)?\s+"  # digit, optional dot, then space
    r"(?=[\(א-ת])"              # followed by '(' or Hebrew letter
)


def strip_margin_prefix(line: str, margin_phrases: set[str]) -> str:
    """Remove a margin-annotation prefix from the start of a list_item line.

    Strategy A: if the line starts with a known margin phrase (from the
    right-margin <text> elements), strip that exact phrase + trailing space.

    Strategy B: if the line begins with Hebrew words followed by a small
    integer + space + Hebrew/paren, treat the leading words as margin prefix
    and discard them. The integer is the section number — that's where the
    body starts.

    Strategy B is only applied when the leading run is short (≤ ~6 words),
    because long Hebrew runs before a digit are real body text.
    """
    s = line.strip()
    # Strategy A: known margin phrase prefix
    for ph in sorted(margin_phrases, key=len, reverse=True):
        if s.startswith(ph) and len(ph) < len(s) - 1:
            s = s[len(ph):].lstrip(" ,.|-")
            break
    # Strategy B: section anchor with short leading run
    m = _SECTION_ANCHOR.search(s)
    if m and m.start() > 0:
        prefix = s[: m.start()].strip()
        # Only treat as margin if prefix is short and lacks sentence punctuation
        if (
            prefix
            and len(prefix.split()) <= 6
            and not prefix.endswith((".", ":", ";"))
            and "(" not in prefix
        ):
            s = s[m.start():]
    return s


# ---------- Hebrew year extraction ------------------------------------------

# Hebrew year pattern: optional ה definite-article, then ת + millennium-letter
# (ש/ר/ק/צ/פ) + decade-letter, gershayim ", final-digit-letter.
_HE_YEAR_RE = re.compile(r"(?:ה)?ת[שרקצפ][א-ת]\"[א-ת]")


def extract_hebrew_year(ast: dict) -> str | None:
    blob = " ".join(f["text"] for f in ast.get("footnotes", []))
    if not blob:
        return None
    m = _HE_YEAR_RE.search(blob)
    return m.group(0) if m else None


# ---------- AST build --------------------------------------------------------

def build_ast(elements: list[dict]) -> dict:
    """Group elements into a Legal AST.

    - section_header → title
    - text in right-margin zone → margin_notes (collected first so list_item
      stripping can use them as known prefixes)
    - list_item → sections (margin prefix stripped, OCR cleaned)
    - footnote → footnotes
    - page_footer → page_artifacts
    - other text → auxiliary (signatures, etc.)
    """
    ast = {
        "title": None,
        "sections": [],
        "margin_notes": [],
        "footnotes": [],
        "page_artifacts": [],
        "auxiliary": [],
    }

    # Pass 1: collect right-margin <text> elements as margin notes (skipping
    # punctuation-only false positives — e.g. a stray ":" or "." in the margin
    # zone is not a real annotation).
    margin_phrases: set[str] = set()
    right_zone = DOCLING_GRID * RIGHT_MARGIN_X_FRAC
    for el in elements:
        if el["kind"] == "text" and el["bbox_grid"][0] >= right_zone:
            txt = clean_ocr_text(el["text"])
            if not is_meaningful_text(txt):
                continue
            ast["margin_notes"].append({"text": txt, "bbox": el["bbox_grid"]})
            margin_phrases.add(txt)

    # Pass 2: classify all other elements
    for el in elements:
        if el["kind"] == "text" and el["bbox_grid"][0] >= right_zone:
            continue  # already collected above
        text_clean = clean_ocr_text(el["text"])
        if not text_clean:
            continue

        if el["kind"].startswith("section_header"):
            ast["title"] = text_clean
        elif el["kind"] == "list_item":
            stripped = strip_margin_prefix(text_clean, margin_phrases)
            ast["sections"].append({
                "kind": el["kind"],
                "bbox": el["bbox_grid"],
                "text": stripped,
            })
        elif el["kind"] == "footnote":
            ast["footnotes"].append({"bbox": el["bbox_grid"], "text": text_clean})
        elif el["kind"] == "page_footer":
            ast["page_artifacts"].append({"bbox": el["bbox_grid"], "text": text_clean})
        elif el["kind"] == "text":
            ast["auxiliary"].append({"bbox": el["bbox_grid"], "text": text_clean})

    # Pass 3: merge same-y entries in RTL reading order (highest x0 first).
    # Docling sometimes splits a single visual line into multiple bbox elements
    # when intra-line spacing varies. Same-y merge stitches these back together
    # so a section like "3. תקציב המדינה ייקבע בחוק." doesn't end up as three
    # orphan list_items.
    ast["sections"] = merge_same_y_rtl(ast["sections"])
    ast["auxiliary"] = merge_same_y_rtl(ast["auxiliary"])

    return ast


def merge_same_y_rtl(entries: list[dict], y_tol: int = 3) -> list[dict]:
    """Merge entries whose y-ranges overlap into single RTL-ordered lines.

    Two entries are 'same-y' if their top/bottom y-coords are within `y_tol`
    of each other. When merging, the entry with the higher x0 (rightmost in
    the page) comes first in the joined text — that's Hebrew reading order.
    """
    if not entries:
        return entries
    # Sort by y_top so same-line entries are adjacent
    by_y = sorted(entries, key=lambda e: (e["bbox"][1], -e["bbox"][0]))
    merged: list[dict] = []
    for entry in by_y:
        if merged:
            prev = merged[-1]
            same_y = (
                abs(entry["bbox"][1] - prev["bbox"][1]) <= y_tol
                and abs(entry["bbox"][3] - prev["bbox"][3]) <= y_tol
            )
            if same_y and entry["text"] and prev["text"]:
                # prev was placed first because it has higher x0 (RTL order)
                prev["text"] = prev["text"] + " " + entry["text"]
                pb, eb = prev["bbox"], entry["bbox"]
                prev["bbox"] = (
                    min(pb[0], eb[0]), min(pb[1], eb[1]),
                    max(pb[2], eb[2]), max(pb[3], eb[3]),
                )
                continue
        merged.append(entry)
    return merged


# ---------- Markdown rendering ----------------------------------------------

def render_markdown(ast: dict, frontmatter: dict) -> str:
    fm_lines = ["---"]
    for k, v in frontmatter.items():
        if isinstance(v, list):
            fm_lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        else:
            fm_lines.append(f"{k}: {v if v else ''}")
    fm_lines.append("---")

    body: list[str] = []
    if ast["title"]:
        body.append(f"# {ast['title']}")
    body.append("")
    body.append("## Full Text")
    body.append("")
    for s in ast["sections"]:
        body.append(s["text"])
        body.append("")
    if ast["auxiliary"]:
        body.append("## Signatures")
        body.append("")
        for a in ast["auxiliary"]:
            body.append(a["text"])
            body.append("")
    if ast["margin_notes"]:
        body.append("## Margin Notes")
        body.append("")
        for n in ast["margin_notes"]:
            body.append(f"- {n['text']}")
        body.append("")
    if ast["footnotes"]:
        body.append("## Footnotes")
        body.append("")
        for f in ast["footnotes"]:
            body.append(f["text"])
            body.append("")
    if ast["page_artifacts"]:
        body.append("<!-- page artifacts (excluded from main rendering) -->")
        for p in ast["page_artifacts"]:
            body.append(f"<!-- {p['text']} -->")

    return "\n".join(fm_lines) + "\n\n" + "\n".join(body) + "\n"


# ---------- Per-bill conversion ---------------------------------------------

def convert_one(converter, entry: dict, output_dir: Path) -> bool:
    bill_id = entry["bill_id"]
    pdf_path = entry.get("pdf_path")
    if not pdf_path or not Path(pdf_path).exists():
        logging.warning("No PDF for bill %s", bill_id)
        return False

    try:
        result = converter.convert(pdf_path)
        doctags = result.document.export_to_doctags()
    except Exception as exc:
        logging.error("Docling failed on %s: %s", pdf_path, exc)
        return False

    elements = parse_doctags(doctags)
    ast = build_ast(elements)

    fm = {
        "title_he": entry.get("name_he", ""),
        "law_id": f"knesset-{bill_id}",
        "category": "basic-laws",
        "enacted": (entry.get("publication_date") or "")[:10],
        "enacted_he": extract_hebrew_year(ast) or "",
        "status": "active",
        "language": ["he"],
        "source_url": entry.get("pdf_url", ""),
        "track": 2,
    }

    md = render_markdown(ast, fm)

    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{bill_id}.md"
    json_path = output_dir / f"{bill_id}.ast.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(ast, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("Wrote %s and %s", md_path.name, json_path.name)
    return True


def main(manifest_path: Path, output_dir: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not manifest_path.exists():
        logging.error("Manifest not found: %s", manifest_path)
        raise SystemExit(1)
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    converter = build_converter()
    ok = fail = 0
    for e in entries:
        if convert_one(converter, e, output_dir):
            ok += 1
        else:
            fail += 1
    print(f"Done. Converted: {ok}, Errors: {fail}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    main(Path(args.input), Path(args.output))
