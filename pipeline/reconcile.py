#!/usr/bin/env python3
"""Layer 3 — Gemini Flash reconciliation.

Reads the two textual witnesses produced by extract_native.py and
extract_ocr.py and asks Gemini 2.5 Flash to reconcile them into
deterministic Hebrew legal markdown using the prompt at
pipeline/prompts/track2_gemini.md.

Inputs (per bill_id):
  data/raw/israel/<bill_id>.native.txt
  data/raw/israel/<bill_id>.ocr.txt

Output:
  laws/israel/<bill_id>.md   (with YAML frontmatter for provenance)

The model is given two clearly-delimited source blocks (NATIVE and OCR)
and is instructed to return markdown only. Frontmatter is added by this
script — not by the model.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

PIPELINE_DIR = Path(__file__).parent
DATA_DIR = PIPELINE_DIR.parent / "data" / "raw" / "israel"
OUT_DIR = PIPELINE_DIR.parent / "laws" / "israel"
MANIFEST_PATH = DATA_DIR / "manifest.json"
MANIFEST_LAWS_PATH = DATA_DIR / "manifest_laws.json"
PROMPT_PATH = PIPELINE_DIR / "prompts" / "track2_gemini.md"

MODEL = "gemini-2.5-flash"


def load_prompt() -> str:
    if not PROMPT_PATH.exists():
        sys.exit(f"Prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def load_api_key() -> str:
    load_dotenv(PIPELINE_DIR / ".env")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set (expected in pipeline/.env or env)")
    return key


def assemble_request(prompt: str, native_text: str, ocr_text: str) -> str:
    """Build a single string with prompt + two delimited source blocks."""
    return (
        prompt
        + "\n\n=== NATIVE ===\n"
        + native_text
        + "\n=== END NATIVE ===\n\n"
        + "=== OCR ===\n"
        + ocr_text
        + "\n=== END OCR ===\n"
    )


def call_gemini(client: genai.Client, request: str) -> str:
    # Disable thinking on 2.5-flash. Reconciliation is mechanical and the
    # detailed prompt does the reasoning work. Thinking tokens otherwise
    # eat the output budget and cause silent truncation on long docs.
    response = client.models.generate_content(
        model=MODEL,
        contents=request,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="text/plain",
            max_output_tokens=65536,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    finish = None
    if response.candidates:
        finish = response.candidates[0].finish_reason
        if finish and str(finish) not in ("FinishReason.STOP", "STOP"):
            logging.warning("Gemini finish_reason=%s (output may be truncated)", finish)
    text = (response.text or "").strip()
    # Strip stray code fences if the model added them despite instructions.
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def build_frontmatter(entry: dict) -> str:
    """YAML frontmatter for provenance. Hebrew strings are double-quoted."""
    title = (entry.get("name_he") or "").replace('"', '\\"')
    pub_date = (entry.get("publication_date") or "")[:10]
    pdf_path = entry.get("pdf_path") or ""
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Determine ID field: prefer law_id (IsraelLaw system), fall back to bill_id
    law_id = entry.get("law_id")
    bill_id = entry.get("bill_id")
    id_line = f"law_id: {law_id}" if law_id else f"bill_id: {bill_id}"

    lines = ["---", id_line, f'title_he: "{title}"']

    if pub_date:
        lines.append(f"publication_date: {pub_date}")
    else:
        lines.append("publication_date: ~")

    latest = (entry.get("latest_publication_date") or "")[:10]
    if latest and latest != pub_date:
        lines.append(f"latest_publication_date: {latest}")

    if entry.get("is_basic_law"):
        lines.append("is_basic_law: true")
    if entry.get("is_budget_law"):
        lines.append("is_budget_law: true")
    if entry.get("law_validity"):
        lines.append(f'law_validity: "{entry["law_validity"]}"')

    category = entry.get("category") or ""
    if category:
        lines.append(f"category: {category}")

    # Tags from classifications
    classifications = entry.get("classifications") or []
    if classifications:
        tag_list = "\n".join(f'  - "{c["desc"]}"' for c in classifications if c.get("desc"))
        if tag_list:
            lines.append("law_tags:")
            lines.append(tag_list)

    # Ministry IDs (name mapping TODO — legacy GovMinistryID range)
    ministry_ids = entry.get("ministry_ids") or []
    if ministry_ids:
        lines.append(f"ministry_ids: {json.dumps(ministry_ids)}")

    lines += [
        f"source_pdf: {pdf_path}",
        "generated_by: pipeline/reconcile.py",
        f"model: {MODEL}",
        f"generated_at: {now}",
        "---",
        "",
    ]
    return "\n".join(lines)


def _id_key(entry: dict) -> str:
    """Return the primary ID string for an entry (law_id or bill_id)."""
    return str(entry.get("law_id") or entry.get("bill_id") or "")


def reconcile_one(client: genai.Client, prompt: str, entry: dict) -> str | None:
    entry_id = _id_key(entry)
    native_path = DATA_DIR / f"{entry_id}.native.txt"
    ocr_path = DATA_DIR / f"{entry_id}.ocr.txt"

    if not native_path.exists():
        logging.warning("Missing native: %s", native_path)
        return None
    if not ocr_path.exists():
        logging.warning("Missing OCR: %s", ocr_path)
        return None

    native_text = native_path.read_text(encoding="utf-8")
    ocr_text = ocr_path.read_text(encoding="utf-8")

    logging.info("  native=%d chars, ocr=%d chars", len(native_text), len(ocr_text))
    request = assemble_request(prompt, native_text, ocr_text)
    body = call_gemini(client, request)
    if not body:
        logging.error("Empty response from Gemini for entry %s", entry_id)
        return None

    return build_frontmatter(entry) + body + ("\n" if not body.endswith("\n") else "")


def main(
    force: bool = False,
    bill_ids: list[str] | None = None,
    manifest_path: Path | None = None,
) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Prefer manifest_laws.json if no override given and it exists
    if manifest_path is None:
        manifest_path = MANIFEST_LAWS_PATH if MANIFEST_LAWS_PATH.exists() else MANIFEST_PATH

    if not manifest_path.exists():
        logging.error("Manifest not found: %s", manifest_path)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompt = load_prompt()
    api_key = load_api_key()
    client = genai.Client(api_key=api_key)

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    selected = [e for e in manifest if e.get("pdf_path")]
    if bill_ids:
        wanted = set(bill_ids)
        selected = [e for e in selected if _id_key(e) in wanted]

    if not selected:
        logging.warning("No PDFs to process.")
        return 0

    successes = 0
    for entry in selected:
        entry_id = _id_key(entry)
        out_path = OUT_DIR / f"{entry_id}.md"

        if out_path.exists() and not force:
            logging.info("skip (exists): %s", out_path.name)
            successes += 1
            continue

        logging.info("reconcile: %s (%s)", entry_id, entry.get("name_he", ""))
        try:
            md = reconcile_one(client, prompt, entry)
        except Exception as exc:  # noqa: BLE001 — we log and continue per pipeline policy
            logging.error("Gemini call failed for entry %s: %s", entry_id, exc)
            continue

        if md is None:
            continue

        out_path.write_text(md, encoding="utf-8")
        logging.info("  wrote %s (%d chars)", out_path.name, len(md))
        successes += 1

    print(f"Done. {successes}/{len(selected)} reconciled.")
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
