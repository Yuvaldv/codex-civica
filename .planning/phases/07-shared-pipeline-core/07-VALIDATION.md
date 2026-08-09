---
phase: 7
slug: shared-pipeline-core
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-09
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None installed — stdlib-only characterization scripts under `pipeline/tests/` (no runner needed) |
| **Config file** | none — Wave 0 creates `pipeline/tests/{capture_golden.py,verify_golden.py}` and `pipeline/tests/golden/` |
| **Quick run command** | `~/.venv-codex/bin/python pipeline/tests/verify_golden.py --quick` (splitter equivalence + frontmatter SHA + status diff; ~2s, no file mutation) |
| **Full suite command** | `~/.venv-codex/bin/python pipeline/tests/verify_golden.py` (adds the link-resolver before/after differential; ~5s incl. checkout/restore) |
| **Estimated runtime** | ~5 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `verify_golden.py --quick` (no file mutation)
- **After every plan wave:** Run `verify_golden.py` (full, includes link-resolver differential + `git status --porcelain laws/israel/` assertion)
- **Before `/gsd:verify-work`:** Full suite green **and** `git status --porcelain laws/israel/` empty
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Criterion | Behavior | Test Type | Automated Command | File Exists | Status |
|-----------|----------|-----------|-------------------|-------------|--------|
| SC-1 | `common/` exists with split/render, progress, deploy; Israel modules import them, no longer define locally | structural | `verify_golden.py --structure` | ❌ Wave 0 | ⬜ pending |
| SC-2a | Pipeline output over `laws/israel/` byte-identical before vs after (redefined gate — see Open Question 1) | golden differential | `diff pipeline/tests/golden/link_resolver_all.diff /tmp/after.diff` | ❌ Wave 0 | ⬜ pending |
| SC-2b | Committed Israel content untouched | smoke | `test -z "$(git status --porcelain laws/israel/)"` | ✓ (git) | ⬜ pending |
| SC-2c | `build_frontmatter` output byte-identical for all 111 laws | golden hash | `verify_golden.py --frontmatter` (expect `dab1887e…`) | ❌ Wave 0 | ⬜ pending |
| SC-2d | `split_frontmatter` behaviour identical to both originals | differential over corpus | `verify_golden.py --split` (112 files + 6 edge cases) | ❌ Wave 0 | ⬜ pending |
| SC-3 | `--status` reproduces the exact 6-line stdout byte-for-byte (treated as the golden fixture — see Open Question 3) | golden stdout | `diff pipeline/tests/golden/status.txt <(… --status)` | ❌ Wave 0 | ⬜ pending |
| SC-3b | `get_next_batch` selection unchanged at counts 1/5/25/100 | golden hash | `verify_golden.py --batch` | ❌ Wave 0 | ⬜ pending |
| SC-3c | `save_progress` writes byte-identical JSON | round-trip | `verify_golden.py --progress-roundtrip` | ❌ Wave 0 | ⬜ pending |
| SC-4 | A non-Israel caller can use `common` alone (proves country-blindness, not just asserts it) | integration | `python pipeline/tests/test_country_blind.py` | ❌ Wave 0 | ⬜ pending |
| SC-4b | `common/` imports nothing Israel-specific | static | `! grep -rnE "^\s*(from|import) (reconcile|batch_import|link_resolver|cross_linker)" pipeline/common/` | ❌ Wave 0 | ⬜ pending |
| — | `deploy()` never executes during this phase | manual-only | reviewer confirms no task invokes it | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pipeline/tests/capture_golden.py` — captures all four BEFORE fingerprints
- [ ] `pipeline/tests/verify_golden.py` — re-runs and diffs; supports `--quick`, `--structure`, `--split`, `--frontmatter`, `--batch`, `--progress-roundtrip`
- [ ] `pipeline/tests/golden/{link_resolver_all.diff,frontmatter_111.json,next_batch.json,status.txt}` — committed fixtures, captured from a clean `HEAD` before any production file is edited
- [ ] `pipeline/tests/test_country_blind.py` — SC-4 proof (temp-dir probe importing only from `common`)
- [ ] Off-repo backup of `data/raw/israel/{import_progress.json,manifest_laws.json}` — gitignored, unrecoverable via git if corrupted
- [ ] Framework install: not required (stdlib only)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `deploy()` is never executed during Phase 7 | SC — safety | Executing it publishes to production GitHub Pages; no automated check can safely verify "did not run" without risking a real deploy | Reviewer confirms no task's commands invoke `deploy()` or `batch_import.py` without `--status` |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies (15/15 automated blocks, verified by gsd-plan-checker)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (07-01 wave 1 captures all 4 golden fingerprints)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-09 (gsd-plan-checker: VERIFICATION PASSED, 0 blockers, 2 cosmetic warnings resolved)

---

## Known Pre-Existing Bug (not fixed in this phase — see 07-RESEARCH.md Pitfall 1)

`link_resolver.py`'s `_STRIP_MG_INDEX` regex (lines 122-124) fails to strip the sidenotes index when a note's text contains a nested Markdown link, causing 4 law files (`2000326`, `2000390`, `2000416`, `2000595`) to accumulate corrupted, duplicating sidenote text on repeated `--all` runs. Nothing in the repo is corrupted today — this is a latent bug that would trigger on a future re-run. **User decision (2026-08-09): defer the fix** — do not fix inside Phase 7 (would break the byte-identity gate this phase relies on for verification). Filed as a follow-up for the v1.0 Phase 4 track in STATE.md Todos.
