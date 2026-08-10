---
phase: 07-shared-pipeline-core
plan: 04
subsystem: pipeline
tags: [extraction-refactor, shared-core, progress-tracking, byte-identity]

# Dependency graph
requires:
  - phase: 07-03
    provides: "pipeline/common/ package + proven sys.path[0] import mechanics"
provides:
  - "pipeline/common/progress.py — load_progress/save_progress/get_next_batch/print_status, parameterised by path, id_keys, source_key, source_label"
  - "batch_import.py reduced to four thin wrappers over common.progress"
affects: [07-05 deploy extraction, 07-06 render_frontmatter extraction, 07-07 close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "print_status's column alignment reproduced via `f'{label}:'.ljust(17) + value` — the 17-char prefix width was measured empirically across all six original f-strings, not assumed"
    - "get_next_batch's `if any(e is entry for e in batch)` identity check kept verbatim — dict rows are unhashable and may compare equal while distinct"

key-files:
  created:
    - pipeline/common/progress.py
  modified:
    - pipeline/batch_import.py

key-decisions:
  - "print_status's source_label formatting uses ljust(17) rather than substituting into a fixed f-string, since the label text itself (\"With PDF\") varies in length for future non-Israel callers"

patterns-established:
  - "Column-aligned print statements in a parameterised extraction: measure the exact prefix width from the original source before generalising, never eyeball it"

requirements-completed: [SC-1, SC-3, SC-3b, SC-3c, SC-4]

# Metrics
duration: 15min
completed: 2026-08-10
---

# Phase 7 Plan 04: Extract Progress Tracking Summary

**`pipeline/common/progress.py` now owns progress load/save, batch selection, and status printing — parameterised by path, id keys, source key, and label — and `batch_import.py` is reduced to four thin wrappers with all 12 call sites untouched. Full `verify_golden.py` gate is 6/6 green.**

## Accomplishments

### Task 1 — `pipeline/common/progress.py`

Ported `load_progress`, `save_progress`, `get_next_batch`, `print_status` verbatim except for the
parameterised names called out in the plan. `save_progress` keeps `json.dump(..., ensure_ascii=False,
indent=2)` with no trailing newline. `get_next_batch` takes `id_keys=("law_id", "bill_id")` and
`source_key="pdf_path"`, with the `if any(e is entry for e in batch):` identity check preserved
exactly. `print_status` takes `source_label: str = "With PDF"`; verified the six-line output is
byte-identical to `golden/status.txt` by direct call, then again via `batch_import.py --status`.

Round-trip verified: `save_progress(tmp, json.loads(live_file))` produces bytes identical to
`data/raw/israel/import_progress.json`.

### Task 2 — Repoint `batch_import.py`

Deleted the four function bodies, replaced with thin wrappers delegating to `_progress.*` bound to
this module's own `PROGRESS_PATH`. Added `from common import progress as _progress` in the local
import position. `git diff` shows zero changes at any of the 12 call-site lines.

**Full gate — 6/6 green:**

```
$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py
INFO split: 112 files + 6 edge cases, 0 mismatches
INFO frontmatter: entries=111 sha256=dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37
INFO batch: 4 counts match
INFO progress-roundtrip: 1867 bytes, byte-identical
INFO status: 6 lines match
INFO link-resolver: differential matches fixture (15101 bytes), laws/israel/ restored
6/6 checks passed
EXIT=0
```

`data/raw/israel/import_progress.json` sha256 (`47c65901...`) matches the 07-01 off-repo backup
manifest exactly — no task wrote the real progress file. `git status --porcelain laws/israel/` empty.

**`--structure` progress: 7 errors → 2.** Remaining: `common/deploy.py` missing, `batch_import` still
implements `deploy` locally — both 07-05's scope.

## Task Commits

| Task | Name | Commit | Files |
|---|---|---|---|
| 1 | Create `pipeline/common/progress.py` | `81b4bb1` | `pipeline/common/progress.py` |
| 2 | Repoint `batch_import.py` to thin wrappers, run the gate | `a82649c` | `pipeline/batch_import.py` |

## Verification Evidence

```
PROGRESS_ROUNDTRIP_OK
MODULE_OK                                        # identity-check grep, boundary-import grep
STATUS_MATCH                                     # print_status() direct call vs golden/status.txt
STATUS_OK                                        # batch_import.py --status vs golden/status.txt
GATE_GREEN 6/6
sha256(data/raw/israel/import_progress.json) == backup manifest value
git status --porcelain laws/israel/ -> empty
git diff --cached --name-only at each commit listed exactly one path
```

## Deviations from Plan

None requiring a rule citation. One clarification: the plan left the exact column-alignment mechanism
for `source_label` open ("hard-code the default padding and substitute only the label text" as a
fallback). Used `f"{source_label}:".ljust(17) + value` — measured the 17-char prefix width directly
from all six original f-strings (`Total laws:      `, `With PDF:        `, etc., each exactly 17
characters before the value) rather than assuming it, then confirmed byte-identical output.

## Constraints Honoured

- `~/.venv-codex/bin/python` used explicitly throughout.
- `batch_import.py` invoked only via `--status`; factory import untouched, still paused at 111/718.
- No write to the real `import_progress.json`; round-trip check used a temp dir.
- Explicit staging only (`git add pipeline/common/progress.py`, then `git add pipeline/batch_import.py`), never `git add -A`.
- `DEPLOY_EVERY` threshold block, `load_manifest`/`save_manifest`, `_process_law`, `run_batch`, and the deferred `import link_resolver` all untouched.

## Notes for Next Plan (07-05)

- `--structure` remaining checklist: `common/deploy.py` (missing) + `batch_import`'s `deploy` (still local). Watch the `SITE_DIR` depth trap flagged in 07-PATTERNS.md — `common/` is one directory deeper than `pipeline/`, so `deploy()` must take `site_dir` as a parameter, not derive it via `Path(__file__).parent.parent`.
- `deploy()` must never be executed during this phase (standing constraint) — gate on import-time smoke + source review only.

## Self-Check: PASSED

- `pipeline/common/progress.py` — FOUND
- `pipeline/batch_import.py` — FOUND (modified)
- Commit `81b4bb1` — FOUND in git history
- Commit `a82649c` — FOUND in git history
- Full `verify_golden.py` exits 0 (6/6); working tree clean except this summary + STATE.md.
