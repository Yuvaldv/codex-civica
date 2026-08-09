---
phase: 07-shared-pipeline-core
plan: 03
subsystem: pipeline
tags: [extraction-refactor, shared-core, package-bootstrap, sys-path, import-alias, byte-identity]

# Dependency graph
requires:
  - phase: 07-01
    provides: "golden/link_resolver_all.diff and the three other BEFORE fixtures"
  - phase: 07-02
    provides: "verify_golden.py — the byte-identity gate this extraction is verified against"
provides:
  - "pipeline/common/ — the country-blind package, importable as top-level `common` from every `python pipeline/X.py` entry point"
  - "pipeline/common/frontmatter.py — the single canonical split_frontmatter (was duplicated in two Israel modules)"
  - "Proven import mechanics (sys.path[0] = script dir, cwd-independent, no pipeline/__init__.py) that 07-04/05/06 reuse verbatim"
  - "The aliasing precedent (`import X as _X`) for extractions whose call sites use a private name"
affects: [07-04 progress extraction, 07-05 deploy extraction, 07-06 render_frontmatter extraction, 07-07 close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New shared module = stdlib-only, no path constants derived inside common/ (depth trap), package marker is a lone docstring with no re-exports"
    - "Repoint via import placed after the stdlib block, blank-line separated, before the module's path constants"
    - "Alias the import rather than rename the call site when the consumer's name is private — smallest diff, and it avoids a NameError only reachable behind a live API client"

key-files:
  created:
    - pipeline/common/__init__.py
    - pipeline/common/frontmatter.py
  modified:
    - pipeline/link_resolver.py
    - pipeline/cross_linker.py

key-decisions:
  - "common/frontmatter.py imports nothing but `from __future__ import annotations` — 07-PATTERNS.md's header template shows `import re` / `from pathlib import Path`, but split_frontmatter uses neither and copying them would ship two dead imports"
  - "The `# ─── Frontmatter ───` banner moved WITH the function into common/ rather than being dropped; link_resolver's now-empty banner was deleted, per 07-PATTERNS.md"
  - "Verified cwd-independence empirically (ran the entry point from a foreign cwd) rather than trusting the sys.path[0] doc claim, since T-07-06 is dispositioned `accept` on exactly that property"

patterns-established:
  - "Each extraction closes a known subset of `--structure`'s error list; record the before/after error count as the plan's progress evidence"
  - "Differential-test the new module against BOTH old implementations over the research edge cases before deleting either one"

requirements-completed: [SC-1, SC-2a, SC-2b, SC-2d]

# Metrics
duration: 9min
completed: 2026-08-09
---

# Phase 7 Plan 03: Extract `split_frontmatter` Summary

**`pipeline/common/` now exists and owns the only `split_frontmatter` in the repo — both Israel modules import it instead of defining it, and the full `verify_golden.py` suite is still 6/6 green with `laws/israel/` byte-identical to HEAD, so the extraction is provably zero-behaviour-change.**

## Performance

- **Duration:** ~9 min
- **Tasks:** 2 of 2
- **Files created:** 2 (`pipeline/common/__init__.py` 1 line, `pipeline/common/frontmatter.py` 22 lines — stdlib only)
- **Files modified:** 2 (`link_resolver.py`, `cross_linker.py`; net **+4 / −26** lines)
- **Gate runtime:** `--quick` ~2.4s, full suite ~8s — unchanged from 07-02

## Accomplishments

### Task 1 — `pipeline/common/` with the canonical splitter (commit `e27f75d`)

`__init__.py` is a single docstring line. No re-exports, no `__all__`, no imports — anything more
would widen the import surface that 07-07's country-blindness assertion has to reason about.

`frontmatter.py` carries the shebang + docstring + `from __future__ import annotations` header, the
box-drawing `# ─── Frontmatter ───` banner, and `split_frontmatter` copied character-for-character
from `link_resolver.py:27-36` — double-quoted form kept canonical, `end + 4` / `split += 1`
arithmetic untouched.

**Differentially verified against both old implementations before either was deleted** — 8 cases,
including the 3 named in the acceptance criteria plus three the plan did not name (`'---'` alone,
`'---\n---\n'`, and a frontmatter with no body):

```
DIFFERENTIAL_OK 8 cases
empty-> ('', '')   nofm-> ('', 'no frontmatter')   onlyopen-> ('', '---\nonly-open\n')
SPLIT_OK
BOUNDARY_OK
```

Boundary assertions, all mechanically checked:

| Assertion | Result |
|---|---|
| `grep -rvE '^\s*#' pipeline/common/ \| grep -cE '(from\|import) (reconcile\|batch_import\|link_resolver\|cross_linker)'` | 0 |
| `grep -c 'GEMINI_API_KEY\|load_dotenv' pipeline/common/frontmatter.py` | 0 |
| `grep -c 'import yaml' pipeline/common/frontmatter.py` | 0 |
| `grep -cE '^\s*(import\|__all__)' pipeline/common/__init__.py` | 0 |
| `test ! -f pipeline/__init__.py` | passes — never created |

### Task 2 — Repoint both modules, delete both copies, run the gate (commit `b0fe1be`)

`link_resolver.py`: `from common.frontmatter import split_frontmatter` after the stdlib block,
blank-line separated, immediately before `PIPELINE_DIR`. The local def and its now-empty banner are
gone. Call site at `:216` (`fm, body = split_frontmatter(text)`) shows **zero** diff hunks.

`cross_linker.py`: `from common.frontmatter import split_frontmatter as _split_frontmatter` in the
same position. Call site at `:217` untouched — the alias is why. `cross_link_one()` needs a live
Gemini client, so a missed rename would have surfaced as a `NameError` only during a real API run,
long after the gate had gone green.

Repo-wide, exactly one definition survives:

```
$ grep -rn '^def _\?split_frontmatter' pipeline/ --include=*.py
pipeline/common/frontmatter.py:14:def split_frontmatter(text: str) -> tuple[str, str]:
```

**Full gate — 6/6 green, including the restore-bracketed link-resolver differential:**

```
$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py
INFO split: 112 files + 6 edge cases, 0 mismatches
INFO frontmatter: entries=111 sha256=dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37
INFO batch: 4 counts match
INFO progress-roundtrip: 1867 bytes, byte-identical
INFO status: 6 lines match
INFO link-resolver: differential matches fixture (15101 bytes), laws/israel/ restored
PASS  --split / --frontmatter / --batch / --progress-roundtrip / --status / link_resolver
6/6 checks passed
EXIT=0
```

The link-resolver differential reproducing the fixture is the load-bearing result: it means
`link_resolver.py --all` over 112 files still produces the *exact* 8-file / 22+/22− diff captured in
07-01 — including the pre-existing `_STRIP_MG_INDEX` staleness the baseline deliberately encodes.

**`--structure` progress: 11 errors → 7.** All four errors this plan owned are cleared:

| Error (07-02 baseline) | Now |
|---|---|
| missing `pipeline/common/__init__.py` | **cleared** |
| missing `pipeline/common/frontmatter.py` | **cleared** |
| `link_resolver` still defines `split_frontmatter` locally | **cleared** |
| `cross_linker` still defines `_split_frontmatter` locally | **cleared** |
| missing `common/progress.py`, `common/deploy.py` | still red — 07-04 / 07-05 |
| `batch_import` still implements `load_progress` / `save_progress` / `get_next_batch` / `print_status` / `deploy` locally | still red — 07-04 / 07-05 |

## Task Commits

| Task | Name | Commit | Files |
|---|---|---|---|
| 1 | Create `pipeline/common/` with the canonical `split_frontmatter` | `e27f75d` | `pipeline/common/__init__.py`, `pipeline/common/frontmatter.py` |
| 2 | Repoint both modules, delete both local copies, run the gate | `b0fe1be` | `pipeline/link_resolver.py`, `pipeline/cross_linker.py` |

`git diff --cached --name-only` at each staging listed only those paths. `git add -A` never used.

## Verification Evidence

```
SPLIT_OK / BOUNDARY_OK                            # Task 1 automated verify
DIFFERENTIAL_OK 8 cases                           # new vs link_resolver vs cross_linker
IMPORT_SMOKE_OK                                   # both names resolve, no NameError
  link_resolver.split_frontmatter('---\na\n---\nb') -> ('---\na\n---\n', 'b')
  cross_linker._split_frontmatter('---\na\n---\nb') -> ('---\na\n---\n', 'b')
backfill_seo_meta import OK                       # downstream `from reconcile import ...` consumer still imports
CWD_INDEPENDENT_OK                                # link_resolver.py --help run from a foreign cwd
grep -c '^def split_frontmatter'  link_resolver.py  -> 0
grep -c '^def _split_frontmatter' cross_linker.py   -> 0
grep -c 'from common.frontmatter import split_frontmatter$'                     link_resolver.py -> 1
grep -c 'from common.frontmatter import split_frontmatter as _split_frontmatter' cross_linker.py -> 1
GATE_GREEN                                        # full acceptance block
verify_golden.py            -> EXIT=0, 6/6
verify_golden.py --split    -> EXIT=0, 112 files + 6 edge cases, 0 mismatches
verify_golden.py --quick    -> EXIT=0, 5/5 (run post-commit per the sampling contract)
git status --porcelain laws/israel/  -> empty
git status --porcelain (whole tree)  -> empty
git diff --diff-filter=D HEAD~1 HEAD -> empty     # no file deletions
```

## Deviations from Plan

**One, cosmetic, with no effect on behaviour or on any gate.**

**1. [Rule 3 — Blocking] `common/frontmatter.py` omits the `import re` / `from pathlib import Path` shown in the header template**

- **Found during:** Task 1
- **Issue:** 07-PATTERNS.md's "Module header pattern to copy" block for this file lists `import re` and `from pathlib import Path`. `split_frontmatter` uses neither — it is pure `str` slicing. Copying the block literally would ship two unused imports into the one module the phase most wants to keep minimal, and 07-06's additions (`render_frontmatter`, `quote`) need neither either.
- **Fix:** Kept `from __future__ import annotations` (required for the `tuple[str, str]` annotation style the repo mandates) and omitted the two unused stdlib imports. The plan's own action text supports this — it says "stdlib imports only" as a *ceiling*, and explicitly notes "This module needs no path constants."
- **Files modified:** `pipeline/common/frontmatter.py`
- **Commit:** `e27f75d`

No Rule 1 (bug), Rule 2 (missing critical functionality), or Rule 4 (architectural) deviations. No
authentication gates. No package installs. No new dependency. Zero source lines of
`split_frontmatter` itself were altered.

## Constraints Honoured

- `~/.venv-codex/bin/python` used explicitly for every Python invocation, no exceptions.
- `_STRIP_MG_INDEX` untouched — the differential still reproduces its buggy output byte-for-byte, which is the point.
- `deploy()` never executed, never imported, never called. `batch_import.py` invoked only via the gate's `--status` path; factory import stays paused at 111/718.
- `cross_linker.py`'s call site at `:217` kept the name `_split_frontmatter` via an aliased import, per constraint 4 and 07-02's hand-off note — so `--split` keeps discriminating on both names.
- Full `verify_golden.py` run after the extraction: green, link-resolver differential matched.
- `laws/israel/` restored by the gate and verified empty under `git status --porcelain` before staging and again after committing.
- Explicit staging only. `git add -A`, `git clean`, `git stash`, `git reset` never used.
- No `pipeline/__init__.py` created.

## Threat Model Coverage

| Threat ID | Disposition | Evidence |
|---|---|---|
| T-07-01 secret leakage via `common/` | mitigated | `common/frontmatter.py` imports only `__future__`; 0 hits for `GEMINI_API_KEY`/`load_dotenv`/`yaml`; 0 country-module imports anywhere under `pipeline/common/` |
| T-07-02 `laws/israel/` tampering + auto-deploy | mitigated | Gate restores and asserts; `git status --porcelain laws/israel/` empty before staging and after both commits; only `pipeline/` paths ever staged |
| T-07-06 import hijack via `sys.path[0]` | accept (re-verified) | Entry point run from a foreign cwd resolved `common` correctly — `sys.path[0]` is the script's directory, not cwd, so a hostile cwd cannot shadow the package. No `pipeline/__init__.py`, so all documented entry points are intact |
| T-07-07 silent change from reformatting | mitigated | Function copied verbatim; differentially executed against both old implementations over 8 edge cases *and* over the 112-file corpus by `--split`; full differential byte-matches the 07-01 fixture |
| T-07-SC pip installs | accept | Zero new dependencies; nothing installed |

**Threat surface scan:** no new network calls, no new file writes, no new subprocess, no new
external input path. `common/frontmatter.py` is a pure function over an in-memory string. Nothing to
flag.

## Known Stubs

None. Both files are complete for this plan's scope. `render_frontmatter` and `quote` are absent
**by design** — 07-PATTERNS.md and this plan both place them in 07-06, deliberately last, because
they carry the 111-file `dab1887e…` blast radius that this extraction deliberately avoids.

## Deferred Issues

None introduced. The two pre-existing items (`_STRIP_MG_INDEX` non-idempotency, stale
`pipeline/requirements.txt`) are unchanged and already tracked in `STATE.md` Todos.

## Notes for Next Plan (07-04)

- The import mechanics are now proven end-to-end — reuse `from common.X import Y` verbatim; do not re-litigate `sys.path`, and do not create `pipeline/__init__.py`.
- 07-04/07-05 are strictly harder than this plan: `common/progress.py` and `common/deploy.py` take **parameters** where this one took none. Watch the two traps 07-PATTERNS.md flags: `SITE_DIR` must be a parameter (a `common/` module is one directory deeper, so `Path(__file__).parent.parent / "site"` silently resolves to the non-existent `pipeline/site`), and `if any(e is entry for e in batch)` is *identity* comparison that must not be modernised.
- `--structure` is your remaining checklist: 7 errors left, all in the `batch_import` orchestrator group. Expect 07-04 to clear `common/progress.py` plus four of the five delegation errors, and 07-05 to clear `common/deploy.py` plus the last one.
- Unlike this plan, 07-04 touches `save_progress`, whose fixture (`golden/next_batch.json`, and the 1867-byte round-trip) is sensitive to `ensure_ascii=False` / `indent=2` / **no trailing newline**. Run `--quick` before you believe anything.

## Self-Check: PASSED

- `pipeline/common/__init__.py` — FOUND
- `pipeline/common/frontmatter.py` — FOUND
- `pipeline/link_resolver.py` — FOUND (modified)
- `pipeline/cross_linker.py` — FOUND (modified)
- Commit `e27f75d` — FOUND in git history
- Commit `b0fe1be` — FOUND in git history
- Full `verify_golden.py` exits 0 (6/6); working tree clean.
