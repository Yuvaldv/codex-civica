#!/usr/bin/env python3
"""Country-blind frontmatter helpers.

Owns the single canonical YAML-frontmatter splitter shared by every country
pipeline. Stdlib only — this module must never import a country module
(`reconcile`, `link_resolver`, `cross_linker`, `batch_import`), never read
`pipeline/.env`, and never reference an API key.
"""
from __future__ import annotations


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


def render_frontmatter(lines: list[str]) -> str:
    """Wrap pre-rendered YAML lines in --- fences. Trailing newline included.

    Callers own field selection, ordering, and value formatting; this owns only
    the block shape. Deliberately thin — see CLAUDE.md 'do not over-abstract'.
    """
    return "\n".join(["---", *lines, "---", ""])


def quote(value: str) -> str:
    """Double-quote a scalar, escaping embedded double quotes."""
    return '"' + value.replace('"', '\\"') + '"'
