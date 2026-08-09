# State — Codex Civica

> Project memory. Updated at phase transitions and plan completions.

---

## Project Reference

**Core value:** Anyone — lawyer, student, or citizen — can find and read any Israeli law in plain, readable form in under 30 seconds.

**Current milestone:** Milestone 1 — Israeli Basic Laws on a live, searchable site.

**Current focus:** Phase 4 — Content (factory import in progress)

---

## Current Position

| Field | Value |
|-------|-------|
| Current phase | Phase 4: Content (factory import in progress) |
| Current plan | Factory-line import of all 718 Israeli laws with PDFs |
| Phase status | In progress |
| Last updated | 2026-05-19 |

**Progress:**

```
Phase 1: Pipeline        [✓] Complete
Phase 2: Site Foundation [✓] Complete (Docusaurus + RTL + sidebar live)
Phase 3: Custom UI       [✓] Complete (navbar, metadata bubbles, grouping)
Phase 4: Content         [▶] In progress — 111/718 laws imported
Phase 5: Deployment      [✓] Complete (GitHub Pages + auto-deploy)
Phase 6: Search          [ ] Not started

Overall: 4/6 phases complete
```

---

## Accumulated Context

### Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-08 | Hebrew-only for Phase 1 | Translation quality risk; Hebrew is source of truth |
| 2026-05-08 | Basic Laws as first batch | Small (14), high-value, well-scoped for pipeline validation |
| 2026-05-08 | Local search before Algolia | Algolia requires approval + index setup; local search ships faster |
| 2026-05-08 | Manual .docx download workflow | WSL2 blocked by Knesset WAF — no automated fix available |
| 2026-05-08 | Flat file structure, categories via frontmatter | Simpler than nested dirs; Docusaurus sidebars handle grouping |
| 2026-05-15 | Dynamic metadata generation via prebuild script | All per-law metadata (category, tags, ministry, status, year) lives in .md frontmatter; generate-law-meta.js reads it at build time |
| 2026-05-15 | Full codebase refactor — no hardcoded law IDs | Removed MINISTER_BY_ID, STATUS_BY_ID, CATEGORY_HE hardcoded maps; DocItem/Content now reads from GENERATED_LAW_META; navbar/homepage link to /laws not a specific ID |
| 2026-05-19 | Inter-law cross-linking via Gemini (Pass 4) | Gemini extracts external law refs per doc; internal link if target converted, Knesset PDF fallback otherwise; referenced-but-unconverted laws queued as priority for next batch |
| 2026-05-19 | Knesset source link at bottom of every law .md | Added automatically by reconcile.py; backfilled on all 40 existing laws |
| 2026-05-19 | Fixed source link missing from batch_import path | stage_reconcile() bypassed reconcile.main(); now appends link directly |
| 2026-05-19 | Fixed NameError reconcile in Phase 3 cross-linker | Added `import reconcile as _reconcile` inside the cross-linker try block |
| 2026-05-19 | Full-body cross-linking (was 12k char truncation) | cross_linker.extract_refs now chunks at 80k chars; long laws get all refs found |
| 2026-05-19 | Full relink_all + link_resolver re-pass on 81 laws | All section anchors, intra-law citations, and inter-law links refreshed |
| 2026-05-19 | Dropped inter-law linking (commit 4281447), then restored it same day | Regex-based citation matcher (old Pass 3 in link_resolver.py) removed for good — superseded by Gemini; Gemini cross_linker.py re-wired into batch_import.py as Phase 3, plus a new deterministic Pass 4 in link_resolver.py that upgrades existing knesset PDF links to internal links via manifest lookup (no LLM call, safe to re-run) |
| 2026-05-19 | Referenced-but-unconverted laws go into a priority queue, not auto-converted inline | `progress["priority"]` drained first by `get_next_batch()` each run — simpler and safer than the old inline auto-convert-during-linking step |

### Known Constraints

- Knesset site blocks WSL2 IP ranges (Reblaze WAF). All .docx files must be downloaded from Windows browser.
- Python venv is at `~/.venv-codex` (Linux-side, not on NTFS).
- `KNS_IsraelLawMinistry` stores `GovMinistryID` in 1–50 range. `KNS_GovMinistry` uses 490+ range. No API join. Ministry names resolved via hardcoded lookup in `generate-law-meta.js`.
- Docusaurus requires at least one doc in the docs dir. `laws/israel/placeholder.md` fills this when the library is empty.

### Todos

- Run batch import: `source ~/.venv-codex/bin/activate && python pipeline/batch_import.py --count 25`
- After pipeline finishes, remove `laws/israel/placeholder.md`
- Ministry name resolution: legacy IDs 1–50 are best-effort mapped in `generate-law-meta.js`; may need refinement for accuracy

### Blockers

- (none)

---

## Session Continuity

**Last session summary (2026-05-19, session 8):** Found this repo with 125 dirty files — a full uncommitted batch (111 converted laws, up from 81) plus a pipeline rewrite that had partially reverted commit `4281447` (which had dropped inter-law linking entirely) without anyone committing the reversal. Reviewed and committed everything in two commits: `3648584` (pipeline: Gemini cross_linker restored as Phase 3 in batch_import.py, new deterministic Pass 4 URL-upgrader in link_resolver.py, reconcile.py frontmatter fixes) and `d0212de` (content: 101 new + 11 backfilled laws, 111/718 total). Added `.firecrawl/` and `.claude/scheduled_tasks.lock` to `.gitignore` — local scratch, never should have been trackable. Then ran `cross_linker.relink_all()` across all 111 laws to backfill cross-links that Phase 3 missed mid-batch (it only sees laws converted-so-far when it runs per-batch, so early laws in a batch miss citations to laws converted later in the same run) — 44 files gained new citation links, committed as `b87ab4e`.

**Current inter-law linking architecture** (see commits `3648584`, `d0212de`):
- Passes 1–3 (`link_resolver.py`): section anchors, intra-law section refs, margin-note index — unchanged, deterministic, LLM-free
- Phase 3 (`batch_import.py` → `cross_linker.py`): Gemini extracts every external law reference per doc, resolves against `manifest_laws.json`, writes `./law_id.md` for converted targets or a knesset PDF fallback link otherwise. Runs on `newly_done` laws after every batch.
- Pass 4 (`link_resolver.py` → `upgrade_pdf_links()`): deterministic, no LLM — swaps an *existing* knesset PDF link for `./law_id.md` once that exact URL's target law is converted. Purely an upgrader, can't discover new references on its own.
- Unresolved references (target in manifest but not yet converted) get queued in `progress["priority"]`, drained first by `get_next_batch()` on the next run — replaces the old inline "auto-convert referenced laws" step.

**Current import state:**
- 1,076 total valid laws | 718 with PDFs | 111 converted | 0 failed
- Working tree is clean as of commit `b87ab4e`
- All 111 laws cross-linked consistently (per-batch Phase 3 + full relink_all backfill)
- 2000595 confirmed complete (from prior session) ✓

**Next-session actions:**
1. Continue factory import: `source ~/.venv-codex/bin/activate && python pipeline/batch_import.py --count 25`
2. Commit after every batch — do not let converted laws sit uncommitted for a full session again
3. Periodically re-run `cross_linker.relink_all()` (or wire it as an end-of-run step in batch_import.py) so cross-batch citations don't accumulate as a manual-backfill chore
4. After import completes (718 laws), delete `laws/israel/placeholder.md` and redeploy

**Files to review on re-entry:**
- `pipeline/batch_import.py` — main factory loop (Phase 1 convert, Phase 2 link_resolver, Phase 3 cross_linker)
- `pipeline/cross_linker.py` — Gemini inter-law reference extractor/linker
- `pipeline/link_resolver.py` — Pass 1–4 (3 intra-law + 1 deterministic inter-law upgrader)
- `data/raw/israel/import_progress.json` — progress + priority queue
- `site/scripts/generate-law-meta.js` — metadata generator (runs as predeploy hook)
- `pipeline/fix_2000595_tail.py` — tail-fix pattern (reuse if another long law truncates)

**Deploy status:** Pushed `main` → `origin/main` (8 commits, up through `9602be5`) and deployed to GitHub Pages (`gh-pages`, based on `9602be5`). Live at https://Yuvaldv.github.io/codex-civica/. Working tree clean, nothing pending.

---

*Last updated: 2026-05-19 (session 8) — pushed + deployed, awaiting next steps*
