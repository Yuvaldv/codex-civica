We are building a legal PDF → markdown conversion pipeline for laws and regulations.

Goal:
Reconstruct legal intent and hierarchy conservatively and deterministically.

Core rules:

* Never hallucinate text
* Never paraphrase legal language
* Preserve numbering exactly
* Preserve hierarchy conservatively
* Prefer explicit uncertainty over incorrect confidence
* Treat the PDF as multiple noisy witnesses of the same document
* Optimize for legal fidelity, not prettiness

Architecture:

LAYER 1 — Native PDF extraction

Extract embedded text directly from the PDF.

Tools:

* pdfplumber
* pymupdf
* pdftotext

Output:
native.txt

LAYER 2 — OCR extraction

Run Tesseract OCR on rendered PDF pages.

Preserve:

* line order
* indentation
* spacing depth
* page boundaries

If possible also preserve:

* coordinates
* bounding boxes
* layout regions

Outputs:
ocr.txt
ocr_layout.json

LAYER 3 — Reconciliation

Feed BOTH native.txt and OCR output into Gemini Flash.

Gemini is NOT rewriting the document.

Gemini is acting as a conservative reconciliation engine.

Gemini responsibilities:

* correct obvious OCR mistakes
* restore missing structure
* preserve numbering exactly
* preserve hierarchy only where strongly evidenced
* isolate margin notes
* isolate footnotes
* isolate signatures
* mark uncertain regions explicitly
* never invent text
* never normalize legal wording

IMPORTANT — Margin notes semantics:

Margin notes belong to the operative section they are attached to.

The system must preserve the relationship between:

* section numbers
* subsection numbers
* clause hierarchy
* attached margin notes

Example:
If a margin note visually corresponds to:

* Section 3
* subsection (א)
* clause (1)

Then the markdown output must reflect that association explicitly.

Do NOT float margin notes globally without structural attachment.

Preferred format example:

> [Margin Note — Section 3(א)(1)]
> Budget proposal timing

Or equivalent deterministic representation.

Margin notes are metadata attached to legal hierarchy nodes.

Markdown output rules:

Hierarchy example:

# Section 1

## (a)

### (1)

Text here

#### (A)

Text here

Margin notes:

> [Margin Note — Section 1(a)(1)]
> Text

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

Validation requirements:

Implement validators for:

* numbering continuity
* orphan subsections
* malformed nesting
* duplicate headings
* broken clause sequences
* unattached margin notes

Example:
(a)
(b)
(d)

Must flag missing (c).

Validation errors must never be silently ignored.

Development rules:

* Do not redesign architecture prematurely
* Do not over-abstract
* Do not refactor without evidence
* Iterate incrementally
* Keep fixtures and golden outputs
* Compare outputs before updating pipeline logic
* Only change the system when evidence shows improvement

Current task:

Implement the first working end-to-end pipeline using:

* native PDF extraction
* Tesseract OCR
* Gemini Flash reconciliation
* deterministic markdown rendering
* validation layer

Focus on getting one law converted correctly before generalizing.
