---
phase: 07-shared-pipeline-core
plan: 01
subsystem: testing
tags: [characterization-testing, golden-fixtures, refactor-safety-net, python-stdlib, git-diff-fingerprint]

# Dependency graph
requires:
  - phase: none
    provides: Wave 1 — no upstream dependency
provides:
  - "pipeline/tests/capture_golden.py — one-shot BEFORE-fingerprint capture for all four Phase 7 gates"
  - "pipeline/tests/golden/frontmatter_111.json — build_frontmatter over all 111 converted entries, frozen clock, sha256 dab1887e…"
  - "pipeline/tests/golden/next_batch.json — get_next_batch selection at counts 1/5/25/100"
  - "pipeline/tests/golden/status.txt — exact 6-line `batch_import.py --status` stdout"
  - "pipeline/tests/golden/link_resolver_all.diff — the diff link_resolver --all produces over laws/israel/ from clean HEAD"
  - "Off-repo backup of the gitignored, git-unrecoverable import state at $HOME/codex-civica-backups/phase07/"
affects: [07-02 verify_golden gate, 07-03 split_frontmatter extraction, 07-04 progress extraction, 07-05 deploy extraction, 07-06 render_frontmatter extraction]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frozen-clock monkeypatch in the harness, never in production code"
    - "git diff as the output fingerprint for an in-place-mutating pipeline"
    - "Before/after differential gate instead of diff-vs-HEAD"

key-files:
  created:
    - pipeline/tests/capture_golden.py
    - pipeline/tests/golden/frontmatter_111.json
    - pipeline/tests/golden/next_batch.json
    - pipeline/tests/golden/status.txt
    - pipeline/tests/golden/link_resolver_all.diff
  modified: []

key-decisions:
  - "Zero new dependencies — the harness is stdlib-only; pytest deliberately not installed"
  - "The frozen-clock shim lives in the harness; reconcile.py is not given an injectable clock"
  - "status.txt is captured by shelling out to the real CLI, not by re-implementing print_status"
  - "The non-empty link-resolver diff (8 files / 22+ / 22-) is captured as-is: it is pre-existing Class-A staleness plus the deferred _STRIP_MG_INDEX bug, and it is exactly what the differential gate must reproduce"

patterns-established:
  - "Pattern 1: sys.path bootstrap for scripts one level below pipeline/ — PIPELINE_DIR = Path(__file__).parent.parent, then bare pipeline imports with # noqa: E402"
  - "Pattern 2: every proof run that touches laws/israel/ is bracketed by `git checkout -- laws/israel/` and asserts `git status --porcelain laws/israel/` is empty before returning"
  - "Pattern 3: fingerprints are one sha256 over json.dumps(mapping, ensure_ascii=False, sort_keys=True), with the mapping written alongside so a mismatch is inspectable"

requirements-completed: [SC-2a, SC-2c, SC-3, SC-3b]

# Metrics
duration: 4min
completed: 2026-08-09
---

# Phase 7 Plan 01: Safety Net + BEFORE Fingerprints Summary

**Phase 7's verification substrate now exists: the gitignored import state has a checksum-verified copy outside the repo, and four committed golden fixtures pin the current behaviour of `build_frontmatter`, `get_next_batch`, `--status`, and `link_resolver --all` — every captured value matched the research baseline exactly, with `laws/israel/` left byte-identical to HEAD.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-09T13:37:55Z
- **Completed:** 2026-08-09T13:41:30Z
- **Tasks:** 3 of 3
- **Files created:** 5 (1 harness, 4 fixtures)
- **Files modified:** 0 production files — no line of pipeline code was touched

## Accomplishments

### Task 1 — Off-repo backup of the git-unrecoverable import state

`data/raw/` is gitignored (`.gitignore:2`), so `git checkout` cannot restore `import_progress.json`. It holds the only record of which 111 laws are converted, the 23-entry priority queue, and `total_deployed`. `done` could be rebuilt from `ls laws/israel/`; `priority` and `total_deployed` could not.

- **Backup path:** `/home/yuvalv/codex-civica-backups/phase07/` — verified outside `/mnt/c/Dev/codex-civica`
- **Files:** `import_progress.json` (1867 B), `manifest_laws.json` (732073 B), copied with `cp -p`
- **Proof:** `cmp` exits 0 on both live↔backup pairs; `MANIFEST.sha256` holds 4 lines
- **Checksums:**
  - `47c65901ebeaf28d5e7697e71af515eac3cd6da0968787a303ea6ce2426429e4` — `import_progress.json` (both copies)
  - `e232b529fa5168f7189a41d476644e2cd99871a7d7503a44d4b06d82db9a5718` — `manifest_laws.json` (both copies)
- **Restore command for a future session:**

```bash
cp $HOME/codex-civica-backups/phase07/import_progress.json data/raw/israel/
cp $HOME/codex-civica-backups/phase07/manifest_laws.json  data/raw/israel/
```

No repo file was written or staged by this task, so it produced no commit by design.

### Task 2 — `pipeline/tests/capture_golden.py` (commit `f4269c2`)

Stdlib-only capture harness, ~230 lines. Four capture functions behind a `--only NAME` selector, `main() -> int`, `raise SystemExit(main())`.

- `capture_frontmatter()` — installs the frozen-clock shim (`reconcile.dt` rebound to a shim exposing `timezone` and a nested `datetime.now()` returning 2000-01-01 UTC) *before* calling `build_frontmatter`, then maps `{id: frontmatter}` over manifest entries present in `progress["done"]`.
- `capture_batch()` — read-only `load_manifest()` / `load_progress()`; records the ordered id list at counts 1/5/25/100. `save_progress` is never called.
- `capture_status()` — shells out to the real CLI (list-form `subprocess.run`) and writes stdout verbatim; `--status` is the only invocation form used.
- `capture_link_resolver()` — `git checkout -- laws/israel/` → purge `__pycache__` → run `link_resolver.py --all` → `git diff laws/israel/` into the fixture → `git checkout --` again → assert `git status --porcelain laws/israel/` is empty, returning non-zero if not.

Security-relevant properties, all asserted mechanically: no `shell=True`, no `git add`, no `import yaml`, no `GEMINI_API_KEY` reference anywhere under `pipeline/tests/`.

### Task 3 — Four BEFORE fingerprints captured and committed (commit `cf95d4e`)

Run under `~/.venv-codex/bin/python` from the repo root. **Every value matched the research baseline exactly — no re-baselining was required.**

| Fixture | Captured value | Research baseline | Match |
|---|---|---|---|
| `frontmatter_111.json` | `entries=111 sha256=dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37` | `entries=111`, `dab1887e…` | ✅ |
| `next_batch.json` | `1→0b9e40e316c044d1`, `5→20f03642a354d5cd`, `25→ea819da6b1647539`, `100→50e6737b1a7a24d2`; first three ids at every count ≥5 = `2001111`, `2001108`, `2001070` | same four short SHAs; same three ids | ✅ |
| `status.txt` | 6 lines — `Total laws: 1076` / `With PDF: 718` / `Converted: 111` / `Failed: 0` / `Pending: 607` / `Total deployed: 111` | identical 6 lines | ✅ |
| `link_resolver_all.diff` | 8 files changed, 22 insertions(+), 22 deletions(-) — 21373 bytes | ~8 files / 22 / 22 | ✅ |

`laws/israel/` was restored and verified empty under `git status --porcelain` both by the harness itself and independently before staging. Only paths under `pipeline/tests/` were staged.

## Task Commits

| Task | Name | Commit | Files |
|---|---|---|---|
| 1 | Off-repo backup of gitignored import state | *(none — writes only outside the repo)* | `$HOME/codex-civica-backups/phase07/{import_progress.json,manifest_laws.json,MANIFEST.sha256}` |
| 2 | Write `pipeline/tests/capture_golden.py` | `f4269c2` | `pipeline/tests/capture_golden.py` |
| 3 | Capture + commit the four BEFORE fingerprints | `cf95d4e` | `pipeline/tests/golden/{frontmatter_111.json,next_batch.json,status.txt,link_resolver_all.diff}` |

## Verification Evidence

```
BACKUP_OK                       # cmp on both pairs + MANIFEST.sha256 non-empty (4 lines)
OUTSIDE_REPO_OK                 # realpath not under /mnt/c/Dev/codex-civica
PARSE_OK / SHAPE_OK             # ast.parse + sys.path.insert + raise SystemExit(main()) + 0 shell=True
SHA_OK                          # frontmatter_111.json == dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37
TREE_CLEAN                      # git status --porcelain laws/israel/ empty
entries= 111 / status_lines=6 / BATCH_OK
git diff --cached --name-only → only pipeline/tests/ paths (0 outside)
grep -rl 'GEMINI_API_KEY|AIza' pipeline/tests/ → 0 files
```

Source assertions from the plan's acceptance criteria, all passing: `PIPELINE_DIR = Path(__file__).parent.parent` (1), `sys.path.insert(0, str(PIPELINE_DIR))` (1), `reconcile.dt = ` (1), `shell=True` (0), `"add"` (0), `import yaml` (0), lines matching `batch_import.py` without `--status` (0).

## Deviations from Plan

**One, structural and pre-agreed by the plan text itself:**

**1. [Rule 3 — Blocking] `main()` signature changed from `main(only=...)` to `main(argv=...)` with argparse inside**
- **Found during:** Task 2 verification
- **Issue:** The plan's own automated verify greps for the literal string `raise SystemExit(main())`, which is incompatible with `raise SystemExit(main(only=args.only))` (the `link_resolver.py` CLI shape the plan also cites).
- **Fix:** Moved the `argparse` block inside `main(argv: list[str] | None = None) -> int` (defaulting to `sys.argv`), so the CLI block is exactly `raise SystemExit(main())` while `--only NAME` still works and `main()` remains callable programmatically.
- **Files modified:** `pipeline/tests/capture_golden.py`
- **Commit:** `f4269c2`

No Rule 1 (bug), Rule 2 (missing critical functionality), or Rule 4 (architectural) deviations. No authentication gates. No package installs.

## Constraints Honoured

- `~/.venv-codex/bin/python` used explicitly for every Python invocation — the ambient `python3` resolves to the in-repo NTFS `.venv/`.
- `batch_import.py` invoked **only** with `--status` (factory import stays paused at 111/718).
- `deploy()` never executed, never imported, never referenced.
- `_STRIP_MG_INDEX` not touched — its current (buggy) output is captured as the golden fingerprint, which is the point of the differential gate.
- `git add -A` never used; every stage was an explicit `pipeline/tests/` path.
- `laws/israel/` restored with `git checkout --` and verified empty via `git status --porcelain` after the capture run.

## Known Stubs

None. Every artifact this plan promised is real, populated, and independently verified against a pre-recorded baseline.

## Deferred Issues

Both pre-existing, both already recorded in `STATE.md` Todos — neither introduced nor touched here:

- `link_resolver._STRIP_MG_INDEX` non-idempotency corrupting `2000326` / `2000390` / `2000416` / `2000595` on repeated `--all` runs. User-deferred to v1.0 Phase 4 follow-up. Its output is deliberately baked into `link_resolver_all.diff`.
- `pipeline/requirements.txt` is stale (missing `python-dotenv`, `google-genai`, both imported by `reconcile.py`). Out of scope for Phase 7.

## Notes for Next Plan (07-02)

- The four fixtures are tracked; `verify_golden.py` must diff against `pipeline/tests/golden/`, never against a `/tmp` file.
- Reuse `capture_golden.py`'s frozen-clock shim and `_git()` helper shapes verbatim so capture and verify cannot drift.
- `capture_golden.py --only <frontmatter|batch|status|link_resolver>` re-captures a single fixture if a baseline ever legitimately moves.
- Research validity: the fixtures are invalidated by any commit touching `laws/israel/`, `pipeline/link_resolver.py`, `pipeline/reconcile.py`, or `data/raw/israel/import_progress.json`.

## Self-Check: PASSED

All 5 claimed repo artifacts and the off-repo `MANIFEST.sha256` exist on disk; both claimed commits (`f4269c2`, `cf95d4e`) exist in git history.
