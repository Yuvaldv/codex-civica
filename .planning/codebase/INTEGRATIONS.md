# External Integrations

**Analysis Date:** 2026-05-08

## APIs & External Services

**AI / Language Models:**
- Anthropic Claude API — AI-assisted processing of legal text in the data pipeline
  - SDK/Client: `anthropic==0.100.0` (`pipeline/requirements.txt`)
  - Auth: `ANTHROPIC_API_KEY` environment variable (`.env`, gitignored)

**Parliamentary Data:**
- Knesset Open Data API — Source for Israeli parliamentary law data
  - SDK/Client: `knesset-data==2.1.5` + `pyslet==0.7.20170805` (OData/Atom feed client)
  - Auth: Public API — no credentials required
  - Data landing zone: `data/raw/israel/`

## Data Storage

**Databases:**
- None — no database detected. Processed law content is stored as Markdown files in `laws/` (e.g., `laws/israel/`) and raw source files in `data/raw/`.

**File Storage:**
- Local filesystem only
  - Raw downloads: `data/raw/`
  - Processed Markdown laws: `laws/`
  - Published site content: `site/docs/`, `site/blog/`

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- None — no user authentication. The site is fully static and public-facing.

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- `tqdm==4.67.3` provides pipeline progress output to stdout
- No structured logging framework detected

## CI/CD & Deployment

**Hosting:**
- GitHub Pages — static site published to GitHub Pages on every push to `main`

**CI Pipeline:**
- GitHub Actions — `.github/workflows/deploy.yml`
  - Trigger: push or PR to `main`
  - Steps: checkout → setup Node 20 → `npm ci` (in `site/`) → `npm run build` → deploy via `peaceiris/actions-gh-pages@v3`
  - Secrets used: `GITHUB_TOKEN` (auto-provided by GitHub Actions)
  - Publish directory: `site/build/`

**Pipeline execution:**
- Python data pipeline runs outside CI (no workflow job defined for pipeline steps yet)

## Environment Configuration

**Required env vars:**
- `ANTHROPIC_API_KEY` — Required for pipeline AI processing (Claude API)

**Secrets location:**
- `.env` file in repo root (gitignored, not committed)
- `.env.local` also gitignored
- `GITHUB_TOKEN` injected automatically by GitHub Actions at deploy time

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

## Document Parsing (External Format Support)

**Library integrations for source document formats:**
- `.docx` (Word): `python-docx==1.2.0`
- `.rtf`: `pyth==0.6.0`
- HTML/XML: `beautifulsoup4==4.14.3` + `lxml==6.1.0`
- OData/Atom feeds: `pyslet==0.7.20170805` (Knesset API feed format)

---

*Integration audit: 2026-05-08*
