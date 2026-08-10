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


def convert_one(doc, xml_bytes: bytes, meta_row: dict, own_slug: str, batch_slugs: frozenset[str],
                 batch_known_anchors: dict[str, frozenset[str]]
                 ) -> tuple[str, list[tuple[str, str | None]], list[validate.ValidationError]]:
    md, internal_links = render.render(doc, retrieved_at=meta_row.get("fetched_at"),
                                        own_slug=own_slug, batch_slugs=batch_slugs,
                                        batch_known_anchors=batch_known_anchors)
    errors = validate.validate(doc, xml_bytes, md)
    return md, internal_links, errors


def main(only_slug: str | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    all_rows = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    all_rows = [r for r in all_rows if r.get("status") == "fetched"]
    rows = [r for r in all_rows if r.get("slug") == only_slug] if only_slug else all_rows

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # UKLINK-01: every fetched slug is a valid internal-link target, whether or
    # not it's the one this invocation is (re)converting -- a `--slug` re-run of
    # one Act must still resolve citations to its batch-mates the same way a
    # full run would, or a single-Act fix-up would silently regress its links
    # to external. Any slug that fails to actually write a file below gets
    # caught by check_cross_references (BROKEN_INTERNAL_LINK), not silently
    # trusted here.
    batch_slugs = frozenset(r["slug"] for r in all_rows)

    # First pass over the WHOLE fetched batch (not just `rows`, which may be
    # narrowed by --slug): parse every doc once and compute its known_anchors,
    # so a cross-document citation can be checked against its actual target's
    # anchors instead of trusted optimistically (see render.py's
    # batch_known_anchors / the Parliament Act 1911 -> Fixed-term Parliaments
    # Act 2011 s.7(2) case that motivated this -- a subsection since omitted
    # entirely from the revised text, so the citation's own SectionRef no
    # longer matches any real anchor in the target document).
    docs: dict[str, tuple["clml.LegalDoc", bytes]] = {}
    batch_known_anchors: dict[str, frozenset[str]] = {}
    parse_errors: dict[str, clml.UnknownElementError] = {}
    for row in all_rows:
        try:
            xml_bytes = (PROJECT_DIR / row["xml_path"]).read_bytes()
            doc = clml.parse(xml_bytes)
        except clml.UnknownElementError as e:
            # A batch-mate's own parse failure shouldn't abort a --slug run
            # targeting a different, healthy doc; that batch-mate's slug just
            # falls back to the pre-existing optimistic cross-doc behavior
            # (no verified known_anchors), and if it's the row actually being
            # converted below, the per-row handling there reports it properly.
            parse_errors[row["slug"]] = e
            continue
        docs[row["slug"]] = (doc, xml_bytes)
        batch_known_anchors[row["slug"]] = render.compute_known_anchors(doc)

    ok, failed = 0, 0
    rendered: dict[str, str] = {}
    links_by_slug: dict[str, list[tuple[str, str | None]]] = {}
    for row in rows:
        slug = row["slug"]
        if slug in parse_errors:
            logging.error("%s: UNHANDLED ELEMENT: %s", slug, parse_errors[slug])
            failed += 1
            continue
        doc, xml_bytes = docs[slug]
        try:
            md, internal_links, errors = convert_one(doc, xml_bytes, row, slug, batch_slugs, batch_known_anchors)
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
