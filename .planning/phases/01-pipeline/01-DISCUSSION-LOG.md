# Discussion Log — Phase 1: Pipeline

**Date:** 2026-05-08
**Phase:** 1 — Pipeline

---

## Areas Discussed

### Retrieval Mechanism

**Question:** How to retrieve Israeli law text programmatically from WSL2?

**Research conducted:**
- Tested Knesset OData API (`knesset.gov.il/Odata/`) — accessible from WSL2, returns law metadata and document URLs
- Tested `fs.knesset.gov.il` file server — accessible from WSL2 (HTTP 200), serves PDF/DOC files
- Tested `main.knesset.gov.il` — blocked by Reblaze WAF from WSL2 (HTTP 247)
- Tested Hebrew Wikisource MediaWiki API — returns HTTP 403 from WSL2
- Checked HaSadna openlaw-bot — it's a Wikisource formatting bot, not a data API
- Tested old `.DOC` files from OData — OLE format, not readable by Pandoc or python-docx
- Confirmed 7,699 total in-effect laws (StatusID=118) in OData
- Confirmed 100% PDF availability for sampled enacted laws

**User decision:** Use OData API for metadata + download PDFs from `fs.knesset.gov.il`. Scope expanded from Basic Laws only to all in-effect laws (7,699).

### PDF Extraction Library

**Question:** Which Python library handles Hebrew RTL PDFs correctly?

**Tested:**
- `pdfplumber` — reverses Hebrew word order (unusable)
- `pymupdf` (fitz) — correct RTL extraction confirmed on Basic Law: Human Dignity and Liberty PDF

**User decision:** pymupdf.

---

## Deferred Ideas

- Consolidated law text (amendments merged) — noted for future milestone
- English translation — out of scope

---

*Log generated: 2026-05-08*
