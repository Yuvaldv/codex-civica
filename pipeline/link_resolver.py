#!/usr/bin/env python3
"""Stage 4 — Intra- and inter-document linker.

Pass 1: Adds <span id="section-N" /> anchors to top-level numbered section headings.
Pass 2: Replaces intra-law section references (סעיף N) with same-page anchor links.
Pass 3: Collects margin-note blockquotes and appends an indexed list under
        ## Sidenotes with links back to the section each note belongs to.
Pass 4: Upgrades knesset.gov.il PDF cross-law links to ./LAWID.md internal links
        when the target law has been converted and lives in laws/israel/.
        Idempotent — safe to re-run as more laws are added.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
LAWS_DIR = PIPELINE_DIR.parent / "laws" / "israel"
MANIFEST_PATH = PIPELINE_DIR.parent / "data" / "raw" / "israel" / "manifest_laws.json"


# ─── Frontmatter ─────────────────────────────────────────────────────────────

def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    split = end + 4
    if split < len(text) and text[split] == "\n":
        split += 1
    return text[:split], text[split:]


# ─── Pass 1: Section anchors ─────────────────────────────────────────────────

# Matches: ^# N.  /  ^# N(א).  /  ^# Nא.  /  ^## N. some text
_SEC_HEADING = re.compile(r"^(#{1,2} )(\d+)([א-ת]?)((?:\([^)]+\))*)(\.)(.*)$")
# Strips any previously injected anchor (both old {#} style and new <span> style)
_STRIP_ANCHOR = re.compile(r"\s*(?:\{#section-\d+\}|<span id=\"section-\d+\" />)")


def add_section_anchors(body: str) -> tuple[str, dict[str, str]]:
    """Add <span id="section-N" /> to numbered section headings; return (body, section_map).
    Section Nא (amended sub-section) shares the anchor with section N.
    Uses HTML spans instead of {#id} to avoid MDX/acorn parse errors."""
    section_map: dict[str, str] = {}
    out = []
    for line in body.split("\n"):
        m = _SEC_HEADING.match(line)
        if m:
            num = m.group(2)      # digits only — shared key for Nא variants
            anchor_id = f"section-{num}"
            section_map[num] = anchor_id
            line = _STRIP_ANCHOR.sub("", line.rstrip())
            line = line + f' <span id="{anchor_id}" />'
        out.append(line)
    return "\n".join(out), section_map


# ─── Pass 2: Intra-law section links ─────────────────────────────────────────

_HE = "א-ת"

_SEC_REF = re.compile(
    rf"(?<![/{_HE}\[#])"
    rf"(?P<pre>[לבמכ]?)"
    rf"(?P<word>סעיף|סעיפים|סעיפי)"
    rf"\s+(?P<num>\d+)(?!\d)"       # (?!\d) blocks backtracking to partial number
    rf"(?P<suf>[א-ת]?)"           # optional letter suffix: 4א, 4ב etc.
    rf"(?P<sub>(?:\([^)]+\))*)"
    # Don't link if followed (with optional letter suffix) by "to [another] law"
    # Allow לחוק זה (this law), block לחוק X, לפקודת X, לתקנות X
    # [א-ת]? accounts for backtracking when suf='' but the letter is still in text
    rf"(?![א-ת]?\s+ל(?:חוק(?!\s+זה)|פקודת|תקנות|דבר\s+המלך))",
)

# Strips any section links previously added so re-runs start clean
_STRIP_SEC_LINK = re.compile(
    rf"\[([לבמכ]?(?:סעיף|סעיפים|סעיפי)\s+\d+[א-ת]?(?:\([^)]+\))*)\]\(#section-\d+\)"
)


def linkify_section_refs(body: str, section_map: dict[str, str]) -> str:
    if not section_map:
        return body

    # Strip any previously-added section links so re-runs apply corrected rules
    body = _STRIP_SEC_LINK.sub(r"\1", body)

    def _replace(m: re.Match) -> str:
        num = m.group("num")
        if num not in section_map:
            return m.group(0)
        anchor = section_map[num]
        pre = m.group("pre")
        word = m.group("word")
        suf = m.group("suf")
        sub = m.group("sub")
        return f"[{pre}{word} {num}{suf}{sub}](#{anchor})"

    out = []
    for line in body.split("\n"):
        # Skip margin-note blockquotes only — body text lives on heading lines
        # in this document structure, so headings must be processed too.
        if line.startswith(">"):
            out.append(line)
            continue
        out.append(_SEC_REF.sub(_replace, line))
    return "\n".join(out)


# ─── Pass 3: Margin note index ───────────────────────────────────────────────

_MG_LINE = re.compile(r"^> (.+)$")
_ANCHOR_IN_HDR = re.compile(r'<span id="(section-\d+)"')
# Strips previously injected Sidenotes block (all past format variants).
_STRIP_MG_INDEX = re.compile(
    r"\n+(?:##+ (?:Sidenotes|הערות גיליון)\n\n?)?(?:- \[[^\]]*\]\(#section-\d+\)\n)+"
)


def collect_margin_notes(body: str) -> list[tuple[str, str]]:
    """Return (anchor_id, note_text) for each margin-note blockquote, in order."""
    notes: list[tuple[str, str]] = []
    current_anchor: str | None = None
    for line in body.split("\n"):
        a = _ANCHOR_IN_HDR.search(line)
        if a:
            current_anchor = a.group(1)
        m = _MG_LINE.match(line)
        if m and current_anchor:
            text = m.group(1).strip()
            if text:
                notes.append((current_anchor, text))
    return notes


def inject_margin_note_index(body: str, notes: list[tuple[str, str]]) -> str:
    """Append/replace ## Sidenotes block at end of document (idempotent)."""
    body = _STRIP_MG_INDEX.sub("", body)
    if not notes:
        return body

    bullets = "\n".join(f"- [{text}](#{anchor})" for anchor, text in notes)
    body = body.rstrip() + f"\n\n## Sidenotes\n\n{bullets}\n"
    return body


# ─── Pass 4: Inter-law link upgrader ─────────────────────────────────────────

_YEAR_SUFFIX = re.compile(r",\s*ה?תש[א-ת]*\"[א-ת]-\d{4}(?:\s*\[.*?\])?$")
_BRACKETS_RE = re.compile(r"\s*\[.*?\]")

_KNESSET_PDF_LINK = re.compile(
    r"\[([^\]]+)\]\((https://fs\.knesset\.gov\.il[^)]+\.PDF)\)",
    re.IGNORECASE,
)


def _normalize_law_title(title: str) -> str:
    t = _BRACKETS_RE.sub("", title)
    t = _YEAR_SUFFIX.sub("", t)
    return t.strip().rstrip(",").strip()


def build_inter_law_index(laws_dir: Path) -> dict[str, str]:
    """Return pdf_url → law_id for all converted laws in laws_dir.
    Requires manifest_laws.json alongside the pipeline."""
    if not MANIFEST_PATH.exists():
        logging.warning("Manifest not found at %s — skipping Pass 4", MANIFEST_PATH)
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)
    converted = {p.stem for p in laws_dir.glob("*.md") if p.stem.isdigit()}
    pdf_map: dict[str, str] = {}
    for entry in manifest:
        lid = str(entry["law_id"])
        if lid not in converted:
            continue
        if entry.get("pdf_url"):
            pdf_map[entry["pdf_url"]] = lid
    return pdf_map


def upgrade_pdf_links(body: str, self_id: str, pdf_map: dict[str, str]) -> tuple[str, int]:
    """Pass 4: replace knesset PDF cross-law links with ./LAWID.md where available.
    Returns (updated_body, number_of_links_upgraded)."""
    count = 0

    def _replace(m: re.Match) -> str:
        nonlocal count
        title = m.group(1)
        pdf_url = m.group(2)
        target_id = pdf_map.get(pdf_url)
        if target_id and target_id != self_id:
            count += 1
            return f"[{title}](./{target_id}.md)"
        return m.group(0)

    body = _KNESSET_PDF_LINK.sub(_replace, body)
    return body, count


# ─── Main entry ───────────────────────────────────────────────────────────────

def resolve_one(md_path: Path, pdf_map: dict[str, str] | None = None) -> None:
    """Run all passes on md_path in-place (passes 1–4)."""
    if pdf_map is None:
        pdf_map = build_inter_law_index(md_path.parent)
    text = md_path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)

    body, section_map = add_section_anchors(body)
    body = linkify_section_refs(body, section_map)

    margin_notes = collect_margin_notes(body)
    body = inject_margin_note_index(body, margin_notes)

    body, inter_fixed = upgrade_pdf_links(body, md_path.stem, pdf_map)

    logging.info(
        "  link-resolve: %d section anchors, %d margin notes, %d PDF links upgraded",
        len(section_map),
        len(margin_notes),
        inter_fixed,
    )
    md_path.write_text(fm + body, encoding="utf-8")


def main(law_ids: list[str] | None = None, relink_all: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if law_ids:
        targets = [LAWS_DIR / f"{lid}.md" for lid in law_ids]
    elif relink_all:
        targets = sorted(LAWS_DIR.glob("*.md"))
    else:
        logging.error("Specify --law-id <id> or --all")
        return 1

    pdf_map = build_inter_law_index(LAWS_DIR)
    logging.info("inter-law index: %d converted laws with PDF URLs", len(pdf_map))

    for path in targets:
        if not path.exists() or path.stem in ("index", "_index", "placeholder"):
            continue
        logging.info("link-resolve: %s", path.name)
        resolve_one(path, pdf_map)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--law-id", action="append", dest="law_ids",
                        help="Process specific law_id (repeatable)")
    parser.add_argument("--all", action="store_true", dest="relink_all",
                        help="Re-run on all converted laws")
    args = parser.parse_args()
    raise SystemExit(main(law_ids=args.law_ids, relink_all=args.relink_all))
