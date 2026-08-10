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
  common/                    ← country-blind shared core (see below)
  fetch.py
  extract_native.py
  extract_ocr.py
  reconcile.py
  batch_import.py            ← Israel factory-line orchestrator
  prompts/track2_gemini.md   ← reconciliation prompt
  .env                       ← GEMINI_API_KEY (not committed)
```

---

## Shared Core (`pipeline/common/`)

The site serves more than one country's laws (Israel today, England starting v1.1), but most of
`batch_import.py` is not actually Israel-specific — the frontmatter block shape, progress-file
bookkeeping, and site deploy mechanism are the same regardless of source. Phase 7 extracted exactly
that ~150-line country-blind core into `pipeline/common/`, so a future country orchestrator imports
these instead of re-implementing them:

```
pipeline/common/
  frontmatter.py   split_frontmatter(text) -> (fm, body)
                   render_frontmatter(lines) -> str    — wraps lines in --- fences, thin by design
                   quote(value) -> str                 — double-quote + escape, for future callers
  progress.py      load_progress(path) / save_progress(path, progress)
                   get_next_batch(manifest, progress, count, id_keys=..., source_key=...)
                   print_status(manifest, progress, source_label=...)
  deploy.py        deploy(site_dir, env_overrides=None) -> bool   — site_dir is REQUIRED,
                                                                     never derived from __file__
```

**One-way dependency rule:** `pipeline/common/` never imports `reconcile`, `batch_import`,
`link_resolver`, or `cross_linker`, never reads `pipeline/.env`, and never references
`GEMINI_API_KEY`. Israel's modules (`batch_import.py`, `link_resolver.py`, `cross_linker.py`) import
`common.*` and keep same-named thin wrapper functions so their existing call sites never change —
e.g. `batch_import.load_progress()` is a one-line delegation to `common.progress.load_progress(PROGRESS_PATH)`.
This boundary is enforced by `pipeline/tests/verify_golden.py --structure` (static) and
`pipeline/tests/test_country_blind.py` / `--country-blind` (an executing probe that round-trips
progress, selects a batch, and renders frontmatter using only `common.*`, with UK-shaped field names,
and never touches Israel code).

What deliberately stayed **out** of `common/`: `_YEAR_RE` / `_strip_year` / `build_seo_description` in
`reconcile.py` (Hebrew-literal-bearing — moving them would be a legal-fidelity error per the project's
core rules), and the `DEPLOY_EVERY` batch-cadence threshold in `batch_import.py` (policy, not
mechanism — each country orchestrator owns its own cadence).

---

## Testing / Characterization Harness

Phase 7's extraction was gated on zero-behaviour-change, proven with a stdlib-only characterization
harness (no pytest — zero new dependencies):

```bash
~/.venv-codex/bin/python pipeline/tests/capture_golden.py    # re-baseline the fixtures (rare — only after an intentional behaviour change)
~/.venv-codex/bin/python pipeline/tests/verify_golden.py --quick   # ~2.4s, mutates nothing
~/.venv-codex/bin/python pipeline/tests/verify_golden.py           # full suite, ~8s
```

The full suite checks: `--structure` (SC-1/SC-4b, `common/` layout + import boundary), `--split`,
`--frontmatter` (SHA-gated over all 111 converted laws), `--batch`, `--progress-roundtrip`,
`--status`, `--country-blind` (SC-4, runs `test_country_blind.py`), and the link-resolver
before/after differential (the one mutating check — bracketed by `git checkout -- laws/israel/` and
asserts the tree is restored).

**The golden fixtures are invalidated by any commit touching** `laws/israel/`, `pipeline/link_resolver.py`,
`pipeline/reconcile.py`, or `data/raw/israel/import_progress.json` — re-run `capture_golden.py` after an
intentional change to any of those before trusting `verify_golden.py` again.

---

## Key Constraints

- **Knesset WAF**: The Knesset website blocks WSL2 IP ranges. `fetch.py` hits the OData API (not the main site) and works fine from WSL2. `.docx` downloads from the main site require a Windows browser.
- **All scripts are idempotent**: They skip files that already exist on disk unless `--force` is passed.
- **Reconciliation is output-only**: The Gemini model is prompted to return markdown only, with no reasoning or commentary in the output. Thinking budget is set to 0 to prevent truncation on long laws.
- **`python pipeline/X.py` is the only supported invocation form.** `python -m pipeline.X` is not supported and never was — there is no `pipeline/__init__.py` (and one must never be added; it would break every documented entry point above). Every module relies on `sys.path[0]` being the script's own directory, which only holds for the plain-script invocation form; `batch_import.run_batch()`'s bare `import link_resolver` (no `sys.path` bootstrap) would raise under `-m`.
- **Interpreter**: always `~/.venv-codex/bin/python`. `python3` / `which python3` resolves to the in-repo `.venv/`, which lacks `google-genai` and `python-dotenv` — a `ModuleNotFoundError` there reads like a regression but is an environment mismatch.

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
