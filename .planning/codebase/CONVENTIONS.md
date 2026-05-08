# Code Conventions

**Mapped:** 2026-05-08
**Project:** codex-civica

## Languages

- **Frontend:** TypeScript (strict mode via `@docusaurus/tsconfig`)
- **Backend/Pipeline:** Python 3.x with pinned dependencies in `requirements.txt`
- **Content:** Markdown / MDX

## TypeScript / React Conventions

### Component Style
Functional components with explicit return type annotations:

```tsx
// site/src/components/HomepageFeatures/index.tsx
export default function HomepageFeatures(): ReactNode {
  return ( ... );
}
```

### Prop Types
Inline type aliases before component definition:

```tsx
type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: ReactNode;
};
```

### Imports
- React types via `import type { ReactNode } from 'react'`
- Docusaurus path aliases: `@site/src/...`, `@theme/...`
- CSS Modules: `import styles from './styles.module.css'`

### CSS
- CSS Modules for component-scoped styles (`styles.module.css` alongside each component)
- Global overrides in `site/src/css/custom.css`
- Docusaurus utility classes used directly in JSX (`clsx`, `hero--primary`, `col--4`)

### Key Anti-Pattern Present
`key={idx}` used in array map in `HomepageFeatures` — should use stable keys in new code:
```tsx
// Avoid (current code):
{FeatureList.map((props, idx) => <Feature key={idx} {...props} />)}
// Prefer:
{FeatureList.map((props) => <Feature key={props.title} {...props} />)}
```

## Python Conventions

No Python source files exist yet — only `pipeline/requirements.txt` with pinned versions.

### Dependency Management
All Python dependencies pinned to exact versions in `pipeline/requirements.txt`. Add new dependencies with pinned versions.

## Markdown / MDX Conventions

- Content files use `.mdx` extension in `site/docs/` and `site/blog/`
- Law content uses `.md` with `_index.md` as directory entry points
- Frontmatter expected by Docusaurus: `title`, `sidebar_label`, `description`

## Docusaurus Configuration

- Config in TypeScript (`docusaurus.config.ts`) using `satisfies` type assertions
- Sidebar defined in `sidebars.ts` as `SidebarsConfig`
- Future flags enabled (`future.v4: true`) for Docusaurus v4 compatibility

## Error Handling

No established patterns yet — codebase is scaffold/boilerplate stage.

---
*Mapped: 2026-05-08*
