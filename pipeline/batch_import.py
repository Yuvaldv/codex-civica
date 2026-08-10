#!/usr/bin/env python3
"""Factory-line batch importer for all Israeli laws.

For each unprocessed law in manifest_laws.json:
  1. extract_native.py  — pdftotext -> .native.txt
  2. extract_ocr.py     — Tesseract  -> .ocr.txt + .ocr_layout.json
  3. reconcile.py       — Gemini Flash -> laws/israel/{law_id}.md

Tracks progress in data/raw/israel/import_progress.json.
Deploys every DEPLOY_EVERY laws via `npm run deploy` in site/.

Usage:
  python pipeline/batch_import.py            # process next 5 laws
  python pipeline/batch_import.py --count 25 # process next 25 laws
  python pipeline/batch_import.py --status   # print progress summary
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from common import progress as _progress

PIPELINE_DIR = Path(__file__).parent
PROJECT_DIR = PIPELINE_DIR.parent
DATA_DIR = PROJECT_DIR / "data" / "raw" / "israel"
LAWS_DIR = PROJECT_DIR / "laws" / "israel"
SITE_DIR = PROJECT_DIR / "site"
MANIFEST_PATH = DATA_DIR / "manifest_laws.json"
PROGRESS_PATH = DATA_DIR / "import_progress.json"

DEFAULT_BATCH = 5
DEPLOY_EVERY = 25


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

def load_progress() -> dict:
    return _progress.load_progress(PROGRESS_PATH)


def save_progress(progress: dict) -> None:
    _progress.save_progress(PROGRESS_PATH, progress)


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        sys.exit(f"manifest_laws.json not found at {MANIFEST_PATH}. Run fetch_laws.py first.")
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest: list[dict]) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Pipeline stages (inline — avoids subprocess overhead for inner loop)
# ---------------------------------------------------------------------------

def stage_native(law_id: int, pdf_path: str, force: bool = False) -> bool:
    """Run pdftotext on the PDF. Returns True on success."""
    if not shutil.which("pdftotext"):
        logging.error("pdftotext not found. Install poppler-utils.")
        return False
    out = DATA_DIR / f"{law_id}.native.txt"
    if out.exists() and not force:
        return True
    cmd = ["pdftotext", "-layout", "-enc", "UTF-8", pdf_path, str(out)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logging.info("  native: %d chars", out.stat().st_size)
        return True
    except subprocess.CalledProcessError as e:
        logging.error("pdftotext failed: %s", e.stderr.strip())
        return False


def stage_ocr(law_id: int, pdf_path: str, dpi: int = 300, force: bool = False) -> bool:
    """Run Tesseract OCR page-by-page. Returns True on success."""
    if not shutil.which("tesseract"):
        logging.error("tesseract not found.")
        return False

    txt_out = DATA_DIR / f"{law_id}.ocr.txt"
    json_out = DATA_DIR / f"{law_id}.ocr_layout.json"
    if txt_out.exists() and json_out.exists() and not force:
        return True

    try:
        import fitz  # type: ignore
    except ImportError:
        logging.error("pymupdf not installed (needed for OCR page rendering).")
        return False

    all_text: list[str] = []
    pages_layout: list[dict] = []

    with fitz.open(pdf_path) as doc:
        n_pages = len(doc)
        for page_idx in range(n_pages):
            logging.info("  OCR page %d/%d", page_idx + 1, n_pages)
            page = doc[page_idx]
            scale = dpi / 72.0
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            fd, tmp_name = tempfile.mkstemp(suffix=".png", prefix=f"ocr_{law_id}_p{page_idx}_")
            os.close(fd)
            tmp = Path(tmp_name)
            pix.save(str(tmp))
            w_px, h_px = pix.width, pix.height

            try:
                res_txt = subprocess.run(
                    ["tesseract", str(tmp), "-", "-l", "heb", "--psm", "6"],
                    capture_output=True, text=True, check=True,
                )
                res_tsv = subprocess.run(
                    ["tesseract", str(tmp), "-", "-l", "heb", "--psm", "6", "tsv"],
                    capture_output=True, text=True, check=True,
                )
                all_text.append(res_txt.stdout)
                words = _parse_tsv(res_tsv.stdout)
                pages_layout.append({
                    "page": page_idx, "width_px": w_px, "height_px": h_px, "words": words,
                })
            except subprocess.CalledProcessError as e:
                logging.error("tesseract failed page %d: %s", page_idx, e.stderr)
                return False
            finally:
                try:
                    tmp.unlink()
                except OSError:
                    pass

    txt_out.write_text("\f".join(all_text), encoding="utf-8")
    layout = {"law_id": law_id, "pdf": pdf_path, "dpi": dpi, "lang": "heb", "pages": pages_layout}
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    logging.info("  OCR done: %d chars, %d pages", sum(len(t) for t in all_text), n_pages)
    return True


def _parse_tsv(tsv: str) -> list[dict]:
    headers = "level page_num block_num par_num line_num word_num left top width height conf text".split()
    words = []
    for line in tsv.strip().split("\n")[1:]:
        parts = line.split("\t")
        if len(parts) != len(headers):
            continue
        row = dict(zip(headers, parts))
        text = row.get("text", "").strip()
        if not text:
            continue
        try:
            words.append({
                "block": int(row["block_num"]), "par": int(row["par_num"]),
                "line": int(row["line_num"]), "word": int(row["word_num"]),
                "x": int(row["left"]), "y": int(row["top"]),
                "w": int(row["width"]), "h": int(row["height"]),
                "conf": float(row["conf"]), "text": text,
            })
        except (KeyError, ValueError):
            pass
    return words


def stage_reconcile(entry: dict, force: bool = False) -> bool:
    """Call Gemini Flash to reconcile native+OCR into markdown. Returns True on success."""
    sys.path.insert(0, str(PIPELINE_DIR))
    try:
        import reconcile
    except ImportError as e:
        logging.error("Cannot import reconcile.py: %s", e)
        return False

    law_id = entry.get("law_id") or entry.get("bill_id")
    out_path = LAWS_DIR / f"{law_id}.md"
    if out_path.exists() and not force:
        logging.info("  reconcile: skip (exists)")
        return True

    try:
        prompt = reconcile.load_prompt()
        api_key = reconcile.load_api_key()
        from google import genai  # type: ignore
        client = genai.Client(api_key=api_key)
        md = reconcile.reconcile_one(client, prompt, entry)
    except Exception as exc:  # noqa: BLE001
        logging.error("Gemini failed for law %s: %s", law_id, exc)
        return False

    if not md:
        logging.error("Empty Gemini response for law %s", law_id)
        return False

    src_url = entry.get("pdf_url") or ""
    if src_url:
        md = md.rstrip() + f'\n\n---\n\n[![מסמך PDF](/img/pdf-icon.svg)]({src_url}) [מסמך המקור באתר הכנסת]({src_url})\n'

    LAWS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    logging.info("  reconcile: wrote %s (%d chars)", out_path.name, len(md))
    return True


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

def deploy() -> bool:
    """Build and deploy the Docusaurus site."""
    logging.info("Deploying site...")
    env = {**os.environ, "USE_SSH": "true", "GIT_USER": "Yuvaldv"}
    try:
        result = subprocess.run(
            ["npm", "run", "deploy"],
            cwd=str(SITE_DIR),
            env=env,
            timeout=300,
            capture_output=False,
        )
        if result.returncode != 0:
            logging.error("Deploy failed with exit code %d", result.returncode)
            return False
        logging.info("Deploy successful.")
        return True
    except (subprocess.TimeoutExpired, OSError) as e:
        logging.error("Deploy error: %s", e)
        return False


# ---------------------------------------------------------------------------
# Main batch loop
# ---------------------------------------------------------------------------

def get_next_batch(manifest: list[dict], progress: dict, count: int) -> list[dict]:
    return _progress.get_next_batch(manifest, progress, count)


def print_status(manifest: list[dict], progress: dict) -> None:
    _progress.print_status(manifest, progress)


def _process_law(entry: dict, force: bool = False) -> bool:
    """Run native → OCR → reconcile for one law. Returns True on full success."""
    law_id = entry.get("law_id") or entry.get("bill_id")
    pdf_path = entry["pdf_path"]
    ok = stage_native(law_id, pdf_path, force=force)
    if ok:
        ok = stage_ocr(law_id, pdf_path, force=force)
    if ok:
        ok = stage_reconcile(entry, force=force)
    return ok


def run_batch(count: int = DEFAULT_BATCH, force: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    manifest = load_manifest()
    progress = load_progress()
    batch = get_next_batch(manifest, progress, count)

    if not batch:
        logging.info("No pending laws with PDFs. All done or no PDFs available.")
        print_status(manifest, progress)
        return 0

    # ── Phase 1: Convert the main batch ──────────────────────────────────────
    logging.info("Phase 1: converting %d laws...", len(batch))
    newly_done: list[dict] = []

    for entry in batch:
        law_id = entry.get("law_id") or entry.get("bill_id")
        name = entry.get("name_he", "")
        logging.info("--- %s: %s", law_id, name[:60])
        if _process_law(entry, force):
            progress["done"].append(law_id)
            newly_done.append(entry)
            # Remove from priority queue once converted
            progress["priority"] = [p for p in progress.get("priority", []) if str(p) != str(law_id)]
            logging.info("  OK: %s", law_id)
        else:
            progress["failed"].append(law_id)
            logging.warning("  FAILED: %s", law_id)
        save_progress(progress)

    if not newly_done:
        print_status(manifest, progress)
        return 0

    # ── Phase 2: Link-resolve newly converted laws ────────────────────────────
    try:
        import link_resolver
    except ImportError as exc:
        logging.error("Cannot import link_resolver: %s", exc)
        print_status(manifest, progress)
        return 0

    logging.info("Phase 2: link-resolving %d laws...", len(newly_done))
    pdf_map = link_resolver.build_inter_law_index(LAWS_DIR)
    for entry in newly_done:
        law_id = entry.get("law_id") or entry.get("bill_id")
        out_path = LAWS_DIR / f"{law_id}.md"
        if out_path.exists():
            link_resolver.resolve_one(out_path, pdf_map)

    # ── Phase 3: Cross-link (inter-law references via Gemini) ─────────────────
    try:
        import cross_linker
        import reconcile as _reconcile
        from google import genai as _genai  # type: ignore
        _cl_client = _genai.Client(api_key=_reconcile.load_api_key())
    except ImportError as exc:
        logging.warning("cross_linker unavailable, skipping: %s", exc)
        _cl_client = None

    if _cl_client is not None:
        logging.info("Phase 3: cross-linking %d laws...", len(newly_done))
        priority_set = set(str(x) for x in progress.get("priority", []))
        new_priority: list[str] = []

        for entry in newly_done:
            law_id = entry.get("law_id") or entry.get("bill_id")
            out_path = LAWS_DIR / f"{law_id}.md"
            if not out_path.exists():
                continue
            unresolved = cross_linker.cross_link_one(out_path, _cl_client, manifest)
            for uid in unresolved:
                if uid not in priority_set and uid not in set(str(x) for x in progress.get("done", [])):
                    new_priority.append(uid)
                    priority_set.add(uid)

        if new_priority:
            progress.setdefault("priority", [])
            progress["priority"].extend(new_priority)
            logging.info("Phase 3: queued %d referenced laws for priority conversion", len(new_priority))
            save_progress(progress)

    # ── Deploy check ──────────────────────────────────────────────────────────
    total_done = len(progress.get("done", []))
    prev_deployed = progress.get("total_deployed", 0)
    deploy_threshold = (prev_deployed // DEPLOY_EVERY + 1) * DEPLOY_EVERY
    if total_done >= deploy_threshold:
        logging.info("Reached %d laws — triggering deploy...", total_done)
        if deploy():
            progress["total_deployed"] = total_done
            save_progress(progress)
        else:
            logging.warning("Deploy failed — will retry next batch.")

    print_status(manifest, progress)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_BATCH, help="Laws to process per run")
    parser.add_argument("--force", action="store_true", help="Reprocess already-done laws")
    parser.add_argument("--status", action="store_true", help="Print progress and exit")
    args = parser.parse_args()

    if args.status:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
        manifest = load_manifest()
        progress = load_progress()
        print_status(manifest, progress)
    else:
        raise SystemExit(run_batch(count=args.count, force=args.force))
