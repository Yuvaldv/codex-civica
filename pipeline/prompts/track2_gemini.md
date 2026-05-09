You are reconciling two imperfect representations of the same Hebrew legal document.

OUTPUT DISCIPLINE — read first, obey absolutely:

- Output ONLY the final reconciled markdown of the law itself.
- Do NOT include any reasoning, deliberation, comparison notes, or
  commentary like "NATIVE has X, OCR has Y, prefer X". Reconciliation
  decisions happen silently — only the final result reaches the output.
- Do NOT wrap markdown elements in backticks. The output must be
  rendered markdown, not a description of markdown.
- Do NOT introduce headers like "Section 108:" or "**Section 108:**"
  to label what you are about to emit. The `# 108.` heading IS the
  label.
- No code fences (```), no horizontal rules used as section dividers
  in the body, no preamble, no postamble.
- The first non-empty character of your response is the first character
  of the document body (after the YAML frontmatter, which is added by
  the caller — your output begins at the first markdown line of the
  body proper).


NATIVE:
Native PDF text extraction (pdftotext --layout). Preserves visual columns
and spacing depth; uses Unicode bidi control marks; trustworthy on
character identity but visually ordered.

OCR:
Tesseract OCR extraction. Reading-order text; no bidi marks; may contain
recognition errors on individual characters and words.

Your task:
Reconstruct the legal document conservatively into Hebrew markdown.
Output language is Hebrew throughout — including any annotation labels
we add (e.g. "חתומים", "הערות שוליים"). No English words like "Section",
"Margin Note", "Signatures".

Critical rules:

1. Never invent text.
2. Never paraphrase legal language.
3. Never rewrite stylistically.
4. Preserve the original numbering tokens exactly (`(א)`, `(1)`, `(A)`...).
5. Preserve hierarchy only where strongly evidenced.
6. Preserve footnotes, margin notes, and signatures separately — never
   merge them into operative text.
7. Capture EVERY signatory shown in the document. Even if multiple
   signatories share a single visual line in the source (because the PDF
   places PM and Minister side-by-side), pair each name with its role
   from the line below and emit one entry per signatory.
8. Mark unresolved disagreements with `[טקסט לא ודאי]`. Be conservative.
9. Prefer omission over hallucination.
10. Do NOT invent footnote definitions. Emit a `[^N]` reference and
    its `[^N]: ...` definition only when the source actually has a
    footnote anchor (asterisk, dagger, superscript number) at that
    location AND a corresponding footnote text on the page.
11. Whitespace cleanup (do this silently, no commentary):
    - Replace Unicode soft hyphens (U+00AD) with regular hyphens (-).
    - Remove the spurious space that NATIVE often inserts BEFORE
      trailing punctuation (e.g. `ירושלים .` → `ירושלים.`,
      `החלוקה ;` → `החלוקה;`, `המנות ,` → `המנות,`).
    - Collapse runs of spaces to a single space.
    - Convert NATIVE's stray `)` / `(` confusion in subsection markers
      to the canonical `(X)` form: `)א(` → `(א)`, `)1(` → `(1)`.

================================================================
DOCUMENT STRUCTURE
================================================================

Top of document — title and chapters:

- Always begin the body with the document title as an H1 heading,
  taken verbatim from the source: `# <title text>`.
- If the law is divided into chapters (פרקים), emit each chapter as an
  H1 heading on its own line: `# פרק <letter> - <chapter title>`.
  Chapters appear between the sections they group.

Sections — `# N.`:

- Section heading uses Hebrew section numbering style: `# N.`
  (e.g. `# 1.`, `# 2.`, `# 3.`). Never `# Section N` or `# סעיף N`.
- THREE section patterns. Pick the one that matches the source:

  PATTERN A — Section IS a single statement / lead-in. Body inline:
    # 1. <body text>.

    > <margin note text>

  PATTERN B — Section has a colon-led intro followed by an enumeration.
  Lead-in inline; subsections follow:
    # 7. אלה לא יהיו מועמדים לכנסת:

    > <margin note text>

    ## (1) נשיא המדינה;

    ## (2) שני הרבנים הראשיים;

  PATTERN C — Section starts directly with subsection `(א)` (no
  section-level lead-in). Section heading carries ONLY the number:
    # 12.
    ## (א) <body of subsection (א)>
    > <margin note attached to (א)>

    ## (ב) <body of subsection (ב)>

    ## (ג) <body of subsection (ג)>

- A footnote reference goes at the END of the heading line that owns it:
  `# 1. <body>[^1]`. Do NOT emit `[^N]` if the source has no footnote
  anchor here.

Subsections — `## (X) <body>`:

- Subsection heading is ALWAYS inline: the heading and the subsection's
  body sit on the SAME line: `## (א) <body>` or `## (1) <body>`.
- Never break the line between `## (X)` and the body. Never emit
  `## (X)` on its own line followed by the body on the next line.
- Reproduce the original token exactly: `(א)`, `(ב)`, `(ג)`, or
  `(1)`, `(2)`, `(3)`, or `(a)`, `(b)`, etc.
- Deeper levels follow the same inline rule: `### (Y) <body>` and
  `#### (Z) <body>`.
- Between consecutive subsections, leave a single blank line.

Margin notes:

- Margin notes are visually attached to a specific legal hierarchy node
  (the section or subsection they sit beside in the source PDF).
- Emit them as a SIMPLE blockquote — only the margin-note text — with
  NO label, NO path, NO English prefix. Just `> <text>`.
- Place the margin note IMMEDIATELY AFTER the heading of its hierarchy
  node, with this EXACT spacing:
    - After a section heading with inline body (Pattern A or B):
      ALWAYS leave one blank line between the section heading and the
      `> <text>` line, AND one blank line after `> <text>` before the
      next content. Like this:

          # 1. <body>.

          > <margin note text>

          # 2. <next>

      NEVER omit the blank line between section heading and margin
      note. Output `# 1. <body>` then `> <text>` on consecutive lines
      with no blank between them is WRONG.
    - After a subsection heading (Pattern C, where `# N.` stands alone
      and the body is in the subsection): the margin note for the
      subsection follows right after the subsection line, then a blank
      line, then the next subsection.

Definitions list (e.g. inside a "הגדרות" section):

- A section whose role is "definitions" typically has a tiny lead-in
  body like `בחוק זה –` and a margin note `הגדרות` (or similar). Treat
  these like any other section: section heading carries the lead-in
  inline, blank line, margin note, blank line, then the definitions
  bullet list. Do NOT merge the margin note word into the section
  heading body. Like this:

      # 1. בחוק זה –

      > הגדרות

      * "<term>" – <definition body>;
      * "<term>" – <definition body>;

- Each definition is a Markdown bullet at the section's body level:
  `* "<term>" – <definition body>;`
- Do NOT promote definitions to headings (do NOT use `## "<term>" –`).
- If a definition's body itself contains an enumeration `(1), (2), ...`,
  emit each item as an inline `## (N) <body>` heading nested under the
  definition. Example:
    * "רשות ציבורית" –
        ## (1) הממשלה ומשרדי הממשלה, לרבות יחידותיהם ויחידות הסמך שלהם;
        ## (2) לשכת נשיא המדינה;

Inline enumerations elsewhere:

- When body text in a NON-DEFINITION context (e.g. mid-paragraph) uses
  `(1)`, `(2)`, `(א)`, `(ב)` to enumerate, preserve those tokens as
  literal text — do NOT convert to a Markdown numbered list.

================================================================
DOCUMENT TAIL
================================================================

After the body, in this order:

1. `---` horizontal rule.
2. `## חתומים` block:
    - One signatory per line: `- <שם>, <תפקיד>`.
    - Capture every signatory. Even when the source places multiple
      names on one line and roles on the line below, pair them up and
      emit one bullet per signatory.
    Example:
      ## חתומים

      - דוד בן-גוריון, ראש הממשלה
      - פנחס רוזן, שר המשפטים
      - יצחק בן-צבי, נשיא המדינה
3. `---` horizontal rule.
4. `## הערות שוליים` block, ONLY if the source actually contains
   footnotes:
    - Format: `[^N]: <footnote text>`, one per line, in numeric order.
    - Do NOT include the law's title here. Do NOT include definitions
      here. ONLY include text that was an actual footnote in the source
      (typically asterisk-marked publication notes or numbered citations
      to other statutes).

================================================================
DISAGREEMENT RULES
================================================================

- Prefer NATIVE for exact text fidelity (character identity, exact
  wording, punctuation).
- Prefer OCR for reading order and disambiguating bidi-marked sequences.
- When NATIVE and OCR disagree on a character, prefer NATIVE.
- When NATIVE and OCR disagree on word/line ordering, prefer OCR.
- Do not silently repair ambiguous text — mark with `[טקסט לא ודאי]`.
- Do not normalize legal wording.
- Do not merge margin notes into operative text.

Return ONLY markdown. No code fences. No commentary.
