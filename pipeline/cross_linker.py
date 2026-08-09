#!/usr/bin/env python3
"""Pass 4 — Inter-law cross-linker.

Asks Gemini to extract all external law references from a converted .md file,
resolves them against the manifest, and rewrites the file with markdown links:

  - Laws already converted  →  ./law_id.md  (Docusaurus internal link)
  - Laws in manifest, not converted  →  Knesset PDF URL  (fallback)
  - Laws not in manifest  →  not linked

Returns law_ids that are in the manifest but not yet converted (for priority queueing).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
PROJECT_DIR = PIPELINE_DIR.parent
LAWS_DIR = PROJECT_DIR / "laws" / "israel"

_GEMINI_MODEL = "gemini-2.5-flash"

_EXTRACT_PROMPT = """\
You are analyzing an Israeli law document written in Hebrew.

Find every reference to an EXTERNAL law, ordinance (פקודה), regulation (תקנות), \
or order (צו) cited in this document.

Exclude:
- "חוק זה" / "לחוק זה" (this law / to this law)
- Section and subsection references (סעיף N, תקנה N)
- Regulations or orders issued under THIS law

For each external reference return a JSON object with keys:
  found_in_doc  — exact text as it appears in the document (may be short name or full name)
  official_name — full official registered Hebrew name with year, as on knesset.gov.il or nevo.co.il
  year_ce       — integer CE year, or null

Rules:
- found_in_doc must be a verbatim substring found in the document body
- official_name must be the FULL registered name even if only a nickname appears in the doc
  (e.g. "חוק הבזק" → "חוק התקשורת (בזק ושידורים), התשמ\"ב-1982")
- Deduplicate: if the same law appears in multiple forms, include it ONCE with the longest found_in_doc
- Return ONLY a valid JSON array, no markdown fences, no explanation

Document:
{text}
"""

# ─── Name normalisation ───────────────────────────────────────────────────────

_STRIP_YEAR = re.compile(r',?\s+ה?תש[א-ת\'"״"]+(?:-\d{4})?')
_STRIP_QUOTES = re.compile(r'["\'""״]')
_MULTI_SPACE = re.compile(r'\s+')


def _norm(s: str) -> str:
    s = _STRIP_YEAR.sub('', s)
    s = _STRIP_QUOTES.sub('', s)
    s = _MULTI_SPACE.sub(' ', s)
    return s.strip()


# ─── Manifest index ───────────────────────────────────────────────────────────

def build_manifest_index(manifest: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for entry in manifest:
        name = entry.get('name_he') or ''
        key = _norm(name)
        if key:
            index[key] = entry
    return index


# ─── Gemini extraction ────────────────────────────────────────────────────────

_CHUNK_SIZE = 80_000  # chars per Gemini call for very long documents


def _extract_refs_chunk(client, chunk: str) -> list[dict]:
    prompt = _EXTRACT_PROMPT.format(text=chunk)
    try:
        resp = client.models.generate_content(model=_GEMINI_MODEL, contents=prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r'^```[^\n]*\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw)
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        return []
    except Exception as exc:
        logging.warning("cross_link extract_refs failed: %s", exc)
        return []


def extract_refs(client, body: str) -> list[dict]:
    """Extract external law refs from body, chunking if necessary."""
    if not body.strip():
        return []

    if len(body) <= _CHUNK_SIZE:
        return _extract_refs_chunk(client, body)

    # Long document: chunk and deduplicate by official_name
    all_refs: list[dict] = []
    seen_official: set[str] = set()
    for start in range(0, len(body), _CHUNK_SIZE):
        chunk = body[start:start + _CHUNK_SIZE]
        for ref in _extract_refs_chunk(client, chunk):
            key = _norm(ref.get('official_name') or ref.get('found_in_doc') or '')
            if key and key not in seen_official:
                seen_official.add(key)
                all_refs.append(ref)
    return all_refs


# ─── Resolution ──────────────────────────────────────────────────────────────

def resolve_refs(
    refs: list[dict],
    index: dict[str, dict],
    converted_ids: set[str],
) -> list[dict]:
    resolved = []
    seen_ids: set[str] = set()

    for ref in refs:
        found = (ref.get('found_in_doc') or '').strip()
        official = (ref.get('official_name') or found).strip()
        if not found:
            continue

        entry = index.get(_norm(official))
        if entry is None:
            entry = index.get(_norm(found))
        if entry is None:
            logging.debug("cross_link: no match for %r", official)
            continue

        law_id = str(entry.get('law_id') or entry.get('bill_id') or '')
        if not law_id or law_id in seen_ids:
            continue
        seen_ids.add(law_id)

        if law_id in converted_ids:
            url = f'./{law_id}.md'
            is_internal = True
        else:
            url = entry.get('pdf_url') or ''
            is_internal = False

        if url:
            resolved.append({
                'found_in_doc': found,
                'official_name': official,
                'law_id': law_id,
                'url': url,
                'is_internal': is_internal,
            })

    return resolved


# ─── Linkification ───────────────────────────────────────────────────────────

# Strips previously injected cross-law links (idempotency)
_STRIP_INTERNAL = re.compile(r'\[([^\[\]]+)\]\(\./\d+\.md\)')
_STRIP_KNESSET = re.compile(r'\[([^\[\]]+)\]\(https://fs\.knesset\.gov\.il/[^\)]+\)')


def _strip_cross_links(body: str) -> str:
    body = _STRIP_INTERNAL.sub(lambda m: m.group(1), body)
    body = _STRIP_KNESSET.sub(lambda m: m.group(1), body)
    return body


def linkify_body(body: str, resolved: list[dict]) -> str:
    if not resolved:
        return body

    body = _strip_cross_links(body)

    # Longest match first — avoids short names clobbering substrings of longer ones
    items = sorted(resolved, key=lambda r: len(r['found_in_doc']), reverse=True)

    for item in items:
        text = item['found_in_doc']
        url = item['url']
        pattern = re.compile(rf'(?<!\[){re.escape(text)}(?!\]\()')
        body = pattern.sub(f'[{text}]({url})', body)

    return body


# ─── Main entry ──────────────────────────────────────────────────────────────

def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith('---'):
        return '', text
    end = text.find('\n---', 3)
    if end == -1:
        return '', text
    split = end + 4
    if split < len(text) and text[split] == '\n':
        split += 1
    return text[:split], text[split:]


def cross_link_one(md_path: Path, client, manifest: list[dict]) -> list[str]:
    """Cross-link one law file in-place. Returns law_ids in manifest but not yet converted."""
    text = md_path.read_text(encoding='utf-8')
    fm, body = _split_frontmatter(text)

    # Strip footer + Sidenotes before sending to Gemini
    body_for_gemini = re.sub(r'\n+---\n+\[מסמך המקור.*$', '', body, flags=re.DOTALL)
    body_for_gemini = re.sub(r'\n+## Sidenotes\n.*$', '', body_for_gemini, flags=re.DOTALL)

    # Build set of already-converted law_ids (this dir + done/ subdir)
    converted_ids: set[str] = {
        p.stem for p in md_path.parent.glob('*.md')
        if p.stem not in ('index', 'placeholder')
    }
    done_dir = md_path.parent / 'done'
    if done_dir.exists():
        converted_ids |= {p.stem for p in done_dir.glob('*.md')}

    index = build_manifest_index(manifest)
    refs = extract_refs(client, body_for_gemini)

    if not refs:
        return []

    resolved = resolve_refs(refs, index, converted_ids)

    n_internal = sum(1 for r in resolved if r['is_internal'])
    n_fallback = len(resolved) - n_internal
    logging.info(
        "  cross_link %s: %d refs → %d internal, %d knesset fallback",
        md_path.name, len(refs), n_internal, n_fallback,
    )

    if resolved:
        body = linkify_body(body, resolved)
        md_path.write_text(fm + body, encoding='utf-8')

    return [r['law_id'] for r in resolved if not r['is_internal']]


def relink_all(client, manifest: list[dict], laws_dir: Path = LAWS_DIR) -> None:
    """Re-run cross_link_one on every converted law (useful after new batch lands)."""
    targets = sorted(laws_dir.glob('*.md'))
    for path in targets:
        if path.stem in ('index', 'placeholder'):
            continue
        cross_link_one(path, client, manifest)
