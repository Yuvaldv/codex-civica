#!/usr/bin/env python3
"""Track 2 (conjecture path): Docling-based PDF→Markdown conversion.

Reads the same data/raw/israel/manifest.json as track 1 (convert.py) and writes
markdown files to laws/israel/track2/ for side-by-side QA.

This script is intentionally minimal — it does not apply our YAML frontmatter or
slug logic. Output is the raw Docling export so we can evaluate the parser's
fidelity in isolation, separately from any post-processing we layer on top.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from docling.document_converter import DocumentConverter

DEFAULT_MANIFEST = Path(__file__).parent.parent / "data" / "raw" / "israel" / "manifest.json"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "laws" / "israel" / "track2"


def convert_one(converter: DocumentConverter, pdf_path: Path, out_path: Path) -> bool:
    try:
        result = converter.convert(str(pdf_path))
    except Exception as exc:
        logging.error("Docling failed on %s: %s", pdf_path.name, exc)
        return False
    md = result.document.export_to_markdown()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return True


def main(manifest_path: Path, output_dir: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not manifest_path.exists():
        logging.error("Manifest not found: %s", manifest_path)
        raise SystemExit(1)

    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    logging.info("Track 2 (Docling) — converting %d laws", len(entries))

    converter = DocumentConverter()
    output_dir.mkdir(parents=True, exist_ok=True)

    ok, fail, skipped = 0, 0, 0
    for entry in entries:
        bill_id = entry["bill_id"]
        pdf_path = entry.get("pdf_path")
        if not pdf_path or not Path(pdf_path).exists():
            logging.warning("No PDF for bill %s — skipping", bill_id)
            skipped += 1
            continue
        out_path = output_dir / f"{bill_id}.md"
        if convert_one(converter, Path(pdf_path), out_path):
            logging.info("Wrote %s", out_path)
            ok += 1
        else:
            fail += 1

    print(f"Done. Converted: {ok}, Skipped (no PDF): {skipped}, Errors: {fail}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    main(Path(args.input), Path(args.output))
