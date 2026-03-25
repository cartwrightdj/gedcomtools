"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/models.py
 Author:  David J. Cartwright
 Purpose: High-level aggregation dataclasses for GEDCOM 7 top-level
          records.  Each class walks the raw GedcomStructure tree once
          and exposes the fields a caller cares about without needing
          to know GEDCOM tag names.

 Created: 2026-03-16
 Updated:
   - 2026-03-16: initial implementation covering INDI, FAM, SOUR,
                 REPO, OBJE, SNOTE, SUBM
   - 2026-03-16: EventDetail gains sources/shared_note_refs/media_refs and
                 age_years property; FamilyDetail gains divorce_year/num_children;
                 MediaDetail.files typed as List[Tuple[str, Optional[str]]]
   - 2026-03-16: import updated GedcomStructure.py → structure.py
======================================================================

High-level view objects for GEDCOM 7 records.

These are **read-only snapshots** — they are built from a
``GedcomStructure`` tree at construction time and do not stay in sync
if the tree is later mutated.

Usage::

    from gedcomtools.gedcom7 import Gedcom7
    from gedcomtools.gedcom7.models import individual_detail, family_detail

    g = Gedcom7("family.ged")

    # by xref
    person = g.get_individual("@I1@")
    print(person.full_name, person.birth_year, person.death_year)

    # iterate all
    for p in g.individuals():
        print(p.full_name, p.sex)

    for f in g.families():
        print(f.xref, f.husband_xref, f.wife_xref, len(f.children_xrefs))
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .structure import GedcomStructure


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------

@dataclass
class EventDetail:
    """A genealogical event (birth, death, marriage, etc.).

    Attributes:
        date:        Raw GEDCOM date string, e.g. ``"1 JAN 2000"`` or
                     ``"ABT 1850"``.
        place:       Place name from the PLAC substructure.
        age:         Age of the individual at the event (AGE substructure).
        cause:       Cause of the event (CAUS — typically used for death).
        event_type:  Free-text TYPE qualifier attached to the event node.
        agency:      AGNC substructure value.
        note:        First inline NOTE payload, if any.
    """

    date: Optional[str] = None
    place: Optional[str] = None
    age: Optional[str] = None
    cause: Optional[str] = None
    event_type: Optional[str] = None
    agency: Optional[str] = None
    note: Optional[str] = None
    sources: List[SourceCitation] = field(default_factory=list)
    shared_note_refs: List[str] = field(default_factory=list)
    media_refs: List[str] = field(default_factory=list)
    place_translations: Dict[str, str] = field(default_factory=dict)

    @property
    def year(self) -> Optional[int]:
        """Extract the four-digit year from the date string, or ``None``.

        Handles dual-year notation (e.g. ``"1800/01"``) by returning the
        primary year.  Prefers a four-digit match over a three-digit one.
        """
        if not self.date:
            return None
        # Prefer a 4-digit year (with optional /YY dual-year suffix)
        m = re.search(r"(\d{4})(?:/\d{2})?", self.date)
        if m:
            return int(m.group(1))
        # Fall back to 3-digit year (rare, very old dates)
        m = re.search(r"\b(\d{3})\b", self.date)
        return int(m.group(1)) if m else None

    @property
    def qualifier(self) -> Optional[str]:
        """Return any date qualifier prefix: ABT, BEF, AFT, CAL, EST, etc."""
        if not self.date:
            return None
        m = re.match(
            r"^(ABT|CAL|EST|BEF|AFT|FROM|TO|BET|INT)\b",
            self.date.strip(),
            re.IGNORECASE,
        )
        return m.group(1).upper() if m else None

    @property
    def age_years(self) -> Optional[int]:
        """Extract the year component from the AGE string (e.g. ``"45y 3m"`` → 45)."""
        if not self.age:
            return None
        m = re.search(r"(\d+)\s*y", self.age, re.IGNORECASE)
        return int(m.group(1)) if m else None


@dataclass
class NameDetail:
    """A single name entry from an INDI NAME structure.

    Attributes:
        full:       Raw GEDCOM NAME payload, e.g. ``"Lt. /de Allen/ jr."``.
        given:      GIVN substructure value.
        surname:    SURN substructure value.
        prefix:     NPFX name prefix (title before name).
        suffix:     NSFX name suffix (Jr., III, etc.).
        nickname:   NICK substructure value.
        surname_prefix: SPFX surname prefix (de, van, von, etc.).
        name_type:  TYPE substructure value (BIRTH, AKA, IMMIGRANT, etc.).
        lang:       Language tag for this name (populated on TRAN entries).
        translations: NAME.TRAN translations of this name in other languages.
    """

    full: str = ""
    given: Optional[str] = None
    surname: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    nickname: Optional[str] = None
    surname_prefix: Optional[str] = None
    name_type: Optional[str] = None
    lang: Optional[str] = None
    translations: List["NameDetail"] = field(default_factory=list)

    @property
    def display(self) -> str:
        """Clean display name with GEDCOM surname slashes removed."""
        return re.sub(r"/([^/]*)/", r"\1", self.full).strip()


@dataclass
class SourceCitation:
    """A source citation attached to a record or event.

    Attributes:
        xref:  Pointer to the SOUR record (e.g. ``"@S1@"``).
        page:  PAGE substructure value (where within the source).
        quality: QUAY substructure value (0–3 quality assessment).
    """

    xref: str
    page: Optional[str] = None
    quality: Optional[str] = None


@dataclass
class FamcLink:
    """A FAMC (family-as-child) pointer with optional pedigree qualifier.

    Attributes:
        xref:     Pointer to the FAM record (e.g. ``"@F1@"``).
        pedigree: PEDI substructure value — one of ``BIRTH``, ``ADOPTED``,
                  ``FOSTER``, ``SEALING``, or ``None`` if absent.
    """

    xref: str
    pedigree: Optional[str] = None


# ---------------------------------------------------------------------------
# Top-level record detail types
# ---------------------------------------------------------------------------

@dataclass
class IndividualDetail:
    """Aggregated view of a GEDCOM 7 INDI record.

    All repeated structures (names, residences, events, source citations)
    are collected into lists.  Single-valued fields like birth and death
    use the first occurrence found.

    Attributes:
        xref:              Xref id, e.g. ``"@I1@"``.
        names:             All NAME entries, primary first.
        sex:               SEX payload (``"M"``, ``"F"``, ``"X"``, ``"U"``).
        birth:             First BIRT event.
        christening:       First CHR event.
        death:             First DEAT event.
        burial:            First BURI event.
        cremation:         First CREM event.
        occupation:        First OCCU payload.
        title:             First TITL payload.
        religion:          First RELI payload.
        nationality:       First NATI payload.
        residences:        All RESI events.
        events:            All generic EVEN structures.
        families_as_child: FAMC links with optional PEDI pedigree qualifier.
        families_as_spouse: FAMS pointer values.
        source_citations:  All SOUR citations on the INDI record itself.
        note_texts:        Inline NOTE payloads (not shared-note pointers).
        shared_note_refs:  SNOTE pointer values.
        media_refs:        OBJE pointer values.
        uid:               First UID payload.
        restriction:       RESN payload.
        last_changed:      CHAN.DATE payload.
    """

    xref: str
    names: List[NameDetail] = field(default_factory=list)
    sex: Optional[str] = None
    birth: Optional[EventDetail] = None
    christening: Optional[EventDetail] = None
    death: Optional[EventDetail] = None
    burial: Optional[EventDetail] = None
    cremation: Optional[EventDetail] = None
    occupation: Optional[str] = None
    title: Optional[str] = None
    religion: Optional[str] = None
    nationality: Optional[str] = None
    residences: List[EventDetail] = field(default_factory=list)
    events: List[EventDetail] = field(default_factory=list)
    families_as_child: List[FamcLink] = field(default_factory=list)
    families_as_spouse: List[str] = field(default_factory=list)
    source_citations: List[SourceCitation] = field(default_factory=list)
    note_texts: List[str] = field(default_factory=list)
    shared_note_refs: List[str] = field(default_factory=list)
    media_refs: List[str] = field(default_factory=list)
    uid: Optional[str] = None
    restriction: Optional[str] = None
    last_changed: Optional[str] = None
    _record: Any = field(default=None, repr=False, compare=False)
    _save_fn: Any = field(default=None, repr=False, compare=False)

    def save(self) -> None:
        """Write Detail fields back to the underlying raw record.

        Raises:
            RuntimeError: If this Detail was not obtained via a parser
                accessor (i.e. has no attached record).
        """
        if self._save_fn is None:
            raise RuntimeError(
                "No raw record attached. Obtain the Detail via "
                "get_individual_detail() to enable save()."
            )
        self._save_fn(self, self._record)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> Optional[NameDetail]:
        """Primary (first) name entry."""
        return self.names[0] if self.names else None

    @property
    def full_name(self) -> str:
        """Clean display name of the primary name entry."""
        name = self.name
        if name is None:
            return "Unknown"
        return name.display or "Unknown"

    @property
    def birth_year(self) -> Optional[int]:
        """Year extracted from the birth date, or ``None``."""
        return self.birth.year if self.birth else None

    @property
    def death_year(self) -> Optional[int]:
        """Year extracted from the death date, or ``None``."""
        return self.death.year if self.death else None

    @property
    def is_living(self) -> bool:
        """``True`` when no death event is recorded."""
        return self.death is None

    @property
    def age_at_death(self) -> Optional[int]:
        """Approximate age at death computed from birth/death years."""
        by, dy = self.birth_year, self.death_year
        return (dy - by) if (by and dy) else None


@dataclass
class FamilyDetail:
    """Aggregated view of a GEDCOM 7 FAM record.

    Attributes:
        xref:            Xref id, e.g. ``"@F1@"``.
        husband_xref:    HUSB pointer value.
        wife_xref:       WIFE pointer value.
        children_xrefs:  CHIL pointer values (in document order).
        marriage:        First MARR event.
        divorce:         First DIV event.
        events:          All generic EVEN structures.
        source_citations: SOUR citations on the FAM record.
        note_texts:      Inline NOTE payloads.
        shared_note_refs: SNOTE pointer values.
        media_refs:      OBJE pointer values.
        uid:             First UID payload.
        restriction:     RESN payload.
        last_changed:    CHAN.DATE payload.
    """

    xref: str
    husband_xref: Optional[str] = None
    wife_xref: Optional[str] = None
    children_xrefs: List[str] = field(default_factory=list)
    marriage: Optional[EventDetail] = None
    divorce: Optional[EventDetail] = None
    events: List[EventDetail] = field(default_factory=list)
    source_citations: List[SourceCitation] = field(default_factory=list)
    note_texts: List[str] = field(default_factory=list)
    shared_note_refs: List[str] = field(default_factory=list)
    media_refs: List[str] = field(default_factory=list)
    uid: Optional[str] = None
    restriction: Optional[str] = None
    last_changed: Optional[str] = None
    _record: Any = field(default=None, repr=False, compare=False)
    _save_fn: Any = field(default=None, repr=False, compare=False)

    def save(self) -> None:
        """Write Detail fields back to the underlying raw record."""
        if self._save_fn is None:
            raise RuntimeError(
                "No raw record attached. Obtain the Detail via "
                "get_family_detail() to enable save()."
            )
        self._save_fn(self, self._record)

    @property
    def marriage_year(self) -> Optional[int]:
        """Year extracted from the marriage date, or ``None``."""
        return self.marriage.year if self.marriage else None

    @property
    def divorce_year(self) -> Optional[int]:
        """Year extracted from the divorce date, or ``None``."""
        return self.divorce.year if self.divorce else None

    @property
    def num_children(self) -> int:
        """Number of children listed in the family record."""
        return len(self.children_xrefs)


@dataclass
class SourceDetail:
    """Aggregated view of a GEDCOM 7 SOUR record.

    Attributes:
        xref:       Xref id.
        title:      TITL payload.
        author:     AUTH payload.
        publication: PUBL payload.
        abbreviation: ABBR payload.
        repository_refs: REPO pointer values.
        note_texts:  Inline NOTE payloads.
        shared_note_refs: SNOTE pointer values.
        media_refs:  OBJE pointer values.
        uid:         First UID payload.
        last_changed: CHAN.DATE payload.
    """

    xref: str
    title: Optional[str] = None
    author: Optional[str] = None
    publication: Optional[str] = None
    abbreviation: Optional[str] = None
    repository_refs: List[str] = field(default_factory=list)
    note_texts: List[str] = field(default_factory=list)
    shared_note_refs: List[str] = field(default_factory=list)
    media_refs: List[str] = field(default_factory=list)
    uid: Optional[str] = None
    last_changed: Optional[str] = None
    _record: Any = field(default=None, repr=False, compare=False)
    _save_fn: Any = field(default=None, repr=False, compare=False)

    def save(self) -> None:
        """Write Detail fields back to the underlying raw record."""
        if self._save_fn is None:
            raise RuntimeError(
                "No raw record attached. Obtain the Detail via "
                "get_source_detail() to enable save()."
            )
        self._save_fn(self, self._record)


@dataclass
class RepositoryDetail:
    """Aggregated view of a GEDCOM 7 REPO record.

    Attributes:
        xref:       Xref id.
        name:       NAME payload.
        address:    ADDR payload.
        phone:      First PHON payload.
        email:      First EMAIL payload.
        website:    First WWW payload.
        note_texts:  Inline NOTE payloads.
        shared_note_refs: SNOTE pointer values.
        uid:         First UID payload.
        last_changed: CHAN.DATE payload.
    """

    xref: str
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    note_texts: List[str] = field(default_factory=list)
    shared_note_refs: List[str] = field(default_factory=list)
    uid: Optional[str] = None
    last_changed: Optional[str] = None
    _record: Any = field(default=None, repr=False, compare=False)
    _save_fn: Any = field(default=None, repr=False, compare=False)

    def save(self) -> None:
        """Write Detail fields back to the underlying raw record."""
        if self._save_fn is None:
            raise RuntimeError(
                "No raw record attached. Obtain the Detail via "
                "get_repository_detail() to enable save()."
            )
        self._save_fn(self, self._record)


@dataclass
class MediaDetail:
    """Aggregated view of a GEDCOM 7 OBJE record.

    Attributes:
        xref:       Xref id.
        files:      List of (file_path, media_type) tuples from FILE substructures.
        title:      TITL payload.
        note_texts:  Inline NOTE payloads.
        shared_note_refs: SNOTE pointer values.
        uid:         First UID payload.
        last_changed: CHAN.DATE payload.
    """

    xref: str
    files: List[Tuple[str, Optional[str]]] = field(default_factory=list)  # (path, form)
    title: Optional[str] = None
    note_texts: List[str] = field(default_factory=list)
    shared_note_refs: List[str] = field(default_factory=list)
    uid: Optional[str] = None
    last_changed: Optional[str] = None
    _record: Any = field(default=None, repr=False, compare=False)
    _save_fn: Any = field(default=None, repr=False, compare=False)

    def save(self) -> None:
        """Write Detail fields back to the underlying raw record."""
        if self._save_fn is None:
            raise RuntimeError(
                "No raw record attached. Obtain the Detail via "
                "get_media_detail() to enable save()."
            )
        self._save_fn(self, self._record)


@dataclass
class SharedNoteDetail:
    """Aggregated view of a GEDCOM 7 SNOTE record.

    Attributes:
        xref:       Xref id.
        text:       Full note text (CONT lines already merged).
        mime:       MIME type if declared.
        language:   LANG payload.
        source_citations: SOUR citations.
        uid:         First UID payload.
        last_changed: CHAN.DATE payload.
    """

    xref: str
    text: str = ""
    mime: Optional[str] = None
    language: Optional[str] = None
    source_citations: List[SourceCitation] = field(default_factory=list)
    uid: Optional[str] = None
    last_changed: Optional[str] = None
    _record: Any = field(default=None, repr=False, compare=False)
    _save_fn: Any = field(default=None, repr=False, compare=False)

    def save(self) -> None:
        """Write Detail fields back to the underlying raw record."""
        if self._save_fn is None:
            raise RuntimeError(
                "No raw record attached. Obtain the Detail via "
                "get_shared_note_detail() to enable save()."
            )
        self._save_fn(self, self._record)


@dataclass
class SubmitterDetail:
    """Aggregated view of a GEDCOM 7 SUBM record.

    Attributes:
        xref:       Xref id.
        name:       NAME payload.
        address:    ADDR payload.
        phone:      First PHON payload.
        email:      First EMAIL payload.
        website:    First WWW payload.
        language:   First LANG payload.
        note_texts:  Inline NOTE payloads.
        shared_note_refs: SNOTE pointer values.
        uid:         First UID payload.
        last_changed: CHAN.DATE payload.
    """

    xref: str
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    language: Optional[str] = None
    note_texts: List[str] = field(default_factory=list)
    shared_note_refs: List[str] = field(default_factory=list)
    uid: Optional[str] = None
    last_changed: Optional[str] = None
    _record: Any = field(default=None, repr=False, compare=False)
    _save_fn: Any = field(default=None, repr=False, compare=False)

    def save(self) -> None:
        """Write Detail fields back to the underlying raw record."""
        if self._save_fn is None:
            raise RuntimeError(
                "No raw record attached. Obtain the Detail via "
                "get_submitter_detail() to enable save()."
            )
        self._save_fn(self, self._record)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _payload(node: GedcomStructure, tag: str) -> Optional[str]:
    """Return the payload of the first child matching *tag*, or ``None``."""
    child = node.first_child(tag)
    return child.payload if child else None


def _payloads(node: GedcomStructure, tag: str) -> List[str]:
    """Return payloads of all children matching *tag*."""
    return [c.payload for c in node.get_children(tag) if c.payload]


def _pointer(node: GedcomStructure, tag: str) -> Optional[str]:
    """Return the pointer payload of the first matching child, or ``None``."""
    child = node.first_child(tag)
    if child and child.payload_is_pointer and child.payload.upper() != "@VOID@":
        return child.payload
    return None


def _pointers(node: GedcomStructure, tag: str) -> List[str]:
    """Return all non-void pointer payloads for children matching *tag*."""
    return [
        c.payload for c in node.get_children(tag)
        if c.payload_is_pointer and c.payload.upper() != "@VOID@"
    ]


def _changed(node: GedcomStructure) -> Optional[str]:
    """Return CHAN.DATE payload if present."""
    chan = node.first_child("CHAN")
    if chan:
        return _payload(chan, "DATE")
    return None


def _uid(node: GedcomStructure) -> Optional[str]:
    """Return the first UID payload."""
    return _payload(node, "UID")


def _source_citations(node: GedcomStructure) -> List[SourceCitation]:
    """Collect all SOUR citation children of *node*."""
    result = []
    for sour in node.get_children("SOUR"):
        if not sour.payload:
            continue
        result.append(SourceCitation(
            xref=sour.payload,
            page=_payload(sour, "PAGE"),
            quality=_payload(sour, "QUAY"),
        ))
    return result


def _note_texts(node: GedcomStructure) -> List[str]:
    """Return inline NOTE payloads (skip pointer notes)."""
    return [
        n.payload for n in node.get_children("NOTE")
        if n.payload and not n.payload_is_pointer
    ]


def _shared_note_refs(node: GedcomStructure) -> List[str]:
    """Return SNOTE pointer values (non-void)."""
    return _pointers(node, "SNOTE")


def _extract_event(node: Optional[GedcomStructure]) -> Optional[EventDetail]:
    """Build an EventDetail from an event structure node."""
    if node is None:
        return None

    # Collect PLAC.TRAN translations: {lang: translated_place_name}
    place_translations: Dict[str, str] = {}
    plac_node = node.first_child("PLAC")
    if plac_node:
        for tran in plac_node.get_children("TRAN"):
            lang = _payload(tran, "LANG")
            if lang and tran.payload:
                place_translations[lang] = tran.payload

    return EventDetail(
        date=_payload(node, "DATE"),
        place=_payload(node, "PLAC"),
        age=_payload(node, "AGE"),
        cause=_payload(node, "CAUS"),
        event_type=_payload(node, "TYPE"),
        agency=_payload(node, "AGNC"),
        note=next(iter(_note_texts(node)), None),
        sources=_source_citations(node),
        shared_note_refs=_shared_note_refs(node),
        media_refs=_pointers(node, "OBJE"),
        place_translations=place_translations,
    )


def _extract_name(node: GedcomStructure) -> NameDetail:
    """Build a NameDetail from a NAME structure node."""
    translations = [
        NameDetail(
            full=tran.payload or "",
            given=_payload(tran, "GIVN"),
            surname=_payload(tran, "SURN"),
            prefix=_payload(tran, "NPFX"),
            suffix=_payload(tran, "NSFX"),
            nickname=_payload(tran, "NICK"),
            surname_prefix=_payload(tran, "SPFX"),
            lang=_payload(tran, "LANG"),
        )
        for tran in node.get_children("TRAN")
    ]
    return NameDetail(
        full=node.payload,
        given=_payload(node, "GIVN"),
        surname=_payload(node, "SURN"),
        prefix=_payload(node, "NPFX"),
        suffix=_payload(node, "NSFX"),
        nickname=_payload(node, "NICK"),
        surname_prefix=_payload(node, "SPFX"),
        name_type=_payload(node, "TYPE"),
        translations=translations,
    )


# ---------------------------------------------------------------------------
# Public factory functions
# ---------------------------------------------------------------------------

def individual_detail(node: GedcomStructure) -> IndividualDetail:
    """Build an :class:`IndividualDetail` from an INDI :class:`GedcomStructure`.

    Args:
        node: A top-level INDI structure.

    Returns:
        Populated :class:`IndividualDetail` snapshot.
    """
    detail = IndividualDetail(xref=node.xref_id or "")

    detail.names = [_extract_name(n) for n in node.get_children("NAME")]
    detail.sex = _payload(node, "SEX")

    detail.birth = _extract_event(node.first_child("BIRT"))
    detail.christening = _extract_event(node.first_child("CHR"))
    detail.death = _extract_event(node.first_child("DEAT"))
    detail.burial = _extract_event(node.first_child("BURI"))
    detail.cremation = _extract_event(node.first_child("CREM"))

    detail.occupation = _payload(node, "OCCU")
    detail.title = _payload(node, "TITL")
    detail.religion = _payload(node, "RELI")
    detail.nationality = _payload(node, "NATI")

    detail.residences = [
        e for e in (_extract_event(n) for n in node.get_children("RESI"))
        if e is not None
    ]
    detail.events = [
        e for e in (_extract_event(n) for n in node.get_children("EVEN"))
        if e is not None
    ]

    detail.families_as_child = [
        FamcLink(
            xref=c.payload,
            pedigree=(
                c.first_child("PEDI").payload.strip().upper()
                if c.first_child("PEDI") and c.first_child("PEDI").payload
                else None
            ),
        )
        for c in node.get_children("FAMC")
        if c.payload_is_pointer and c.payload.upper() != "@VOID@"
    ]
    detail.families_as_spouse = _pointers(node, "FAMS")

    detail.source_citations = _source_citations(node)
    detail.note_texts = _note_texts(node)
    detail.shared_note_refs = _shared_note_refs(node)
    detail.media_refs = _pointers(node, "OBJE")
    detail.uid = _uid(node)
    detail.restriction = _payload(node, "RESN")
    detail.last_changed = _changed(node)
    detail._record = node
    detail._save_fn = _save_individual_g7

    return detail


def family_detail(node: GedcomStructure) -> FamilyDetail:
    """Build a :class:`FamilyDetail` from a FAM :class:`GedcomStructure`.

    Args:
        node: A top-level FAM structure.

    Returns:
        Populated :class:`FamilyDetail` snapshot.
    """
    detail = FamilyDetail(xref=node.xref_id or "")

    detail.husband_xref = _pointer(node, "HUSB")
    detail.wife_xref = _pointer(node, "WIFE")
    detail.children_xrefs = _pointers(node, "CHIL")

    detail.marriage = _extract_event(node.first_child("MARR"))
    detail.divorce = _extract_event(node.first_child("DIV"))

    detail.events = [
        e for e in (_extract_event(n) for n in node.get_children("EVEN"))
        if e is not None
    ]

    detail.source_citations = _source_citations(node)
    detail.note_texts = _note_texts(node)
    detail.shared_note_refs = _shared_note_refs(node)
    detail.media_refs = _pointers(node, "OBJE")
    detail.uid = _uid(node)
    detail.restriction = _payload(node, "RESN")
    detail.last_changed = _changed(node)
    detail._record = node
    detail._save_fn = _save_family_g7

    return detail


def source_detail(node: GedcomStructure) -> SourceDetail:
    """Build a :class:`SourceDetail` from a SOUR :class:`GedcomStructure`.

    Args:
        node: A top-level SOUR structure.

    Returns:
        Populated :class:`SourceDetail` snapshot.
    """
    detail = SourceDetail(xref=node.xref_id or "")

    detail.title = _payload(node, "TITL")
    detail.author = _payload(node, "AUTH")
    detail.publication = _payload(node, "PUBL")
    detail.abbreviation = _payload(node, "ABBR")
    detail.repository_refs = _pointers(node, "REPO")
    detail.note_texts = _note_texts(node)
    detail.shared_note_refs = _shared_note_refs(node)
    detail.media_refs = _pointers(node, "OBJE")
    detail.uid = _uid(node)
    detail.last_changed = _changed(node)
    detail._record = node
    detail._save_fn = _save_source_g7

    return detail


def repository_detail(node: GedcomStructure) -> RepositoryDetail:
    """Build a :class:`RepositoryDetail` from a REPO :class:`GedcomStructure`.

    Args:
        node: A top-level REPO structure.

    Returns:
        Populated :class:`RepositoryDetail` snapshot.
    """
    detail = RepositoryDetail(xref=node.xref_id or "")

    detail.name = _payload(node, "NAME")
    detail.address = _payload(node, "ADDR")
    detail.phone = _payload(node, "PHON")
    detail.email = _payload(node, "EMAIL")
    detail.website = _payload(node, "WWW")
    detail.note_texts = _note_texts(node)
    detail.shared_note_refs = _shared_note_refs(node)
    detail.uid = _uid(node)
    detail.last_changed = _changed(node)
    detail._record = node
    detail._save_fn = _save_repository_g7

    return detail


def media_detail(node: GedcomStructure) -> MediaDetail:
    """Build a :class:`MediaDetail` from an OBJE :class:`GedcomStructure`.

    Args:
        node: A top-level OBJE structure.

    Returns:
        Populated :class:`MediaDetail` snapshot.
    """
    detail = MediaDetail(xref=node.xref_id or "")

    detail.files = [
        (f.payload, _payload(f, "FORM"))
        for f in node.get_children("FILE")
        if f.payload
    ]
    detail.title = _payload(node, "TITL")
    detail.note_texts = _note_texts(node)
    detail.shared_note_refs = _shared_note_refs(node)
    detail.uid = _uid(node)
    detail.last_changed = _changed(node)
    detail._record = node
    detail._save_fn = _save_media_g7

    return detail


def shared_note_detail(node: GedcomStructure) -> SharedNoteDetail:
    """Build a :class:`SharedNoteDetail` from an SNOTE :class:`GedcomStructure`.

    Args:
        node: A top-level SNOTE structure.

    Returns:
        Populated :class:`SharedNoteDetail` snapshot.
    """
    detail = SharedNoteDetail(xref=node.xref_id or "")

    detail.text = node.payload
    detail.mime = _payload(node, "MIME")
    detail.language = _payload(node, "LANG")
    detail.source_citations = _source_citations(node)
    detail.uid = _uid(node)
    detail.last_changed = _changed(node)
    detail._record = node
    detail._save_fn = _save_shared_note_g7

    return detail


def submitter_detail(node: GedcomStructure) -> SubmitterDetail:
    """Build a :class:`SubmitterDetail` from a SUBM :class:`GedcomStructure`.

    Args:
        node: A top-level SUBM structure.

    Returns:
        Populated :class:`SubmitterDetail` snapshot.
    """
    detail = SubmitterDetail(xref=node.xref_id or "")

    detail.name = _payload(node, "NAME")
    detail.address = _payload(node, "ADDR")
    detail.phone = _payload(node, "PHON")
    detail.email = _payload(node, "EMAIL")
    detail.website = _payload(node, "WWW")
    detail.language = _payload(node, "LANG")
    detail.note_texts = _note_texts(node)
    detail.shared_note_refs = _shared_note_refs(node)
    detail.uid = _uid(node)
    detail.last_changed = _changed(node)
    detail._record = node
    detail._save_fn = _save_submitter_g7

    return detail


# ---------------------------------------------------------------------------
# G7 write-back helpers
# ---------------------------------------------------------------------------

def _g7_set(node: GedcomStructure, tag: str, value: Optional[str]) -> None:
    """Set, create, or remove a single-value child node.

    * value is not None  → set existing child's payload, or create one.
    * value is None      → remove existing child, if present.
    """
    child = node.first_child(tag)
    if value is None:
        if child is not None:
            node.children.remove(child)
    elif child is not None:
        child.payload = value
    else:
        GedcomStructure(level=node.level + 1, tag=tag, payload=value, parent=node)


def _g7_save_event(
    event: Optional["EventDetail"],
    event_node: Optional[GedcomStructure],
    parent_node: GedcomStructure,
    event_tag: str,
) -> None:
    """Write an EventDetail back into its GedcomStructure node.

    Creates the event node under *parent_node* if it doesn't exist yet.
    Does nothing when *event* is None.
    """
    if event is None:
        return
    if event_node is None:
        event_node = GedcomStructure(
            level=parent_node.level + 1, tag=event_tag, parent=parent_node
        )
    _g7_set(event_node, "DATE", event.date)
    _g7_set(event_node, "PLAC", event.place)
    _g7_set(event_node, "AGE", event.age)
    _g7_set(event_node, "CAUS", event.cause)
    _g7_set(event_node, "TYPE", event.event_type)
    _g7_set(event_node, "AGNC", event.agency)
    _g7_set(event_node, "NOTE", event.note)


def _g7_save_name(name: "NameDetail", name_node: GedcomStructure) -> None:
    """Write a NameDetail back into a NAME GedcomStructure node."""
    name_node.payload = name.full
    _g7_set(name_node, "GIVN", name.given)
    _g7_set(name_node, "SURN", name.surname)
    _g7_set(name_node, "NPFX", name.prefix)
    _g7_set(name_node, "NSFX", name.suffix)
    _g7_set(name_node, "NICK", name.nickname)
    _g7_set(name_node, "SPFX", name.surname_prefix)
    _g7_set(name_node, "TYPE", name.name_type)


def _save_individual_g7(detail: "IndividualDetail", node: GedcomStructure) -> None:
    name_nodes = node.get_children("NAME")
    for i, nd in enumerate(detail.names):
        if i < len(name_nodes):
            _g7_save_name(nd, name_nodes[i])
        else:
            new_node = GedcomStructure(
                level=node.level + 1, tag="NAME", payload=nd.full, parent=node
            )
            _g7_save_name(nd, new_node)
    # Remove any NAME nodes beyond what the detail list now contains
    for orphan in name_nodes[len(detail.names):]:
        node.children.remove(orphan)
    _g7_set(node, "SEX", detail.sex)
    _g7_save_event(detail.birth, node.first_child("BIRT"), node, "BIRT")
    _g7_save_event(detail.christening, node.first_child("CHR"), node, "CHR")
    _g7_save_event(detail.death, node.first_child("DEAT"), node, "DEAT")
    _g7_save_event(detail.burial, node.first_child("BURI"), node, "BURI")
    _g7_save_event(detail.cremation, node.first_child("CREM"), node, "CREM")
    _g7_set(node, "OCCU", detail.occupation)
    _g7_set(node, "TITL", detail.title)
    _g7_set(node, "RELI", detail.religion)
    _g7_set(node, "NATI", detail.nationality)
    _g7_set(node, "RESN", detail.restriction)


def _save_family_g7(detail: "FamilyDetail", node: GedcomStructure) -> None:
    _g7_save_event(detail.marriage, node.first_child("MARR"), node, "MARR")
    _g7_save_event(detail.divorce, node.first_child("DIV"), node, "DIV")
    _g7_set(node, "RESN", detail.restriction)


def _save_source_g7(detail: "SourceDetail", node: GedcomStructure) -> None:
    _g7_set(node, "TITL", detail.title)
    _g7_set(node, "AUTH", detail.author)
    _g7_set(node, "PUBL", detail.publication)
    _g7_set(node, "ABBR", detail.abbreviation)


def _save_repository_g7(detail: "RepositoryDetail", node: GedcomStructure) -> None:
    _g7_set(node, "NAME", detail.name)
    _g7_set(node, "ADDR", detail.address)
    _g7_set(node, "PHON", detail.phone)
    _g7_set(node, "EMAIL", detail.email)
    _g7_set(node, "WWW", detail.website)


def _save_media_g7(detail: "MediaDetail", node: GedcomStructure) -> None:
    # Rebuild FILE children from the files list
    for child in list(node.get_children("FILE")):
        node.children.remove(child)
    for path, form in detail.files:
        file_node = GedcomStructure(level=node.level + 1, tag="FILE", payload=path, parent=node)
        if form:
            GedcomStructure(level=file_node.level + 1, tag="FORM", payload=form, parent=file_node)
    _g7_set(node, "TITL", detail.title)


def _save_shared_note_g7(detail: "SharedNoteDetail", node: GedcomStructure) -> None:
    node.payload = detail.text
    _g7_set(node, "MIME", detail.mime)
    _g7_set(node, "LANG", detail.language)


def _save_submitter_g7(detail: "SubmitterDetail", node: GedcomStructure) -> None:
    _g7_set(node, "NAME", detail.name)
    _g7_set(node, "ADDR", detail.address)
    _g7_set(node, "PHON", detail.phone)
    _g7_set(node, "EMAIL", detail.email)
    _g7_set(node, "WWW", detail.website)
    _g7_set(node, "LANG", detail.language)
