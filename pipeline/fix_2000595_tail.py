#!/usr/bin/env python3
"""One-shot fix for law 2000595 tail (sections 527-546 + תוספת).

The main reconcile run hit the 65k token output limit and stopped after
truncating section 527. This script:
  1. Extracts native tail from line 2889 (where section 527 begins)
  2. Extracts OCR tail from line 2544
  3. Calls Gemini on ONLY the tail with a modified prompt (no title header)
  4. Strips the truncated section 527 + everything after it from the MD
  5. Appends the Gemini tail output
  6. Re-runs link_resolver on the file
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
PROJECT_DIR = PIPELINE_DIR.parent
DATA_DIR = PROJECT_DIR / "data" / "raw" / "israel"
LAWS_DIR = PROJECT_DIR / "laws" / "israel"
LAW_ID = "2000595"

# Line numbers (1-based) where section 527 begins in each source file
NATIVE_TAIL_LINE = 2889
OCR_TAIL_LINE = 2544

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

TAIL_PROMPT = """\
You are reconciling two imperfect representations of the TAIL of a Hebrew legal document.

OUTPUT DISCIPLINE — read first, obey absolutely:

- Output ONLY the final reconciled markdown of the tail sections.
- Do NOT include a document title heading — the document title was already
  emitted for sections 1–526. Begin directly with the first section heading
  of the tail (section 527).
- Do NOT include any reasoning, deliberation, comparison notes, or commentary.
- Do NOT wrap markdown elements in backticks.
- No code fences (```), no preamble, no postamble.

NATIVE:
Native PDF text extraction (pdftotext --layout). Preserves visual columns
and spacing depth; uses Unicode bidi control marks; trustworthy on
character identity but visually ordered.

OCR:
Tesseract OCR extraction. Reading-order text; no bidi marks; may contain
recognition errors on individual characters and words.

IMPORTANT — Section numbering in OCR:
The OCR source uses short sequential counters (7, 8, 9...) within each chapter
rather than the absolute section numbers from the law (527, 528, 529...).
You MUST use the absolute section numbers from the NATIVE source for all
section headings. The NATIVE source has the correct absolute numbers.

Your task:
Reconstruct the tail of the legal document conservatively into Hebrew markdown.
Output language is Hebrew throughout. No English words.

Critical rules:

1. Never invent text.
2. Never paraphrase legal language.
3. Never rewrite stylistically.
4. Preserve the original numbering tokens exactly ((א), (1), (A)...).
5. Preserve hierarchy only where strongly evidenced.
6. Preserve footnotes, margin notes, and signatures separately.
7. Capture EVERY signatory shown in the document.
8. Mark unresolved disagreements with [טקסט לא ודאי].
9. Prefer omission over hallucination.
10. Do NOT invent footnote definitions. Emit [^N] and [^N]: only when
    the source actually has a footnote anchor at that location.
11. Whitespace cleanup (silently):
    - Replace Unicode soft hyphens (U+00AD) with regular hyphens (-).
    - Remove spurious space before trailing punctuation.
    - Collapse runs of spaces to a single space.
    - Convert )א( → (א), )1( → (1).

================================================================
DOCUMENT STRUCTURE
================================================================

Sections — # N.:

- Section heading: # N. (e.g. # 527., # 528.)
- THREE section patterns:

  PATTERN A — Section IS a single statement. Body inline:
    # 527. <body text>.

    > <margin note text>

  PATTERN B — Section has a colon-led intro followed by enumeration:
    # 528. <intro>:

    > <margin note text>

    ## (1) ...
    ## (2) ...

  PATTERN C — Section starts directly with subsection (א):
    # 534.
    ## (א) <body>
    ## (ב) <body>

- Footnote reference at end of heading line that owns it: # 527. <body>[^N]

Subsections — ## (X) <body>:
- Always inline: ## (א) <body text>, never split across lines.
- Deeper levels: ### (Y) and #### (Z) follow the same inline rule.

Margin notes:
- Simple blockquote: > <text>
- Place IMMEDIATELY AFTER the heading of its hierarchy node, with a blank
  line before the > line AND a blank line after it.

Schedule (תוספת):
- If the source contains a schedule (תוספת) with sample charges, emit it
  after section 546 using this structure:
    # תוספת
    ## טופס <N>
    <charge text verbatim>
- Preserve all 36 charge form templates exactly.

After all body sections and the תוספת:

1. --- horizontal rule.
2. ## חתומים block with one bullet per signatory.
3. --- horizontal rule.
4. Footnotes block: [^N]: <text> in numeric order.

================================================================
DISAGREEMENT RULES
================================================================

- Prefer NATIVE for exact text fidelity.
- Prefer OCR for reading order.
- When NATIVE and OCR disagree on a character, prefer NATIVE.
- When NATIVE and OCR disagree on word/line ordering, prefer OCR.
- Mark ambiguous text with [טקסט לא ודאי].

Return ONLY markdown. No code fences. No commentary.
"""


def extract_tail(path: Path, start_line: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start_line - 1:])  # 1-based → 0-based


def call_gemini(native_tail: str, ocr_tail: str) -> str:
    from dotenv import load_dotenv
    from google import genai
    from google.genai import types

    load_dotenv(PIPELINE_DIR / ".env")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set")

    client = genai.Client(api_key=key)
    request = (
        TAIL_PROMPT
        + "\n\n=== NATIVE ===\n"
        + native_tail
        + "\n=== END NATIVE ===\n\n"
        + "=== OCR ===\n"
        + ocr_tail
        + "\n=== END OCR ===\n"
    )

    logging.info("Sending tail to Gemini (native=%d chars, ocr=%d chars)",
                 len(native_tail), len(ocr_tail))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
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
        logging.info("finish_reason=%s", finish)
        if finish and str(finish) not in ("FinishReason.STOP", "STOP"):
            logging.warning("Output may be truncated (finish_reason=%s)", finish)

    text = (response.text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def strip_tail_from_md(md_path: Path) -> str:
    """Remove section 527 (truncated) and everything after it, return trimmed body."""
    text = md_path.read_text(encoding="utf-8")
    # Find the line `# 527.` — this is the truncated entry we'll replace
    marker = "\n# 527."
    idx = text.find(marker)
    if idx == -1:
        # Try without the newline prefix (if it's the very start of body)
        marker = "# 527."
        idx = text.find(marker)
        if idx == -1:
            logging.warning("Could not find '# 527.' in MD — appending tail to end")
            return text.rstrip()

    return text[:idx].rstrip()


def run_link_resolver(md_path: Path) -> None:
    sys.path.insert(0, str(PIPELINE_DIR))
    import link_resolver
    logging.info("Running link_resolver on %s", md_path.name)
    link_resolver.resolve_one(md_path)
    logging.info("link_resolver done")


def main() -> None:
    native_path = DATA_DIR / f"{LAW_ID}.native.txt"
    ocr_path = DATA_DIR / f"{LAW_ID}.ocr.txt"
    md_path = LAWS_DIR / f"{LAW_ID}.md"

    for p in (native_path, ocr_path, md_path):
        if not p.exists():
            sys.exit(f"Missing: {p}")

    # 1. Extract tails
    native_tail = extract_tail(native_path, NATIVE_TAIL_LINE)
    ocr_tail = extract_tail(ocr_path, OCR_TAIL_LINE)
    logging.info("Extracted native tail: %d chars, OCR tail: %d chars",
                 len(native_tail), len(ocr_tail))

    # 2. Call Gemini
    tail_md = call_gemini(native_tail, ocr_tail)
    if not tail_md:
        sys.exit("Empty response from Gemini")
    logging.info("Received tail from Gemini: %d chars", len(tail_md))

    # 3. Strip truncated section 527+ from existing MD
    base = strip_tail_from_md(md_path)
    logging.info("Stripped MD to %d chars", len(base))

    # 4. Assemble: base + blank line + tail
    new_md = base + "\n\n" + tail_md + "\n"
    md_path.write_text(new_md, encoding="utf-8")
    logging.info("Wrote %d chars to %s", len(new_md), md_path.name)

    # 5. Re-run link_resolver
    run_link_resolver(md_path)
    logging.info("Done. Law 2000595 tail fix complete.")


if __name__ == "__main__":
    main()
