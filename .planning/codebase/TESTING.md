# Testing

**Mapped:** 2026-05-08
**Project:** codex-civica

## Current State

**Zero tests exist in this codebase.** No test files, no test framework configuration, no CI test gates.

## Frontend (site/)

- No test framework installed (`package.json` has no Jest, Vitest, Playwright, or Cypress)
- No `*.test.ts`, `*.spec.ts`, or `__tests__/` directories
- TypeScript type checking available via `npm run typecheck` (tsc)

## Backend / Pipeline (pipeline/)

- No test framework in `requirements.txt` (no pytest, unittest, etc.)
- No test files
- No test runner configured

## CI / CD

No CI configuration file found (no `.github/workflows/`, no `.circleci/`, etc.)

## Gaps to Address

| Gap | Priority | Notes |
|-----|----------|-------|
| Frontend unit tests | Medium | Vitest + React Testing Library recommended for Docusaurus/React |
| Pipeline unit tests | High | pytest for Python pipeline scripts |
| Frontmatter schema validation | High | Validate law Markdown before site build |
| CI test gate | High | Tests should run before deploy |
| E2E tests | Low | Playwright for site smoke tests post-deploy |

## Recommendations for New Code

- Add **pytest** to `pipeline/requirements.txt` for pipeline tests
- Add **Vitest** + `@testing-library/react` to `site/` devDependencies for component tests
- Validate law frontmatter schema before ingestion into `site/docs/`

---
*Mapped: 2026-05-08*
