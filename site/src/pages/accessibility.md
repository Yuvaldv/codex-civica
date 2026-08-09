---
title: Accessibility Policy
description: Accessibility commitment and known limitations for Codex Civica.
---

# Accessibility Policy

_Last updated: 2026-08-09_

## Our commitment

Codex Civica aims to make legislative text readable and navigable for as many people as possible, including people using assistive technologies such as screen readers, keyboard-only navigation, or browser zoom/high-contrast modes. We build on [Docusaurus](https://docusaurus.io), which follows semantic HTML and accessibility conventions out of the box, and we work incrementally to improve on that baseline. This is an ongoing effort rather than a certified or audited compliance status — we have not undergone a formal WCAG conformance audit.

## What we've done

- Set correct page language (`lang`) and text direction (`dir`) attributes on law pages, since the underlying legislation is in Hebrew and rendered right-to-left, while the site's own interface is in English.
- Added descriptive, per-page titles and meta descriptions so pages are distinguishable when browsing with a screen reader or in search results.
- Preserved the numbering and hierarchical structure of legal text (sections, subsections, clauses) using semantic markdown headings, so the structure is conveyed to assistive technology, not just visually.

## Known limitations

- Legal text on this site is reconstructed from scanned/native PDF sources through an automated extraction and OCR pipeline. Some regions of some documents may be marked as uncertain, incompletely structured, or still pending import — this reflects the source material and conversion process, not an accessibility feature.
- Not every law currently on the site has been individually reviewed for reading order, table structure, or alt text on any embedded images.
- Color contrast and interactive components follow the Docusaurus theme defaults with brand color overrides; these have not been independently audited against WCAG 2.1 AA.

## Reporting an issue

If you encounter an accessibility barrier on this site — content that isn't reachable by keyboard, isn't announced correctly by a screen reader, or is otherwise hard to use — please let us know via [GitHub Issues](https://github.com/Yuvaldv/codex-civica/issues). Include the page URL and, if possible, the assistive technology and browser you were using. We treat accessibility reports as bugs and prioritize fixes accordingly.
