---
phase: 01-pipeline
plan: "01"
subsystem: pipeline
tags: [python, requests, tqdm, pymupdf, odata, knesset, pdf]

# Dependency graph
requires: []
provides:
  - "pipeline/fetch.py: paginated OData fetch + PDF download for all ~7,699 enacted Israeli laws"
  - "pipeline/requirements.txt: pinned dependencies including pymupdf==1.25.5"
  - "data/raw/israel/manifest.json: per-law metadata index (runtime artifact)"
affects:
  - "02-pipeline (convert.py reads manifest.json and PDFs produced here)"
  - "03-pipeline (validate.py reads laws/ written from PDFs fetched here)"

# Tech tracking
tech-stack:
  added:
    - pymupdf==1.25.5
  patterns:
    - "OData pagination: $skip/$top with PAGE_SIZE=100, time.sleep(0.1) polite delay"
    - "Crash-safe manifest: save every PAGE_SIZE bills; load on startup for resume"
    - "Idempotent downloads: skip if dest_path.exists()"
    - "Security: cast BillID to int() before path construction (path traversal guard)"

key-files:
  created:
    - pipeline/fetch.py
  modified:
    - pipeline/requirements.txt
    - .gitignore

key-decisions:
  - "Use requests directly against OData API — knesset-data package does not support $filter params"
  - "GroupTypeID=9 (Reshumot) + ApplicationDesc=PDF to identify official publication PDFs"
  - "If multiple PDFs per law, pick the one with latest LastUpdatedDate"
  - "BillID cast to int() before path construction (T-01-06 threat mitigation)"
  - "data/raw/ and *.pdf added to .gitignore — runtime output never committed"

patterns-established:
  - "Pipeline scripts: path resolution via Path(__file__).parent.parent for repo-root-relative paths"
  - "Manifest keyed by str(bill_id) in memory, written as JSON list to disk"

requirements-completed:
  - PIPE-01

# Metrics
duration: 20min
completed: "2026-05-08"
---

# Phase 01 Plan 01: Fetch Summary

**Knesset OData paginated metadata fetch + fs.knesset.gov.il PDF download producing crash-safe manifest.json with per-law bill_id, name_he, publication_date, sub_type_id, pdf_path, pdf_url**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-08T18:00:00Z
- **Completed:** 2026-05-08T18:20:07Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Implemented `pipeline/fetch.py` with paginated KNS_Bill OData fetch (100 laws/page), PDF URL resolution via KNS_DocumentBill, and chunked PDF download
- Added crash recovery via manifest.json checkpoint saves every PAGE_SIZE laws
- Smoke tested with `--limit 3`: 3 manifest entries written, 2 PDFs downloaded (1 law had no Reshumot PDF — handled gracefully as pdf_path=None)
- Added pymupdf==1.25.5 to pipeline/requirements.txt for use by convert.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pymupdf to requirements.txt** - `74d63c5` (chore)
2. **Task 2: Write pipeline/fetch.py** - `810847d` (feat)

## Files Created/Modified

- `pipeline/fetch.py` - OData fetch + PDF download script with CLI --limit flag
- `pipeline/requirements.txt` - Added pymupdf==1.25.5 in alphabetical order
- `.gitignore` - Added data/raw/ and *.pdf patterns (runtime output)

## Decisions Made

- Used `requests` directly against OData API — `knesset-data` package wraps OData but does not support the `$filter` query parameter needed for `StatusID eq 118`
- PDF URL construction: OData `FilePath` field uses `//N/path` format; prepend `https:` to get `https://N/path` (direct to fs.knesset.gov.il)
- When multiple PDFs exist per law (e.g., original + amendment), pick the one with the latest `LastUpdatedDate` to get the most current version
- MAX_RETRIES=3 with RETRY_DELAY=2s per T-01-05 (server rate-limiting mitigation)
- `int(bill_id)` cast in `fetch_pdf_url` and path construction per T-01-06 (path traversal guard)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added data/raw/ and *.pdf to .gitignore**
- **Found during:** Task 2 (fetch.py execution smoke test)
- **Issue:** After running `--limit 3`, `data/` directory with PDFs and manifest.json appeared as untracked in git. Plan notes these are runtime outputs not to be committed, but .gitignore lacked the pattern
- **Fix:** Added `data/raw/` and `*.pdf` patterns to .gitignore
- **Files modified:** .gitignore
- **Verification:** `git status --short` shows `data/` no longer as untracked after adding pattern
- **Committed in:** 810847d (included with Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical configuration)
**Impact on plan:** Essential to prevent accidental commit of multi-GB PDF corpus. No scope creep.

## Issues Encountered

- `pdf_path` stored in manifest.json uses the absolute worktree path at runtime. When the pipeline runs from the main repo, the path will reflect that location correctly since `DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "israel"` resolves relative to the script's location. No action needed.

## Known Stubs

None — all manifest fields are populated from live OData data. Laws with no Reshumot PDF have `pdf_path: null` and `pdf_url: null` (legitimate case, not a stub).

## Threat Flags

None — all trust boundaries and mitigations are documented in the plan's threat model and implemented in fetch.py (T-01-05, T-01-06).

## User Setup Required

None — pipeline runs fully from WSL2 using `~/.venv-codex` virtual environment. No credentials or external service registration needed.

## Next Phase Readiness

- `pipeline/fetch.py` is ready for production use: run `python pipeline/fetch.py` (no --limit) to fetch all 7,699 enacted laws
- `manifest.json` schema matches what convert.py will read (bill_id, name_he, publication_date, sub_type_id, pdf_path, pdf_url)
- No blockers for Plan 02 (convert.py) or Plan 03 (validate.py)

## Self-Check

- [x] pipeline/fetch.py exists at worktree path
- [x] pipeline/requirements.txt contains pymupdf==1.25.5
- [x] `python pipeline/fetch.py --help` exits 0
- [x] Smoke test `--limit 3` produced manifest.json with 3 entries, all required fields present
- [x] 2 PDFs in data/raw/israel/ (1 law had no PDF — handled gracefully)
- [x] Task 1 commit: 74d63c5
- [x] Task 2 commit: 810847d

## Self-Check: PASSED

---
*Phase: 01-pipeline*
*Completed: 2026-05-08*
