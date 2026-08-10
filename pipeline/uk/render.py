"""IR (pipeline/uk/ir.py) -> deterministic Markdown. Pure function, no I/O.

Anchor style: <span id="..." /> not {#id} -- avoids MDX/acorn parse errors
(see pipeline/link_resolver.py:50, the same reason Israel made this call).
"""
from __future__ import annotations

import datetime as dt

from ir import LegalDoc, Provision, Run

MAX_HEADING = 6


def _clamp(level: int) -> int:
    return min(level, MAX_HEADING)


def _anchor(id_: str | None) -> str:
    return f' <span id="{id_}" />' if id_ else ""


def _external_link(uri: str) -> str:
    """legislation.gov.uk id-URIs resolve to the public site with /id/ stripped."""
    return uri.replace("http://www.legislation.gov.uk/id/", "https://www.legislation.gov.uk/") \
              .replace("https://www.legislation.gov.uk/id/", "https://www.legislation.gov.uk/")


def _render_run(run: Run, doc: LegalDoc, footnotes: list[tuple[str, str]]) -> str:
    if run.kind in ("addition", "substitution"):
        inner = "".join(_render_run(c, doc, footnotes) for c in run.children) or run.text
        marker = _footnote_marker(run.commentary_ref, doc, footnotes)
        return f"[{inner}]{marker}"
    if run.kind == "repeal":
        marker = _footnote_marker(run.commentary_ref, doc, footnotes)
        if run.retain_text:
            inner = "".join(_render_run(c, doc, footnotes) for c in run.children) or run.text
            extent_note = f" (repealed for {run.extent})" if run.extent else " (repealed)"
            return f"[{inner}]{marker}{extent_note}"
        return f". . . . . .{marker}"
    if run.kind == "term":
        return run.text
    if run.kind == "citation":
        if run.uri:
            return f"[{run.text}]({_external_link(run.uri)})"
        return run.text
    if run.kind == "emphasis":
        return f"*{run.text}*"
    if run.kind == "commentary_marker":
        return _footnote_marker(run.commentary_ref, doc, footnotes)
    return run.text


def _footnote_marker(commentary_ref: str | None, doc: LegalDoc, footnotes: list[tuple[str, str]]) -> str:
    if not commentary_ref:
        return ""
    commentary = doc.commentaries.get(commentary_ref)
    text = commentary.text if commentary else f"see amending instrument (commentary {commentary_ref} not found)"
    label = f"f{commentary_ref}"
    if not any(existing_label == label for existing_label, _ in footnotes):
        footnotes.append((label, text))
    return f"[^{label}]"


def _render_runs(runs: list[Run], doc: LegalDoc, footnotes: list[tuple[str, str]]) -> str:
    return "".join(_render_run(r, doc, footnotes) for r in runs)


def _extent_annotation(prov: Provision, doc: LegalDoc, label: str) -> str | None:
    if prov.extent and prov.extent != doc.meta.extent:
        return f"> [Extent — {label}] {prov.extent}\n"
    return None


def _render_provision(prov: Provision, doc: LegalDoc, level: int, out: list[str],
                       footnotes: list[tuple[str, str]], path_label: str) -> None:
    if prov.kind == "block_quote":
        out.append("> [Quoted block text — not this Act's own numbered provision]\n")
        text = _render_runs(prov.runs, doc, footnotes).strip()
        for line in text.splitlines() or [""]:
            out.append(f"> {line}\n")
        out.append("\n")
        return

    if prov.kind == "uncertain":
        out.append(_render_runs(prov.runs, doc, footnotes) + "\n\n")
        return

    if prov.kind == "table":
        out.append(_render_runs(prov.runs, doc, footnotes) + "\n\n")
        return

    if prov.kind in ("part", "chapter", "crossheading", "schedule"):
        heading_text = " — ".join(x for x in (prov.number, prov.heading) if x)
        if prov.kind == "crossheading":
            out.append(f"{'#' * _clamp(level)} {heading_text}\n\n")
        else:
            out.append(f"{'#' * _clamp(level)} {heading_text}{_anchor(prov.id)}\n\n")
        if prov.kind == "schedule" and prov.reference:
            out.append(f"> [Enabled by — {prov.reference}]\n\n")
        ext = _extent_annotation(prov, doc, path_label or heading_text)
        if ext:
            out.append(ext + "\n")
        for child in prov.children:
            _render_provision(child, doc, level + 1, out, footnotes, path_label)
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

    ext = _extent_annotation(prov, doc, path_label or heading_text)
    if ext:
        out.append(ext + "\n")

    body_text = _render_runs(prov.runs, doc, footnotes).strip()
    if body_text:
        out.append(body_text + "\n\n")

    for child in prov.children:
        _render_provision(child, doc, level + 1, out, footnotes, path_label)

    trailing_text = _render_runs(prov.trailing_runs, doc, footnotes).strip()
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


def render(doc: LegalDoc, retrieved_at: str | None = None) -> str:
    retrieved_at = retrieved_at or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out: list[str] = [_render_frontmatter(doc, retrieved_at)]
    out.append(_render_unapplied_banner(doc))
    if doc.preamble:
        out.append(doc.preamble + "\n\n")

    footnotes: list[tuple[str, str]] = []
    for prov in doc.body:
        _render_provision(prov, doc, 1, out, footnotes, "")
    for sched in doc.schedules:
        _render_provision(sched, doc, 1, out, footnotes, "")

    out.append(_render_term_index(doc))

    used_refs = {label[1:] for label, _ in footnotes}  # strip the leading "f"
    unused = [c for cid, c in doc.commentaries.items() if cid not in used_refs and c.text]
    if unused:
        out.append("## Editorial Notes\n\n")
        out.append(
            "Notes recorded by the source publisher and not tied to a specific inline "
            "amendment marker above:\n\n"
        )
        for c in unused:
            out.append(f"- {c.text}\n")
        out.append("\n")

    if footnotes:
        out.append("---\n\n")
        for label, text in footnotes:
            out.append(f"[^{label}]: {text}\n")

    return "".join(out)
