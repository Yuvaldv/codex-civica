# Codebase Structure

**Mapped:** 2026-05-08
**Project:** codex-civica

## Directory Layout

```
codex-civica/
├── data/                        # Raw source data
│   └── raw/
│       └── israel/              # Israeli legislative raw data (empty — not yet populated)
├── laws/                        # Processed law content (Markdown)
│   ├── _index.md                # Root index (empty placeholder)
│   └── israel/
│       └── _index.md            # Israel laws index (empty placeholder)
├── pipeline/                    # Python data pipeline
│   └── requirements.txt         # Pinned Python dependencies
├── site/                        # Docusaurus v3 website
│   ├── blog/                    # Blog posts (Docusaurus default samples)
│   ├── docs/                    # Documentation pages (Docusaurus default samples)
│   ├── src/
│   │   ├── components/
│   │   │   └── HomepageFeatures/  # Homepage feature cards component
│   │   │       ├── index.tsx
│   │   │       └── styles.module.css
│   │   ├── css/
│   │   │   └── custom.css       # Global CSS overrides
│   │   └── pages/
│   │       ├── index.tsx        # Homepage
│   │       ├── index.module.css
│   │       └── markdown-page.mdx
│   ├── static/
│   │   └── img/                 # Static images (logos, social card, illustrations)
│   ├── docusaurus.config.ts     # Site configuration (title, navbar, footer, plugins)
│   ├── sidebars.ts              # Docs sidebar structure
│   ├── tsconfig.json            # TypeScript config
│   ├── package.json             # Node dependencies
│   └── package-lock.json
├── entities.json                # MemPalace entity registry
└── mempalace.yaml               # MemPalace configuration
```

## Key Locations

| Purpose | Path |
|---------|------|
| Site entry point | `site/src/pages/index.tsx` |
| Site configuration | `site/docusaurus.config.ts` |
| Sidebar config | `site/sidebars.ts` |
| Homepage component | `site/src/components/HomepageFeatures/index.tsx` |
| Global styles | `site/src/css/custom.css` |
| Pipeline dependencies | `pipeline/requirements.txt` |
| Law content (Israel) | `laws/israel/` |
| Raw data (Israel) | `data/raw/israel/` |

## Naming Conventions

- **Site components:** PascalCase directories and files (`HomepageFeatures/index.tsx`)
- **CSS Modules:** `styles.module.css` alongside component
- **Law content:** Markdown with `_index.md` as directory entry points
- **Config files:** camelCase TypeScript (`.ts`) for Docusaurus config
- **Python files:** snake_case (no Python source files yet, only `requirements.txt`)

## Where to Add New Code

| Task | Location |
|------|----------|
| New site page | `site/src/pages/` |
| New React component | `site/src/components/<ComponentName>/` |
| New law document | `laws/<country>/<law-slug>.md` |
| Pipeline scripts | `pipeline/` (no scripts yet) |
| Raw source data | `data/raw/<country>/` |

---
*Mapped: 2026-05-08*
