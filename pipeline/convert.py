#!/usr/bin/env python3
"""Convert Knesset law PDFs to structured Markdown with YAML frontmatter."""

import argparse
import json
import logging
import re
import unicodedata
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


def extract_text(pdf_path: str) -> str:
    doc = fitz.open(str(pdf_path))
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()
    return "\n\n".join(pages_text)


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


def build_markdown(frontmatter_dict: dict, body_text: str, name_he: str) -> str:
    fm_str = yaml.dump(
        frontmatter_dict, allow_unicode=True, default_flow_style=False, sort_keys=False
    )
    body_clean = re.sub(r"\n{3,}", "\n\n", body_text.strip())
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
