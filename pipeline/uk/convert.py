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


def convert_one(xml_path: Path, meta_row: dict, own_slug: str, batch_slugs: frozenset[str]
                 ) -> tuple[str, list[tuple[str, str | None]], list[validate.ValidationError]]:
    xml_bytes = xml_path.read_bytes()
    doc = clml.parse(xml_bytes)
    md, internal_links = render.render(doc, retrieved_at=meta_row.get("fetched_at"),
                                        own_slug=own_slug, batch_slugs=batch_slugs)
    errors = validate.validate(doc, xml_bytes, md)
    return md, internal_links, errors


def main(only_slug: str | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = [r for r in rows if r.get("status") == "fetched"]
    if only_slug:
        rows = [r for r in rows if r.get("slug") == only_slug]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # UKLINK-01: every fetched slug is a valid internal-link target, whether or
    # not it's the one this invocation is (re)converting -- a `--slug` re-run of
    # one Act must still resolve citations to its batch-mates the same way a
    # full run would, or a single-Act fix-up would silently regress its links
    # to external. Any slug that fails to actually write a file below gets
    # caught by check_cross_references (BROKEN_INTERNAL_LINK), not silently
    # trusted here.
    batch_slugs = frozenset(r["slug"] for r in json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
                             if r.get("status") == "fetched")

    ok, failed = 0, 0
    rendered: dict[str, str] = {}
    links_by_slug: dict[str, list[tuple[str, str | None]]] = {}
    for row in rows:
        slug = row["slug"]
        xml_path = PROJECT_DIR / row["xml_path"]
        try:
            md, internal_links, errors = convert_one(xml_path, row, slug, batch_slugs)
        except clml.UnknownElementError as e:
            logging.error("%s: UNHANDLED ELEMENT: %s", slug, e)
            failed += 1
            continue

        out_path = OUT_DIR / f"{slug}.md"
        out_path.write_text(md, encoding="utf-8")
        rendered[slug] = md
        links_by_slug[slug] = internal_links

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

    # Batch-level check: needs every rendered doc at once, so it can't run
    # inside the per-doc loop above. A `--slug` single-doc run only has that
    # one doc's markdown in `rendered`, so it can only check that doc's own
    # self-anchors -- cross-doc link checks need the full batch present on
    # disk already; re-read those from OUT_DIR so a `--slug` re-run still
    # validates against its batch-mates instead of silently skipping them.
    full_rendered = dict(rendered)
    if only_slug:
        for slug in batch_slugs - rendered.keys():
            existing = OUT_DIR / f"{slug}.md"
            if existing.exists():
                full_rendered[slug] = existing.read_text(encoding="utf-8")
    link_errors = validate.check_cross_references(full_rendered, links_by_slug)
    if link_errors:
        failed += len(link_errors)
        logging.error("cross-reference check: %d broken/silent reference(s)", len(link_errors))
        for err in link_errors:
            logging.error("  %s", err)

    logging.info("done: %d ok, %d failed", ok, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", help="Convert a single manifest entry by slug")
    args = parser.parse_args()
    raise SystemExit(main(only_slug=args.slug))
