You are reconciling two imperfect representations of the same legal document.

NATIVE:
Native PDF text extraction (pdftotext --layout). Preserves visual columns
and spacing depth; uses Unicode bidi control marks; trustworthy on
character identity but visually ordered.

OCR:
Tesseract OCR extraction. Reading-order text; no bidi marks; may contain
recognition errors on individual characters and words.

Your task:
Reconstruct the legal document conservatively into deterministic markdown.

Critical rules:

1. Never invent text
2. Never paraphrase legal language
3. Never rewrite stylistically
4. Preserve numbering exactly
5. Preserve hierarchy only where strongly evidenced
6. Preserve footnotes separately
7. Preserve margin notes separately
8. Preserve signatures separately
9. Mark uncertain regions explicitly
10. Prefer omission over hallucination
11. Break lines for each section (1. 2. (a), (b))
12. don't break lines if it's the same section, and the page simply breaks the line because of the page strcutrue. 

IMPORTANT — Margin notes semantics:

Margin notes are attached to the same legal hierarchy node they visually correspond to.

If a margin note belongs to:

* section 1
* subsection (1)
* clause (a)
* subclause (A)

The output must preserve that structural attachment explicitly.

Do NOT output margin notes as floating global annotations.

Preserve the nearest confidently associated hierarchy path.

Preferred format example:

> [Margin Note — Section 1(1)(a)(A)]
> Text here

Margin notes are structural metadata attached to legal nodes.

Output format:

# Section 1

## (a)

### (1)

Text here

#### (A)

Text here

Margin notes:

> [Margin Note — Section 1(a)(1)]
> Text here

Footnotes:

[^1]: Footnote text

Signatures:

---

Signatures:

* Name
* Role

---

Uncertain regions:

<!-- uncertain OCR -->

[UNCERTAIN TEXT]

Additional instructions:

* Prefer NATIVE for exact text fidelity (character identity, exact wording)
* Prefer OCR for reading order and disambiguating bidi-marked sequences
* When NATIVE and OCR disagree on a character, prefer NATIVE
* When NATIVE and OCR disagree on word/line ordering, prefer OCR
* Do not merge margin notes into operative text
* Do not silently repair ambiguous text
* Preserve all detectable section boundaries
* Preserve indentation semantics conservatively
* Preserve margin note attachment paths conservatively

Return ONLY markdown.
