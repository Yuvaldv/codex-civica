---
phase: 07-shared-pipeline-core
plan: 07
subsystem: pipeline
tags: [close-out, country-blindness-probe, structural-gate, documentation, phase-exit]

# Dependency graph
requires:
  - phase: 07-06
    provides: "The complete country-blind surface: split_frontmatter, render_frontmatter, quote, progress.*, deploy.*, all four extractions done"
provides:
  - "pipeline/tests/test_country_blind.py — executing proof of SC-4, not a prose assertion"
  - "verify_golden.py default suite now 8/8 (added --structure and --country-blind, both formerly opt-in)"
  - "pipeline/PIPELINE.md documents common/, the import boundary, the single supported invocation form, and the harness"
  - "STATE.md records the redefined phase-exit gate rationale; both deferred defects confirmed untouched"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Proving a 'boundary' criterion (SC-4: a new country package needs zero Israel code) means writing a program that imports only the shared surface and actually calls it with foreign-shaped data — a grep alone only proves absence, not sufficiency"
    - "A structural gate (--structure) that was red-by-design during active extraction becomes part of the default suite only once its own precondition (all four extractions landing) is met — flipping it early would have masked incomplete work as a false pass"

key-files:
  created:
    - pipeline/tests/test_country_blind.py
  modified:
    - pipeline/tests/verify_golden.py
    - pipeline/PIPELINE.md
    - .planning/STATE.md

key-decisions:
  - "The probe uses doc_id/xml_path (not law_id/bill_id/pdf_path) throughout, including a fourth manifest entry with no file on disk, so the priority-drain-first and missing-source-skip behaviours are exercised with zero Israel-shaped names anywhere in the test data"
  - "print_status's non-labelled fields (with_pdf/pending counts) are computed via hardcoded 'pdf_path'/'law_id'/'bill_id' lookups per 07-04's interfaces — only source_label was ever meant to be parameterised, so the probe's 'With XML: 0' output is expected, not a bug, and was not 'fixed' here (out of this plan's scope)"

patterns-established:
  - "Phase close-out checklist: rerun every named success criterion as one command each, confirm the deferred-defect list is unchanged, and diff the phase's full commit range against the one file everyone is nervous about (link_resolver.py) to prove zero touches"

requirements-completed: [SC-1, SC-2a, SC-2b, SC-4, SC-4b]

# Metrics
duration: 25min
completed: 2026-08-10
---

# Phase 7 Plan 07: Close-Out — Country-Blindness Probe + Documentation Summary

**`pipeline/tests/test_country_blind.py` proves SC-4 by executing, not asserting: it round-trips progress, selects a batch, and renders frontmatter using only `pipeline/common/`, with UK-shaped field names (`doc_id`/`xml_path`) and zero Israel imports. `--structure` and `--country-blind` are now part of the default `verify_golden.py` suite (8/8 green). `pipeline/PIPELINE.md` documents the shared core, the import boundary, and the single supported invocation form. Phase 7 closes with `laws/israel/` both `git status`-clean and `git diff --stat`-empty against HEAD, and `link_resolver.py` — home of the deferred `_STRIP_MG_INDEX` bug — untouched across all seven plans.**

## Accomplishments

### Task 1 — The country-blindness probe + wiring into the default gate

`pipeline/tests/test_country_blind.py` imports only `common.deploy`, `common.frontmatter`,
`common.progress`, and stdlib — verified by grep, zero matches for `reconcile|batch_import|
link_resolver|cross_linker`. Four assertion groups, each printing a line a reviewer can read as proof:

1. **Progress round-trip** — `save_progress`/`load_progress` through a `tempfile.mkdtemp()` path;
   also asserts the empty-state default on a nonexistent path.
2. **Batch selection** — a synthetic 4-entry manifest keyed by `doc_id`/`xml_path` (no `law_id`,
   `bill_id`, or `pdf_path` anywhere), with `uk1` done, `uk2` failed, `uk3` in the priority queue, and
   `uk4` missing its file on disk. `get_next_batch(..., id_keys=("doc_id",), source_key="xml_path")`
   returns exactly `["uk3"]` — proving priority-drain-first, done/failed-skip, and missing-source-skip
   simultaneously.
3. **Frontmatter render** — `render_frontmatter` over UK-shaped lines (`doc_id`, `nation: england`,
   an OGL licence line); asserts the block opens/closes with a fence, ends with a trailing newline,
   and round-trips through `split_frontmatter`. `quote()` on an embedded-double-quote value.
4. **Deploy signature only** — `inspect.signature(deploy)` confirms `site_dir` is required;
   `deploy()` is never called.

```
$ ~/.venv-codex/bin/python pipeline/tests/test_country_blind.py
progress round-trip OK (temp path, nonexistent-path default OK)
batch selection OK — no Israel key names, priority drained first, done/failed/missing-file skipped: ['uk3']
...
render_frontmatter OK — UK-shaped fields, fenced, trailing newline, round-trips via split_frontmatter
quote OK — embedded double quote escaped: "has \"embedded\" quotes"
deploy signature OK — site_dir required, env_overrides optional; deploy() NEVER invoked
COUNTRY_BLIND_OK — full common/ surface exercised with zero Israel code
```

Wired `check_country_blind()` into `verify_golden.py` (runs the probe as a subprocess, fails on
non-zero exit). Removed `check_structure`'s "opt-in, red until 07-06" docstring caveat — it's been
green since 07-05. Both `structure` and `country_blind` moved from opt-in-only into `FULL` /
`CHECK_ORDER`, alongside the existing `QUICK` set and the mutating `link_resolver` differential.

```
$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py
PASS  --structure / --split / --frontmatter / --batch / --progress-roundtrip / --status / --country-blind / link_resolver
8/8 checks passed
```

### Task 2 — Documentation + phase-exit gate

`pipeline/PIPELINE.md` gained two new sections: **Shared Core (`pipeline/common/`)** — the layout
table, the one-way dependency rule, what's enforced by `--structure`/`--country-blind`, and what
deliberately stayed out (`_strip_year`/`build_seo_description`'s Hebrew literals; `DEPLOY_EVERY`
cadence policy) — and **Testing / Characterization Harness** — the two commands, what the full suite
checks, and the fixture-invalidation rule. **Key Constraints** gained two bullets: `python pipeline/X.py`
as the only supported form (no `pipeline/__init__.py`, ever) and the mandatory
`~/.venv-codex/bin/python` interpreter.

`.planning/STATE.md` gained a Decisions row explaining the redefined exit gate: the literal ROADMAP
wording ("re-run pipeline, `git diff --stat laws/israel/` must be empty") is unachievable as a live
re-run because of the pre-existing `_STRIP_MG_INDEX` bug, so the gate became a BEFORE/AFTER
diff-fingerprint differential — and at phase close, both the differential *and* the literal wording
hold, because the committed Israel content was genuinely never touched.

**Phase-exit gate — all green:**

```
pipeline_md_common_OK
pipeline_md_verify_golden_OK
state_strip_mg_OK
verify_golden.py: 8/8 checks passed
batch_import.py --status: diffs clean against golden/status.txt
git status --porcelain laws/israel/: empty
git diff --stat laws/israel/: empty
PHASE_EXIT_GATE_GREEN
```

**`_STRIP_MG_INDEX` untouched across the whole phase:**

```
$ git log --oneline b9b55eb..HEAD -- pipeline/link_resolver.py
(no output — link_resolver.py was never committed to across Phase 7)
$ git diff b9b55eb -- pipeline/link_resolver.py | grep -c '_STRIP_MG_INDEX'
0
```

## Task Commits

| Task | Name | Commit | Files |
|---|---|---|---|
| 1 | Country-blindness probe + wire into default gate | `87cc033` | `pipeline/tests/test_country_blind.py`, `pipeline/tests/verify_golden.py` |
| 2 | Document the layout, close the phase | `33c1e73` | `pipeline/PIPELINE.md`, `.planning/STATE.md` |

## Verification Evidence — Four Criteria, Four Commands

| Criterion | Command | Result |
|---|---|---|
| SC-1 (common/ layout + boundary) | `verify_golden.py --structure` | PASS — "common/ present, boundary clean, no local redefinitions" |
| SC-2 (byte-identity of extracted behaviour) | `verify_golden.py` (split/frontmatter/batch/progress-roundtrip/link-resolver) + `git diff --stat laws/israel/` | PASS — 111-law SHA `dab1887e...` unchanged; diff-stat empty |
| SC-3 (`--status` unchanged) | `batch_import.py --status \| diff golden/status.txt -` | PASS — 6 lines match |
| SC-4 (country-blind, provably) | `verify_golden.py --country-blind` (runs `test_country_blind.py`) | PASS — 0 exit, full surface exercised, zero Israel imports |

## Deviations from Plan

None requiring a rule citation. One clarification worth recording: `print_status`'s `with_pdf`/
`pending` line values are computed from hardcoded `"pdf_path"`/`"law_id"`/`"bill_id"` lookups inside
`common/progress.py` (only `source_label` was parameterised back in 07-04). The probe's `"With XML: 0"`
output against a `doc_id`/`xml_path`-shaped manifest is therefore expected — not a defect this plan
introduced or was scoped to fix.

## Constraints Honoured

- `deploy()` never executed anywhere across the whole phase — Task 1's probe only inspects its signature.
- `link_resolver._STRIP_MG_INDEX` never touched — confirmed by `git log`/`git diff` over the full phase commit range.
- Explicit staging only at every commit (`git add <specific paths>`), never `git add -A`.
- `~/.venv-codex/bin/python` used explicitly throughout.
- `git status --porcelain laws/israel/` and `git diff --stat laws/israel/` both empty at phase close.

## Deferred Issues

Both remain open, exactly as before this phase, per `.planning/STATE.md` Todos:

1. `link_resolver.py`'s `_STRIP_MG_INDEX` regex (sidenote-corruption bug on nested Markdown links) — deferred by user request to a v1.0 Phase 4 follow-up.
2. Stale `pipeline/requirements.txt` (missing `python-dotenv`, `google-genai`) — needs a follow-up fix, out of Phase 7 scope.

## Notes for Next Phase

Phase 7 (Shared Pipeline Core) is complete: all four success criteria hold, the full gate is 8/8, and
`pipeline/common/` is ready for a future England/UK orchestrator to import without copying a line of
Israel-specific code. Per `STATE.md`, the next v1.1 phases (8+) are the actual UK CLML fetch/parse/
render pipeline — none of that work started in Phase 7 by design.

## Self-Check: PASSED

- `pipeline/tests/test_country_blind.py` — FOUND, exits 0
- `pipeline/tests/verify_golden.py` — FOUND (modified), 8/8 checks pass
- `pipeline/PIPELINE.md` — FOUND (modified)
- `.planning/STATE.md` — FOUND (modified)
- Commit `87cc033` — FOUND in git history
- Commit `33c1e73` — FOUND in git history
- Phase-exit gate: `PHASE_EXIT_GATE_GREEN`; `laws/israel/` byte-identical to HEAD; `link_resolver.py` untouched.
