---
phase: 07-shared-pipeline-core
plan: 02
subsystem: testing
tags: [characterization-testing, golden-fixtures, refactor-gate, negative-control, python-stdlib, exit-code-contract]

# Dependency graph
requires:
  - phase: 07-01
    provides: "capture_golden.py (frozen-clock shim, _git helper) + the four golden fixtures under pipeline/tests/golden/"
provides:
  - "pipeline/tests/verify_golden.py — the Phase 7 gate; exit 0 only when every selected fingerprint is byte-identical"
  - "--quick (~2.4s, mutates nothing): --split + --frontmatter + --batch + --progress-roundtrip + --status"
  - "default no-flag full suite (~8s): --quick plus the restore-bracketed link-resolver differential"
  - "--structure: opt-in SC-1/SC-4b layout gate, currently red-by-design; doubles as a 07-03..07-06 progress tracker"
  - "Proof that the gate discriminates: two one-line production perturbations each drove it red with a specific, actionable message"
affects: [07-03 split_frontmatter extraction, 07-04 progress extraction, 07-05 deploy extraction, 07-06 render_frontmatter extraction, 07-07 close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gate scripts return int from main(argv); `raise SystemExit(main())`; a non-empty diff is exit 1, never a warning"
    - "Negative control as an acceptance criterion — a gate never observed failing is not known to have teeth"
    - "Failure messages name the first differing law_id / line, not just the hash"
    - "Opt-in forward-looking check (--structure) excluded from the default suite so it can be red-by-design"

key-files:
  created:
    - pipeline/tests/verify_golden.py
  modified: []

key-decisions:
  - "--structure asserts *delegation*, not absence, for the four batch_import symbols — 07-PATTERNS.md mandates same-named thin wrappers there, so a literal `^def NAME` absence check could never pass"
  - "The frozen-clock shim and _git() helper are copied verbatim from capture_golden.py rather than imported, per 07-01's drift note"
  - "--split hard-fails if the corpus is not 112 files: a changed corpus invalidates every fixture, so silently checking fewer files would weaken the gate"
  - "The progress-file symbol pair in --structure is composed via an f-string so this file contains zero direct references to the progress writer — the gate must never write import_progress.json"

patterns-established:
  - "PASS/FAIL summary printed with print() (always visible) while diagnostics go through logging at WARNING for --quick, INFO otherwise"
  - "Every check is a `check_*() -> bool`; main() aggregates, so adding a criterion is one function plus one registry entry"

requirements-completed: [SC-2a, SC-2b, SC-2c, SC-2d, SC-3, SC-3b, SC-3c]

# Metrics
duration: 12min
completed: 2026-08-09
---

# Phase 7 Plan 02: The Gate Summary

**`pipeline/tests/verify_golden.py` now re-derives all four BEFORE fingerprints in one command and exits non-zero on any drift — proven green on completely unmodified source (6/6 checks, `laws/israel/` byte-identical afterwards) and proven red twice under deliberate one-line production perturbations, each time naming the exact law_id or output line that moved.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 2 of 2
- **Files created:** 1 (`pipeline/tests/verify_golden.py`, 547 lines, stdlib only)
- **Files modified:** 0 production files — every perturbation was reverted with `git checkout --`
- **Runtime:** `--quick` 2.4s, full suite 8.0s (both inside the 5s/2s targets set in 07-VALIDATION.md, full suite slightly over because it runs `link_resolver --all` over 112 files)

## Accomplishments

### Task 1 — `pipeline/tests/verify_golden.py` (commit `f880436`)

Seven checks, one function each, all returning `bool`; `main(argv=None) -> int` aggregates and
`raise SystemExit(main())` carries the result to the shell.

| Flag | What it re-derives | Fixture / expected |
|---|---|---|
| `--split` | `link_resolver.split_frontmatter` vs `cross_linker._split_frontmatter` over 112 corpus files + the 6 research edge cases | 0 mismatches |
| `--frontmatter` | `build_frontmatter` over all 111 converted entries, frozen clock, `json.dumps(..., ensure_ascii=False, sort_keys=True)` | `golden/frontmatter_111.json`, sha256 `dab1887e…` |
| `--batch` | `get_next_batch` selection at counts 1/5/25/100 | `golden/next_batch.json` |
| `--progress-roundtrip` | in-memory `io.StringIO` re-serialisation of the live progress file | 1867 bytes, byte-identical |
| `--status` | stdout of the status CLI | `golden/status.txt`, 6 lines |
| `--structure` | SC-1 layout + SC-4b import boundary | opt-in, red until 07-06 |
| *(no flag)* | `--quick` + the link-resolver differential | `golden/link_resolver_all.diff` |

Design details worth carrying forward:

- **Diagnostics name the thing that moved.** `--frontmatter` reports the first differing `law_id` *and* the first differing line inside it, not just a hash. `--batch` reports the first differing index per count. `--status` and the differential report the first differing line. `_first_diff_line()` is shared.
- **The fixture itself is checked.** If the rebuilt blob equals the fixture but the fixture's sha256 is not `dab1887e…`, that is a failure — it means the fixture was edited to match a regression.
- **`--split` hard-fails on a corpus size other than 112**, pointing at `capture_golden.py` for re-baselining, because a changed corpus invalidates all four fixtures at once.
- **Safety properties, all mechanically asserted:** 0 occurrences of `shell=True`, 0 of `"add"`, 0 of the API-key name, 0 direct references to the progress writer; every line mentioning the batch CLI also contains `--status`. All subprocess calls are list-form.
- **Restore discipline is a hard failure, not a warning.** The differential runs `git checkout -- laws/israel/` before and after, then asserts `git status --porcelain laws/israel/` is empty; a surviving dirty tree returns 1 even if the diff itself matched. Every push to `main` auto-deploys, so an unrestored tree is a publish risk.

### Task 2 — Positive and negative controls

**Positive control — the gate is green on untouched source.**

```
$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py --quick        # 2.4s
PASS  --split
PASS  --frontmatter
PASS  --batch
PASS  --progress-roundtrip
PASS  --status
5/5 checks passed
EXIT=0

$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py                # 8.0s
INFO split: 112 files + 6 edge cases, 0 mismatches
INFO frontmatter: entries=111 sha256=dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37
INFO batch: 4 counts match
INFO progress-roundtrip: 1867 bytes, byte-identical
INFO status: 6 lines match
INFO link-resolver: differential matches fixture (15101 bytes), laws/israel/ restored
PASS  --split
PASS  --frontmatter
PASS  --batch
PASS  --progress-roundtrip
PASS  --status
PASS  link_resolver
6/6 checks passed
EXIT=0
```

(`15101` is the fixture's character count; the file is 21373 *bytes* on disk — Hebrew is multi-byte. Same content, different unit from 07-01's report.)

**Negative control 1 — `reconcile.py:178`, the `generated_by` literal.**

Perturbed `"generated_by: pipeline/reconcile.py",` → `"generated_by: pipeline/reconcile.py (PERTURBED)",`:

```
$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py --frontmatter
ERROR frontmatter: sha256 d479585c8bf4557c31232d7c7834f6a5aa404e4f20ba29004f6587c2ec5722de, expected dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37
ERROR frontmatter: first differing law_id=2000001 — line 18: expected 'generated_by: pipeline/reconcile.py', got 'generated_by: pipeline/reconcile.py (PERTURBED)'
ERROR gate RED — failing checks: --frontmatter
FAIL  --frontmatter
0/1 checks passed
EXIT=1
```

After `git checkout -- pipeline/reconcile.py`:

```
RESTORED=[]
INFO frontmatter: entries=111 sha256=dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37
PASS  --frontmatter
1/1 checks passed
EXIT=0
```

**Negative control 2 — `batch_import.py:309`, the `With PDF` label.**

Perturbed `print(f"With PDF:        {with_pdf}")` → `print(f"With PDFs:       {with_pdf}")` (same total width, so only the label text moved):

```
$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py --status
ERROR status: stdout differs from fixture — line 2: expected 'With PDF:        718', got 'With PDFs:       718'
ERROR gate RED — failing checks: --status
FAIL  --status
0/1 checks passed
EXIT=1
```

After `git checkout -- pipeline/reconcile.py pipeline/batch_import.py`:

```
PIPELINE_SRC_DIRTY=[]
INFO status: 6 lines match
PASS  --status
1/1 checks passed
EXIT=0
```

**Opt-in `--structure`, red by design** (recorded here as the 07-03..07-06 to-do list; it will go green when the last extraction lands):

```
$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py --structure
ERROR structure: missing …/pipeline/common/__init__.py
ERROR structure: missing …/pipeline/common/frontmatter.py
ERROR structure: missing …/pipeline/common/progress.py
ERROR structure: missing …/pipeline/common/deploy.py
ERROR structure: link_resolver still defines split_frontmatter locally
ERROR structure: cross_linker still defines _split_frontmatter locally
ERROR structure: batch_import still implements load_progress locally (expected a thin delegation into common)
ERROR structure: batch_import still implements <the progress writer> locally (expected a thin delegation into common)
ERROR structure: batch_import still implements get_next_batch locally (expected a thin delegation into common)
ERROR structure: batch_import still implements print_status locally (expected a thin delegation into common)
ERROR structure: batch_import still implements deploy locally (expected a thin delegation into common)
EXIT=1
```

## Task Commits

| Task | Name | Commit | Files |
|---|---|---|---|
| 1 | Write `verify_golden.py` with the full flag set | `f880436` | `pipeline/tests/verify_golden.py` |
| 2 | Prove green now, red under perturbation | *(none — proof only; both perturbations reverted with `git checkout --`, no repo change to commit)* | — |

At staging time `git diff --cached --name-only` listed exactly one path: `pipeline/tests/verify_golden.py`.

## Verification Evidence

```
PARSE_OK / FLAGS_OK                                   # ast.parse + all 7 flags present + 0 shell=True
save_progress count: 0                                # round-trip is in-memory only
shell=True count: 0
batch_import.py lines without --status: 0
sha literal dab1887e…: 1
GEMINI_API_KEY refs: 0                                # T-07-01 mitigated
"add" refs: 0                                         # gate never stages anything
main annotated -> int (line 493); file ends with `raise SystemExit(main())`
GATE_GREEN_SOURCE_UNTOUCHED                           # --quick && full && laws/israel/ clean && 4 pipeline modules clean
git status --porcelain (whole tree) → empty after everything
sha256 data/raw/israel/import_progress.json == 47c65901…  # matches 07-01's off-repo backup, untouched
```

## Deviations from Plan

**Three, all small, none changing the gate's contract.**

**1. [Rule 1 — Bug] `--structure` asserts delegation, not absence, for the four `batch_import` symbols**

- **Found during:** Task 1, writing `check_structure`
- **Issue:** The plan says to assert `load_progress` / the progress writer / `get_next_batch` / `print_status` / `deploy` are "no longer *defined* (regex on `^def NAME`)". But `07-PATTERNS.md` (the binding design for 07-04/07-05) explicitly keeps **same-named thin wrappers** in `batch_import.py` so its 12 call sites stay untouched. A literal `^def NAME` absence check could therefore never pass, even after 07-06 — a permanently-red check is a dead check, which is exactly the silent-degradation failure mode T-07-05 exists to prevent.
- **Fix:** `^def NAME` absence is still enforced for the two symbols that really are deleted (`link_resolver.split_frontmatter`, `cross_linker._split_frontmatter`). For the orchestrator's five symbols the check parses the module with `ast` and requires each definition to be a *thin delegation* — one statement after any docstring, and that statement a call on an attribute (i.e. `_progress.load_progress(...)`). A local re-implementation fails; the mandated wrapper passes.
- **Files modified:** `pipeline/tests/verify_golden.py`
- **Commit:** `f880436`

**2. [Rule 3 — Blocking] Line numbers for both perturbation targets were off by one / seven**

- **Found during:** Task 2
- **Issue:** The plan names `reconcile.py` line 179 and `batch_import.py` line 302. The actual literals are at `reconcile.py:178` (`"generated_by: pipeline/reconcile.py",`) and `batch_import.py:309` (`print(f"With PDF:        {with_pdf}")`). Line 302 is inside `print_status`'s `pending` comprehension, not a label.
- **Fix:** Perturbed by exact string match (asserting a single occurrence) rather than by line number, so the experiment targets the intended literal regardless of drift.
- **Files modified:** none persisted — both files restored with `git checkout --`
- **Commit:** n/a

**3. [Rule 3 — Blocking] The commit landed at the end of Task 1 rather than the end of Task 2**

- **Found during:** Task 2
- **Issue:** The plan places the `git add pipeline/tests/verify_golden.py` commit inside Task 2, but the GSD executor contract requires one atomic commit per task, and Task 2 produces no repo change by construction (both perturbations are reverted).
- **Fix:** Committed the gate at the end of Task 1 once its own acceptance criteria passed, staging only `pipeline/tests/verify_golden.py` — which satisfies Task 2's "`git diff --cached --name-only` lists only `verify_golden.py`" criterion at the moment of staging. Task 2 is a proof task with no commit, exactly as 07-01's Task 1 was.
- **Commit:** `f880436`

No Rule 2 (missing critical functionality) or Rule 4 (architectural) deviations. No authentication gates. No package installs. No new dependency.

## Constraints Honoured

- `~/.venv-codex/bin/python` used explicitly for every Python invocation.
- `_STRIP_MG_INDEX` untouched — its buggy output is the golden baseline the differential reproduces.
- `deploy()` never executed, never imported, never called. `--structure` only *reads* its definition via `ast`.
- The batch CLI invoked **only** with `--status`; the factory import stays paused at 111/718.
- `capture_golden.py`'s frozen-clock shim and `_git()` helper reused verbatim, per 07-01's drift note.
- `laws/israel/` restored and verified empty under `git status --porcelain` after every proof run; production source restored and verified clean after both negative controls.
- `git add -A` never used; `git clean` / `git stash` / `git reset` never used.

## Threat Model Coverage

| Threat ID | Disposition | Evidence |
|---|---|---|
| T-07-01 secret leakage | mitigated | 0 occurrences of the API-key name in the file; the gate never reads or logs `pipeline/.env` |
| T-07-02 `laws/israel/` tampering | mitigated | Differential brackets the run with `git checkout --` and returns 1 on a surviving dirty tree; whole-tree `git status --porcelain` empty at close |
| T-07-03 command injection | mitigated | 0 `shell=True`; all argv list-form; no caller string interpolated into argv; batch CLI only with `--status` |
| T-07-04 progress-file loss | mitigated | Round-trip is pure `io.StringIO`; sha256 of the live file still matches 07-01's off-repo backup |
| T-07-05 silent gate degradation | mitigated | Two negative controls recorded verbatim above, each producing exit 1 with a specific message |

No new threat surface: the file adds no network call, no new dependency, and no new file write outside the restore-protected differential.

## Known Stubs

None. Every flag is implemented and exercised; `--structure` is deliberately red because the code it checks for does not exist yet, which is a real result, not a stub.

## Deferred Issues

None introduced. The two pre-existing items (`_STRIP_MG_INDEX` non-idempotency, stale `pipeline/requirements.txt`) are unchanged and already tracked in `STATE.md` Todos.

## Notes for Next Plan (07-03)

- Run `~/.venv-codex/bin/python pipeline/tests/verify_golden.py --quick` after every task commit and the full suite before closing the plan — this is now the phase's sampling contract.
- `--structure`'s error list is your checklist: it names every file still missing from `pipeline/common/` and every symbol still implemented in an Israel module.
- After 07-03 the `--split` check keeps working only if **both** names still resolve — `link_resolver.split_frontmatter` (direct import) and `cross_linker._split_frontmatter` (aliased import). Do not rename the call site in `cross_linker.py`.
- The fixtures are invalidated by any commit touching `laws/israel/`, `pipeline/link_resolver.py`, `pipeline/reconcile.py`, or `data/raw/israel/import_progress.json`. Re-baseline with `capture_golden.py --only <name>` only with an explicit, recorded reason.

## Self-Check: PASSED

`pipeline/tests/verify_golden.py` exists on disk; commit `f880436` exists in git history; the full suite exits 0 and the working tree is clean.
