"""Backfill source links on all converted law .md files.

Replaces:
  - plain text: מסמך המקור באתר הכנסת
  - old link:   [מסמך המקור באתר הכנסת](url)
  - missing entirely (e.g. 2000595)

With the new format (both image and text linked):
  [![מסמך PDF](/img/pdf-icon.svg)](url) [מסמך המקור באתר הכנסת](url)
"""
import re
import sys
from pathlib import Path

LAWS_DIR = Path(__file__).parent.parent / "laws" / "israel"
SKIP = {"placeholder.md", "index.md"}

IMAGE = "/img/pdf-icon.svg"


def source_link_block(url: str) -> str:
    return f"---\n\n[![מסמך PDF]({IMAGE})]({url}) [מסמך המקור באתר הכנסת]({url})"


def get_pdf_url(text: str) -> str | None:
    m = re.search(r"^source_pdf:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def fix_file(path: Path, dry_run: bool = False) -> str:
    text = path.read_text(encoding="utf-8")
    url = get_pdf_url(text)
    if not url:
        return "skip (no source_pdf)"

    new_block = source_link_block(url)

    # Pattern A: already the new format — nothing to do
    if f"[![מסמך PDF]({IMAGE})]({url})" in text:
        return "ok (already new format)"

    # Pattern B: old markdown link [מסמך המקור באתר הכנסת](any-url)
    old_link_pat = re.compile(
        r"\[מסמך המקור באתר הכנסת\]\([^)]+\)"
    )
    if old_link_pat.search(text):
        new_text = old_link_pat.sub(
            f"[![מסמך PDF]({IMAGE})]({url}) [מסמך המקור באתר הכנסת]({url})",
            text,
        )
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
        return "fixed (old link → new format)"

    # Pattern C: plain text line (standalone, not part of a section)
    # Must be on its own line and not preceded by [ (not already a link)
    plain_pat = re.compile(
        r"(?<!\[)מסמך המקור באתר הכנסת(?!\])"
    )
    if plain_pat.search(text):
        # Replace the plain text line with the full new block (including ---)
        # The surrounding --- may or may not be there; be conservative
        # Look for: --- \n\n מסמך המקור ...  or just the bare text
        block_pat = re.compile(
            r"---\s*\n\nמסמך המקור באתר הכנסת"
        )
        if block_pat.search(text):
            new_text = block_pat.sub(new_block, text)
        else:
            new_text = plain_pat.sub(
                f"[![מסמך PDF]({IMAGE})]({url}) [מסמך המקור באתר הכנסת]({url})",
                text,
            )
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
        return "fixed (plain text → new format)"

    # Pattern D: missing entirely — insert before ## Sidenotes or at end of body
    sidenotes_pat = re.compile(r"\n## Sidenotes\b")
    m = sidenotes_pat.search(text)
    if m:
        insert_at = m.start()
        new_text = text[:insert_at] + f"\n\n---\n\n[![מסמך PDF]({IMAGE})]({url}) [מסמך המקור באתר הכנסת]({url})\n" + text[insert_at:]
    else:
        new_text = text.rstrip() + f"\n\n---\n\n[![מסמך PDF]({IMAGE})]({url}) [מסמך המקור באתר הכנסת]({url})\n"

    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return "fixed (missing → added)"


def main(dry_run: bool = False) -> None:
    files = sorted(p for p in LAWS_DIR.glob("*.md") if p.name not in SKIP)
    results: dict[str, list[str]] = {}
    for path in files:
        status = fix_file(path, dry_run=dry_run)
        results.setdefault(status, []).append(path.name)

    for status, names in sorted(results.items()):
        print(f"\n[{status}] ({len(names)} files)")
        for n in names:
            print(f"  {n}")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("DRY RUN — no files written\n")
    main(dry_run=dry)
