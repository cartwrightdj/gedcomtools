# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gedcom/models5.py
 Author:  David J. Cartwright
 Purpose: Convert raw GEDCOM 5 Element objects into the shared
          high-level model dataclasses (IndividualDetail, FamilyDetail,
          etc.) that are also produced by the GEDCOM 7 parser.

          Keeps Gedcom5x and its Element classes completely untouched.

 Created: 2026-03-16
 Updated:
======================================================================
"""

from __future__ import annotations

from typing import List, Optional

from .elements import (
    Element,
    FamilyRecord,
    IndividualRecord,
    ObjectRecord,
    RepositoryRecord,
    SourceRecord,
    SubmitterRecord,
)
from ..gedcom7.models import (
    EventDetail,
    FamilyDetail,
    IndividualDetail,
    MediaDetail,
    NameDetail,
    RepositoryDetail,
    SourceCitation,
    SourceDetail,
    SubmitterDetail,
)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _cv(element: Element, tag: str) -> Optional[str]:
    """Return the stripped value of the first child matching *tag*, or None."""
    child = element.sub_record(tag)
    if child and child.value:
        v = child.value.strip()
        return v or None
    return None


def _mvs(element: Element, tag: str) -> List[str]:
    """Return multi-line values of all children matching *tag*."""
    return [
        c.get_multi_line_value()
        for c in element.get_child_elements()
        if c.tag == tag and c.get_multi_line_value()
    ]


def _is_pointer(value: Optional[str]) -> bool:
    return bool(value and value.strip().startswith("@") and value.strip().endswith("@"))


def _pointer_value(element: Element, tag: str) -> Optional[str]:
    """Return the pointer payload of the first child matching *tag*, if it is
    a valid xref pointer, else None."""
    child = element.sub_record(tag)
    if child and _is_pointer(child.value):
        return child.value.strip()
    return None


def _pointer_values(element: Element, tag: str) -> List[str]:
    """Return all pointer payloads for children matching *tag*."""
    return [
        c.value.strip()
        for c in element.get_child_elements()
        if c.tag == tag and _is_pointer(c.value)
    ]


def _source_citations(element: Element) -> List[SourceCitation]:
    result = []
    for c in element.get_child_elements():
        if c.tag == "SOUR" and _is_pointer(c.value):
            result.append(SourceCitation(
                xref=c.value.strip(),
                page=_cv(c, "PAGE"),
                quality=_cv(c, "QUAY"),
            ))
    return result


def _note_texts(element: Element) -> List[str]:
    return [
        c.get_multi_line_value()
        for c in element.get_child_elements()
        if c.tag == "NOTE" and not _is_pointer(c.value)
        and c.get_multi_line_value()
    ]


def _changed(element: Element) -> Optional[str]:
    chan = element.sub_record("CHAN")
    if chan:
        return _cv(chan, "DATE")
    return None


def _event_detail(el: Optional[Element]) -> Optional[EventDetail]:
    if el is None:
        return None
    note = next(
        (c.get_multi_line_value() for c in el.get_child_elements()
         if c.tag == "NOTE" and not _is_pointer(c.value)
         and c.get_multi_line_value()),
        None,
    )
    return EventDetail(
        date=_cv(el, "DATE"),
        place=_cv(el, "PLAC"),
        age=_cv(el, "AGE"),
        cause=_cv(el, "CAUS"),
        event_type=_cv(el, "TYPE"),
        agency=_cv(el, "AGNC"),
        note=note,
        sources=_source_citations(el),
        shared_note_refs=_pointer_values(el, "SNOTE"),
        media_refs=_pointer_values(el, "OBJE"),
    )


def _name_detail(el: Element) -> NameDetail:
    return NameDetail(
        full=el.value or "",
        given=_cv(el, "GIVN"),
        surname=_cv(el, "SURN"),
        prefix=_cv(el, "NPFX"),
        suffix=_cv(el, "NSFX"),
        nickname=_cv(el, "NICK"),
        surname_prefix=_cv(el, "SPFX"),
        name_type=_cv(el, "TYPE"),
    )


# ---------------------------------------------------------------------------
# Public converters
# ---------------------------------------------------------------------------

def individual_detail_from_g5(rec: IndividualRecord) -> IndividualDetail:
    """Convert a GEDCOM 5 :class:`IndividualRecord` to :class:`IndividualDetail`.

    The returned object is structurally identical to what
    :func:`gedcomtools.gedcom7.models.individual_detail` produces,
    allowing the same calling code to work against both parsers.
    """
    detail = IndividualDetail(xref=rec.xref or "")
    detail._record = rec
    detail._save_fn = _save_individual_g5

    # Names — build a NameDetail for every NAME child
    for el in rec.get_child_elements():
        if el.tag == "NAME":
            detail.names.append(_name_detail(el))

    detail.sex = rec.get_gender() or None

    # Vital events
    detail.birth = _event_detail(rec.sub_record("BIRT"))
    detail.christening = _event_detail(rec.sub_record("CHR"))
    detail.death = _event_detail(rec.sub_record("DEAT"))
    detail.burial = _event_detail(rec.sub_record("BURI"))
    detail.cremation = _event_detail(rec.sub_record("CREM"))

    # Simple fact payloads
    detail.occupation = _cv(rec, "OCCU")
    detail.title = _cv(rec, "TITL")
    detail.religion = _cv(rec, "RELI")
    detail.nationality = _cv(rec, "NATI")

    # Repeated events
    detail.residences = [
        _event_detail(c) for c in rec.get_child_elements()
        if c.tag == "RESI" and _event_detail(c) is not None
    ]
    detail.events = [
        _event_detail(c) for c in rec.get_child_elements()
        if c.tag == "EVEN" and _event_detail(c) is not None
    ]

    # Family links
    detail.families_as_child = _pointer_values(rec, "FAMC")
    detail.families_as_spouse = _pointer_values(rec, "FAMS")

    # Citations, notes, media
    detail.source_citations = _source_citations(rec)
    detail.note_texts = _note_texts(rec)
    detail.shared_note_refs = _pointer_values(rec, "SNOTE")
    detail.media_refs = _pointer_values(rec, "OBJE")

    # Misc
    detail.uid = _cv(rec, "UID") or _cv(rec, "_UID")
    detail.restriction = _cv(rec, "RESN")
    detail.last_changed = rec.get_last_change_date() or None

    return detail


def family_detail_from_g5(rec: FamilyRecord) -> FamilyDetail:
    """Convert a GEDCOM 5 :class:`FamilyRecord` to :class:`FamilyDetail`."""
    detail = FamilyDetail(xref=rec.xref or "")
    detail._record = rec
    detail._save_fn = _save_family_g5

    detail.husband_xref = _pointer_value(rec, "HUSB")
    detail.wife_xref = _pointer_value(rec, "WIFE")
    detail.children_xrefs = _pointer_values(rec, "CHIL")

    detail.marriage = _event_detail(rec.sub_record("MARR"))
    detail.divorce = _event_detail(rec.sub_record("DIV"))

    detail.events = [
        _event_detail(c) for c in rec.get_child_elements()
        if c.tag == "EVEN" and _event_detail(c) is not None
    ]

    detail.source_citations = _source_citations(rec)
    detail.note_texts = _note_texts(rec)
    detail.shared_note_refs = _pointer_values(rec, "SNOTE")
    detail.media_refs = _pointer_values(rec, "OBJE")

    detail.uid = _cv(rec, "UID") or _cv(rec, "_UID")
    detail.restriction = _cv(rec, "RESN")
    detail.last_changed = _changed(rec)

    return detail


def source_detail_from_g5(rec: SourceRecord) -> SourceDetail:
    """Convert a GEDCOM 5 :class:`SourceRecord` to :class:`SourceDetail`."""
    detail = SourceDetail(xref=rec.xref or "")
    detail._record = rec
    detail._save_fn = _save_source_g5

    detail.title = _cv(rec, "TITL")
    detail.author = _cv(rec, "AUTH")
    detail.publication = _cv(rec, "PUBL")
    detail.abbreviation = _cv(rec, "ABBR")
    detail.repository_refs = _pointer_values(rec, "REPO")
    detail.note_texts = _note_texts(rec)
    detail.shared_note_refs = _pointer_values(rec, "SNOTE")
    detail.media_refs = _pointer_values(rec, "OBJE")
    detail.uid = _cv(rec, "UID") or _cv(rec, "_UID")
    detail.last_changed = _changed(rec)

    return detail


def repository_detail_from_g5(rec: RepositoryRecord) -> RepositoryDetail:
    """Convert a GEDCOM 5 :class:`RepositoryRecord` to :class:`RepositoryDetail`."""
    detail = RepositoryDetail(xref=rec.xref or "")
    detail._record = rec
    detail._save_fn = _save_repository_g5

    detail.name = _cv(rec, "NAME")
    detail.address = _cv(rec, "ADDR")
    detail.phone = _cv(rec, "PHON")
    detail.email = _cv(rec, "EMAIL")
    detail.website = _cv(rec, "WWW")
    detail.note_texts = _note_texts(rec)
    detail.shared_note_refs = _pointer_values(rec, "SNOTE")
    detail.uid = _cv(rec, "UID") or _cv(rec, "_UID")
    detail.last_changed = _changed(rec)

    return detail


def media_detail_from_g5(rec: ObjectRecord) -> MediaDetail:
    """Convert a GEDCOM 5 :class:`ObjectRecord` to :class:`MediaDetail`."""
    detail = MediaDetail(xref=rec.xref or "")
    detail._record = rec
    detail._save_fn = _save_media_g5

    detail.files = [
        (c.value.strip(), _cv(c, "FORM"))
        for c in rec.get_child_elements()
        if c.tag == "FILE" and c.value
    ]
    detail.title = _cv(rec, "TITL")
    detail.note_texts = _note_texts(rec)
    detail.shared_note_refs = _pointer_values(rec, "SNOTE")
    detail.uid = _cv(rec, "UID") or _cv(rec, "_UID")
    detail.last_changed = _changed(rec)

    return detail


def submitter_detail_from_g5(rec: SubmitterRecord) -> SubmitterDetail:
    """Convert a GEDCOM 5 :class:`SubmitterRecord` to :class:`SubmitterDetail`."""
    detail = SubmitterDetail(xref=rec.xref or "")
    detail._record = rec
    detail._save_fn = _save_submitter_g5

    detail.name = _cv(rec, "NAME")
    detail.address = _cv(rec, "ADDR")
    detail.phone = _cv(rec, "PHON")
    detail.email = _cv(rec, "EMAIL")
    detail.website = _cv(rec, "WWW")
    detail.language = _cv(rec, "LANG")
    detail.note_texts = _note_texts(rec)
    detail.shared_note_refs = _pointer_values(rec, "SNOTE")
    detail.uid = _cv(rec, "UID") or _cv(rec, "_UID")
    detail.last_changed = _changed(rec)

    return detail


# ---------------------------------------------------------------------------
# G5 write-back helpers
# ---------------------------------------------------------------------------

def _g5_set(element: Element, tag: str, value: Optional[str]) -> None:
    """Set, create, or remove a single-value child element.

    * value is not None  → set existing child's value, or create one.
    * value is None      → remove existing child, if present.
    """
    child = element.sub_record(tag)
    if value is None:
        if child is not None:
            element.get_child_elements().remove(child)
    elif child is not None:
        child.set_value(value)
    else:
        element.new_child_element(tag, value=value)


def _g5_save_event(
    event: Optional[EventDetail],
    event_el: Optional[Element],
    parent_el: Element,
    event_tag: str,
) -> None:
    """Write an EventDetail back into its Element node.

    Creates the event element under *parent_el* if it doesn't exist yet.
    Does nothing when *event* is None.
    """
    if event is None:
        return
    if event_el is None:
        event_el = parent_el.new_child_element(event_tag)
    _g5_set(event_el, "DATE", event.date)
    _g5_set(event_el, "PLAC", event.place)
    _g5_set(event_el, "AGE", event.age)
    _g5_set(event_el, "CAUS", event.cause)
    _g5_set(event_el, "TYPE", event.event_type)
    _g5_set(event_el, "AGNC", event.agency)
    _g5_set(event_el, "NOTE", event.note)


def _g5_save_name(name: NameDetail, name_el: Element) -> None:
    """Write a NameDetail back into a NAME Element."""
    name_el.set_value(name.full)
    _g5_set(name_el, "GIVN", name.given)
    _g5_set(name_el, "SURN", name.surname)
    _g5_set(name_el, "NPFX", name.prefix)
    _g5_set(name_el, "NSFX", name.suffix)
    _g5_set(name_el, "NICK", name.nickname)
    _g5_set(name_el, "SPFX", name.surname_prefix)
    _g5_set(name_el, "TYPE", name.name_type)


def _save_individual_g5(detail: IndividualDetail, rec: IndividualRecord) -> None:
    name_els = [c for c in rec.get_child_elements() if c.tag == "NAME"]
    for i, nd in enumerate(detail.names):
        if i < len(name_els):
            _g5_save_name(nd, name_els[i])
        else:
            new_el = rec.new_child_element("NAME", value=nd.full)
            _g5_save_name(nd, new_el)
    # Remove any NAME elements beyond what the detail list now contains
    for orphan in name_els[len(detail.names):]:
        rec.get_child_elements().remove(orphan)
    _g5_set(rec, "SEX", detail.sex)
    _g5_save_event(detail.birth, rec.sub_record("BIRT"), rec, "BIRT")
    _g5_save_event(detail.christening, rec.sub_record("CHR"), rec, "CHR")
    _g5_save_event(detail.death, rec.sub_record("DEAT"), rec, "DEAT")
    _g5_save_event(detail.burial, rec.sub_record("BURI"), rec, "BURI")
    _g5_save_event(detail.cremation, rec.sub_record("CREM"), rec, "CREM")
    _g5_set(rec, "OCCU", detail.occupation)
    _g5_set(rec, "TITL", detail.title)
    _g5_set(rec, "RELI", detail.religion)
    _g5_set(rec, "NATI", detail.nationality)
    _g5_set(rec, "RESN", detail.restriction)


def _save_family_g5(detail: FamilyDetail, rec: FamilyRecord) -> None:
    _g5_save_event(detail.marriage, rec.sub_record("MARR"), rec, "MARR")
    _g5_save_event(detail.divorce, rec.sub_record("DIV"), rec, "DIV")
    _g5_set(rec, "RESN", detail.restriction)


def _save_source_g5(detail: SourceDetail, rec: SourceRecord) -> None:
    _g5_set(rec, "TITL", detail.title)
    _g5_set(rec, "AUTH", detail.author)
    _g5_set(rec, "PUBL", detail.publication)
    _g5_set(rec, "ABBR", detail.abbreviation)


def _save_repository_g5(detail: RepositoryDetail, rec: RepositoryRecord) -> None:
    _g5_set(rec, "NAME", detail.name)
    _g5_set(rec, "ADDR", detail.address)
    _g5_set(rec, "PHON", detail.phone)
    _g5_set(rec, "EMAIL", detail.email)
    _g5_set(rec, "WWW", detail.website)


def _save_media_g5(detail: MediaDetail, rec: ObjectRecord) -> None:
    _g5_set(rec, "TITL", detail.title)


def _save_submitter_g5(detail: SubmitterDetail, rec: SubmitterRecord) -> None:
    _g5_set(rec, "NAME", detail.name)
    _g5_set(rec, "ADDR", detail.address)
    _g5_set(rec, "PHON", detail.phone)
    _g5_set(rec, "EMAIL", detail.email)
    _g5_set(rec, "WWW", detail.website)
    _g5_set(rec, "LANG", detail.language)
