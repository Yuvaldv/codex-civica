#!/usr/bin/env python3
"""Track 2 v3 — page image → Gemini 2.5 Flash → clean Hebrew markdown.

Skips OCR entirely. Each PDF page is rendered to PNG at 200 DPI and sent
multimodally to Gemini 2.5 Flash with a verbatim-preserve prompt. The model
returns Hebrew legal markdown in logical reading order with hierarchy intact.

Output:
  laws/israel/track2-gemini/<bill_id>.md  — rendered markdown w/ frontmatter

The pipeline is intentionally one-shot per document: all pages of a single
law go in one multimodal call so the model sees clause continuations across
page breaks.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import fitz  # pymupdf
from dotenv import load_dotenv
from google import genai
from google.genai import types

PIPELINE_DIR = Path(__file__).parent
DEFAULT_MANIFEST = PIPELINE_DIR.parent / "data" / "raw" / "israel" / "manifest.json"
DEFAULT_OUTPUT = PIPELINE_DIR.parent / "laws" / "israel" / "track2-gemini"
PROMPT_PATH = PIPELINE_DIR / "prompts" / "track2_gemini.md"

MODEL = "gemini-2.5-flash"
RENDER_DPI = 200


def load_prompt() -> str:
    """Read the Gemini prompt from pipeline/prompts/track2_gemini.md.

    The prompt is kept in a separate file so it can be iterated without
    touching the pipeline code. Edit prompts/track2_gemini.md and re-run.
    """
    if not PROMPT_PATH.exists():
        sys.exit(f"Prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


PROMPT = load_prompt()


def load_api_key() -> str:
    load_dotenv(PIPELINE_DIR / ".env")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set (expected in pipeline/.env or env)")
    return key


def render_pages(pdf_path: Path, dpi: int = RENDER_DPI) -> list[bytes]:
    """Render each PDF page to PNG bytes."""
    doc = fitz.open(pdf_path)
    images: list[bytes] = []
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
    finally:
        doc.close()
    return images


def call_gemini(client: genai.Client, page_pngs: list[bytes]) -> str:
    parts: list = [PROMPT]
    parts.extend(
        types.Part.from_bytes(data=png, mime_type="image/png")
        for png in page_pngs
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="text/plain",
        ),
    )
    text = (response.text or "").strip()
    # Strip stray code fences if the model added them despite instructions.
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
    return text


def build_frontmatter(entry: dict) -> str:
    fm = {
        "title_he": entry.get("name_he", ""),
        "law_id": f"knesset-{entry['bill_id']}",
        "category": "basic-laws",
        "enacted": (entry.get("publication_date") or "")[:10],
        "status": "active",
        "language": ["he"],
        "source_url": entry.get("pdf_url", ""),
        "track": "2-gemini",
    }
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        else:
            lines.append(f"{k}: {v if v else ''}")
    lines.append("---")
    return "\n".join(lines)


def convert_one(client: genai.Client, entry: dict, output_dir: Path) -> bool:
    bill_id = entry["bill_id"]
    pdf_path = entry.get("pdf_path")
    if not pdf_path or not Path(pdf_path).exists():
        logging.warning("No PDF for bill %s", bill_id)
        return False

    logging.info("Rendering %s", pdf_path)
    pages = render_pages(Path(pdf_path))
    logging.info("Calling Gemini (%s) with %d page(s)", MODEL, len(pages))
    try:
        body = call_gemini(client, pages)
    except Exception as exc:
        logging.error("Gemini call failed for %s: %s", bill_id, exc)
        return False

    fm = build_frontmatter(entry)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{bill_id}.md"
    md_path.write_text(f"{fm}\n\n{body}\n", encoding="utf-8")
    logging.info("Wrote %s", md_path.name)
    return True


def main(manifest_path: Path, output_dir: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not manifest_path.exists():
        logging.error("Manifest not found: %s", manifest_path)
        sys.exit(1)
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    client = genai.Client(api_key=load_api_key())
    ok = fail = 0
    for e in entries:
        if convert_one(client, e, output_dir):
            ok += 1
        else:
            fail += 1
    print(f"Done. Converted: {ok}, Errors: {fail}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    main(Path(args.input), Path(args.output))
