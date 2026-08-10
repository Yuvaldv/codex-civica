#!/usr/bin/env python3
"""UKLINK-01/02/03 proof, independent of live batch content.

The current 10-Act starter batch has zero real in-batch citations (verified
by grepping every fetched XML's Citation URIs against the batch's own slugs)
-- every citation in the live data resolves external, so the in-batch branch
of render._resolve_link is structurally present but never actually exercised
by `python pipeline/uk/convert.py`. This synthetic two-document scenario
exercises it directly, using ir.py's dataclasses (no XML/clml.py needed --
this is a render.py logic test, not a parser test).

Run: ~/.venv-codex/bin/python pipeline/uk/tests/test_link_resolution.py
No pytest (deliberately -- see pipeline/tests/test_country_blind.py's
precedent; this pipeline keeps zero new test dependencies).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import render  # noqa: E402
import validate  # noqa: E402
from ir import Commentary, DocMeta, LegalDoc, Provision, Run  # noqa: E402

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"{status}  {label}" + (f"  -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def _meta(title: str) -> DocMeta:
    return DocMeta(
        title=title, long_title=None, year="2020", number="1", chapter="1",
        document_main_type="UnitedKingdomPublicGeneralAct", document_status="revised",
        enactment_date="2020-01-01", valid_date="2020-01-01", extent="E+W+S+N.I.",
        number_of_provisions=1, publisher="Statute Law Database",
    )


# ---------------------------------------------------------------------------
# Scenario: "amender-2020-1" (in the batch) amends section 3 of
# "amended-2010-1" (also in the batch, cited via CitationSubRef). A third
# citation targets an Act that is NOT in the batch (must go external).
# ---------------------------------------------------------------------------

BATCH = frozenset({"amender-2020-1", "amended-2010-1"})

amended_doc = LegalDoc(
    meta=_meta("Amended Act 2010"),
    body=[
        Provision(kind="section", id="section-3", number="3", runs=[Run(text="Original text.")]),
    ],
)

in_batch_citation = Run(
    text="section 3 of the Amended Act 2010", kind="citation",
    uri="http://www.legislation.gov.uk/id/amended/2010/1/section/3",
    target_anchor="section-3",
)
compound_citation = Run(
    text="s. 3(1)(2) of the Amended Act 2010", kind="citation",
    uri="http://www.legislation.gov.uk/id/amended/2010/1/section/3/1/2",
    target_anchor="section-3-1-2",  # compound ref -- no such single provision exists
)
external_citation = Run(
    text="the Unrelated Act 1999", kind="citation",
    uri="http://www.legislation.gov.uk/id/unrelated/1999/9",
)
self_citation = Run(
    text="section 3 of this Act", kind="citation",
    uri="http://www.legislation.gov.uk/id/amender/2020/1/section/3",
    target_anchor="section-3",
)
whole_doc_self_citation = Run(
    text="this Act", kind="citation",
    uri="http://www.legislation.gov.uk/id/amender/2020/1",  # no SectionRef at all
)

amender_doc = LegalDoc(
    meta=_meta("Amender Act 2020"),
    body=[
        Provision(kind="section", id="section-3", number="3", runs=[
            Run(text="See "), in_batch_citation, Run(text=", "),
            compound_citation, Run(text=", "),
            external_citation, Run(text=", "),
            self_citation, Run(text=", and "),
            whole_doc_self_citation, Run(text="."),
        ]),
    ],
)

md_amended, links_amended = render.render(amended_doc, retrieved_at="t", own_slug="amended-2010-1", batch_slugs=BATCH)
md_amender, links_amender = render.render(amender_doc, retrieved_at="t", own_slug="amender-2020-1", batch_slugs=BATCH)

# UKLINK-01 / UKLINK-03: a citation from one batch doc's own body text to
# another batch doc's specific provision becomes a relative internal link,
# at the exact point it appears -- this IS the "amending Act links inline
# back to the provision it amends" mechanism, exercised end to end.
check(
    "in-batch citation resolves to relative link with anchor",
    "[section 3 of the Amended Act 2010](./amended-2010-1.md#section-3)" in md_amender,
)

# Compound SectionRef ("s. 3(1)(2)") has no single matching provision in the
# target doc. Self-citations to one of these are known-safe to degrade (see
# check below) because a doc can cheaply verify its OWN anchors before
# trusting SectionRef. A CROSS-doc compound ref is a real, documented gap
# (render.py is a pure per-document function -- it doesn't have another doc's
# anchor set at render time to check against) -- it still emits the anchor
# optimistically, and relies on check_cross_references to catch it rather
# than silently showing a broken fragment. Proven below, not assumed.
check(
    "compound cross-doc SectionRef still emits an (unverified) anchor",
    "[s. 3(1)(2) of the Amended Act 2010](./amended-2010-1.md#section-3-1-2)" in md_amender,
)

# UKLINK-01: a target outside the batch is never silently dropped -- explicit
# external legislation.gov.uk link.
check(
    "out-of-batch citation resolves external",
    "[the Unrelated Act 1999](https://www.legislation.gov.uk/unrelated/1999/9)" in md_amender,
)

check(
    "self-citation resolves to a same-page fragment, not ./own-slug.md",
    "[section 3 of this Act](#section-3)" in md_amender,
)

check(
    "whole-document self-citation (no anchor) renders as plain text, not an empty-href link",
    "this Act." in md_amender and "[this Act]()" not in md_amender and "[this Act](" not in md_amender,
)

# The compound cross-doc ref above is exactly the gap check_cross_references
# exists for: it must be caught here, at the batch validation step, since
# render.py itself couldn't verify it.
rendered = {"amended-2010-1": md_amended, "amender-2020-1": md_amender}
links_by_slug = {"amender-2020-1": links_amender, "amended-2010-1": links_amended}
errors = validate.check_cross_references(rendered, links_by_slug)
check(
    "batch validator catches the compound cross-doc ref render.py couldn't verify",
    any(e.code == "BROKEN_ANCHOR" and "section-3-1-2" in e.message for e in errors),
    detail=str(errors),
)

# A batch with ONLY the clean, resolvable citation (no compound ref) produces
# zero errors -- confirms the validator isn't just failing everything.
clean_body = [Provision(kind="section", id="section-9", number="9",
                         runs=[in_batch_citation, self_citation])]
clean_doc = LegalDoc(meta=_meta("Clean Amender Act 2020"), body=clean_body)
md_clean, links_clean = render.render(clean_doc, retrieved_at="t", own_slug="amender-2020-1", batch_slugs=BATCH)
clean_errors = validate.check_cross_references(
    {"amended-2010-1": md_amended, "amender-2020-1": md_clean},
    {"amender-2020-1": links_clean, "amended-2010-1": links_amended},
)
check("a batch with only resolvable references produces zero errors", clean_errors == [], detail=str(clean_errors))

# Now break it: claim amender-2020-1 links to a doc that was never rendered.
broken_links = {"amender-2020-1": [("amended-2010-1", "section-99-does-not-exist")]}
broken_errors = validate.check_cross_references(rendered, broken_links)
check(
    "validator catches a broken anchor rather than passing silently",
    any(e.code == "BROKEN_ANCHOR" for e in broken_errors),
    detail=str(broken_errors),
)

missing_doc_links = {"amender-2020-1": [("not-in-batch-1999-9", None)]}
missing_errors = validate.check_cross_references(rendered, missing_doc_links)
check(
    "validator catches a link to a doc that was never rendered",
    any(e.code == "BROKEN_INTERNAL_LINK" for e in missing_errors),
    detail=str(missing_errors),
)

# UKLINK-02: the commentary/footnote path also resolves citations, and the
# amendments list links back to the provision it affects.
commentary = Commentary(
    id="c1", kind="F", text="substituted by the Amended Act 2010, s. 3",
    runs=[Run(text="substituted by "), in_batch_citation],
)
doc_with_footnote = LegalDoc(
    meta=_meta("Amender Act 2020"),
    body=[Provision(kind="section", id="section-5", number="5", runs=[
        Run(kind="substitution", text="", commentary_ref="c1", children=[Run(text="new words")]),
    ])],
    commentaries={"c1": commentary},
)
md_fn, _ = render.render(doc_with_footnote, retrieved_at="t", own_slug="amender-2020-1", batch_slugs=BATCH)
check(
    "UKLINK-02: end-of-document footnote links back to the provision it affects",
    "[^fc1]: [section-5](#section-5): substituted by [section 3 of the Amended Act 2010]"
    "(./amended-2010-1.md#section-3)" in md_fn,
    detail=md_fn.split("---")[-1],
)

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) FAILED: {FAILURES}")
    sys.exit(1)
print("All link-resolution checks passed.")
