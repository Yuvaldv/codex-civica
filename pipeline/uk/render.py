"""IR (pipeline/uk/ir.py) -> deterministic Markdown. Pure function, no I/O.

Anchor style: <span id="..." /> not {#id} -- avoids MDX/acorn parse errors
(see pipeline/link_resolver.py:50, the same reason Israel made this call).
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from ir import LegalDoc, Provision, Run

MAX_HEADING = 6

# Extracts (type, year, number) from a legislation.gov.uk id-URI, e.g.
# ".../id/ukpga/1990/18" or ".../id/ukpga/1990/18/section/1/2/a".
_ID_URI_RE = re.compile(r"legislation\.gov\.uk/id/([a-z]+)/(\d+)/(\d+)(?:/|$)")


def _collect_known_anchors(provisions: list[Provision], out: set[str]) -> None:
    """Every provision id that _render_provision will actually turn into a
    <span id> -- everything except block_quote/uncertain/table, which never
    get one. Used to sanity-check self-citation SectionRefs before trusting
    them as a fragment (see RenderContext.known_anchors)."""
    for p in provisions:
        if p.id and p.kind not in ("block_quote", "uncertain", "table"):
            out.add(p.id)
        _collect_known_anchors(p.children, out)


def compute_known_anchors(doc: LegalDoc) -> frozenset[str]:
    """Public entry point for convert.py's first pass: every anchor `doc`
    will render, without doing a full render. Same logic RenderContext uses
    for its own doc, exposed so a batch-wide slug->anchors map can be built
    before any document is actually rendered (see batch_known_anchors)."""
    ids: set[str] = set()
    _collect_known_anchors(doc.body, ids)
    _collect_known_anchors(doc.schedules, ids)
    return frozenset(ids)


@dataclass
class RenderContext:
    """Render-time context threaded alongside each Provision/Run -- constant
    for one render() call, unlike the per-provision `anchor`/`path_label`
    which change with recursion depth. Keeps citation resolution (UKLINK-01)
    batch-aware without mutating the pure IR."""

    doc: LegalDoc
    own_slug: str | None = None
    batch_slugs: frozenset[str] = field(default_factory=frozenset)
    # Other in-batch documents' own known_anchors, keyed by slug -- lets a
    # cross-document citation get the same anchor-safety check a self-citation
    # already gets (see known_anchors below). Populated by convert.py's first
    # pass; empty by default so a caller that hasn't done that pass (e.g. a
    # single-document render) still gets the pre-existing optimistic behavior
    # instead of a crash or a silent no-op.
    batch_known_anchors: dict[str, frozenset[str]] = field(default_factory=dict)
    # Every internal link this render actually emitted (target slug, target
    # anchor-or-None), recorded structurally as it happens -- the validator
    # checks these directly rather than re-parsing them back out of the
    # rendered Markdown, which is ambiguous: this doc's own bracket-footnote
    # convention ([text][^flabel]) can sit directly against unrelated literal
    # parenthetical source text, producing a "](...)" that looks like a
    # Markdown link but isn't one.
    internal_links: list[tuple[str, str | None]] = field(default_factory=list)
    # Every id this doc will actually anchor. legislation.gov.uk's own
    # SectionRef can name a compound citation ("S. 8(2)(6)(b)" -> one combined
    # ref spanning three sibling subsections, "S. 16(5)(6)(8)(a)") or a virtual
    # location ("introduction") that never corresponds to a single node in our
    # provision tree -- self-citing one of those with a fragment we know is
    # wrong would be a confidently-broken link, so _resolve_link checks
    # against this set instead of trusting SectionRef unconditionally.
    known_anchors: frozenset[str] = field(init=False, default_factory=frozenset)

    def __post_init__(self) -> None:
        self.known_anchors = compute_known_anchors(self.doc)


def _clamp(level: int) -> int:
    return min(level, MAX_HEADING)


def _anchor(id_: str | None) -> str:
    return f' <span id="{id_}" />' if id_ else ""


def _mdx_escape(text: str) -> str:
    """Escape literal MDX/JSX expression delimiters in source-derived text so
    Docusaurus's acorn-based MDX parser doesn't choke on legal citations that
    happen to contain literal braces (e.g. "by {S.I. 2011/1418}, art. 2").
    Renders back to a literal '{'/'}' on the page -- purely a parser escape,
    not a text change.
    """
    return text.replace("{", "\\{").replace("}", "\\}")


def _external_link(uri: str) -> str:
    """legislation.gov.uk id-URIs resolve to the public site with /id/ stripped."""
    return uri.replace("http://www.legislation.gov.uk/id/", "https://www.legislation.gov.uk/") \
              .replace("https://www.legislation.gov.uk/id/", "https://www.legislation.gov.uk/")


def _batch_slug_for_uri(uri: str) -> str | None:
    """type/year/number, in this pipeline's own slug format, if the URI names one."""
    m = _ID_URI_RE.search(uri)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def _resolve_link(uri: str, target_anchor: str | None, ctx: RenderContext) -> str | None:
    """UKLINK-01: a citation whose target is in this conversion batch becomes a
    relative link to that doc's own .md file (Docusaurus resolves these at
    build time); anything else -- another jurisdiction's instrument, an Act
    not in this batch -- is never silently dropped, it becomes an explicit
    legislation.gov.uk link. Never guesses: relies only on the source's own
    URI and (for the anchor) its own SectionRef.

    Returns None (not a link at all -- caller falls back to plain text) only
    for a whole-document self-citation with no usable anchor: linking a page
    to itself with an empty href is a no-op at best and an MDX lint warning
    at worst, so there is nothing worth wrapping in `[]()`."""
    slug = _batch_slug_for_uri(uri)
    if not slug or slug not in ctx.batch_slugs:
        return _external_link(uri)
    if slug == ctx.own_slug and target_anchor not in ctx.known_anchors:
        # Compound or virtual SectionRef with no single matching provision --
        # degrade to a plain self-reference rather than a fragment we already
        # know is wrong.
        target_anchor = None
    elif slug != ctx.own_slug and target_anchor is not None:
        other_anchors = ctx.batch_known_anchors.get(slug)
        # Same anchor-safety check as the self-citation case above, now that a
        # real example exists (Parliament Act 1911 -> Fixed-term Parliaments
        # Act 2011 s.7(2), a subsection since omitted from the revised text
        # entirely -- the enclosing section survives so the *document* link is
        # still good, only the fragment is stale). Unlike self-citations, a
        # bad anchor here still leaves a useful target (the other document),
        # so drop only the fragment, never the whole link.
        if other_anchors is not None and target_anchor not in other_anchors:
            target_anchor = None
    if target_anchor or slug != ctx.own_slug:
        ctx.internal_links.append((slug, target_anchor))
    if slug == ctx.own_slug and not target_anchor:
        return None
    anchor = f"#{target_anchor}" if target_anchor else ""
    return f"./{slug}.md{anchor}" if slug != ctx.own_slug else anchor


class _Footnote:
    __slots__ = ("text", "anchors")

    def __init__(self, text: str) -> None:
        self.text = text
        self.anchors: list[str] = []


def _render_run(run: Run, ctx: RenderContext, footnotes: dict[str, _Footnote], anchor: str | None) -> str:
    if run.kind in ("addition", "substitution"):
        inner = "".join(_render_run(c, ctx, footnotes, anchor) for c in run.children) or _mdx_escape(run.text)
        marker = _footnote_marker(run.commentary_ref, ctx, footnotes, anchor)
        return f"[{inner}]{marker}"
    if run.kind == "repeal":
        marker = _footnote_marker(run.commentary_ref, ctx, footnotes, anchor)
        if run.retain_text:
            inner = "".join(_render_run(c, ctx, footnotes, anchor) for c in run.children) or _mdx_escape(run.text)
            extent_note = f" (repealed for {run.extent})" if run.extent else " (repealed)"
            return f"[{inner}]{marker}{extent_note}"
        return f". . . . . .{marker}"
    if run.kind == "term":
        return _mdx_escape(run.text)
    if run.kind == "citation":
        if run.uri:
            # UKLINK-03: this is the same resolver used for every citation regardless of
            # which document it appears in -- when an amending Act in the batch cites a
            # provision of another Act in the batch (inline, in its own body text, at the
            # exact point of the citation), this link IS that back-link. No separate
            # "amending provision" code path is needed.
            link = _resolve_link(run.uri, run.target_anchor, ctx)
            if link is not None:
                return f"[{_mdx_escape(run.text)}]({link})"
        return _mdx_escape(run.text)
    if run.kind == "emphasis":
        return f"*{_mdx_escape(run.text)}*"
    if run.kind == "commentary_marker":
        return _footnote_marker(run.commentary_ref, ctx, footnotes, anchor)
    return _mdx_escape(run.text)


def _footnote_marker(commentary_ref: str | None, ctx: RenderContext,
                      footnotes: dict[str, _Footnote], anchor: str | None) -> str:
    if not commentary_ref:
        return ""
    label = f"f{commentary_ref}"
    if label not in footnotes:
        commentary = ctx.doc.commentaries.get(commentary_ref)
        if commentary and commentary.runs:
            text = _render_runs(commentary.runs, ctx, footnotes, None)
        elif commentary:
            text = _mdx_escape(commentary.text)
        else:
            text = f"see amending instrument (commentary {commentary_ref} not found)"
        footnotes[label] = _Footnote(text)
    # UKLINK-02: record every provision this amendment was invoked from, so the
    # end-of-document footnote can link back to what it affects, not just cite
    # the amending instrument. A ref can legitimately fire from more than one
    # provision (e.g. a Repeal spanning several subsections) -- keep them all.
    if anchor and anchor not in footnotes[label].anchors:
        footnotes[label].anchors.append(anchor)
    return f"[^{label}]"


def _render_runs(runs: list[Run], ctx: RenderContext, footnotes: dict[str, _Footnote],
                  anchor: str | None) -> str:
    return "".join(_render_run(r, ctx, footnotes, anchor) for r in runs)


def _extent_annotation(prov: Provision, ctx: RenderContext, label: str) -> str | None:
    if prov.extent and prov.extent != ctx.doc.meta.extent:
        return f"> [Extent — {label}] {prov.extent}\n"
    return None


def _render_provision(prov: Provision, ctx: RenderContext, level: int, out: list[str],
                       footnotes: dict[str, _Footnote], path_label: str,
                       anchor_hint: str | None = None) -> None:
    anchor = prov.id or anchor_hint

    if prov.kind == "block_quote":
        out.append("> [Quoted block text — not this Act's own numbered provision]\n")
        text = _render_runs(prov.runs, ctx, footnotes, anchor).strip()
        for line in text.splitlines() or [""]:
            out.append(f"> {line}\n")
        out.append("\n")
        return

    if prov.kind == "uncertain":
        out.append(_render_runs(prov.runs, ctx, footnotes, anchor) + "\n\n")
        return

    if prov.kind == "table":
        out.append(_render_runs(prov.runs, ctx, footnotes, anchor) + "\n\n")
        return

    if prov.kind in ("part", "chapter", "crossheading", "schedule"):
        heading_text = " — ".join(x for x in (prov.number, prov.heading) if x)
        out.append(f"{'#' * _clamp(level)} {heading_text}{_anchor(prov.id)}\n\n")
        if prov.kind == "schedule" and prov.reference:
            out.append(f"> [Enabled by — {prov.reference}]\n\n")
        ext = _extent_annotation(prov, ctx, path_label or heading_text)
        if ext:
            out.append(ext + "\n")
        for child in prov.children:
            _render_provision(child, ctx, level + 1, out, footnotes, path_label, anchor)
        return

    # Numbered provision: section/subsection/para/subpara/pN
    label = f"{prov.number}." if prov.kind == "section" and prov.number else (
        f"({prov.number})" if prov.number else "")
    heading_text = " ".join(x for x in (label, prov.heading) if x) or "(unnumbered)"
    status_marker = ""
    if prov.status == "Repealed":
        status_marker = " **[REPEALED]**"
    elif prov.status == "Prospective":
        status_marker = " **[NOT YET IN FORCE — prospective]**"

    out.append(f"{'#' * _clamp(level)} {heading_text}{status_marker}{_anchor(prov.id)}\n\n")

    ext = _extent_annotation(prov, ctx, path_label or heading_text)
    if ext:
        out.append(ext + "\n")

    body_text = _render_runs(prov.runs, ctx, footnotes, anchor).strip()
    if body_text:
        out.append(body_text + "\n\n")

    for child in prov.children:
        _render_provision(child, ctx, level + 1, out, footnotes, path_label, anchor)

    trailing_text = _render_runs(prov.trailing_runs, ctx, footnotes, anchor).strip()
    if trailing_text:
        out.append(trailing_text + "\n\n")


def _render_frontmatter(doc: LegalDoc, retrieved_at: str) -> str:
    m = doc.meta
    lines = [
        "---",
        f'title: "{_esc(m.title)}"',
        f'long_title: "{_esc(m.long_title or "")}"',
        f"year: {m.year or '~'}",
        f"chapter: {m.chapter or '~'}",
        f"enactment_date: {m.enactment_date or '~'}",
        f"document_main_type: {m.document_main_type or '~'}",
        f"document_status: {m.document_status or '~'}",
        f"valid_date: {m.valid_date or '~'}",
        f'as_at: "{m.valid_date or retrieved_at}"',
        f"extent: {m.extent or '~'}",
        f"number_of_provisions: {m.number_of_provisions if m.number_of_provisions is not None else '~'}",
        f"unapplied_effects_count: {len(doc.unapplied_effects)}",
        f'publisher: "{_esc(m.publisher)}"' if m.publisher else "publisher: ~",
        "jurisdiction: uk",
        "generated_by: pipeline/uk/render.py",
        f"retrieved_at: {retrieved_at}",
        "---",
        "",
    ]
    return "\n".join(lines)


def _esc(value: str) -> str:
    return value.replace('"', '\\"')


def _render_unapplied_banner(doc: LegalDoc) -> str:
    if not doc.unapplied_effects:
        return ""
    lines = [
        f"> **{len(doc.unapplied_effects)} change(s) not yet applied to this Act.** "
        "The source publisher (legislation.gov.uk) has recorded amendments that are not "
        "yet incorporated into the text below:",
        ">",
    ]
    for eff in doc.unapplied_effects:
        refs = ", ".join(eff.affected_refs) if eff.affected_refs else "unspecified provision(s)"
        lines.append(f"> - {refs}: {eff.type_text} (by *{eff.affecting_title}*)")
    return "\n".join(lines) + "\n\n"


def _render_term_index(doc: LegalDoc) -> str:
    if not doc.terms:
        return ""
    lines = ["## Defined Terms", ""]
    for term in sorted(doc.terms, key=str.lower):
        lines.append(f"- {term}")
    return "\n".join(lines) + "\n\n"


def render(doc: LegalDoc, retrieved_at: str | None = None,
           own_slug: str | None = None,
           batch_slugs: frozenset[str] = frozenset(),
           batch_known_anchors: dict[str, frozenset[str]] | None = None
           ) -> tuple[str, list[tuple[str, str | None]]]:
    """Returns (markdown, internal_links) -- internal_links is every (target
    slug, target anchor-or-None) this render resolved in-batch (UKLINK-01),
    for validate.check_cross_references to verify without re-parsing Markdown.

    own_slug/batch_slugs: the set of other documents converted in the same
    run, so citations to them resolve as internal links instead of always
    going external. A single-document conversion (batch_slugs empty or just
    {own_slug}) is still fully correct -- every citation simply has nothing
    in-batch to resolve to, so it falls through to the external link, exactly
    as before this parameter existed.

    batch_known_anchors: optional slug -> that document's own known_anchors,
    from a first pass over the whole batch (see compute_known_anchors). Lets
    a cross-document citation's anchor get the same safety check a
    self-citation already gets. Omitting it (the default) falls back to
    trusting the source SectionRef for cross-document anchors, exactly as
    before this parameter existed."""
    retrieved_at = retrieved_at or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ctx = RenderContext(doc=doc, own_slug=own_slug, batch_slugs=batch_slugs,
                         batch_known_anchors=batch_known_anchors or {})

    out: list[str] = [_render_frontmatter(doc, retrieved_at)]
    out.append(_render_unapplied_banner(doc))
    if doc.preamble:
        out.append(_mdx_escape(doc.preamble) + "\n\n")

    footnotes: dict[str, _Footnote] = {}
    for prov in doc.body:
        _render_provision(prov, ctx, 1, out, footnotes, "")
    for sched in doc.schedules:
        _render_provision(sched, ctx, 1, out, footnotes, "")

    out.append(_render_term_index(doc))

    used_refs = {label[1:] for label in footnotes}  # strip the leading "f"
    unused = [c for cid, c in doc.commentaries.items() if cid not in used_refs and c.text]
    if unused:
        out.append("## Editorial Notes\n\n")
        out.append(
            "Notes recorded by the source publisher and not tied to a specific inline "
            "amendment marker above:\n\n"
        )
        for c in unused:
            note_text = _render_runs(c.runs, ctx, footnotes, None) if c.runs else _mdx_escape(c.text)
            out.append(f"- {note_text}\n")
        out.append("\n")

    if footnotes:
        # UKLINK-02: every amendment affecting this document, listed at the end,
        # each entry linking back to the provision(s) it affects (self-anchor,
        # always resolvable) and forward to the amending instrument (internal
        # link if that instrument is in this batch, external otherwise -- see
        # _resolve_link).
        out.append("---\n\n")
        for label, fn in footnotes.items():
            prefix = ""
            if fn.anchors:
                if own_slug:
                    ctx.internal_links.extend((own_slug, a) for a in fn.anchors)
                prefix = ", ".join(f"[{a}](#{a})" for a in fn.anchors) + ": "
            out.append(f"[^{label}]: {prefix}{fn.text}\n")

    return "".join(out), ctx.internal_links
