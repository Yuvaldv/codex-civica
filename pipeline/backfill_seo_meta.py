"""Backfill `title` + `description` frontmatter onto already-converted laws.

reconcile.build_frontmatter() now emits both fields for new conversions;
this is a one-time pass for laws converted before that change. Deterministic
(no LLM) — derives description from title/publication_date/law_validity
already present in each file's own frontmatter.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reconcile import build_seo_description  # noqa: E402

LAWS_DIR = Path(__file__).parent.parent / "laws" / "israel"
SKIP = {"placeholder.md", "index.md", "_index.md"}


def get_field(text: str, name: str) -> str | None:
    m = re.search(rf'^{name}:\s*"?([^"\n]*)"?\s*$', text, re.MULTILINE)
    return m.group(1).strip() if m else None


def fix_file(path: Path, dry_run: bool = False) -> str:
    text = path.read_text(encoding="utf-8")

    if re.search(r"^description:", text, re.MULTILINE):
        return "ok (already has description)"

    title = get_field(text, "title_he")
    if not title:
        return "skip (no title_he)"
    pub_date = get_field(text, "publication_date") or ""
    law_validity = get_field(text, "law_validity")

    description = build_seo_description(title, pub_date, law_validity).replace('"', '\\"')

    new_lines = []
    if not re.search(r"^title:", text, re.MULTILINE):
        new_lines.append(f'title: "{title}"')
    new_lines.append(f'description: "{description}"')
    insertion = "\n".join(new_lines) + "\n"

    # Insert right after the title_he line
    new_text = re.sub(
        r'(^title_he:\s*"[^"\n]*"\s*\n)',
        r"\1" + insertion,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if new_text == text:
        return "skip (title_he line not matched)"

    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return "fixed"


def main(dry_run: bool = False) -> None:
    files = sorted(p for p in LAWS_DIR.glob("*.md") if p.name not in SKIP)
    results: dict[str, list[str]] = {}
    for path in files:
        status = fix_file(path, dry_run=dry_run)
        results.setdefault(status, []).append(path.name)

    for status, names in sorted(results.items()):
        print(f"\n[{status}] ({len(names)} files)")
        if status not in ("ok (already has description)", "fixed"):
            for n in names:
                print(f"  {n}")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("DRY RUN — no files written\n")
    main(dry_run=dry)
