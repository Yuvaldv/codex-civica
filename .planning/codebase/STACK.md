# Technology Stack

**Analysis Date:** 2026-05-08

## Languages

**Primary:**
- Python 3.12 - Data pipeline (`pipeline/`)
- TypeScript ~6.0.2 - Site frontend (`site/src/`)

**Secondary:**
- MDX / Markdown - Content authoring (`site/docs/`, `site/blog/`, `laws/`)
- CSS / CSS Modules - Site styling (`site/src/css/`, `site/src/components/`)
- YAML - Configuration and metadata (`mempalace.yaml`, `site/blog/authors.yml`)
- JSON - Data files and configuration (`entities.json`, `site/package.json`)

## Runtime

**Environment:**
- Python 3.12 (pipeline) — isolated via `.venv/` (venv)
- Node.js >=20.0 (site) — Node v22.22.2 confirmed in dev environment

**Package Manager:**
- Python: pip — lockfile via pinned `pipeline/requirements.txt`
- Node: npm 10.9.7 — Lockfile: `site/package-lock.json` (present)

## Frameworks

**Core:**
- Docusaurus 3.10.1 (`@docusaurus/core`) — Static site generator for the public-facing legal reference site (`site/`)
- React 19.0 — UI rendering inside Docusaurus (`site/src/`)

**Build/Dev:**
- Docusaurus CLI — `docusaurus start`, `docusaurus build`, `docusaurus serve` (configured in `site/package.json`)
- TypeScript strict mode — type-checked via `tsc` (`site/tsconfig.json`)
- MDX (`@mdx-js/react` ^3.0.0) — Markdown with JSX in docs and blog

## Key Dependencies

**Pipeline (Python):**
- `anthropic==0.100.0` - Anthropic Claude SDK for AI-assisted law processing
- `knesset-data==2.1.5` - Knesset (Israeli parliament) open data client
- `beautifulsoup4==4.14.3` - HTML parsing for law document scraping
- `lxml==6.1.0` - XML/HTML parsing (used alongside bs4)
- `pydantic==2.13.4` - Data validation and schema enforcement
- `python-frontmatter==1.1.0` - Parse/write YAML frontmatter in Markdown files
- `python-docx==1.2.0` - Parse `.docx` law source files
- `Markdown==3.10.2` - Markdown rendering for law content
- `requests==2.33.1` - HTTP client for external data fetching
- `tqdm==4.67.3` - Progress bars for pipeline runs
- `PyYAML==6.0.3` - YAML serialization
- `python-hebrew-numbers==0.2.3` - Hebrew numeral conversion (domain-specific)
- `pyth==0.6.0` - RTF document parsing
- `pyslet==0.7.20170805` - OData/Atom feed client (Knesset API)

**Site (Node):**
- `@docusaurus/preset-classic 3.10.1` - Full preset (docs + blog + theme)
- `@docusaurus/faster 3.10.1` - Performance improvements for Docusaurus
- `prism-react-renderer ^2.3.0` - Syntax highlighting
- `clsx ^2.0.0` - Conditional CSS class utility
- `react ^19.0.0` + `react-dom ^19.0.0` - UI framework

## Configuration

**Environment:**
- `.env` file referenced in `.gitignore` (contains environment configuration — not committed)
- `.env.local` also gitignored
- Expected env vars: Anthropic API key (for pipeline AI calls)
- No environment variable loading library detected in site (Docusaurus handles via Node)

**Build:**
- `site/docusaurus.config.ts` — Main site config (URL, nav, presets, theme)
- `site/tsconfig.json` — TypeScript config extending `@docusaurus/tsconfig`
- `site/sidebars.ts` — Docs sidebar structure
- `pipeline/requirements.txt` — Pinned Python dependencies

**Line Endings:**
- LF enforced for all text files via `.gitattributes`
- Binary types declared: `.docx`, `.pdf`, `.png`, `.jpg`

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js >=20.0
- npm (for site dependencies)
- `.venv/` Python virtual environment in repo root

**Production:**
- Static site deployed to GitHub Pages via `peaceiris/actions-gh-pages@v3`
- Pipeline runs locally or in CI (no hosted runtime detected)
- No server/API deployment — fully static output

---

*Stack analysis: 2026-05-08*
