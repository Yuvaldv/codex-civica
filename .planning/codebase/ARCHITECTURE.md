<!-- refreshed: 2026-05-08 -->
# Architecture

**Analysis Date:** 2026-05-08

## System Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                      Data Sources (External)                    │
│    Knesset API, government document sites, raw legal files      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Pipeline (Python)                           │
│  `pipeline/`  — scrape, parse, normalize, write Markdown        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ writes .md files
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Content Store (Markdown)                       │
│  `laws/`  — structured legal content per jurisdiction          │
│  `data/raw/`  — raw source files before processing             │
└─────────────────────────┬───────────────────────────────────────┘
                          │ consumed at build time
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Site (Docusaurus)                           │
│  `site/`  — static site generator, React frontend              │
│  `site/docs/`  — law documents rendered as docs                │
│  `site/src/`   — custom React components and pages             │
└─────────────────────────┬───────────────────────────────────────┘
                          │ built artifact
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Deployment (GitHub Pages)                      │
│  `site/build/`  — static output, published via CI              │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File/Path |
|-----------|----------------|-----------|
| Pipeline | Scrape, parse, and convert legal documents to Markdown | `pipeline/` |
| Content Store | Versioned Markdown files representing laws by jurisdiction | `laws/`, `data/raw/` |
| Site | Docusaurus static site that renders laws as browsable docs | `site/` |
| CI/CD | Builds and deploys site to GitHub Pages on push to main | `.github/workflows/deploy.yml` |
| Docusaurus Config | Defines nav, plugins, theming for the public-facing site | `site/docusaurus.config.ts` |
| Homepage | Custom React landing page | `site/src/pages/index.tsx` |
| Feature Component | Homepage feature highlights section | `site/src/components/HomepageFeatures/index.tsx` |

## Pattern Overview

**Overall:** Multi-stage offline pipeline feeding a static site generator

**Key Characteristics:**
- No server-side runtime — the pipeline runs locally or in CI, producing static files
- Laws are stored as plain Markdown files in `laws/` — the "database" is the filesystem
- The site build step is a pure read of `laws/` and `site/docs/` into static HTML
- The pipeline is decoupled from the site: it produces content, the site consumes it
- Jurisdiction-based directory partitioning: `laws/israel/`, `data/raw/israel/`

## Layers

**Data Ingestion Layer:**
- Purpose: Pull raw legal documents from external sources (Knesset API, web)
- Location: `pipeline/`
- Contains: Python scripts that use `knesset-data`, `beautifulsoup4`, `requests`, `lxml`, `python-docx`
- Depends on: External APIs and web, `data/raw/` for intermediate storage
- Used by: Content Store (output destination)

**Content Store Layer:**
- Purpose: Versioned, normalized Markdown representation of laws by jurisdiction
- Location: `laws/`, `data/raw/`
- Contains: `.md` files with frontmatter, organized by country (`laws/israel/`)
- Depends on: Pipeline (populated by)
- Used by: Site build (`site/docs/` or directly linked)

**Presentation Layer:**
- Purpose: Docusaurus static site rendering laws as searchable, navigable docs
- Location: `site/`
- Contains: Docusaurus config, React TSX components, MDX docs, blog posts
- Depends on: `laws/` content (at build time), Node.js >=20
- Used by: End users via browser; deployed to GitHub Pages

**CI/CD Layer:**
- Purpose: Automated build and deployment on push to `main`
- Location: `.github/workflows/deploy.yml`
- Contains: GitHub Actions workflow — install, build, publish to `gh-pages` branch
- Depends on: `site/` build pipeline
- Used by: GitHub Actions runner

## Data Flow

### Primary Content Flow (Pipeline to Site)

1. Pipeline scripts fetch raw legal data from external sources — `pipeline/` (Python scripts, not yet implemented beyond scaffold)
2. Raw files stored in `data/raw/israel/` for preservation
3. Pipeline parses and normalizes documents using `knesset-data`, `lxml`, `python-docx`, `beautifulsoup4`
4. Normalized content written as Markdown files to `laws/israel/`
5. Markdown files carry YAML frontmatter via `python-frontmatter`
6. At site build time, Docusaurus reads `site/docs/` (which will reference or mirror `laws/`) and generates static HTML
7. `npm run build` inside `site/` produces `site/build/`
8. CI pushes `site/build/` to the `gh-pages` branch

### CI/CD Flow (Push to Deploy)

1. Push to `main` triggers `.github/workflows/deploy.yml`
2. Node.js 20 installed, `npm ci` run in `site/`
3. `npm run build` executed in `site/`
4. `peaceiris/actions-gh-pages@v3` publishes `site/build/` to GitHub Pages

**State Management:**
- No runtime state — all state is Markdown files on disk in `laws/` and `data/raw/`
- Site has no client-side state management (Docusaurus default)
- Docusaurus sidebar is auto-generated from `laws/` directory structure via `{type: 'autogenerated'}`

## Key Abstractions

**Jurisdiction Directory:**
- Purpose: Partitions all content by country code (e.g., `israel`)
- Examples: `laws/israel/`, `data/raw/israel/`
- Pattern: `laws/<country>/` and `data/raw/<country>/` — add new jurisdictions by creating a new subdirectory

**Law Document:**
- Purpose: A single normalized legal document as a Markdown file with YAML frontmatter
- Examples: `laws/israel/*.md` (currently empty scaffold)
- Pattern: Markdown + frontmatter, filename reflects law identifier

**Pipeline Script:**
- Purpose: One or more Python scripts that ingest a source and write to `laws/` or `data/raw/`
- Examples: `pipeline/` (scaffold only — no `.py` files yet)
- Pattern: Python module using `knesset-data`, `requests`, `lxml`, `Anthropic SDK` (AI-assisted processing)

## Entry Points

**Site Development:**
- Location: `site/`
- Triggers: `npm run start` (dev server) or `npm run build` (production)
- Responsibilities: Serves Docusaurus site with hot reload or produces static build

**Pipeline Execution:**
- Location: `pipeline/` (Python)
- Triggers: Manual execution or future CI job
- Responsibilities: Fetch, parse, normalize legal data into `laws/`

**CI Deployment:**
- Location: `.github/workflows/deploy.yml`
- Triggers: Push or PR to `main`
- Responsibilities: Build site, deploy to GitHub Pages

## Architectural Constraints

- **Threading:** Pipeline is Python — synchronous execution expected; no async framework detected in dependencies
- **Global state:** None — filesystem is the only shared state between pipeline and site
- **Circular imports:** Not applicable — pipeline (Python) and site (TypeScript/React) are fully decoupled
- **Content coupling:** The site build will fail if `laws/` files have broken Markdown or invalid frontmatter — content quality is a build-time concern
- **No database:** All persistence is files. Scaling requires either more files or a migration away from flat-file storage.

## Anti-Patterns

### Uninitialized Pipeline

**What happens:** `pipeline/` contains only `requirements.txt` with no Python source files. The `data/raw/israel/` and `laws/israel/` directories are empty stubs.
**Why it's wrong:** The system has no working data ingestion. The site has no real content. Everything past the scaffold is unimplemented.
**Do this instead:** Add Python scripts to `pipeline/` following the pattern of reading from `knesset-data` and writing Markdown to `laws/israel/`.

### Unconfigured Docusaurus Site

**What happens:** `site/docusaurus.config.ts` still contains Docusaurus template defaults (`title: 'My Site'`, `organizationName: 'facebook'`, `url: 'https://your-docusaurus-site.example.com'`).
**Why it's wrong:** The site cannot be correctly deployed or indexed until these values are updated to reflect the actual project.
**Do this instead:** Update `site/docusaurus.config.ts` with correct `title`, `url`, `organizationName`, `projectName`, `baseUrl`, and `editUrl` values for the codex-civica repo.

## Error Handling

**Strategy:** Not yet defined — pipeline has no source files to inspect

**Patterns:**
- Docusaurus is configured with `onBrokenLinks: 'throw'` — broken doc links fail the build hard
- Pipeline dependencies include `tqdm` for progress reporting during long ingestion runs

## Cross-Cutting Concerns

**Logging:** Pipeline — `tqdm` for progress bars; no structured logging framework detected
**Validation:** `pydantic` v2 is available in pipeline requirements — expected to be used for document schema validation
**Authentication:** `anthropic` SDK in pipeline requirements suggests AI-assisted content processing; auth via environment variable (`ANTHROPIC_API_KEY`)

---

*Architecture analysis: 2026-05-08*
