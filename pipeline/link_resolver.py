#!/usr/bin/env python3
"""Stage 4 — Intra-document linker.

Pass 1: Adds <span id="section-N" /> anchors to top-level numbered section headings.
Pass 2: Replaces intra-law section references (סעיף N) with same-page anchor links.
Pass 3: Collects margin-note blockquotes and appends an indexed list under
        ## Sidenotes with links back to the section each note belongs to.

Inter-law (cross-document) hyperlinks are handled outside the pipeline.
"""
from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
LAWS_DIR = PIPELINE_DIR.parent / "laws" / "israel"


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


# ─── Main entry ───────────────────────────────────────────────────────────────

def resolve_one(md_path: Path) -> None:
    """Run intra-document passes on md_path in-place (passes 1–3)."""
    text = md_path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)

    body, section_map = add_section_anchors(body)
    body = linkify_section_refs(body, section_map)

    margin_notes = collect_margin_notes(body)
    body = inject_margin_note_index(body, margin_notes)

    logging.info(
        "  link-resolve: %d section anchors, %d margin notes indexed",
        len(section_map),
        len(margin_notes),
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

    for path in targets:
        if not path.exists() or path.stem in ("index", "_index", "placeholder"):
            continue
        logging.info("link-resolve: %s", path.name)
        resolve_one(path)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--law-id", action="append", dest="law_ids",
                        help="Process specific law_id (repeatable)")
    parser.add_argument("--all", action="store_true", dest="relink_all",
                        help="Re-run on all converted laws")
    args = parser.parse_args()
    raise SystemExit(main(law_ids=args.law_ids, relink_all=args.relink_all))
