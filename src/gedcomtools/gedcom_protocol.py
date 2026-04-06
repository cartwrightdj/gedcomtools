# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gedcom_protocol.py
 Author:  David J. Cartwright
 Purpose: Structural typing protocols for GEDCOM format objects.

          GedcomFile  — satisfied by both Gedcom5 and Gedcom7.
          GedcomNode  — satisfied by GedcomStructure (G7) and Element (G5).

          Neither class needs to inherit from these protocols; structural
          subtyping (duck-typing) means any class with the right methods
          automatically satisfies them.  @runtime_checkable enables
          isinstance() checks for defensive assertions.

 Created: 2026-04-03
======================================================================
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from gedcomtools.gedcom7.models import (
        FamilyDetail,
        IndividualDetail,
        MediaDetail,
        RepositoryDetail,
        SharedNoteDetail,
        SourceDetail,
        SubmitterDetail,
    )


@runtime_checkable
class GedcomFile(Protocol):
    """Structural protocol satisfied by :class:`~gedcomtools.gedcom5.gedcom5.Gedcom5`
    and :class:`~gedcomtools.gedcom7.gedcom7.Gedcom7`.

    Defines the complete public API used by the CLI layer (``gctool_*`` modules)
    so that type checkers catch missing methods on new format classes at
    analysis time rather than at runtime.

    ``@runtime_checkable`` enables::

        assert isinstance(obj, GedcomFile)   # checks all method names are present

    Note: data attributes (e.g. ``filepath``) are not checked by isinstance —
    they are present for static type-checker use only.
    """

    filepath: Optional[Path]

    # ------------------------------------------------------------------
    # Version / validation
    # ------------------------------------------------------------------

    def detect_gedcom_version(self) -> Optional[str]: ...
    def validate(self) -> list: ...

    # ------------------------------------------------------------------
    # Raw record accessors  (return format-specific record objects)
    # ------------------------------------------------------------------

    def individuals(self) -> list: ...
    def families(self) -> list: ...
    def sources(self) -> list: ...
    def repositories(self) -> list: ...
    def media_objects(self) -> list: ...
    def submitters(self) -> list: ...
    def shared_notes(self) -> list: ...

    # ------------------------------------------------------------------
    # Detail model accessors  (shared dataclasses, same for G5 and G7)
    # ------------------------------------------------------------------

    def individual_details(self) -> List[IndividualDetail]: ...
    def family_details(self) -> List[FamilyDetail]: ...
    def source_details(self) -> List[SourceDetail]: ...
    def repository_details(self) -> List[RepositoryDetail]: ...
    def media_details(self) -> List[MediaDetail]: ...
    def submitter_details(self) -> List[SubmitterDetail]: ...
    def shared_note_details(self) -> List[SharedNoteDetail]: ...

    def get_individual_detail(self, xref: str) -> Optional[IndividualDetail]: ...
    def get_family_detail(self, xref: str) -> Optional[FamilyDetail]: ...
    def get_source_detail(self, xref: str) -> Optional[SourceDetail]: ...
    def get_repository_detail(self, xref: str) -> Optional[RepositoryDetail]: ...
    def get_media_detail(self, xref: str) -> Optional[MediaDetail]: ...
    def get_submitter_detail(self, xref: str) -> Optional[SubmitterDetail]: ...
    def get_shared_note_detail(self, xref: str) -> Optional[SharedNoteDetail]: ...

    # ------------------------------------------------------------------
    # Relationship traversal
    # ------------------------------------------------------------------

    def get_parents(self, xref: str) -> list: ...
    def get_children_of(self, xref: str) -> list: ...
    def get_spouses(self, xref: str) -> list: ...


@runtime_checkable
class GedcomNode(Protocol):
    """Minimal structural protocol for a GEDCOM tree node.

    Satisfied by :class:`~gedcomtools.gedcom7.structure.GedcomStructure` (G7)
    and :class:`~gedcomtools.gedcom5.elements.Element` (G5) at the level of
    attributes that are safe to access without knowing the concrete type.

    The two node types differ beyond this minimum:
    * G7 exposes ``.payload`` and ``.children`` (a list).
    * G5 exposes ``.value`` via ``get_value()`` and children via
      ``get_child_elements()``.

    Code that needs format-specific behaviour should branch on the format
    string from ``_load()`` and cast to the concrete type rather than
    relying on this protocol for the extended interface.
    """

    tag: str
