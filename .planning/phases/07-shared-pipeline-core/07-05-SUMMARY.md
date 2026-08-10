---
phase: 07-shared-pipeline-core
plan: 05
subsystem: pipeline
tags: [extraction-refactor, shared-core, deploy, security-boundary, byte-identity]

# Dependency graph
requires:
  - phase: 07-04
    provides: "pipeline/common/progress.py + the wrapper pattern this plan repeats for deploy"
provides:
  - "pipeline/common/deploy.py — deploy(site_dir, env_overrides=None), site_dir required (no __file__-derived path)"
  - "batch_import.deploy() reduced to a one-line wrapper"
  - "Statically-verified common/ security boundary: no Israel imports, no secrets, no shell=True, no __file__ paths, stdlib-only"
affects: [07-06 render_frontmatter extraction, 07-07 close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A module one directory deeper than its source (common/ vs pipeline/) must take the path as a required parameter — never re-derive via Path(__file__).parent.parent, which silently resolves to a sibling that doesn't exist"

key-files:
  created:
    - pipeline/common/deploy.py
  modified:
    - pipeline/batch_import.py

key-decisions:
  - "deploy() left genuinely un-executed for the whole phase — every verification here is import-time (inspect.signature) or static (grep), never a real subprocess.run"

patterns-established:
  - "Security boundary assertions for a shared package: Israel-import grep, secret grep, shell=True grep, __file__ grep, stdlib-only import grep — run as a batch and recorded verbatim in the plan summary"

requirements-completed: [SC-1, SC-4]

# Metrics
duration: 10min
completed: 2026-08-10
---

# Phase 7 Plan 05: Extract Deploy Summary

**`pipeline/common/deploy.py` now owns the Docusaurus deploy shell-out, with `site_dir` as a required parameter (never derived from `__file__`, since `common/` sits one directory deeper than `batch_import.py`). `batch_import.deploy()` is a one-line wrapper; the `DEPLOY_EVERY` cadence policy stays in the orchestrator. `deploy()` was never executed. `pipeline/common/` is now statically proven free of Israel imports, secrets, shell injection, and `__file__`-derived paths.**

## Accomplishments

### Task 1 — `pipeline/common/deploy.py` + wrapper

Ported `deploy` verbatim except: `cwd=str(site_dir)` (required positional parameter, no default) and
`env = {**os.environ, **(env_overrides or {})}` replacing the hard-coded Israel dict. Preserved
exactly: the `logging.info("Deploying site...")` opener, list-form `subprocess.run(["npm", "run",
"deploy"], ...)`, `timeout=300`, `capture_output=False`, the `returncode != 0` branch, and the
`(subprocess.TimeoutExpired, OSError)` exception tuple.

`batch_import.py`: `deploy()` reduced to `return _deploy.deploy(SITE_DIR, {"USE_SSH": "true",
"GIT_USER": "Yuvaldv"})`, with `from common import deploy as _deploy` added alongside 07-04's
`from common import progress as _progress`. The single call site (`if deploy():`) and the
`DEPLOY_EVERY` threshold block are unchanged — confirmed via `git diff`.

```
DEPLOY_SHAPE_OK
DEPLOY_OK
```

### Task 2 — Security boundary + full gate

Ran the plan's exact automated verify command (Israel-import grep, secret grep, `shell=True` grep,
`__file__` grep, `--status` diff, full `verify_golden.py`, clean-tree check):

```
$ ! grep -rnE "^\s*(from|import) (reconcile|batch_import|link_resolver|cross_linker)" pipeline/common/ \
  && ! grep -rn "GEMINI_API_KEY\|load_dotenv\|GIT_USER" pipeline/common/ \
  && ! grep -rn "shell=True" pipeline/common/ \
  && ! grep -rn "Path(__file__)" pipeline/common/ \
  && ~/.venv-codex/bin/python pipeline/batch_import.py --status | diff pipeline/tests/golden/status.txt - \
  && ~/.venv-codex/bin/python pipeline/tests/verify_golden.py \
  && test -z "$(git status --porcelain laws/israel/)"
INFO split: 112 files + 6 edge cases, 0 mismatches
INFO frontmatter: entries=111 sha256=dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37
INFO batch: 4 counts match
INFO progress-roundtrip: 1867 bytes, byte-identical
INFO status: 6 lines match
INFO link-resolver: differential matches fixture (15101 bytes), laws/israel/ restored
6/6 checks passed
BOUNDARY_AND_GATE_OK
```

**Dependency surface** (assertion 6): only stdlib imports appear under `pipeline/common/` —
`__future__`, `json`, `logging`, `os`, `subprocess`, `pathlib`.

**Env-logging assertion** (assertion 4, `logging\.(info|error|warning|debug)\([^)]*env`): zero matches
— no logging call in `common/` takes an environment dict as an argument.

**Noted false positives, not violations:** the broader `\.env` pattern from the acceptance-criteria
prose (not the plan's actual automated verify command, which uses `GEMINI_API_KEY|load_dotenv|GIT_USER`
without `\.env`) matches two unrelated substrings — `os.environ` in `deploy.py`'s env-merge line, and
the word "`pipeline/.env`" inside `frontmatter.py`'s own docstring (a 07-03 comment stating the
constraint, not a violation of it). Neither reads a `.env` file or references a secret; confirmed by
inspection. The plan's real gate (assertion 2 as coded in the automated `<verify>` block) passed clean.

**Bonus:** `--structure` (opt-in, "expected red until 07-06" per the plan and per its own docstring)
is already fully green — it only asserts `common/`'s four modules exist, no local redefinitions, no
Israel imports, and full orchestrator delegation, none of which depend on `render_frontmatter`
(07-06 adds a function inside the existing `frontmatter.py`, not a new module the checker inspects).

```
$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py --structure
INFO structure: common/ present, boundary clean, no local redefinitions
PASS  --structure
1/1 checks passed
```

**`deploy()` was never executed** in this plan or any prior plan in Phase 7. Confirmed by reviewing
every command run across 07-01 through 07-05: `batch_import.py` was invoked only with `--status`;
`deploy()`/`common.deploy.deploy()` were referenced only via `inspect.signature` and source grep.
`npm run deploy` was never invoked.

## Task Commits

| Task | Name | Commit | Files |
|---|---|---|---|
| 1 | Create `pipeline/common/deploy.py`, reduce `batch_import.deploy()` to a wrapper | `f16c35d` | `pipeline/common/deploy.py` |
| 2 | Lock down the `common/` security boundary, re-run the full gate | `75ccaba` | `pipeline/batch_import.py` |

## Verification Evidence

```
DEPLOY_SHAPE_OK / DEPLOY_OK                       # Task 1 automated verify
BOUNDARY_AND_GATE_OK                              # Task 2 automated verify (exact plan command)
GATE_GREEN 6/6                                    # full verify_golden.py
--structure 1/1 (early — not required until 07-06, passes now as a bonus)
git status --porcelain laws/israel/  -> empty
git diff pipeline/batch_import.py    -> only the deploy() body + one import line changed
```

## Deviations from Plan

None requiring a rule citation. `--structure` passing early (rather than staying red until 07-06, as
the plan's own comment anticipates) is a pleasant surprise, not a deviation — the checker's actual
scope (module existence + delegation + import boundary) never depended on `render_frontmatter`
specifically.

## Constraints Honoured

- `deploy()` never executed anywhere in this plan — verification was import-time signature inspection and static grep only.
- `~/.venv-codex/bin/python` used explicitly throughout.
- `batch_import.py` invoked only via `--status`.
- Explicit staging only (`git add pipeline/common/deploy.py`, then `git add pipeline/batch_import.py`), never `git add -A`.
- `DEPLOY_EVERY` threshold block, single call site `if deploy():`, and all other `batch_import.py` orchestration logic untouched.
- No secret read, logged, or referenced anywhere in `pipeline/common/`.

## Notes for Next Plan (07-06)

- `--structure` is already green; 07-06 (`render_frontmatter`/`quote` extraction into `frontmatter.py`, plus the `reconcile.py` fence-wrapping delegation) is now the last extraction wave before 07-07 close-out.
- `reconcile.py` is flagged in 07-PATTERNS.md as "highest risk" — three precise edits only, gated on the `dab1887e…` SHA fingerprint; forgetting any one of the three produces doubled fences on all 111 laws.

## Self-Check: PASSED

- `pipeline/common/deploy.py` — FOUND
- `pipeline/batch_import.py` — FOUND (modified)
- Commit `f16c35d` — FOUND in git history
- Commit `75ccaba` — FOUND in git history
- Full `verify_golden.py` exits 0 (6/6); `--structure` also green; working tree clean except this summary + STATE.md.
