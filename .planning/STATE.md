# State — Codex Civica

> Project memory. Updated at phase transitions and plan completions.

---

## Project Reference

**Core value:** Anyone — lawyer, student, or citizen — can find and read any Israeli law in plain, readable form in under 30 seconds.

**Current milestone:** Milestone 1 — Israeli Basic Laws on a live, searchable site.

**Current focus:** Phase 2 — Content (factory import restarted from scratch)

---

## Current Position

| Field | Value |
|-------|-------|
| Current phase | Phase 2: Content (factory import restarted) |
| Current plan | Factory-line import of all 718 Israeli laws with PDFs |
| Phase status | In progress |
| Last updated | 2026-05-15 |

**Progress:**

```
Phase 1: Pipeline       [✓] Complete (pipeline operational)
Phase 2: Content        [▶] Restarted — 0/718 laws imported (fresh start)
Phase 3: Site Foundation[ ] Not started
Phase 4: Search         [ ] Not started
Phase 5: Custom UI      [ ] Not started
Phase 6: Deployment     [ ] Not started

Overall: 1/6 phases complete
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

**Last session summary (2026-05-15):** Refactored entire site to remove hardcoded law IDs. Deleted all 71 law markdowns and reset import progress to restart fresh.

**What was built this session:**
- **Deleted**: All 71 law markdowns in `laws/israel/` — fresh start
- **Reset**: `data/raw/israel/import_progress.json` → `{done:[], failed:[], total_deployed:0}`
- **`site/src/theme/DocItem/Content/index.jsx`**: Removed hardcoded MINISTER_BY_ID, STATUS_BY_ID, CATEGORY_HE. Now imports GENERATED_LAW_META and looks up current law by bill_id/law_id. Fully dynamic.
- **`site/docusaurus.config.ts`**: Navbar 🇮🇱 flag now links to `/laws` (the index), not a hardcoded law ID
- **`site/src/pages/index.tsx`**: Israel card on homepage now links to `/laws`
- **`laws/israel/placeholder.md`**: Added so Docusaurus builds with an empty law library
- **Build confirmed passing** — git push failed (no auth in session); needs manual push

**Current import state:**
- 1,076 total valid laws | 718 with PDFs | 0 converted | 718 pending
- Progress tracked in `data/raw/israel/import_progress.json`
- Auto-deploy triggers every 25 laws

**Next-session actions:**
1. Push current main branch: `git push origin main`
2. Start factory import: `source ~/.venv-codex/bin/activate && python pipeline/batch_import.py --count 25`
3. Check status: `python pipeline/batch_import.py --status`
4. After import completes (718 laws), delete `laws/israel/placeholder.md` and redeploy

**Files to review on re-entry:**
- `pipeline/batch_import.py` — main factory loop
- `data/raw/israel/import_progress.json` — current progress
- `site/scripts/generate-law-meta.js` — metadata generator (runs as predeploy hook)
- `site/src/clientModules/lawSort.js` — group-by sidebar logic
- `site/src/theme/DocItem/Content/index.jsx` — dynamic metadata bubbles

---

*Last updated: 2026-05-15*
