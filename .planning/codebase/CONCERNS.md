# Concerns & Technical Debt

**Mapped:** 2026-05-08
**Project:** codex-civica

## Tech Debt

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | Pipeline entirely unimplemented | `pipeline/` | High |
| 2 | Docusaurus site unconfigured (still default boilerplate) | `site/docusaurus.config.ts` | High |
| 3 | `laws/` content not wired to `site/docs/` | `laws/`, `site/docs/` | High |
| 4 | `laws/_index.md` and `laws/israel/_index.md` are empty | `laws/` | Medium |
| 5 | `data/raw/israel/` is empty — no source data ingested | `data/raw/israel/` | Medium |
| 6 | No pip lockfile (`requirements.lock`) — only `requirements.txt` | `pipeline/` | Low |
| 7 | `site/docs/` and `site/blog/` contain Docusaurus default tutorial content | `site/` | Low |

## Known Bugs

| Bug | Location | Notes |
|-----|----------|-------|
| `key={idx}` anti-pattern | `site/src/components/HomepageFeatures/index.tsx:64` | Array index as React key causes reconciliation issues on reorder |
| Empty `_index.md` files | `laws/_index.md`, `laws/israel/_index.md` | May cause Docusaurus build warnings or 404s |

## Security

| Issue | Location | Severity | Notes |
|-------|----------|----------|-------|
| Unpinned third-party GitHub Action | (no CI file yet, but `site/package.json` references GitHub) | Medium | When CI is added, pin action SHAs, not tags |
| No CSP headers configured | `site/docusaurus.config.ts` | Medium | No `headers` plugin or security headers |
| API key injection undocumented | `pipeline/requirements.txt` (anthropic==0.100.0) | Medium | Anthropic API key usage not documented; ensure it's via env var, never hardcoded |

## Performance

| Issue | Location | Notes |
|-------|----------|-------|
| No image optimization | `site/static/img/` | Docusaurus has built-in image optimization via `@docusaurus/faster` (already installed) |
| No incremental pipeline processing | `pipeline/` | Pipeline not yet built; design for incremental updates from the start |

## Fragile Areas

| Area | Risk | Mitigation |
|------|------|-----------|
| Site build on bad frontmatter | High — `onBrokenLinks: 'throw'` will fail build | Add frontmatter validation before build |
| No CI test gate before deploy | High — broken builds can reach production | Add CI pipeline with build + test steps |
| `pyslet` (last release 2017) | Medium — unmaintained, may break on Python 3.12+ | Evaluate alternatives or fork |
| `pyth` (0.6.0) | Medium — unmaintained RTF parser | Verify still functional; consider `python-docx` as alternative |
| `knesset-data` (2.1.5) | Medium — niche library, unclear maintenance | Pin tightly; have fallback if API changes |

## Missing Features (Blocking Core Functionality)

| Feature | Impact |
|---------|--------|
| Data pipeline (`pipeline/`) | No law data can be ingested without it |
| `laws/` → `site/docs/` wiring | Laws are not accessible on the site |
| Site identity (title, logo, URLs) | Still shows Docusaurus defaults |
| Search | No search configured in `docusaurus.config.ts` |
| Pipeline CI job | No automated data refresh |

## Dependency Risk

| Package | Version | Risk |
|---------|---------|------|
| `pyslet` | 0.7.20170805 | Last release 2017 — likely incompatible with modern Python |
| `pyth` | 0.6.0 | Unmaintained RTF library |
| `knesset-data` | 2.1.5 | Niche, unclear maintenance status |

---
*Mapped: 2026-05-08*
