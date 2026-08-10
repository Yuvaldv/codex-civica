---
phase: 07-shared-pipeline-core
plan: 06
subsystem: pipeline
tags: [extraction-refactor, shared-core, frontmatter, highest-risk, sha-gate, byte-identity]

# Dependency graph
requires:
  - phase: 07-05
    provides: "pipeline/common/deploy.py + fully-green --structure boundary this plan preserves"
provides:
  - "pipeline/common/frontmatter.py — split_frontmatter, render_frontmatter, quote (all four named extractions complete)"
  - "reconcile.build_frontmatter delegates fence-wrapping only, field selection/ordering/formatting untouched"
affects: [07-07 close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "render_frontmatter(lines) = join(['---', *lines, '---', '']) — the trailing empty-string element is what produces the trailing newline with no extra blank line; load-bearing, not cosmetic"
    - "quote() exists for future non-Israel callers only; reconcile.py keeps its own value-site .replace('\"','\\\\\"') escaping untouched to avoid double-escaping"

key-files:
  modified:
    - pipeline/common/frontmatter.py
    - pipeline/reconcile.py

key-decisions:
  - "Did not adopt quote() at reconcile.py's value sites (lines 122, 127) — they already escape inline; adopting quote() there would double-escape embedded quotes. quote() ships unused in this phase, for 07-07's country-blindness probe and future UK caller"
  - "No PyYAML — confirmed installed but deliberately unused; safe_dump would re-quote, reorder, line-wrap, and emit null for ~, any of which fails the SHA gate"

patterns-established:
  - "For a 111-file blast-radius extraction, run the exact-SHA fixture check before ever running the full suite — it is the single sharpest signal and isolates frontmatter regressions from unrelated failures"

requirements-completed: [SC-1, SC-2a, SC-2b, SC-2c, SC-4]

# Metrics
duration: 12min
completed: 2026-08-10
---

# Phase 7 Plan 06: Extract render_frontmatter Summary

**`pipeline/common/frontmatter.py` now holds all three frontmatter primitives — `split_frontmatter`, `render_frontmatter`, `quote`. `reconcile.build_frontmatter` delegates only the `---`-fence wrapping; every field decision, ordering, and value-formatting rule stayed exactly where it was. The SHA gate over all 111 converted laws (`dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37`) matched on the first run — no doubled fences, no lost trailing newline, no reordering. This was the highest-risk extraction in Phase 7 and the last of the four named in the success criteria.**

## Accomplishments

### Task 1 — `render_frontmatter` + `quote`

Appended both functions to `pipeline/common/frontmatter.py` verbatim from 07-PATTERNS.md.
`render_frontmatter` is a single return statement — no loops, no conditionals, no validation.
`quote()` ships unused in this phase (by design — `reconcile.py`'s two value sites already escape
inline; adopting it there would double-escape).

```
RENDER_OK
NO_YAML
```

### Task 2 — Delegate `reconcile.build_frontmatter`

Exactly three edits, as prescribed:

1. `from common.frontmatter import render_frontmatter` after the third-party import block.
2. Line 135: `"---", id_line,` → `id_line,` (dropped the leading literal fence).
3. Lines 181-184: dropped the trailing literal `"---"` and `""`, changed `return "\n".join(lines)` to `return render_frontmatter(lines)`.

Nothing else touched — `id_line`, the `title`/`title_he`/`sidebar_label`/`description` lines, the
`hide_table_of_contents` append, the `publication_date`/`~` branches, `category`, the `law_tags`
block-list construction, and the `ministry_ids` `json.dumps` line are all byte-identical to before.
`_YEAR_RE`, `_strip_year`, and `build_seo_description` (Hebrew-literal-bearing) were never touched.

**SHA gate — matched on the first run:**

```
$ ~/.venv-codex/bin/python pipeline/tests/verify_golden.py --frontmatter
INFO frontmatter: entries=111 sha256=dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37
PASS  --frontmatter
1/1 checks passed
```

**Downstream consumer smoke test:**

```
$ ~/.venv-codex/bin/python -c "import sys; sys.path.insert(0,'pipeline'); import backfill_seo_meta; print('BACKFILL_IMPORT_OK')"
BACKFILL_IMPORT_OK
```

`backfill_seo_meta.py`'s `from reconcile import build_seo_description` still resolves — the new
`from common.frontmatter import ...` in `reconcile.py` also resolves via the same `sys.path[0]`.

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
```

`--structure` (already green since 07-05) stayed green:

```
INFO structure: common/ present, boundary clean, no local redefinitions
PASS  --structure
```

**`git diff --numstat pipeline/reconcile.py`:** `4  4  pipeline/reconcile.py` — four lines added, four
removed, exactly the surgical shape the plan required.

## Task Commits

| Task | Name | Commit | Files |
|---|---|---|---|
| 1 | Add `render_frontmatter` and `quote` to `common/frontmatter.py` | `cef5c23` | `pipeline/common/frontmatter.py` |
| 2 | Delegate fence-wrapping from `reconcile.build_frontmatter`, clear the SHA gate | `1ff876c` | `pipeline/reconcile.py` |

## Verification Evidence

```
RENDER_OK / NO_YAML                               # Task 1 automated verify
SHA_GATE_GREEN                                    # Task 2 automated verify (exact plan command)
frontmatter SHA == dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37 (111 entries)
BACKFILL_IMPORT_OK
GATE_GREEN 6/6, --structure also green
grep 'from common.frontmatter import render_frontmatter' reconcile.py -> 1
grep 'return render_frontmatter(lines)' reconcile.py -> 1
grep 'def _strip_year' reconcile.py -> 1
grep 'def build_seo_description' reconcile.py -> 1
git diff --numstat pipeline/reconcile.py -> 4  4
git status --porcelain laws/israel/ -> empty
```

## Deviations from Plan

None. All three edits landed exactly where 07-PATTERNS.md and the plan's interface block specified —
line numbers verified against the working tree matched the plan's citations exactly before editing.

## Constraints Honoured

- SHA gate run first, in isolation, before the full suite — matched on the first attempt, no fixture adjustment.
- `_YEAR_RE`, `_strip_year`, `build_seo_description` left untouched (Hebrew-literal-bearing; CLAUDE.md legal-fidelity constraint).
- `quote()` not adopted at `reconcile.py`'s value sites — avoided double-escaping.
- No PyYAML used anywhere in `common/frontmatter.py`.
- No clock parameter added to `build_frontmatter`; `generated_at` non-determinism stays handled by the test harness's frozen-clock shim only.
- Explicit staging only (`git add pipeline/common/frontmatter.py`, then `git add pipeline/reconcile.py`), never `git add -A`.
- `git status --porcelain laws/israel/` empty before both commits.

## Notes for Next Plan (07-07)

- All four named extractions (`split_frontmatter`, `progress`, `deploy`, `render_frontmatter`) are now complete. `--structure` has been green since 07-05.
- 07-07 is close-out: the country-blindness probe (`test_country_blind.py`), final `--structure`/full-suite confirmation, and phase wrap-up documentation — no further extraction work remains.

## Self-Check: PASSED

- `pipeline/common/frontmatter.py` — FOUND (modified, now defines all three functions)
- `pipeline/reconcile.py` — FOUND (modified)
- Commit `cef5c23` — FOUND in git history
- Commit `1ff876c` — FOUND in git history
- Full `verify_golden.py` exits 0 (6/6); `--structure` green; working tree clean except this summary + STATE.md.
