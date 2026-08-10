"""CLML XML -> IR (pipeline/uk/ir.py). The only module that knows the XML dialect.

No LLM, no inference: CLML already encodes hierarchy, numbering, and cross-
references explicitly. This is a deterministic tree walk. Unknown elements
are never silently dropped -- they raise UnknownElementError so the caller
can decide (log, skip, or fail the batch).
"""
from __future__ import annotations

import re

from lxml import etree

from ir import (
    Commentary,
    DocMeta,
    LegalDoc,
    Provision,
    Run,
    UnappliedEffect,
)

NS = {
    "leg": "http://www.legislation.gov.uk/namespaces/legislation",
    "ukm": "http://www.legislation.gov.uk/namespaces/metadata",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dct": "http://purl.org/dc/terms/",
}

# Inline elements that can appear mixed with text inside a <Text> node.
# Nested Addition-inside-Substitution etc. is handled by recursing on `.children`.
_INLINE_CHANGE_TAGS = {"Addition": "addition", "Substitution": "substitution", "Repeal": "repeal"}
_INLINE_PLAIN_TAGS = {"Term": "term", "Emphasis": "emphasis", "Citation": "citation",
                      "CitationSubRef": "citation", "Abbreviation": "plain",
                      "CommentaryRef": "plain", "Char": "plain", "InlineAmendment": "plain",
                      "Acronym": "plain"}

# Container/structural elements this parser understands. Anything else inside
# the operative body that isn't handled explicitly (Figure, Form, Tabular,
# IncludedDocument) raises UnknownElementError -- fail loudly per
# ARCHITECTURE.md, never silently drop legal text.
_NUMBERED_RE = re.compile(r"^P(\d+)$")
_NUMBERED_PARA_RE = re.compile(r"^P(\d+)para$")


class UnknownElementError(Exception):
    pass


def _local(el) -> str:
    return etree.QName(el).localname


def _text_of(el, path: str) -> str | None:
    found = el.find(path, NS)
    if found is None or found.text is None:
        return None
    return " ".join(found.text.split())


# ---------------------------------------------------------------------------
# Mixed-content (inline run) extraction
# ---------------------------------------------------------------------------

def _walk_mixed_content(el) -> list[Run]:
    """Walk an element's mixed content (text + inline child elements + tails)."""
    runs: list[Run] = []
    if el.text:
        runs.append(Run(text=el.text))
    for child in el:
        tag = _local(child)
        if tag in _INLINE_CHANGE_TAGS:
            runs.append(Run(
                text="",
                kind=_INLINE_CHANGE_TAGS[tag],
                commentary_ref=child.get("CommentaryRef"),
                retain_text=(child.get("RetainText") == "true"),
                extent=child.get("Extent"),
                children=_walk_mixed_content(child),
            ))
        elif tag == "Term":
            runs.append(Run(text="".join(child.itertext()), kind="term", uri=child.get("id")))
        elif tag in ("Citation", "CitationSubRef"):
            runs.append(Run(text="".join(child.itertext()), kind="citation", uri=child.get("URI")))
        elif tag == "CommentaryRef":
            # Standalone editorial reference marker (e.g. an ellipsis explained by a footnote) --
            # never drop the Ref, even though the element itself carries no text.
            runs.append(Run(text="", kind="commentary_marker", commentary_ref=child.get("Ref")))
        elif tag in _INLINE_PLAIN_TAGS:
            runs.append(Run(text="".join(child.itertext())))
        elif tag in ("Pnumber",):
            # Pnumber itself can be wrapped in an Addition (inserted section number) --
            # handled at the caller (numbered-provision) level, not here.
            runs.append(Run(text="".join(child.itertext())))
        else:
            # Unknown inline element inside running text: fail loudly per
            # ARCHITECTURE.md rather than silently drop legal wording.
            raise UnknownElementError(f"unhandled inline element <{tag}> inside mixed content")
        if child.tail:
            runs.append(Run(text=child.tail))
    return runs


# ---------------------------------------------------------------------------
# Provision (structural) walk
# ---------------------------------------------------------------------------

def _find_para_children(el, tag: str) -> list:
    """Find ALL '<Tag>para' siblings wrapping a numbered provision's content.

    Usually exactly one. Some archaic Acts (e.g. Union with Scotland Act 1706,
    s.II) give a single <P1> SEVERAL sibling <P1para> elements -- one per prose
    paragraph of that clause. A .find() (singular) silently drops every
    paragraph after the first -- found via the round-trip validator on live
    data; six whole paragraphs of operative text were being discarded."""
    m = _NUMBERED_RE.match(tag)
    if m:
        paras = el.findall(f"leg:P{m.group(1)}para", NS)
        if paras:
            return paras
    bare = el.find("leg:P", NS)  # bare unnumbered paragraph wrapper (older Acts)
    return [bare] if bare is not None else []


def _walk_para(para_el, prefer_short: bool = False) -> tuple[list[Run], list[Provision], list[Run]]:
    """Split a <Pnpara> element's children into (leading runs, nested provisions, trailing runs)."""
    leading: list[Run] = []
    children: list[Provision] = []
    trailing: list[Run] = []
    seen_child_provision = False

    for node in para_el:
        tag = _local(node)
        if tag == "Text":
            runs = _walk_mixed_content(node)
            if not seen_child_provision:
                leading.extend(runs)
            else:
                trailing.extend(runs)
        elif _NUMBERED_RE.match(tag):
            children.append(_walk_numbered_provision(node, prefer_short))
            seen_child_provision = True
        elif tag in ("BlockAmendment", "BlockText"):
            children.append(_walk_block_amendment(node))
            seen_child_provision = True
        elif tag == "AppendText":
            trailing.extend(_walk_mixed_content(node))
        elif tag in ("UnorderedList", "OrderedList"):
            list_runs = _walk_list(node)
            if not seen_child_provision:
                leading.extend(list_runs)
            else:
                trailing.extend(list_runs)
        elif tag == "Figure":
            marker = [Run(text="[UNCERTAIN TEXT — Figure/Image, not extractable as text]")]
            (trailing if seen_child_provision else leading).extend(marker)
        elif tag == "Tabular":
            marker = [_walk_tabular(node)]
            (trailing if seen_child_provision else leading).extend(marker)
        else:
            raise UnknownElementError(f"unhandled element <{tag}> inside a provision paragraph")

    return leading, children, trailing


def _walk_list(list_el) -> list[Run]:
    """<UnorderedList>/<OrderedList><ListItem><Para><Text>...</Text></Para></ListItem>...
    Rendered as a run-level bullet list -- CLAUDE.md has no bespoke list construct,
    so this stays inline as Markdown "- " lines within the surrounding provision text."""
    runs: list[Run] = []
    for item in list_el.findall("leg:ListItem", NS):
        runs.append(Run(text="\n- "))
        for para in item.findall("leg:Para", NS):
            for text_el in para.findall("leg:Text", NS):
                runs.extend(_walk_mixed_content(text_el))
            # A nested list can sit either directly under ListItem or one level
            # deeper as a sibling of Para/Text inside Para itself (observed live
            # in Interpretation Act 1978's amended EU-terms definitions).
            for nested in para.findall("leg:UnorderedList", NS) + para.findall("leg:OrderedList", NS):
                runs.extend(_walk_list(nested))
        for nested in item.findall("leg:UnorderedList", NS) + item.findall("leg:OrderedList", NS):
            runs.extend(_walk_list(nested))
    runs.append(Run(text="\n"))
    return runs


def _walk_numbered_provision(el, prefer_short: bool = False) -> Provision:
    tag = _local(el)
    depth = int(_NUMBERED_RE.match(tag).group(1))
    kind = {1: "section", 2: "subsection", 3: "para", 4: "subpara"}.get(depth, f"p{depth}")

    number = None
    pnumber_el = el.find("leg:Pnumber", NS)
    if pnumber_el is not None:
        number = "".join(pnumber_el.itertext()).strip()

    # shortId is only guaranteed unique within schedules (Pitfall 14's recommended
    # short anchor form); in the body it has been observed to collide across two
    # genuinely distinct provisions (e.g. Computer Misuse Act 1990, s.5(2)(b) --
    # two different <P3> elements both carry shortId="section-5-2-b"). Prefer the
    # always-unique full @id outside schedules.
    prov = Provision(
        kind=kind,
        id=(el.get("shortId") if prefer_short else None) or el.get("id"),
        number=number,
        extent=el.get("RestrictExtent"),
        start_date=el.get("RestrictStartDate"),
        status=el.get("Status"),
    )

    paras = _find_para_children(el, tag)
    combined_leading: list[Run] = []
    combined_children: list[Provision] = []
    combined_trailing: list[Run] = []
    for i, para in enumerate(paras):
        leading, children, trailing = _walk_para(para, prefer_short)
        if i > 0 and leading:
            combined_leading.append(Run(text="\n\n"))
        combined_leading.extend(leading)
        combined_children.extend(children)
        if trailing:
            combined_trailing.append(Run(text="\n\n"))
        combined_trailing.extend(trailing)
    prov.runs = combined_leading
    prov.children = combined_children
    prov.trailing_runs = combined_trailing
    return prov


def _walk_block_amendment(el) -> Provision:
    """<BlockAmendment>/<BlockText> -- quoted text from another Act. Never a real provision:
    no id, no anchor, excluded from numbering (Pitfall 6)."""
    prov = Provision(kind="block_quote", id=None, number=None)
    runs: list[Run] = []
    # Render everything inside as a flat text blob, preserving inline change-markup
    # where present, since BlockAmendment content has its own (irrelevant-to-this-doc)
    # numbering that must never be mistaken for ours (Pitfall 6).
    for node in el.iter("{http://www.legislation.gov.uk/namespaces/legislation}Text"):
        runs.extend(_walk_mixed_content(node))
        runs.append(Run(text="\n"))
    prov.runs = runs
    return prov


def _walk_group_or_block(el, kind_for_leaf: str, prefer_short: bool = False) -> list[Provision]:
    """<P1group> (heading + one-or-more leaf provisions) or <Pblock> (crossheading only).

    Usually P1group wraps a single numbered <P1>. But some pre-standardised-schema
    Acts (e.g. Magna Carta) wrap MULTIPLE bare <P> siblings under one P1group/Title --
    all of them belong to that heading, not just the first (a plain "process the
    first child and break" walk silently drops the rest -- found via the round-trip
    validator on live data)."""
    tag = _local(el)
    titles = [" ".join(t.text.split()) for t in el.findall("leg:Title", NS) if t.text]
    heading = " ".join(titles) if titles else None

    if tag == "Pblock":
        return [Provision(kind="crossheading", heading=heading, id=el.get("id"))]

    leaves: list[Provision] = []
    for node in el:
        t = _local(node)
        if _NUMBERED_RE.match(t):
            leaves.append(_walk_numbered_provision(node, prefer_short))
        elif t == "P":
            leading, children, trailing = _walk_para(node, prefer_short) if len(node) else ([], [], [])
            if not len(node):
                leading = _walk_mixed_content(node)
            leaves.append(Provision(kind="section", id=node.get("id"), runs=leading,
                                     children=children, trailing_runs=trailing))
    if not leaves:
        # Group with no numbered content (rare) -- treat as a crossheading.
        return [Provision(kind="crossheading", heading=heading, id=el.get("id"))]
    leaves[0].heading = heading
    # P1group itself can carry RestrictExtent (observed live: Computer Misuse Act
    # 1990 attaches the Northern-Ireland/Scotland-only extent variation to the
    # <P1group>, not to the <P1> it wraps) -- the group's extent is the leaf's
    # extent unless the leaf already declared a more specific one of its own.
    group_extent = el.get("RestrictExtent")
    if group_extent:
        for leaf in leaves:
            if not leaf.extent:
                leaf.extent = group_extent
    return leaves


_XHTML = "{http://www.w3.org/1999/xhtml}"


def _walk_tabular(el) -> Run:
    """<Tabular><table xmlns="...xhtml">...</table></Tabular> -- pre-rendered into a
    Markdown pipe-table at the IR level (a bounded, deliberate exception to "IR has no
    rendering logic": a table's row/column structure IS its textual content)."""
    table = el.find(f"{_XHTML}table")
    if table is None:
        return Run(text="[UNCERTAIN TEXT — Tabular content, no <table> found]")
    rows: list[list[str]] = []
    for tr in table.iter(f"{_XHTML}tr"):
        cells = [" ".join("".join(cell.itertext()).split())
                 for cell in tr if cell.tag in (f"{_XHTML}td", f"{_XHTML}th")]
        if cells:
            rows.append(cells)
    if not rows:
        return Run(text="[UNCERTAIN TEXT — Tabular content, no rows found]")
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join("---" for _ in rows[0]) + " |"]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return Run(text="\n" + "\n".join(lines) + "\n")


def _walk_body(container, prefer_short: bool = False) -> list[Provision]:
    out: list[Provision] = []
    for el in container:
        tag = _local(el)
        if tag in ("Part", "Chapter"):
            number = _text_of(el, "leg:Number")
            heading = " ".join(
                " ".join(t.text.split()) for t in el.findall("leg:Title", NS) if t.text
            ) or None
            prov = Provision(
                kind="part" if tag == "Part" else "chapter",
                id=el.get("id"), number=number, heading=heading,
                extent=el.get("RestrictExtent"), start_date=el.get("RestrictStartDate"),
            )
            prov.children = _walk_body(el, prefer_short)
            out.append(prov)
        elif tag == "Pblock":
            crossheading = _walk_group_or_block(el, "crossheading", prefer_short)[0]
            crossheading.children = _walk_body(el, prefer_short)
            out.append(crossheading)
        elif tag == "P1group":
            out.extend(_walk_group_or_block(el, "section", prefer_short))
        elif _NUMBERED_RE.match(tag):
            out.append(_walk_numbered_provision(el, prefer_short))
        elif tag == "P":
            # Bare unnumbered paragraph directly under Body (pre-CLML-schema-standardisation
            # Acts, e.g. Magna Carta) -- a leaf provision with no Pnumber. May wrap a <Text>
            # child (like a Pnpara) or, rarely, carry text directly.
            if len(el):
                leading, children, trailing = _walk_para(el, prefer_short)
            else:
                leading, children, trailing = _walk_mixed_content(el), [], []
            out.append(Provision(kind="para", id=el.get("id"), runs=leading,
                                  children=children, trailing_runs=trailing))
        elif tag in ("BlockAmendment", "BlockText"):
            out.append(_walk_block_amendment(el))
        elif tag == "Figure":
            # Scanned image, no extractable text -- genuinely uncertain content
            # (CLAUDE.md "prefer explicit uncertainty over incorrect confidence").
            out.append(Provision(kind="uncertain", id=el.get("id"),
                                  runs=[Run(text="[UNCERTAIN TEXT — Figure/Image, not extractable as text]")]))
        elif tag == "Tabular":
            out.append(Provision(kind="table", id=el.get("id"), runs=[_walk_tabular(el)]))
        elif tag in ("Number", "Title", "TitleBlock", "Reference"):
            continue  # consumed by the caller (Part/Chapter/Schedule header)
        else:
            raise UnknownElementError(f"unhandled structural element <{tag}>")
    return out


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------

def _walk_schedules(schedules_el) -> list[Provision]:
    if schedules_el is None:
        return []
    out: list[Provision] = []
    for sched in schedules_el.findall("leg:Schedule", NS):
        number = _text_of(sched, "leg:Number")
        title = _text_of(sched, "leg:TitleBlock/leg:Title")
        reference = _text_of(sched, "leg:Reference")
        prov = Provision(
            kind="schedule", id=sched.get("id"), number=number, heading=title,
            reference=reference, extent=sched.get("RestrictExtent"),
            start_date=sched.get("RestrictStartDate"), status=sched.get("Status"),
        )
        body = sched.find("leg:ScheduleBody", NS)
        if body is not None:
            prov.children = _walk_body(body, prefer_short=True)
        out.append(prov)
    return out


# ---------------------------------------------------------------------------
# Metadata, UnappliedEffects, Commentaries, Terms
# ---------------------------------------------------------------------------

def _parse_metadata(root) -> DocMeta:
    title = _text_of(root, ".//dc:title") or ""
    long_title = _text_of(root, ".//dc:description")
    year_el = root.find(".//ukm:Year", NS)
    number_el = root.find(".//ukm:Number", NS)
    main_type_el = root.find(".//ukm:DocumentMainType", NS)
    status_el = root.find(".//ukm:DocumentStatus", NS)
    enactment_el = root.find(".//ukm:EnactmentDate", NS)
    valid = _text_of(root, ".//dct:valid")

    n_provisions = root.get("NumberOfProvisions")
    return DocMeta(
        title=title,
        long_title=long_title,
        year=year_el.get("Value") if year_el is not None else None,
        number=number_el.get("Value") if number_el is not None else None,
        chapter=number_el.get("Value") if number_el is not None else None,
        document_main_type=main_type_el.get("Value") if main_type_el is not None else None,
        document_status=status_el.get("Value") if status_el is not None else None,
        enactment_date=enactment_el.get("Date") if enactment_el is not None else None,
        valid_date=valid,
        extent=root.get("RestrictExtent"),
        number_of_provisions=int(n_provisions) if n_provisions else None,
    )


def _parse_unapplied_effects(root) -> list[UnappliedEffect]:
    out: list[UnappliedEffect] = []
    for eff in root.findall(".//ukm:UnappliedEffects/ukm:UnappliedEffect", NS):
        affecting_title = _text_of(eff, "ukm:AffectingTitle") or eff.get("AffectingURI") or "?"
        refs = [s.get("Ref") for s in eff.findall("ukm:AffectedProvisions/ukm:Section", NS) if s.get("Ref")]
        out.append(UnappliedEffect(
            affecting_title=affecting_title,
            type_text=eff.get("Type") or "",
            affected_refs=refs,
        ))
    return out


def _parse_commentaries(root) -> dict[str, Commentary]:
    out: dict[str, Commentary] = {}
    for c in root.findall(".//leg:Commentaries/leg:Commentary", NS):
        cid = c.get("id")
        if not cid:
            continue
        # Full mixed-content flatten (itertext), not just leading .text -- commentary
        # sentences routinely end in a <Citation> child (the amending instrument), which
        # a .text-only read silently truncates before.
        text = " ".join("".join(c.itertext()).split())
        out[cid] = Commentary(id=cid, kind=c.get("Type") or "", text=text)
    return out


def _collect_terms(provisions: list[Provision], seen: list[str]) -> None:
    for p in provisions:
        for r in p.runs + p.trailing_runs:
            if r.kind == "term" and r.text not in seen:
                seen.append(r.text)
        _collect_terms(p.children, seen)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse(xml_bytes: bytes) -> LegalDoc:
    root = etree.fromstring(xml_bytes)
    meta = _parse_metadata(root)

    primary = root.find(".//leg:Primary", NS)
    if primary is None:
        primary = root.find(".//leg:Secondary", NS)
    body: list[Provision] = []
    schedules: list[Provision] = []
    preamble: str | None = None
    if primary is not None:
        body_el = primary.find("leg:Body", NS)
        if body_el is not None:
            body = _walk_body(body_el)
        schedules = _walk_schedules(primary.find("leg:Schedules", NS))
        # Flatten the whole PrimaryPreamble (Recital/IntroductoryText/EnactingText all
        # vary by era -- pre-1707 Acts use different child names than modern ones).
        preamble_el = primary.find(".//leg:PrimaryPreamble", NS)
        if preamble_el is not None:
            preamble = " ".join("".join(preamble_el.itertext()).split())

    doc = LegalDoc(
        meta=meta,
        preamble=preamble,
        body=body,
        schedules=schedules,
        unapplied_effects=_parse_unapplied_effects(root),
        commentaries=_parse_commentaries(root),
    )

    terms: list[str] = []
    _collect_terms(body, terms)
    _collect_terms(schedules, terms)
    doc.terms = terms

    return doc
