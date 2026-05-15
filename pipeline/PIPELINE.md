# Pipeline — Human Guide

This pipeline converts Israeli law PDFs into structured Hebrew markdown. It has four sequential stages: fetch, native extraction, OCR extraction, and Gemini reconciliation.

---

## Overview

```
Knesset OData API
      │
      ▼
 fetch.py               → downloads PDFs + builds manifest.json
      │
      ▼
 extract_native.py      → pdftotext: embedded text from each PDF
      │
      ▼
 extract_ocr.py         → Tesseract: OCR text + word-level layout JSON
      │
      ▼
 reconcile.py           → Gemini 2.5 Flash: merge both into legal markdown
      │
      ▼
 laws/israel/<id>.md    → final output with YAML frontmatter
```

The two-witness design (native + OCR) is intentional: native PDF text is character-accurate but has bidi/ordering issues; OCR text is reading-order correct but has recognition errors. Gemini reconciles them conservatively into clean markdown.

---

## Prerequisites

```bash
# Python environment
source ~/.venv-codex/bin/activate   # or: source .venv/bin/activate

# System tools
sudo apt install poppler-utils tesseract-ocr tesseract-ocr-heb

# API key
echo "GEMINI_API_KEY=<your-key>" > pipeline/.env
```

---

## Running the Pipeline

### Step 1 — Fetch PDFs

Queries the Knesset OData API for all enacted laws, downloads their PDFs, and writes a manifest.

```bash
python pipeline/fetch.py
```

To fetch only Basic Laws:
```bash
python pipeline/fetch.py --name-prefix 'חוק-יסוד' --name-prefix 'חוק יסוד'
```

To test with a small batch:
```bash
python pipeline/fetch.py --limit 10
```

**Outputs:**
- `data/raw/israel/<bill_id>.pdf` — one file per law
- `data/raw/israel/manifest.json` — metadata index (bill_id, title, dates, paths)

The manifest is checkpointed every 100 bills, so interrupted runs are safe to resume.

---

### Step 2 — Native Extraction

Extracts the embedded text layer from each PDF using `pdftotext`.

```bash
python pipeline/extract_native.py
```

To re-extract a specific law:
```bash
python pipeline/extract_native.py --bill-id 147391 --force
```

**Output:** `data/raw/israel/<bill_id>.native.txt`

Page boundaries are preserved as form-feed characters (`\f`). Spacing depth and column layout are retained via `-layout` mode.

---

### Step 3 — OCR Extraction

Renders each PDF page to a 300 DPI PNG, then runs Tesseract (Hebrew) twice: once for plain text, once for word-level layout with bounding boxes.

```bash
python pipeline/extract_ocr.py
```

This is the slowest step — expect several seconds per page. For a single law:
```bash
python pipeline/extract_ocr.py --bill-id 147391 --force
```

**Outputs:**
- `data/raw/israel/<bill_id>.ocr.txt` — OCR text, form-feed between pages
- `data/raw/israel/<bill_id>.ocr_layout.json` — word bounding boxes, confidence scores, block/line structure

---

### Step 4 — Reconciliation

Feeds both text witnesses into Gemini 2.5 Flash. The model acts as a conservative reconciliation engine — it corrects OCR errors using the native text as reference, preserves exact numbering, isolates margin notes, footnotes, and signatures, and marks uncertain regions.

```bash
python pipeline/reconcile.py
```

For specific laws only:
```bash
python pipeline/reconcile.py --bill-id 147391 --bill-id 149942
```

To re-run even if output exists:
```bash
python pipeline/reconcile.py --force
```

**Output:** `laws/israel/<bill_id>.md` with YAML frontmatter (bill_id, title, dates, provenance).

---

## File Layout

```
data/raw/israel/
  manifest.json              ← metadata for all fetched laws
  <bill_id>.pdf              ← source PDF
  <bill_id>.native.txt       ← pdftotext output
  <bill_id>.ocr.txt          ← Tesseract plain text
  <bill_id>.ocr_layout.json  ← Tesseract word layout

laws/israel/
  <bill_id>.md               ← final markdown output
  _index.md                  ← index page (maintained separately)

pipeline/
  fetch.py
  extract_native.py
  extract_ocr.py
  reconcile.py
  prompts/track2_gemini.md   ← reconciliation prompt
  .env                       ← GEMINI_API_KEY (not committed)
```

---

## Key Constraints

- **Knesset WAF**: The Knesset website blocks WSL2 IP ranges. `fetch.py` hits the OData API (not the main site) and works fine from WSL2. `.docx` downloads from the main site require a Windows browser.
- **All scripts are idempotent**: They skip files that already exist on disk unless `--force` is passed.
- **Reconciliation is output-only**: The Gemini model is prompted to return markdown only, with no reasoning or commentary in the output. Thinking budget is set to 0 to prevent truncation on long laws.

---

## Output Format

Each `laws/israel/<id>.md` starts with YAML frontmatter:

```yaml
---
bill_id: 147391
title_he: "חוק החוזים (חלק כללי), התשל\"ג-1973"
publication_date: 1973-07-05
source_pdf: data/raw/israel/147391.pdf
generated_by: pipeline/reconcile.py
model: gemini-2.5-flash
generated_at: 2026-05-15T10:00:00Z
---
```

The body uses a strict markdown hierarchy: `#` for sections, `##` for subsections, `###`/`####` for deeper levels. Margin notes are blockquotes (`>`). Footnotes use `[^N]` references. Signatures close the document under `## חתומים`.
