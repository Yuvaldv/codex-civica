#!/usr/bin/env python3
"""Convert Knesset law PDFs to structured Markdown with YAML frontmatter."""

import argparse
import json
import logging
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import fitz  # pymupdf
import yaml

MANIFEST_PATH_DEFAULT = Path(__file__).parent.parent / "data" / "raw" / "israel" / "manifest.json"
OUTPUT_DIR_DEFAULT = Path(__file__).parent.parent / "laws" / "israel"
MANDATORY_FIELDS = ["title_he", "law_id", "category", "enacted", "status", "source_url"]


def detect_category(name_he: str) -> str:
    name_he = name_he.strip()
    if name_he.startswith("חוק-יסוד") or name_he.startswith("חוק יסוד"):
        return "basic-laws"
    return "civil-law"


def make_slug(name_he: str, bill_id: int) -> str:
    text = name_he.strip()
    text = re.sub(r"[ְ-ׇ]", "", text)  # remove Hebrew nikud
    text = re.sub(r'[:\.,;()\[\]"\'״׳]', " ", text)  # punctuation to spaces

    if text.startswith("חוק-יסוד") or text.startswith("חוק יסוד"):
        text = re.sub(r"^חוק.יסוד\s*", "", text).strip()
        prefix = "basic-law"
    elif text.startswith("חוק"):
        text = re.sub(r"^חוק\s*", "", text).strip()
        prefix = "law"
    else:
        prefix = ""

    year_match = re.search(r"(\d{4})", name_he)
    year_suffix = f"-{year_match.group(1)}" if year_match else ""

    ascii_part = unicodedata.normalize("NFKD", text)
    ascii_part = ascii_part.encode("ascii", "ignore").decode("ascii")
    ascii_part = re.sub(r"[^a-zA-Z0-9\s-]", "", ascii_part).strip()
    ascii_part = re.sub(r"\s+", "-", ascii_part).lower()
    ascii_part = re.sub(r"-+", "-", ascii_part).strip("-")

    if not ascii_part:
        slug = f"{prefix}-{bill_id}" if prefix else f"law-{bill_id}"
    else:
        slug = f"{prefix}-{ascii_part}{year_suffix}" if prefix else f"{ascii_part}{year_suffix}"

    slug = re.sub(r"-+", "-", slug).strip("-").lower()
    return slug or f"law-{bill_id}"


LINE_TOL = 4          # words within this many points in y = same visual line
PARA_GAP = 14         # y-gap between rows that triggers a paragraph break
MARGIN_FRAC = 0.18    # outermost fraction of page width treated as margin zone
NOTE_GAP = 14         # max y-gap between consecutive margin lines in one note


def _collect_lines(page) -> tuple[list, float]:
    """Return (lines, body_size) where each line is (y0, x0, x1, size, text).

    Uses pymupdf's dict mode which applies bidi at line level — yields Hebrew
    text in correct logical order with parens already mirrored. body_size is
    the dominant font size (the body text); smaller sizes mark margin
    annotations, section headers, and footnotes.
    """
    d = page.get_text("dict")
    lines: list[tuple] = []
    size_counts: dict[float, int] = {}
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [s for s in line.get("spans", []) if s["text"].strip()]
            if not spans:
                continue
            text = "".join(s["text"] for s in line.get("spans", []))
            line_size = round(min(s["size"] for s in spans), 1)
            bx = line["bbox"]
            lines.append((bx[1], bx[0], bx[2], line_size, text))
            size_counts[line_size] = size_counts.get(line_size, 0) + 1
    if not size_counts:
        return [], 0.0
    body_size = max(size_counts.items(), key=lambda kv: kv[1])[0]
    return lines, body_size


def _classify_lines(lines, body_size, page_w):
    """Split lines into (body_rows, margin_notes).

    Margin annotations are smaller-font lines whose bbox lies entirely within
    the outer left or right margin zone of the page. Everything else is body.
    Body lines are clustered into visual rows (y-proximity) and emitted in
    RTL reading order. Margin lines are clustered into multi-line notes.
    """
    left_zone = page_w * MARGIN_FRAC
    right_zone = page_w * (1 - MARGIN_FRAC)

    body_lines = []
    margin_lines = []
    for y, x0, x1, size, text in lines:
        is_small = size < body_size
        if is_small and x1 < left_zone:
            margin_lines.append((y, x0, x1, text, "left"))
        elif is_small and x0 > right_zone:
            margin_lines.append((y, x0, x1, text, "right"))
        else:
            body_lines.append((y, x0, x1, text))

    # Cluster body lines into visual rows
    body_lines.sort(key=lambda l: l[0])
    rows = []
    for y, x0, x1, text in body_lines:
        if rows and abs(y - rows[-1][0]) <= LINE_TOL:
            rows[-1][1].append((x0, text))
        else:
            rows.append([y, [(x0, text)]])

    # Group margin lines into notes by y-proximity
    margin_lines.sort(key=lambda l: l[0])
    notes: list[tuple[float, str]] = []
    cur: list = []
    for ml in margin_lines:
        if cur and ml[0] - cur[-1][0] > NOTE_GAP:
            notes.append(_finalize_note(cur))
            cur = []
        cur.append(ml)
    if cur:
        notes.append(_finalize_note(cur))

    return rows, notes


def _finalize_note(group) -> tuple[float, str]:
    """Join a cluster of margin lines into one annotation. Returns (anchor_y, text)."""
    # Each line in the group is already left-to-right in logical order from dict
    # mode. Multiple lines stack vertically — join with space.
    anchor_y = group[0][0]
    text = " ".join(g[3].strip() for g in group)
    return (anchor_y, text)


def extract_text(pdf_path: str) -> str:
    """Extract Hebrew RTL text + margin annotations from a PDF."""
    doc = fitz.open(str(pdf_path))
    page_outputs = []

    for page in doc:
        lines, body_size = _collect_lines(page)
        if not lines:
            page_outputs.append("")
            continue
        rows, notes = _classify_lines(lines, body_size, page.rect.width)

        # Pair notes to body rows by closest y. We render the note as a
        # blockquote line immediately before its anchored body row.
        note_idx = 0
        notes_sorted = sorted(notes, key=lambda n: n[0])
        out_lines: list[str] = []
        prev_y: float | None = None
        for y, word_list in rows:
            # Emit any notes that anchor before/at this row
            while note_idx < len(notes_sorted) and notes_sorted[note_idx][0] <= y + LINE_TOL:
                ny, ntext = notes_sorted[note_idx]
                if out_lines and out_lines[-1] != "":
                    out_lines.append("")
                out_lines.append(f"> *{ntext.strip()}*")
                out_lines.append("")
                note_idx += 1

            if prev_y is not None and (y - prev_y) > PARA_GAP:
                if out_lines and out_lines[-1] != "":
                    out_lines.append("")
            # Sort row words right-to-left for Hebrew reading order
            rtl = sorted(word_list, key=lambda w: -w[0])
            out_lines.append(" ".join(t for _, t in rtl))
            prev_y = y

        # Trailing notes (if any anchor past the last body row)
        while note_idx < len(notes_sorted):
            _, ntext = notes_sorted[note_idx]
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            out_lines.append(f"> *{ntext.strip()}*")
            note_idx += 1

        page_outputs.append("\n".join(out_lines))

    doc.close()
    return "\n\n".join(page_outputs)


def build_frontmatter(entry: dict) -> dict:
    bill_id = entry["bill_id"]
    name_he = entry.get("name_he", "")
    pub_date = entry.get("publication_date")
    enacted = ""
    if pub_date:
        try:
            enacted = datetime.fromisoformat(pub_date).date().isoformat()
        except ValueError:
            enacted = pub_date[:10] if len(pub_date) >= 10 else pub_date

    return {
        "title_he": name_he,
        "law_id": f"knesset-{bill_id}",
        "category": detect_category(name_he),
        "tags": [],
        "enacted": enacted,
        "status": "active",
        "language": ["he"],
        "source_url": entry.get("pdf_url") or "",
        "related_laws": [],
    }


_SOFT_HYPHEN = "­"


def fix_rtl_artifacts(text: str) -> str:
    """Clean up RTL PDF extraction artifacts in dict-mode Hebrew text.

    pymupdf's dict mode applies bidi at line level, so Hebrew words come out in
    correct logical order. Residual issues are:
      - soft hyphens used as compound-word joiners or footnote markers
      - section markers stored with leading punctuation: '.1', ',5', ',3'
      - reversed-mirrored parens around Hebrew content: ')א(' instead of '(א)'
      - footnote markers stuck to neighbours: '­1', '­4', '\xad3המיילדות'
      - missing space between word and following parenthesised number: 'בסעיף(5)'
    """
    sh = _SOFT_HYPHEN
    # Soft hyphen between two Hebrew letters → real compound hyphen
    text = re.sub(f"([א-ת]){sh}([א-ת])", r"\1-\2", text)
    # Soft hyphen + digit (start of token) = footnote superscript: ' ­1 ' → ' [^1] '
    text = re.sub(rf"(?<!\w){sh}(\d+)\b", r"[^\1]", text)
    text = re.sub(rf"\b(\d+){sh}(?!\w)", r"[^\1]", text)
    # Remaining soft hyphens = stray PDF artifacts
    text = text.replace(sh, "")

    # Reversed parens around Hebrew content: ')א(' → '(א)', ')ב(' → '(ב)'
    text = re.sub(
        r"\)\s*([^()]*?[א-ת][^()]*?)\s*\(",
        lambda m: "(" + m.group(1).strip() + ")",
        text,
    )

    # Section markers extracted with leading punctuation:
    #   '.1' → '1.', '.17' → '17.', ',3' → '3,'
    # Only at line start or after whitespace, and only when the digit is short.
    text = re.sub(r"(^|\s)\.(\d{1,3})\b", r"\1\2.", text, flags=re.MULTILINE)
    # Comma-prefixed digit at the very END of a token attached to a Hebrew word:
    # 'ברפואה,1947' is fine; ',5בסעיף' should be 'בסעיף 5,' but we can't reliably
    # invert across the line — instead, just split it: ',5בסעיף' → 'בסעיף 5,'
    text = re.sub(r",(\d+)([א-ת]\w*)", r"\2 \1,", text)
    # Digit-glued-to-Hebrew without comma: 'יבוא22סעיף' → 'בסעיף 22 יבוא'? Too risky to
    # reverse — instead just insert spaces: '22סעיף' → '22 סעיף', 'יבוא22' → 'יבוא 22'.
    text = re.sub(r"(\d+)([א-ת])", r"\1 \2", text)
    text = re.sub(r"([א-ת])(\d+)", r"\1 \2", text)

    # Insert space before opening paren glued to Hebrew letter: 'ביילוד(1)' → 'ביילוד (1)'
    text = re.sub(r"([א-ת])\(", r"\1 (", text)
    # Insert space after closing paren glued to Hebrew letter: '(א)שר' → '(א) שר'
    text = re.sub(r"\)([א-ת])", r") \1", text)

    # Collapse double-spaces left by the above passes
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Trim trailing whitespace per line
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text


def build_markdown(frontmatter_dict: dict, body_text: str, name_he: str) -> str:
    fm_str = yaml.dump(
        frontmatter_dict, allow_unicode=True, default_flow_style=False, sort_keys=False
    )
    body_clean = fix_rtl_artifacts(body_text.strip())
    body_clean = re.sub(r"\n{3,}", "\n\n", body_clean)
    return f"---\n{fm_str}---\n\n# {name_he}\n\n## Full Text\n\n{body_clean}\n"


def convert_pdf(entry: dict, output_dir: Path) -> tuple[bool, str]:
    """Returns (success, slug)."""
    bill_id = entry["bill_id"]
    pdf_path = entry.get("pdf_path")
    name_he = entry.get("name_he", "")

    slug = make_slug(name_he, bill_id)
    out_path = Path(output_dir) / f"{slug}.md"

    # Slug collision: if file exists with different law_id, append bill_id
    if out_path.exists():
        try:
            import frontmatter as fm_mod
            existing = fm_mod.load(str(out_path))
            if existing.get("law_id") != f"knesset-{bill_id}":
                slug = f"{slug}-{bill_id}"
                out_path = Path(output_dir) / f"{slug}.md"
            else:
                logging.info("Skipping %s (already converted)", slug)
                return True, slug
        except Exception:
            logging.info("Skipping %s (already exists)", slug)
            return True, slug

    if not pdf_path or not Path(pdf_path).exists():
        logging.warning("No PDF for bill %s (%s) — skipping", bill_id, name_he[:40])
        return False, slug

    try:
        body_text = extract_text(pdf_path)
    except Exception as e:
        logging.error("PDF extraction failed for bill %s: %s", bill_id, e)
        return False, slug

    fm = build_frontmatter(entry)
    md_content = build_markdown(fm, body_text, name_he)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md_content, encoding="utf-8")
    logging.info("Wrote %s", out_path)
    return True, slug


def main(manifest_path: str, output_dir: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)

    if not manifest_path.exists():
        logging.error("Manifest not found: %s — run fetch.py first", manifest_path)
        raise SystemExit(1)

    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    logging.info("Converting %d laws from manifest", len(entries))

    success_count = 0
    skip_count = 0
    fail_count = 0

    for entry in entries:
        ok, slug = convert_pdf(entry, output_dir)
        if ok:
            if (output_dir / f"{slug}.md").exists():
                success_count += 1
            else:
                skip_count += 1
        else:
            fail_count += 1

    print(f"Done. Converted: {success_count}, Skipped (no PDF): {skip_count}, Errors: {fail_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=str(MANIFEST_PATH_DEFAULT),
        help="Path to manifest.json (default: data/raw/israel/manifest.json)",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_DIR_DEFAULT),
        help="Output directory for .md files (default: laws/israel/)",
    )
    args = parser.parse_args()
    main(args.input, args.output)
