#!/usr/bin/env python3
"""Stage 4 — Cross-reference linker.

Pass 1: Adds {#section-N} anchors to top-level numbered section headings.
Pass 2: Replaces intra-law section references (סעיף N) with same-page anchor links.
Pass 3: Replaces inter-law name citations with links to already-converted laws.
Pass 4: Collects margin-note blockquotes and appends an indexed list under
        ## הערות שוליים with links back to the section each note belongs to.

Returns a list of law_ids cited but not yet converted, so the caller
can trigger pipeline processing for them.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
DATA_DIR = PIPELINE_DIR.parent / "data" / "raw" / "israel"
LAWS_DIR = PIPELINE_DIR.parent / "laws" / "israel"
MANIFEST_LAWS_PATH = DATA_DIR / "manifest_laws.json"

_HE = r"א-ת"  # Hebrew letter range

# Hebrew year suffix: ה?תשXXX"X-YYYY (handles ASCII " and Hebrew gershayim ״)
_YEAR_PAT = rf"ה?תש[{_HE}]{{0,4}}[\"״״][{_HE}][-–—]\d{{4}}"

_SELF_REF = re.compile(rf'חוק\s+(?:זה|האמור|הנ"ל|הנדון)')


def _norm_quotes(s: str) -> str:
    return (
        s.replace("״", '"')
         .replace("׳", "'")
         .replace("“", '"').replace("”", '"')
         .replace("‘", "'").replace("’", "'")
    )


def _extract_year(s: str) -> int | None:
    m = re.search(r"\d{4}", s)
    return int(m.group()) if m else None


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


# ─── Pass 3: Inter-law links ──────────────────────────────────────────────────

_CITE_RE = re.compile(
    rf"(?<!\[)"
    rf"((?:חוק(?:-יסוד)?|פקודת|תקנות|דבר\s+המלך)[^,\n\[\]{{}}]{{3,80}}?)"
    rf",\s*({_YEAR_PAT})",
)

# Basic Laws without year: חוק-יסוד: X
_BASIC_RE = re.compile(
    rf"(?<!\[)(חוק-יסוד:\s*[{_HE} \"'()\-]{{3,60}}?)(?=[,.\s)\[\n]|$)",
)


def build_law_index(manifest: list[dict]) -> dict:
    """Build name-based lookups: (base_name, year) → (law_id, name_he)."""
    by_year: dict[tuple[str, int], tuple[int, str]] = {}
    by_exact: dict[str, tuple[int, str]] = {}

    for entry in manifest:
        law_id = entry.get("law_id") or entry.get("bill_id")
        name_he = (entry.get("name_he") or "").strip()
        if not law_id or not name_he:
            continue
        lid = int(law_id)
        norm = _norm_quotes(name_he)
        by_exact[norm] = (lid, name_he)

        m = re.search(rf",\s*({_YEAR_PAT})$", norm)
        if m:
            base = norm[: m.start()].strip()
            year = _extract_year(m.group(1))
            if year:
                by_year[(base, year)] = (lid, name_he)

    return {"by_year": by_year, "by_exact": by_exact}


def linkify_law_refs(
    body: str,
    law_index: dict,
    converted_set: set[str],
) -> tuple[str, list[int]]:
    """Replace cited law names with links. Returns (body, unresolved_law_ids)."""
    by_year = law_index["by_year"]
    by_exact = law_index["by_exact"]
    unresolved: list[int] = []
    seen: set[int] = set()

    def _lookup(base: str, year: int | None) -> tuple[int, str] | None:
        norm = _norm_quotes(base.strip())
        if year:
            hit = by_year.get((norm, year))
            if not hit:
                # Strip amendment qualifier: "(תיקון מס' N)"
                stripped = re.sub(r"\s*\(תיקון[^)]*\)", "", norm).strip()
                hit = by_year.get((stripped, year))
        else:
            hit = by_exact.get(norm)
        return hit

    def _make_link(full: str, base: str, year: int | None) -> str:
        if _SELF_REF.search(base):
            return full
        hit = _lookup(base, year)
        if not hit:
            return full
        lid, _ = hit
        if str(lid) in converted_set:
            return f"[{full}](./{lid})"
        if lid not in seen:
            unresolved.append(lid)
            seen.add(lid)
        return full

    def _replace_cite(m: re.Match) -> str:
        return _make_link(m.group(0), m.group(1), _extract_year(m.group(2)))

    def _replace_basic(m: re.Match) -> str:
        return _make_link(m.group(0), m.group(1), None)

    out = []
    for line in body.split("\n"):
        if re.match(r"^#{1,6} ", line) or line.startswith(">"):
            out.append(line)
            continue
        line = _CITE_RE.sub(_replace_cite, line)
        line = _BASIC_RE.sub(_replace_basic, line)
        out.append(line)

    return "\n".join(out), unresolved


# ─── Pass 4: Margin note index ───────────────────────────────────────────────

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

def resolve_one(
    md_path: Path,
    law_index: dict,
    converted_set: set[str],
) -> list[int]:
    """Run all passes on md_path in-place. Returns unresolved inter-law law_ids."""
    text = md_path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)

    body, section_map = add_section_anchors(body)
    body = linkify_section_refs(body, section_map)
    body, unresolved = linkify_law_refs(body, law_index, converted_set)

    margin_notes = collect_margin_notes(body)
    body = inject_margin_note_index(body, margin_notes)

    logging.info(
        "  link-resolve: %d section anchors, %d unresolved inter-law refs, %d margin notes indexed",
        len(section_map),
        len(unresolved),
        len(margin_notes),
    )
    md_path.write_text(fm + body, encoding="utf-8")
    return unresolved


def _load_manifest() -> list[dict]:
    with open(MANIFEST_LAWS_PATH, encoding="utf-8") as f:
        return json.load(f)


def main(law_ids: list[str] | None = None, relink_all: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    manifest = _load_manifest()
    law_index = build_law_index(manifest)
    converted_set = {
        p.stem for p in LAWS_DIR.glob("*.md")
        if p.stem not in ("index", "_index", "placeholder")
    }
    logging.info("Converted laws available for linking: %d", len(converted_set))

    if law_ids:
        targets = [LAWS_DIR / f"{lid}.md" for lid in law_ids]
    elif relink_all:
        targets = sorted(LAWS_DIR.glob("*.md"))
    else:
        logging.error("Specify --law-id <id> or --all")
        return 1

    all_unresolved: set[int] = set()
    for path in targets:
        if not path.exists() or path.stem in ("index", "_index", "placeholder"):
            continue
        logging.info("link-resolve: %s", path.name)
        unresolved = resolve_one(path, law_index, converted_set)
        all_unresolved.update(unresolved)

    if all_unresolved:
        logging.info(
            "Referenced but not yet converted — %d law_ids: %s%s",
            len(all_unresolved),
            sorted(all_unresolved)[:8],
            " ..." if len(all_unresolved) > 8 else "",
        )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--law-id", action="append", dest="law_ids",
                        help="Process specific law_id (repeatable)")
    parser.add_argument("--all", action="store_true", dest="relink_all",
                        help="Re-run on all converted laws")
    args = parser.parse_args()
    raise SystemExit(main(law_ids=args.law_ids, relink_all=args.relink_all))
