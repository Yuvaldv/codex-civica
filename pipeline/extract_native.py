#!/usr/bin/env python3
"""Layer 1 — Native PDF text extraction via pdftotext.

Reads data/raw/israel/manifest.json. For each entry with a pdf_path,
runs `pdftotext -layout -enc UTF-8` to produce <bill_id>.native.txt
alongside the source PDF.

Page boundaries are preserved as form-feed (\\f, 0x0C) characters,
which is pdftotext's default behavior.
"""

import argparse
import json
import logging
import shutil
import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "israel"
MANIFEST_PATH = DATA_DIR / "manifest.json"


def extract_one(pdf_path: Path, out_path: Path) -> bool:
    """Run `pdftotext -layout -enc UTF-8 <pdf> <out>`.

    Returns True on success, False on failure (errors are logged).
    """
    cmd = ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), str(out_path)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error("pdftotext failed for %s: %s", pdf_path, e.stderr.strip())
        return False


def main(force: bool = False, bill_ids: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not shutil.which("pdftotext"):
        logging.error("pdftotext not found on PATH. Install poppler-utils.")
        return 1

    if not MANIFEST_PATH.exists():
        logging.error("Manifest not found: %s", MANIFEST_PATH)
        return 1

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    selected = [e for e in manifest if e.get("pdf_path")]
    if bill_ids:
        wanted = set(bill_ids)
        selected = [e for e in selected if str(e["bill_id"]) in wanted]

    if not selected:
        logging.warning("No PDFs to process.")
        return 0

    successes = 0
    for entry in selected:
        bill_id = entry["bill_id"]
        pdf_path = Path(entry["pdf_path"])
        if not pdf_path.exists():
            logging.warning("PDF missing on disk: %s", pdf_path)
            continue

        out_path = DATA_DIR / f"{bill_id}.native.txt"
        if out_path.exists() and not force:
            logging.info("skip (exists): %s", out_path.name)
            successes += 1
            continue

        logging.info("extract: %s -> %s", pdf_path.name, out_path.name)
        if extract_one(pdf_path, out_path):
            successes += 1

    print(f"Done. {successes}/{len(selected)} extracted.")
    return 0 if successes == len(selected) else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite existing outputs")
    parser.add_argument(
        "--bill-id",
        action="append",
        default=None,
        dest="bill_ids",
        help="Only process specific bill_id (repeatable)",
    )
    args = parser.parse_args()
    raise SystemExit(main(force=args.force, bill_ids=args.bill_ids))
