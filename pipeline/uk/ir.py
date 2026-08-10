"""Intermediate representation for CLML documents.

pipeline/uk/clml.py builds this tree from XML; pipeline/uk/render.py walks it
to produce Markdown; pipeline/uk/validate.py walks it to check fidelity.
Kept deliberately thin — no rendering logic, no XML-specific code.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Run:
    """One piece of inline content within a provision's text."""

    text: str
    kind: str = "plain"  # plain|term|citation|addition|substitution|repeal|emphasis
    uri: str | None = None
    retain_text: bool = False  # Repeal RetainText="true" — repealed but text kept for another extent
    extent: str | None = None  # per-Run extent override (e.g. Repeal Extent="S")
    commentary_ref: str | None = None
    children: list["Run"] = field(default_factory=list)  # for nested Addition/Substitution


@dataclass
class Provision:
    kind: str  # part|chapter|crossheading|section|subsection|para|subpara|schedule|schedule_part|schedule_chapter
    id: str | None = None
    number: str | None = None  # verbatim Pnumber / Number text
    heading: str | None = None  # P1group/Title or Part/Chapter/Schedule Title
    runs: list[Run] = field(default_factory=list)  # this provision's own text (before children)
    trailing_runs: list[Run] = field(default_factory=list)  # continuation text after nested children
    children: list["Provision"] = field(default_factory=list)
    extent: str | None = None
    start_date: str | None = None
    status: str | None = None  # None|"Repealed"|"Prospective"
    reference: str | None = None  # Schedule's enabling-section back-link
    block_quotes: list["Provision"] = field(default_factory=list)  # BlockAmendment content attached here


@dataclass
class UnappliedEffect:
    affecting_title: str
    type_text: str
    affected_refs: list[str] = field(default_factory=list)


@dataclass
class Commentary:
    id: str
    kind: str  # the Commentary/@Type, e.g. "F", "C", "I"
    text: str


@dataclass
class DocMeta:
    title: str
    long_title: str | None
    year: str | None
    number: str | None
    chapter: str | None
    document_main_type: str | None
    document_status: str | None
    enactment_date: str | None
    valid_date: str | None
    extent: str | None
    number_of_provisions: int | None
    publisher: str | None  # dc:publisher — drives OGL attribution wording on site


@dataclass
class LegalDoc:
    meta: DocMeta
    preamble: str | None = None  # PrimaryPrelims/PrimaryPreamble/EnactingText -- "Be it enacted..."
    body: list[Provision] = field(default_factory=list)
    schedules: list[Provision] = field(default_factory=list)
    unapplied_effects: list[UnappliedEffect] = field(default_factory=list)
    commentaries: dict[str, Commentary] = field(default_factory=dict)
    terms: list[str] = field(default_factory=list)  # defined terms, in document order, deduped
    repealed: list[Provision] = field(default_factory=list)  # Status="Repealed" provisions, pulled out of body
