# State — Codex Civica

> Project memory. Updated at phase transitions and plan completions.

---

## Project Reference

**Core value:** Anyone — lawyer, student, or citizen — can find and read any Israeli law in plain, readable form in under 30 seconds.

**Current milestone:** Milestone 1 — Israeli Basic Laws on a live, searchable site.

**Current focus:** Phase 1 — Pipeline

---

## Current Position

| Field | Value |
|-------|-------|
| Current phase | Phase 1: Pipeline |
| Current plan | TBD |
| Phase status | Not started |
| Last updated | 2026-05-08 |

**Progress:**

```
Phase 1: Pipeline       [ ] Not started
Phase 2: Content        [ ] Not started
Phase 3: Site Foundation[ ] Not started
Phase 4: Search         [ ] Not started
Phase 5: Custom UI      [ ] Not started
Phase 6: Deployment     [ ] Not started

Overall: 0/6 phases complete
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

### Known Constraints

- Knesset site blocks WSL2 IP ranges (Reblaze WAF). All .docx files must be downloaded from Windows browser.
- Python venv is at `~/.venv-codex` (Linux-side, not on NTFS).
- `pipeline/` has only `requirements.txt` — no Python scripts yet. Phase 1 creates them.
- `site/` contains Docusaurus boilerplate — Phase 3 removes it.
- `site/docusaurus.config.ts` still has template defaults — Phase 3 updates it.

### Todos

- (none yet — roadmap just initialized)

### Blockers

- (none)

---

## Session Continuity

**Last session summary:** Project initialized. Roadmap created covering 6 phases and 17 requirements.

**Next action:** Run `/gsd-plan-phase 1` to plan the pipeline phase.

**Files to review on re-entry:**
- `/mnt/c/Dev/codex-civica/.planning/ROADMAP.md` — phase structure
- `/mnt/c/Dev/codex-civica/.planning/REQUIREMENTS.md` — requirement details
- `/mnt/c/Dev/codex-civica/.planning/STATE.md` — this file

---

*Last updated: 2026-05-08*
