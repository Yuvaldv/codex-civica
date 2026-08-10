#!/usr/bin/env python3
"""CLML XML (data/raw/uk/xml/) -> Markdown (laws/uk/england/). Deterministic:
no LLM anywhere in this path (CLML is a single authoritative witness, not a
noisy one -- there is nothing to reconcile).

Usage:
  python pipeline/uk/convert.py            # convert every manifest_uk.json entry
  python pipeline/uk/convert.py --slug ukpga-1998-42
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import clml  # noqa: E402
import render  # noqa: E402
import validate  # noqa: E402

PROJECT_DIR = Path(__file__).parent.parent.parent
MANIFEST_PATH = PROJECT_DIR / "data" / "raw" / "uk" / "manifest_uk.json"
OUT_DIR = PROJECT_DIR / "laws" / "uk" / "england"


def convert_one(xml_path: Path, meta_row: dict) -> tuple[str, list[validate.ValidationError]]:
    xml_bytes = xml_path.read_bytes()
    doc = clml.parse(xml_bytes)
    md = render.render(doc, retrieved_at=meta_row.get("fetched_at"))
    errors = validate.validate(doc, xml_bytes, md)
    return md, errors


def main(only_slug: str | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = [r for r in rows if r.get("status") == "fetched"]
    if only_slug:
        rows = [r for r in rows if r.get("slug") == only_slug]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ok, failed = 0, 0
    for row in rows:
        slug = row["slug"]
        xml_path = PROJECT_DIR / row["xml_path"]
        try:
            md, errors = convert_one(xml_path, row)
        except clml.UnknownElementError as e:
            logging.error("%s: UNHANDLED ELEMENT: %s", slug, e)
            failed += 1
            continue

        out_path = OUT_DIR / f"{slug}.md"
        out_path.write_text(md, encoding="utf-8")

        if errors:
            failed += 1
            logging.error("%s: %d validation error(s)", slug, len(errors))
            for err in errors[:5]:
                logging.error("  %s", err)
            if len(errors) > 5:
                logging.error("  ... and %d more", len(errors) - 5)
        else:
            ok += 1
            logging.info("%s: OK (%d chars)", slug, len(md))

    logging.info("done: %d ok, %d failed", ok, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", help="Convert a single manifest entry by slug")
    args = parser.parse_args()
    raise SystemExit(main(only_slug=args.slug))
