# Codex Civica

Israeli laws as clean, readable Hebrew markdown — fetched directly from the Knesset, converted with high fidelity, and published as a searchable public site.

> **Status:** Pipeline complete. Site in development.

---

## What this is

Israeli law exists as scanned PDFs on government servers. They are difficult to search, navigate, or read — especially for non-lawyers. Codex Civica converts them into structured markdown and hosts them on a clean, accessible website.

The goal: anyone can find and read any Israeli law in under 30 seconds.

---

## How the pipeline works

Converting Hebrew legal PDFs faithfully is harder than it sounds. Hebrew is RTL; laws have complex hierarchies (sections, subsections, clauses); margin notes are legally meaningful and must stay attached to the right section; PDFs mix embedded text with scanned pages.

The pipeline uses a **two-witness reconciliation** approach:

```
PDF
 ├─ pdftotext (native text)   → character-accurate, but bidi/ordering issues
 └─ Tesseract OCR (heb)       → reading-order correct, but recognition errors
         │
         ▼
   Gemini 2.5 Flash
   (conservative reconciliation engine)
         │
         ▼
   structured Hebrew markdown
```

Gemini is not rewriting the law. It acts as a reconciliation engine: it corrects OCR errors using the native text as ground truth, preserves exact numbering, isolates margin notes and footnotes, and marks anything ambiguous with `[טקסט לא ודאי]`. The output is deterministic and legally faithful — never paraphrased, never hallucinated.

---

## Pipeline scripts

| Script | What it does |
|--------|-------------|
| `pipeline/fetch.py` | Queries Knesset OData API, downloads PDFs, writes `manifest.json` |
| `pipeline/extract_native.py` | Extracts embedded text via `pdftotext -layout` |
| `pipeline/extract_ocr.py` | Renders pages to PNG at 300 DPI, runs Tesseract (Hebrew), saves text + word layout JSON |
| `pipeline/reconcile.py` | Feeds both witnesses to Gemini Flash, writes final markdown to `laws/israel/` |

All scripts are idempotent — they skip existing outputs and support `--bill-id` for targeted runs.

See [`pipeline/PIPELINE.md`](pipeline/PIPELINE.md) for the full human walkthrough and [`pipeline/PIPELINE_AI.md`](pipeline/PIPELINE_AI.md) for the technical reference.

---

## Running the pipeline

**Prerequisites:**
```bash
sudo apt install poppler-utils tesseract-ocr tesseract-ocr-heb
pip install -r pipeline/requirements.txt
echo "GEMINI_API_KEY=<your-key>" > pipeline/.env
```

**Full run:**
```bash
python pipeline/fetch.py                  # fetch PDFs from Knesset
python pipeline/extract_native.py         # extract embedded text
python pipeline/extract_ocr.py            # OCR all pages
python pipeline/reconcile.py              # reconcile → markdown
```

**Single law:**
```bash
python pipeline/fetch.py --name-prefix 'חוק-יסוד'
python pipeline/extract_native.py --bill-id 147449
python pipeline/extract_ocr.py    --bill-id 147449
python pipeline/reconcile.py      --bill-id 147449
```

---

## Output format

Each law is a markdown file with YAML frontmatter:

```markdown
---
bill_id: 147449
title_he: "חוק-יסוד: הממשלה"
publication_date: 1968-08-13
source_pdf: data/raw/israel/147449.pdf
generated_by: pipeline/reconcile.py
model: gemini-2.5-flash
generated_at: 2026-05-15T10:00:00Z
---

# חוק-יסוד: הממשלה

# 1. הממשלה היא הרשות המבצעת של המדינה.

> הממשלה

## (א) הממשלה תפעל בהתאם לחוק זה.
```

Hierarchy: `#` sections → `##` subsections → `###`/`####` deeper levels. Margin notes are blockquotes. Footnotes use `[^N]`. Signatures close the document under `## חתומים`.

---

## Repository structure

```
pipeline/           Python scripts + reconciliation prompt
  fetch.py
  extract_native.py
  extract_ocr.py
  reconcile.py
  prompts/
    track2_gemini.md
  PIPELINE.md       Human walkthrough
  PIPELINE_AI.md    Technical reference

data/raw/israel/    Source PDFs + extraction outputs (gitignored)
  manifest.json
  <bill_id>.pdf
  <bill_id>.native.txt
  <bill_id>.ocr.txt
  <bill_id>.ocr_layout.json

laws/israel/        Final markdown (committed)
  <bill_id>.md

site/               Docusaurus site (in development)
```

---

## Roadmap

- [x] Phase 1: Pipeline — fetch, extract, reconcile
- [ ] Phase 2: Content — all 14 Israeli Basic Laws converted and validated
- [ ] Phase 3: Site Foundation — Docusaurus with Hebrew RTL, sidebar, no boilerplate
- [ ] Phase 4: Search — full-text search by law name or keyword
- [ ] Phase 5: Custom UI — homepage, law pages, mobile, accessible
- [ ] Phase 6: Deployment — GitHub Pages, auto-deploy on push to main

---

## Design principles

- **Never hallucinate text.** Prefer omission over invention.
- **Preserve legal language exactly.** No normalization, no paraphrase.
- **Preserve numbering exactly.** `(א)`, `(1)`, `(A)` — as in the source.
- **Attach margin notes to their hierarchy node.** They are not decorative.
- **Mark uncertainty explicitly.** `[טקסט לא ודאי]` is better than silent confidence.

---

## Contributing

The pipeline and content are open. If you want to help convert laws, improve the reconciliation prompt, or build the site — open an issue or a PR.
