---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: UK Laws
status: planning
last_updated: "2026-08-09T00:00:00.000Z"
last_activity: 2026-08-09
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# State — Codex Civica

> Project memory. Updated at phase transitions and plan completions.

---

## Project Reference

**Core value:** Anyone — lawyer, student, or citizen — can find and read any Israeli law in plain, readable form in under 30 seconds.

**Current milestone:** v1.1 — UK Laws: Pipeline + Law Directory (England only).

**Current focus:** Roadmap created — Phases 7–13. Next: plan Phase 7 (Shared Pipeline Core). (v1.0 Israel work — Phase 4 Content 111/718 paused, Phase 6 Search not started — remains open in parallel, not abandoned.)

---

## Current Position

Phase: 7 — Shared Pipeline Core (not started)
Plan: —
Status: Roadmap complete, awaiting phase planning
Progress: 0/7 phases complete (0%) — [░░░░░░░░░░] v1.1
Last activity: 2026-08-09 — Milestone v1.1 roadmap created (Phases 7–13, 23/23 requirements mapped)

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
| 2026-05-19 | Paused factory import at 111/718 — ~100 laws is enough for now | User call, not a technical blocker. Don't resume `batch_import.py` proactively; wait for explicit next steps |
| 2026-05-19 | SEO: deterministic (no-LLM) `title`/`description` frontmatter, not Gemini-generated | Both are metadata, not legal text, but templating from data already in the entry is faster, free, and consistent — matches the pipeline's deterministic-by-default posture |
| 2026-05-19 | SEO: per-page `lang`/`dir`/`og:locale` fix via swizzled DocItem/Content Head, not full i18n locale routing | Real bug (found `lang=en dir=ltr` on 100%-Hebrew pages via an actual `npm run build`) but full i18n (`/he/` routes, translation JSON) is heavy for a site whose chrome is intentionally English; the lightweight fix is scoped to doc pages only and is fully SSR-verified |
| 2026-08-09 | Legal pages (terms/privacy/accessibility) as plain `.md` under `src/pages`, not React/Layout components | Matches Docusaurus's built-in MDXPage wrapper, no styling code needed; content is honest about current state (no analytics/cookies exist, no formal a11y audit done) rather than aspirational boilerplate |
| 2026-08-09 | No OCR, no Gemini/LLM in the UK text path | CLML is a single authoritative XML witness — nothing to reconcile; an LLM here would risk paraphrasing text CLAUDE.md requires verbatim. UK conversion is a deterministic `lxml` tree walk (CLML → typed IR → Markdown) |
| 2026-08-09 | UK pipeline is a sibling of Israel's, not a shared framework | Two data sources is not evidence for an abstraction (CLAUDE.md: "do not over-abstract"); only the ~150 genuinely country-blind lines (frontmatter split, progress tracking, deploy) move to `pipeline/common/` in Phase 7 |
| 2026-08-09 | Rebase Israel route `/laws` → `/laws/israel` now, with client redirects for the 111 indexed URLs (Phase 10) | User decision. Symmetric structure for every downstream consumer; cheaper now (111/718 corpus, no search feature yet) than retrofitting later. Isolated into its own phase so the highest-blast-radius site change is separated from the additive second-country change |
| 2026-08-09 | UK validation is round-trip fidelity, not Israel's inference validators | Israel's numbering-continuity/orphan-subsection checks would false-positive-flood on CLML's legitimate gaps (repealed sections, `19A` inserted numbers, `BlockAmendment` quoted text). UK uses verbatim `<Text>`-node conservation as the hard phase-exit gate |
| 2026-08-09 | v1.1 roadmap = Phases 7–13, continuing v1.0's numbering | v1.0 Phases 1–6 stay open and untouched (Phase 4 paused at 111/718, Phase 6 not started); v1.1 runs in parallel per user's explicit "new milestone" choice |

### Known Constraints

- Knesset site blocks WSL2 IP ranges (Reblaze WAF). All .docx files must be downloaded from Windows browser.
- Python venv is at `~/.venv-codex` (Linux-side, not on NTFS).
- `KNS_IsraelLawMinistry` stores `GovMinistryID` in 1–50 range. `KNS_GovMinistry` uses 490+ range. No API join. Ministry names resolved via hardcoded lookup in `generate-law-meta.js`.
- Docusaurus requires at least one doc in the docs dir. `laws/israel/placeholder.md` fills this when the library is empty.
- legislation.gov.uk enforces a mandatory 5s `Crawl-delay` and an identifying User-Agent; no bulk download exists and no concurrency is permitted. Fetch must be sequential and cache-first.
- UK site content must carry OGL v3 attribution (with the conditional EU/Westlaw variant where `dc:publisher` requires it).
- Large UK Acts (>1MB XML — e.g. Companies Act 2006 at 15MB, Data Protection Act 2018 at 5.8MB) are blocked on a page-splitting strategy; out of scope for the v1.1 Tier A starter batch, but a known constraint for any later expansion.

### Todos

- Factory import paused at 111/718 by user request (2026-05-19) — do not resume until asked
- Ministry name resolution: legacy IDs 1–50 are best-effort mapped in `generate-law-meta.js`; may need refinement for accuracy
- SEO follow-ups not yet done: homepage/`/laws` index meta description is still the generic "Laws of the world..." tagline; no per-category landing-page descriptions; Google Search Console not yet verified/submitted
- Open design call for Phase 9 planning: amendment-markup rendering policy is set to bracket-and-footnote (per UKCONV-06), but `Tabular`/`Figure` edge cases still need a decision during planning
- **Pre-existing bug (found during Phase 7 research, 2026-08-09), fix deferred by user request:** `link_resolver.py`'s `_STRIP_MG_INDEX` regex (lines 122-124) fails to strip the sidenotes index when a note's text contains a nested Markdown link — corrupts 4 law files (`2000326`, `2000390`, `2000416`, `2000595`) a little more on every `--all` re-run. Nothing in the repo is corrupted today (reproduced from a clean `HEAD`, not present in committed history); this is latent and would trigger on the next factory-import resume. Not fixed in Phase 7 (would break its byte-identity verification gate). Track as v1.0 Phase 4 follow-up work.
- Stale `pipeline/requirements.txt` (found during Phase 7 research): missing `python-dotenv` and `google-genai`, both imported by `reconcile.py`. A fresh env provisioned from `requirements.txt` alone cannot import `reconcile`. Out of scope for Phase 7; needs a follow-up fix.
- Open design call for Phase 11 planning: nation segment lives in the path (`laws/uk/england/`) per UKSITE-02 — confirm the Docusaurus sidebar/routing shape against the installed Docusaurus version at implementation time
- Pin/verify `@docusaurus/plugin-client-redirects` against the installed Docusaurus version before Phase 10 implementation

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

- 1,076 total valid laws | 718 with PDFs | 111 converted | 0 failed — **paused here by user request**, not resuming without explicit go-ahead
- Working tree is clean
- All 111 laws cross-linked consistently (per-batch Phase 3 + full relink_all backfill)
- 2000595 confirmed complete (from prior session) ✓

**SEO pass (same session, after the import pause):** Found via an actual `npm run build` — not just source review — that law pages served `<html lang=en dir=ltr>` on 100%-Hebrew content, and meta description auto-scraped the first line of body text (one law's description was literally the word "פירושים" / "definitions"). Fixed:

- `pipeline/reconcile.py`: `build_frontmatter()` now emits `title` + `description` (deterministic, templated from title/pub_date/law_validity already in the entry — no LLM call, no legal text touched)
- `pipeline/backfill_seo_meta.py`: one-time backfill of `title`+`description` onto all 111 already-converted laws
- `site/src/theme/DocItem/Content/index.jsx`: swizzled wrapper now also renders `<html lang="he" dir="rtl">`, `og:locale=he_IL`, and a `schema.org/Legislation` JSON-LD block — scoped to doc pages only, homepage/chrome stay `en`/`ltr`
- `site/static/robots.txt`: added (sitemap.xml itself was already auto-generated and working — 113 URLs, verified)
- Commits: `51ad88f` (pipeline+site code), `b41930f` (content backfill)

**Session 9 (2026-08-09):** Added Terms & Conditions, Privacy Policy, and Accessibility Policy pages (`site/src/pages/{terms,privacy,accessibility}.md`) plus a "Legal" footer column linking to them (`site/docusaurus.config.ts`). Verified via `npm run typecheck` and a full `npm run build` (111 laws, pages render at `/terms`, `/privacy`, `/accessibility`). Committed as `3389d5c`, pushed, deployed via `USE_SSH=true GIT_USER=Yuvaldv npm run deploy`. Import remains paused at 111/718 — untouched this session.

**Session 10 (2026-08-09) — Milestone v1.1 kickoff:** Started milestone v1.1 (UK Laws, England only) in parallel with the still-open v1.0. Scoped explicitly to England (Westminster `ukpga`/`aep` Acts read for their England extent) — Scotland/Wales/NI are future milestones. Ran project research (4 files + SUMMARY, HIGH confidence): legislation.gov.uk publishes CLML XML, so the UK path is a *rendering* problem, not a reconstruction problem — no OCR, no Gemini, deterministic `lxml` tree walk. Defined 23 v1.1 requirements (UKFETCH ×3, UKCONV ×10, UKVALID ×2, UKLINK ×3, UKSITE ×5). Resolved the one open research decision with the user: rebase Israel `/laws` → `/laws/israel` now with client redirects for the 111 indexed URLs. Roadmap created as Phases 7–13, continuing v1.0's numbering; all 23 requirements mapped.

**Next-session actions:**

1. Plan Phase 7 (`/gsd:plan-phase 7`) — shared-core extraction into `pipeline/common/`, gated on `git diff --stat laws/israel/` staying empty
2. Do NOT resume the Israel factory import (`batch_import.py`) unless explicitly asked — still paused at 111/718
3. Phase 9 and Phases 10/11 are flagged for a deeper research pass at planning time (amendment-markup edge cases; Docusaurus multi-instance + redirects config against the installed version)

**Files to review on re-entry:**

- `.planning/ROADMAP.md` — v1.0 Phases 1–6 (open) + v1.1 Phases 7–13 (new)
- `.planning/REQUIREMENTS.md` — v1.1's 23 requirements + traceability
- `.planning/research/SUMMARY.md` — CLML findings, pitfalls, build-order rationale
- `pipeline/batch_import.py` — main Israel factory loop (source for the Phase 7 common extraction)
- `pipeline/reconcile.py` — `build_frontmatter()` / `build_seo_description()` (frontmatter contract to share)
- `site/docusaurus.config.ts`, `site/sidebars.ts` — targets for the Phase 10 route rebase and Phase 11 second instance
- `site/src/theme/DocItem/Content/index.jsx`, `site/scripts/generate-law-meta.js`, `site/src/clientModules/lawSort.js` — the three files hardcoding Hebrew/RTL/Israel and numeric law IDs (Phase 11)

**Deploy status:** Pushed `main` → `origin/main` (up through `3389d5c`) and deployed to GitHub Pages (`gh-pages`). Live at https://Yuvaldv.github.io/codex-civica/. Deploy command: `USE_SSH=true GIT_USER=Yuvaldv npm run deploy`.

---

*Last updated: 2026-08-09 (session 10) — milestone v1.1 roadmap created (Phases 7–13, 23/23 requirements mapped); Israel import still paused at 111/718*
