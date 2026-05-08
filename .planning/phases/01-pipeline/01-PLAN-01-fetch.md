---
phase: 01-pipeline
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pipeline/fetch.py
  - pipeline/requirements.txt
autonomous: true
requirements:
  - PIPE-01

must_haves:
  truths:
    - "Running `python pipeline/fetch.py` fetches all enacted laws from the Knesset OData API and downloads PDFs to data/raw/israel/"
    - "data/raw/israel/manifest.json exists after a run and contains bill_id, name_he, publication_date, sub_type_id, and pdf_path per law"
    - "The script paginates through all pages (100 records/page) until no more results"
    - "HTTP errors are logged and the run continues — a single bad response does not abort the full fetch"
    - "A tqdm progress bar tracks download progress"
  artifacts:
    - path: "pipeline/fetch.py"
      provides: "Knesset OData metadata fetch + PDF download"
      exports: ["fetch_bills", "fetch_pdf_urls", "download_pdf", "main"]
    - path: "pipeline/requirements.txt"
      provides: "Pinned Python dependencies including pymupdf"
      contains: "pymupdf"
    - path: "data/raw/israel/manifest.json"
      provides: "Per-law metadata index produced at runtime"
      contains: "bill_id"
  key_links:
    - from: "pipeline/fetch.py"
      to: "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Bill"
      via: "requests.get with $filter=StatusID eq 118&$top=100&$skip=N&$format=json"
      pattern: "KNS_Bill"
    - from: "pipeline/fetch.py"
      to: "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_DocumentBill"
      via: "requests.get with $filter=BillID eq X&$format=json"
      pattern: "KNS_DocumentBill"
    - from: "pipeline/fetch.py"
      to: "data/raw/israel/manifest.json"
      via: "json.dump after each batch of 100 bills"
      pattern: "manifest.json"
---

<objective>
Build pipeline/fetch.py — the first stage of the Codex Civica data pipeline.

Purpose: Fetch metadata for all ~7,699 enacted Israeli laws from the Knesset OData API and download their official PDFs from fs.knesset.gov.il. The script produces data/raw/israel/manifest.json (the contract consumed by convert.py) and populates data/raw/israel/ with raw PDFs.

Output:
- pipeline/fetch.py — runnable Python script with tqdm progress, batch-safe manifest writes, graceful HTTP error handling
- pipeline/requirements.txt — updated to include pymupdf==1.25.5 (needed by convert.py, logically grouped here)
- data/raw/israel/manifest.json — produced at runtime (not committed)
- data/raw/israel/{bill_id}.pdf — PDF files produced at runtime (not committed)
</objective>

<execution_context>
@/home/yuvalv/.claude/get-shit-done/workflows/execute-plan.md
@/home/yuvalv/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/mnt/c/Dev/codex-civica/.planning/PROJECT.md
@/mnt/c/Dev/codex-civica/.planning/ROADMAP.md
@/mnt/c/Dev/codex-civica/.planning/STATE.md
@/mnt/c/Dev/codex-civica/.planning/phases/01-pipeline/01-CONTEXT.md
@/mnt/c/Dev/codex-civica/CLAUDE.md
@/mnt/c/Dev/codex-civica/pipeline/requirements.txt

<interfaces>
<!-- Confirmed live OData field names from KNS_Bill (StatusID eq 118): -->
<!-- BillID, KnessetNum, Name (Hebrew), SubTypeID, SubTypeDesc, PublicationDate, LastUpdatedDate -->
<!-- Confirmed live OData field names from KNS_DocumentBill: -->
<!-- DocumentBillID, BillID, GroupTypeID, GroupTypeDesc, ApplicationID, ApplicationDesc, FilePath, LastUpdatedDate -->
<!-- Filter for PDFs: ApplicationDesc == "PDF", GroupTypeID == 9 (Reshumot = official publication) -->
<!-- Base URLs: -->
<!--   Metadata: https://knesset.gov.il/Odata/ParliamentInfo.svc/ -->
<!--   Files:    https://fs.knesset.gov.il/ (no Reblaze, WSL2 accessible, HTTP 200) -->
<!-- Pagination: $top=100&$skip=N&$format=json -->

Manifest JSON schema (one entry per law):
{
  "bill_id": 147449,
  "name_he": "חוק-יסוד: הממשלה",
  "publication_date": "1968-08-01T00:00:00",
  "sub_type_id": 53,
  "pdf_path": "data/raw/israel/147449.pdf",
  "pdf_url": "https://fs.knesset.gov.il//1/law/1_lsr_207874.PDF"
}
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add pymupdf to requirements.txt</name>
  <files>pipeline/requirements.txt</files>
  <read_first>
    - pipeline/requirements.txt — read current contents before editing; append pymupdf after tqdm line to keep related packages grouped
  </read_first>
  <action>
    Add `pymupdf==1.25.5` to pipeline/requirements.txt. Insert it in alphabetical order between the existing packages. The package is imported as `fitz` in Python code (import name differs from pip name). Do not change any other line. Do not add a comment. Just the package==version line.

    Verify the version is available: `pip index versions pymupdf 2>/dev/null | head -1` or use 1.25.5 which is a stable release compatible with Python 3.12.
  </action>
  <verify>
    <automated>grep -c 'pymupdf' /mnt/c/Dev/codex-civica/pipeline/requirements.txt</automated>
  </verify>
  <done>pipeline/requirements.txt contains exactly one line `pymupdf==1.25.5` (or latest stable for Python 3.12)</done>
</task>

<task type="auto">
  <name>Task 2: Write pipeline/fetch.py</name>
  <files>pipeline/fetch.py</files>
  <read_first>
    - pipeline/requirements.txt — confirm available packages before importing (requests, tqdm, python-frontmatter, PyYAML, knesset-data all present)
    - CLAUDE.md — venv path (~/.venv-codex), data paths (data/raw/israel/), manifest fields
    - .planning/phases/01-pipeline/01-CONTEXT.md — locked decisions: OData endpoints, pagination, manifest schema, pdf_path format
  </read_first>
  <action>
    Create `/mnt/c/Dev/codex-civica/pipeline/fetch.py` implementing the following exactly:

    **Shebang and imports:**
    ```python
    #!/usr/bin/env python3
    """Fetch Knesset law metadata and PDFs from OData API and fs.knesset.gov.il."""

    import argparse
    import json
    import logging
    import os
    import time
    from pathlib import Path

    import requests
    from tqdm import tqdm
    ```

    **Constants:**
    ```python
    ODATA_BASE = "https://knesset.gov.il/Odata/ParliamentInfo.svc"
    FS_BASE = "https://fs.knesset.gov.il"
    DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "israel"
    MANIFEST_PATH = DATA_DIR / "manifest.json"
    STATUS_IN_EFFECT = 118        # StatusID for enacted/in-effect laws
    GROUP_TYPE_RESHUMOT = 9       # GroupTypeID for official Reshumot publication
    PAGE_SIZE = 100
    REQUEST_TIMEOUT = 30          # seconds
    RETRY_DELAY = 2               # seconds between retries
    MAX_RETRIES = 3
    ```

    **Function: `fetch_bills(session, skip=0, top=100)` → list[dict]**
    - URL: `{ODATA_BASE}/KNS_Bill?$filter=StatusID eq {STATUS_IN_EFFECT}&$top={top}&$skip={skip}&$format=json`
    - GET with timeout=REQUEST_TIMEOUT
    - Returns `response.json()["value"]` (list of bill dicts) or raises on HTTP error
    - Raises `requests.HTTPError` on non-200

    **Function: `fetch_pdf_url(session, bill_id)` → str | None**
    - URL: `{ODATA_BASE}/KNS_DocumentBill?$filter=BillID eq {bill_id} and GroupTypeID eq {GROUP_TYPE_RESHUMOT}&$format=json`
    - Filter results: keep only entries where `ApplicationDesc == "PDF"` (case-insensitive)
    - If multiple PDFs exist, return the one with the latest `LastUpdatedDate`
    - Return `None` if no PDF found (some laws only have DOC/TIF)
    - Raises `requests.HTTPError` on non-200

    **Function: `download_pdf(session, url, dest_path)` → bool**
    - GET with `stream=True`, timeout=REQUEST_TIMEOUT
    - Write to `dest_path` in binary chunks (8192 bytes)
    - Returns `True` on success, `False` on any HTTP/IO error (logs the error)
    - Skip download if `dest_path.exists()` — do not re-download existing files

    **Function: `load_manifest()` → dict[str, dict]**
    - If `MANIFEST_PATH` exists, load and return as dict keyed by `str(bill_id)`
    - Otherwise return `{}`

    **Function: `save_manifest(manifest)` → None**
    - Write manifest dict values as a JSON list to `MANIFEST_PATH`
    - Use `json.dump(list(manifest.values()), f, ensure_ascii=False, indent=2)`
    - Creates `DATA_DIR` if it does not exist (`DATA_DIR.mkdir(parents=True, exist_ok=True)`)

    **Function: `main(limit=None)`**
    ```
    - Set up logging: `logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")`
    - Create requests.Session()
    - Load existing manifest (crash recovery)
    - Count already-fetched entries: skip bills whose bill_id is in manifest AND pdf_path exists
    - Paginate through KNS_Bill:
        skip = 0
        all_bills = []
        while True:
            page = fetch_bills(session, skip=skip, top=PAGE_SIZE)
            if not page:
                break
            all_bills.extend(page)
            skip += PAGE_SIZE
            if limit and len(all_bills) >= limit:
                all_bills = all_bills[:limit]
                break
            time.sleep(0.1)  # polite delay
    - tqdm outer loop over all_bills (desc="Downloading PDFs"):
        For each bill:
            bill_id = bill["BillID"]
            str_id = str(bill_id)
            # Skip if already in manifest and PDF exists on disk
            if str_id in manifest and Path(manifest[str_id]["pdf_path"]).exists():
                continue
            pdf_url = None
            try:
                pdf_url = fetch_pdf_url(session, bill_id)
            except Exception as e:
                logging.warning("Could not fetch doc list for bill %s: %s", bill_id, e)
            pdf_path = None
            if pdf_url:
                dest = DATA_DIR / f"{bill_id}.pdf"
                success = download_pdf(session, pdf_url, dest)
                if success:
                    pdf_path = str(dest)
            manifest[str_id] = {
                "bill_id": bill_id,
                "name_he": bill["Name"],
                "publication_date": bill.get("PublicationDate"),
                "sub_type_id": bill.get("SubTypeID"),
                "pdf_path": pdf_path,
                "pdf_url": pdf_url,
            }
        # Save manifest after each page boundary (every PAGE_SIZE bills)
        if len(manifest) % PAGE_SIZE == 0:
            save_manifest(manifest)
    - save_manifest(manifest)  # final save
    - Print summary: f"Done. {len(manifest)} laws in manifest. PDFs downloaded: {sum(1 for v in manifest.values() if v['pdf_path'])}"
    ```

    **CLI entrypoint:**
    ```python
    if __name__ == "__main__":
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Fetch only first N laws (for testing)"
        )
        args = parser.parse_args()
        main(limit=args.limit)
    ```

    **Edge cases to handle:**
    - `KNS_DocumentBill` returns 0 entries (law has no documents) → pdf_url = None, pdf_path = None in manifest
    - PDF file already downloaded → skip (idempotent)
    - Manifest already contains bill → overwrite only if pdf_path changes
    - `requests.HTTPError`, `requests.ConnectionError`, `requests.Timeout` in fetch_pdf_url or download_pdf → log warning, continue

    Do NOT use `knesset-data` package in this script — it does not support `$filter` parameters. Use `requests` directly against the OData URLs.
  </action>
  <verify>
    <automated>cd /mnt/c/Dev/codex-civica && source ~/.venv-codex/bin/activate && python pipeline/fetch.py --help</automated>
  </verify>
  <done>
    All of the following are true:
    - `python pipeline/fetch.py --help` exits 0 and prints usage including `--limit`
    - fetch.py contains `def fetch_bills(`
    - fetch.py contains `def fetch_pdf_url(`
    - fetch.py contains `def download_pdf(`
    - fetch.py contains `def main(`
    - fetch.py contains `ODATA_BASE = "https://knesset.gov.il/Odata/ParliamentInfo.svc"`
    - fetch.py contains `manifest.json` reference
    - Running `python pipeline/fetch.py --limit 2` (with internet) downloads 2 PDFs and writes manifest.json
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| WSL2 → knesset.gov.il OData | Metadata fetched from external government API over HTTPS |
| WSL2 → fs.knesset.gov.il | Binary PDF files downloaded from external file server over HTTPS |
| fetch.py → data/raw/israel/ | Filenames derived from BillID (integer); used to construct file paths |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01-01 | Spoofing | requests.get to knesset.gov.il | accept | HTTPS with certifi; government domain; no auth token to steal |
| T-01-02 | Tampering | PDF download from fs.knesset.gov.il | accept | Content is public law text; integrity via HTTPS TLS; no signature check needed for this phase |
| T-01-03 | Repudiation | manifest.json write | accept | Manifest is a local cache; no audit trail required; Git history provides version control |
| T-01-04 | Information Disclosure | manifest.json contains law metadata | accept | Public data only; no secrets; manifest is gitignored |
| T-01-05 | Denial of Service | Unbounded pagination requests to OData | mitigate | polite delay (time.sleep(0.1)) between pages; REQUEST_TIMEOUT=30s; MAX_RETRIES=3 to avoid hammering server |
| T-01-06 | Elevation of Privilege | Path traversal via BillID in pdf_path | mitigate | BillID is int from JSON (never user input); cast to int before constructing path: `DATA_DIR / f"{int(bill_id)}.pdf"`. Reject non-integer BillID values with ValueError |
| T-01-07 | Tampering | JSON injection in manifest.json via Name field | mitigate | json.dump with ensure_ascii=False handles escaping; no string interpolation into JSON |
</threat_model>

<verification>
Full pipeline entry check (run after Task 2):

```bash
cd /mnt/c/Dev/codex-civica
source ~/.venv-codex/bin/activate

# 1. Script imports cleanly
python -c "import pipeline.fetch" 2>&1 || python -c "import sys; sys.path.insert(0,'pipeline'); import fetch"

# 2. --help works
python pipeline/fetch.py --help

# 3. Smoke test with limit=3 (downloads 3 laws)
python pipeline/fetch.py --limit 3

# 4. Manifest was written
python -c "
import json
from pathlib import Path
m = json.loads(Path('data/raw/israel/manifest.json').read_text())
assert len(m) >= 1, 'manifest empty'
required = {'bill_id','name_he','publication_date','sub_type_id','pdf_path'}
for entry in m:
    missing = required - set(entry.keys())
    assert not missing, f'Missing fields: {missing}'
print(f'manifest.json OK: {len(m)} entries, all required fields present')
"

# 5. At least one PDF on disk
ls data/raw/israel/*.pdf | head -3
```
</verification>

<success_criteria>
- pipeline/fetch.py exists and `python pipeline/fetch.py --help` exits 0
- pipeline/requirements.txt contains `pymupdf==1.25.5`
- Running with `--limit 3` produces data/raw/israel/manifest.json with 3 entries, each containing: bill_id (int), name_he (Hebrew string), publication_date (ISO string or null), sub_type_id (int), pdf_path (string or null), pdf_url (string or null)
- At least 1 PDF file exists in data/raw/israel/ after the smoke test
- No unhandled exceptions on HTTP timeout or 404 from KNS_DocumentBill
</success_criteria>

<output>
After completion, create `/mnt/c/Dev/codex-civica/.planning/phases/01-pipeline/01-01-SUMMARY.md`
</output>
