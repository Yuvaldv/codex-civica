#!/usr/bin/env python3
"""Layer 2 — Tesseract OCR with word-level layout.

For each PDF in data/raw/israel/manifest.json, renders every page to a PNG
at DPI, runs Tesseract (Hebrew) twice per page:
  1. text mode -> plain text per page (concatenated with form-feeds)
  2. tsv  mode -> word-level layout (bbox + confidence)

Outputs (alongside the source PDF):
  <bill_id>.ocr.txt          — UTF-8 text, form-feed (\\f) between pages
  <bill_id>.ocr_layout.json  — {bill_id, pdf, dpi, pages: [{page, width_px,
                                  height_px, words: [{x,y,w,h,conf,text,
                                  block,par,line,word}]}]}
"""

import argparse
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz  # pymupdf

DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "israel"
MANIFEST_PATH = DATA_DIR / "manifest.json"
DPI = 300
TESS_LANG = "heb"

TSV_HEADERS = (
    "level page_num block_num par_num line_num word_num "
    "left top width height conf text"
).split()


def render_page_to_png(pdf_path: Path, page_idx: int, dpi: int) -> tuple[Path, int, int]:
    """Render one PDF page to a temp PNG. Returns (path, width_px, height_px)."""
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_idx]
        scale = dpi / 72.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        fd, tmp_name = tempfile.mkstemp(suffix=".png", prefix=f"ocr_{pdf_path.stem}_p{page_idx}_")
        # mkstemp opens the file; close the fd then let pymupdf write to the path.
        import os
        os.close(fd)
        tmp = Path(tmp_name)
        pix.save(str(tmp))
        return tmp, pix.width, pix.height
    finally:
        doc.close()


def tesseract_text(image: Path, lang: str) -> str:
    """Run `tesseract <image> - -l <lang>` and return stdout."""
    res = subprocess.run(
        ["tesseract", str(image), "-", "-l", lang, "--psm", "6"],
        capture_output=True, text=True, check=True,
    )
    return res.stdout


def tesseract_tsv(image: Path, lang: str) -> str:
    """Run tesseract with tsv config and return stdout (TSV)."""
    res = subprocess.run(
        ["tesseract", str(image), "-", "-l", lang, "--psm", "6", "tsv"],
        capture_output=True, text=True, check=True,
    )
    return res.stdout


def parse_tsv_words(tsv: str) -> list[dict]:
    """Parse Tesseract TSV output into a list of word dicts.

    Filters to rows where text is non-empty (i.e. actual words, not block/line markers).
    """
    lines = tsv.strip().split("\n")
    if not lines:
        return []
    headers = lines[0].split("\t")
    if headers != TSV_HEADERS:
        logging.warning("Unexpected TSV header: %r", headers)

    words = []
    for raw in lines[1:]:
        parts = raw.split("\t")
        if len(parts) != len(headers):
            continue
        row = dict(zip(headers, parts))
        text = row.get("text", "").strip()
        if not text:
            continue
        try:
            words.append({
                "block": int(row["block_num"]),
                "par": int(row["par_num"]),
                "line": int(row["line_num"]),
                "word": int(row["word_num"]),
                "x": int(row["left"]),
                "y": int(row["top"]),
                "w": int(row["width"]),
                "h": int(row["height"]),
                "conf": float(row["conf"]),
                "text": text,
            })
        except (KeyError, ValueError) as e:
            logging.warning("Skipping malformed TSV row: %s", e)
    return words


def process_pdf(pdf_path: Path, bill_id: int, dpi: int, lang: str) -> tuple[str, dict]:
    """OCR every page of pdf_path. Returns (full_text, layout_dict)."""
    doc = fitz.open(pdf_path)
    n_pages = len(doc)
    doc.close()

    all_text_parts: list[str] = []
    pages_layout: list[dict] = []

    for page_idx in range(n_pages):
        logging.info("  page %d/%d", page_idx + 1, n_pages)
        png_path, w_px, h_px = render_page_to_png(pdf_path, page_idx, dpi)
        try:
            text = tesseract_text(png_path, lang)
            tsv = tesseract_tsv(png_path, lang)
            words = parse_tsv_words(tsv)
            all_text_parts.append(text)
            pages_layout.append({
                "page": page_idx,
                "width_px": w_px,
                "height_px": h_px,
                "words": words,
            })
        finally:
            try:
                png_path.unlink()
            except OSError:
                pass

    full_text = "\f".join(all_text_parts)
    layout = {
        "bill_id": bill_id,
        "pdf": str(pdf_path),
        "dpi": dpi,
        "lang": lang,
        "pages": pages_layout,
    }
    return full_text, layout


def main(force: bool = False, bill_ids: list[str] | None = None, dpi: int = DPI) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not shutil.which("tesseract"):
        logging.error("tesseract not found on PATH. Install tesseract-ocr.")
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

        txt_out = DATA_DIR / f"{bill_id}.ocr.txt"
        json_out = DATA_DIR / f"{bill_id}.ocr_layout.json"

        if txt_out.exists() and json_out.exists() and not force:
            logging.info("skip (exists): %s", txt_out.name)
            successes += 1
            continue

        logging.info("OCR: %s (%d dpi)", pdf_path.name, dpi)
        try:
            text, layout = process_pdf(pdf_path, bill_id, dpi, TESS_LANG)
        except subprocess.CalledProcessError as e:
            logging.error("tesseract failed for %s: %s", pdf_path, e.stderr)
            continue

        txt_out.write_text(text, encoding="utf-8")
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(layout, f, ensure_ascii=False, indent=2)
        logging.info("  wrote %s (%d chars) and %s (%d pages)",
                     txt_out.name, len(text), json_out.name, len(layout["pages"]))
        successes += 1

    print(f"Done. {successes}/{len(selected)} OCR'd.")
    return 0 if successes == len(selected) else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--dpi", type=int, default=DPI, help=f"Render DPI (default {DPI})")
    parser.add_argument(
        "--bill-id",
        action="append",
        default=None,
        dest="bill_ids",
        help="Only process specific bill_id (repeatable)",
    )
    args = parser.parse_args()
    raise SystemExit(main(force=args.force, bill_ids=args.bill_ids, dpi=args.dpi))
