# Phase 1 Context — Pipeline

**Phase:** 1 — Pipeline
**Goal:** A working pipeline that fetches, converts, and validates Israeli laws programmatically
**Date:** 2026-05-08

---

## Domain

Build three Python scripts that form the complete data pipeline:
1. `fetch.py` — OData metadata + PDF download from Knesset sources
2. `convert.py` — PDF → structured Markdown with frontmatter
3. `validate.py` — frontmatter completeness + link integrity report

No site work. No UI. Pure data pipeline.

---

## Decisions

### Retrieval Mechanism

**Decision: OData API for metadata + `fs.knesset.gov.il` for PDFs — fully automated from WSL2.**

- Source 1 (metadata): `https://knesset.gov.il/Odata/ParliamentInfo.svc/`
  - `KNS_Bill` — query `StatusID eq 118` to get all in-effect laws (7,699 total confirmed)
  - Fields: `BillID`, `Name` (Hebrew), `SubTypeID`, `PublicationDate`
  - `KNS_DocumentBill` — query by `BillID` to get document URLs (`FilePath`)
  - Filter `GroupTypeID eq 9` (official publication in Reshumot) + `ApplicationDesc` contains PDF
- Source 2 (content): `https://fs.knesset.gov.il/` — direct file download, accessible from WSL2 (confirmed HTTP 200)

**Why not main.knesset.gov.il consolidated DOCX:**
- Blocked from WSL2 by Reblaze WAF (returns HTTP 247)
- Consolidated DOCX not in OData — only original publications are

**Why not Hebrew Wikisource:**
- Returns HTTP 403 from WSL2

**Why not LibreOffice DOC conversion:**
- Knesset publishes original laws as old OLE `.DOC` format — not readable by Pandoc or python-docx
- LibreOffice headless adds system dependency

**Scope: All in-effect laws (7,699), not just Basic Laws.**
- The OData + PDF approach scales to the full corpus at no extra cost
- Basic Laws are just the first batch processed through the same pipeline

### PDF Extraction Library

**Decision: `pymupdf` (fitz) for PDF → text extraction.**

- Tested on Basic Law: Human Dignity and Liberty PDF from `fs.knesset.gov.il`
- `pymupdf` extracts Hebrew RTL text in correct reading order ✅
- `pdfplumber` reverses word order in Hebrew PDFs ❌
- `pymupdf` is already implicitly available; add to `requirements.txt`

### Pipeline Scripts

**`pipeline/fetch.py`**
- Query OData `KNS_Bill` for all `StatusID eq 118` (with pagination)
- For each bill, query `KNS_DocumentBill` for GroupTypeID=9 PDFs
- Download PDFs to `data/raw/israel/{bill_id}.pdf`
- Write `data/raw/israel/manifest.json` with per-law metadata: `bill_id`, `name_he`, `publication_date`, `sub_type_id`, `pdf_path`
- Use `tqdm` for progress bars (already in requirements.txt)
- Handle pagination (`$skip`/`$top`) — OData returns max 100 per page

**`pipeline/convert.py`**
- Read `manifest.json` for metadata
- For each PDF: extract text with `pymupdf`
- Map OData fields → frontmatter schema (CLAUDE.md canonical schema)
- Generate slug from `name_he` (using `python-hebrew-numbers` for numeral cleanup)
- Write `.md` to `laws/israel/{slug}.md`
- OData `SubTypeID` → `category` mapping (use known SubTypeDesc values)

**`pipeline/validate.py`**
- Read all `.md` files in `laws/israel/`
- Check mandatory frontmatter fields: `title`, `title_he`, `law_id`, `category`, `enacted`, `status`
- Check internal links resolve
- Output: `data/validation_report.json` + human-readable STDOUT summary
- Exit code 0 = clean, 1 = errors found

**`pipeline/README.md`**
- Documents the full pipeline workflow
- No manual download step needed — fully automated from WSL2
- Command sequence: `python fetch.py` → `python convert.py` → `python validate.py`

### Venv

**Decision: Use `~/.venv-codex` (Linux-side, confirmed in CLAUDE.md).**
- The `.venv/` in repo root appears to be a stub — the real dev environment is `~/.venv-codex`
- All pipeline commands: `source ~/.venv-codex/bin/activate && python pipeline/fetch.py`

### OData Pagination

- OData returns max 100 records per page
- Must use `$skip` / `$top` pattern to paginate through all 7,699 laws
- The `knesset-data` package wraps this — prefer it over raw `requests` where it covers the needed endpoints

### PDF Availability

- Confirmed 100% PDF availability across sampled enacted laws (20/20)
- All PDFs on `fs.knesset.gov.il` — no Reblaze protection on file server
- Some laws may have multiple PDFs (amendments) — fetch the `GroupTypeID eq 9` (Reshumot publication) one

---

## Canonical Refs

- `CLAUDE.md` — frontmatter schema, law categories taxonomy, naming conventions, venv location
- `pipeline/requirements.txt` — pinned dependencies (add `pymupdf`)
- `.planning/codebase/STACK.md` — Python 3.12, existing packages
- `.planning/REQUIREMENTS.md` — PIPE-01, PIPE-02, PIPE-03 success criteria
- `.planning/ROADMAP.md` — Phase 1 success criteria

---

## Code Context

- No Python source files exist yet in `pipeline/` — all three scripts are greenfield
- `pipeline/requirements.txt` has all dependencies except `pymupdf` — add it
- `laws/israel/_index.md` exists as placeholder — pipeline writes alongside it
- `data/raw/israel/` directory exists but is empty

---

## Deferred Ideas

- Consolidated law text (with amendments merged) — requires Windows browser download or alternative source; Phase 2+ decision
- `link.py` cross-reference resolver — Phase 2 (needs volume)
- Amendment tracking / history — future milestone
- English translation — out of scope for Milestone 1
