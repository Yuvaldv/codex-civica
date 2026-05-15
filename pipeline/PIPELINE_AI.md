# Pipeline — AI Reference

Machine-readable specification for the fetch-and-convert pipeline. All paths are relative to the repo root.

---

## Stage Map

| Stage | Script | Inputs | Outputs |
|-------|--------|--------|---------|
| 1. Fetch | `pipeline/fetch.py` | Knesset OData API | `data/raw/israel/*.pdf`, `manifest.json` |
| 2. Native extract | `pipeline/extract_native.py` | `*.pdf` + manifest | `*.native.txt` |
| 3. OCR extract | `pipeline/extract_ocr.py` | `*.pdf` + manifest | `*.ocr.txt`, `*.ocr_layout.json` |
| 4. Reconcile | `pipeline/reconcile.py` | `*.native.txt` + `*.ocr.txt` + manifest | `laws/israel/*.md` |

All scripts read `data/raw/israel/manifest.json` to select bills. All scripts are idempotent: they skip existing outputs unless `--force` is passed. All support `--bill-id <id>` (repeatable) for targeted runs.

---

## manifest.json Schema

```json
[
  {
    "bill_id": 147391,               // int — Knesset internal ID
    "name_he": "חוק החוזים ...",     // string — Hebrew title from KNS_Bill.Name
    "publication_date": "1973-07-05T00:00:00", // ISO datetime or null
    "sub_type_id": null,             // int or null — KNS_Bill.SubTypeID
    "pdf_path": "data/raw/israel/147391.pdf",  // string or null — local path
    "pdf_url": "https://fs.knesset.gov.il/..."  // string or null — source URL
  }
]
```

Bills without `pdf_path` had no Reshumot PDF found on OData. They are in the manifest but skipped by extraction and reconciliation stages.

---

## Stage 1 — fetch.py

**API endpoints used:**
- `GET https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Bill` — bill metadata  
  Filter: `StatusID eq 118` (enacted) + optional `startswith(Name, '<prefix>')`
- `GET .../KNS_DocumentBill?$filter=BillID eq {id} and GroupTypeID eq 9` — PDF URL  
  GroupTypeID 9 = Reshumot (official publication). Picks most-recent `LastUpdatedDate` where `ApplicationDesc == "PDF"`.
- `GET https://fs.knesset.gov.il/...` — PDF binary (chunked streaming)

**Key constants:**
```python
STATUS_IN_EFFECT = 118
GROUP_TYPE_RESHUMOT = 9
PAGE_SIZE = 100
REQUEST_TIMEOUT = 30   # seconds
RETRY_DELAY = 2
MAX_RETRIES = 3
```

**CLI flags:**
```
--limit N            Stop after N bills (testing)
--name-prefix STR    Server-side OData startswith filter (repeatable, OR'd)
```

**Crash recovery:** Manifest is saved every 100 bills. Interrupted runs resume from existing manifest. Bills already in manifest with `pdf_path` pointing to an existing file are skipped.

**Security invariant:** `bill_id` is cast to `int` before use in URLs and file paths to prevent injection.

---

## Stage 2 — extract_native.py

**Tool:** `pdftotext -layout -enc UTF-8 <pdf> <out>`

**Requires:** `poppler-utils` on PATH.

**Output format:** UTF-8 text. Page boundaries = form-feed character `\f` (U+000C). Visual column layout preserved via `-layout`.

**CLI flags:**
```
--force              Overwrite existing .native.txt
--bill-id ID         Only process this bill (repeatable)
```

---

## Stage 3 — extract_ocr.py

**Tools:** PyMuPDF (`fitz`) for PDF-to-PNG rendering; `tesseract` for OCR.

**Requires:** `tesseract-ocr` + `tesseract-ocr-heb` on PATH.

**Per-page process:**
1. Render page to temp PNG at DPI (default 300) using `fitz.Matrix(300/72, 300/72)`
2. Run `tesseract <png> - -l heb --psm 6` → plain text
3. Run `tesseract <png> - -l heb --psm 6 tsv` → word layout
4. Delete temp PNG

**ocr.txt format:** UTF-8 text, pages separated by `\f`.

**ocr_layout.json schema:**
```json
{
  "bill_id": 147391,
  "pdf": "data/raw/israel/147391.pdf",
  "dpi": 300,
  "lang": "heb",
  "pages": [
    {
      "page": 0,           // 0-indexed
      "width_px": 2480,
      "height_px": 3508,
      "words": [
        {
          "block": 1, "par": 1, "line": 1, "word": 1,
          "x": 120, "y": 80, "w": 45, "h": 18,
          "conf": 94.5,
          "text": "חוק"
        }
      ]
    }
  ]
}
```

Words with empty `text` are filtered out. Rows with `conf == -1` (Tesseract block/line markers) are excluded by the empty-text filter.

**CLI flags:**
```
--force              Overwrite existing .ocr.txt and .ocr_layout.json
--dpi N              Render resolution (default 300)
--bill-id ID         Only process this bill (repeatable)
```

---

## Stage 4 — reconcile.py

**Model:** `gemini-2.5-flash` via `google.genai` SDK

**Config:**
```python
temperature=0.0
response_mime_type="text/plain"
max_output_tokens=65536
thinking_config=ThinkingConfig(thinking_budget=0)
```

`thinking_budget=0` is critical: thinking tokens compete with output tokens and silently truncate long laws.

**Request assembly:**
```
<prompt from pipeline/prompts/track2_gemini.md>

=== NATIVE ===
<contents of <bill_id>.native.txt>
=== END NATIVE ===

=== OCR ===
<contents of <bill_id>.ocr.txt>
=== END OCR ===
```

**API key:** Read from `pipeline/.env` via `python-dotenv`. Env var: `GEMINI_API_KEY`.

**Output:** Gemini returns markdown body only (no frontmatter, no code fences). The script prepends YAML frontmatter and writes to `laws/israel/<bill_id>.md`.

**Code-fence stripping:** If the model returns output wrapped in ` ```markdown ``` `, the script strips the fences before writing.

**Finish reason check:** Any finish reason other than `STOP` is logged as a warning (indicates truncation).

**CLI flags:**
```
--force              Overwrite existing .md output
--bill-id ID         Only process this bill (repeatable)
```

---

## Output File — laws/israel/<bill_id>.md

**Frontmatter fields:**
```yaml
bill_id: <int>
title_he: "<Hebrew title, double-quoted, internal quotes escaped>"
publication_date: <YYYY-MM-DD or ~>
source_pdf: <relative path>
generated_by: pipeline/reconcile.py
model: gemini-2.5-flash
generated_at: <ISO 8601 UTC>
```

**Body structure (from prompt contract):**

| Element | Markdown |
|---------|----------|
| Document title | `# <title>` (H1) |
| Chapter | `# פרק <X> - <title>` (H1) |
| Section | `# N.` (H1) |
| Subsection | `## (X) <body>` (H2, inline body) |
| Sub-subsection | `### (Y) <body>` (H3, inline body) |
| Clause | `#### (Z) <body>` (H4, inline body) |
| Margin note | `> <text>` (blockquote, no label) |
| Uncertain text | `[טקסט לא ודאי]` |
| Footnote ref | `[^N]` inline |
| Definition bullet | `* "<term>" – <body>;` |
| Signature block | `## חתומים` then `- <name>, <role>` per line |
| Footnote definitions | `## הערות שוליים` then `[^N]: <text>` |

**Margin note placement invariant:** Margin note blockquote appears immediately after the heading it is attached to, separated by one blank line before and after. For Pattern A/B sections (inline body): blank line between section heading and blockquote. For Pattern C (standalone `# N.`): margin note follows the subsection heading it is visually adjacent to.

**Disagreement resolution:**
- Character identity → prefer NATIVE
- Word/line ordering → prefer OCR
- Unresolvable disagreement → `[טקסט לא ודאי]`

---

## Dependency Map

```
fetch.py
  └── requests, tqdm
      writes: manifest.json, *.pdf

extract_native.py
  └── subprocess(pdftotext)
      reads:  manifest.json, *.pdf
      writes: *.native.txt

extract_ocr.py
  └── fitz (pymupdf), subprocess(tesseract)
      reads:  manifest.json, *.pdf
      writes: *.ocr.txt, *.ocr_layout.json

reconcile.py
  └── google.genai, python-dotenv
      reads:  manifest.json, *.native.txt, *.ocr.txt, pipeline/.env
      writes: laws/israel/*.md
```

---

## Extending the Pipeline

**Adding a new country/corpus:**
- Create a parallel `data/raw/<country>/manifest.json` with the same schema
- Add a `laws/<country>/` output directory
- The extraction and reconciliation scripts are parameterized by `DATA_DIR` and `OUT_DIR` at the top of each file — adjust or make them CLI flags

**Re-running a single bill end-to-end:**
```bash
python pipeline/extract_native.py --bill-id <id> --force
python pipeline/extract_ocr.py    --bill-id <id> --force
python pipeline/reconcile.py      --bill-id <id> --force
```

**Updating the reconciliation prompt:** Edit `pipeline/prompts/track2_gemini.md`. Run `--force` on affected bills to regenerate. Keep old prompt version in git if running A/B comparisons.
