"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_vocab.py
 Purpose: FamilySearch GedcomX vocabulary extension types.

 Types: VocabConceptAttribute, VocabTranslation, VocabTerm,
        VocabConcept, VocabConcepts

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field

from gedcomtools.gedcomx.gx_base import GedcomXModel
from gedcomtools.gedcomx.textvalue import TextValue
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class VocabConceptAttribute(GedcomXModel):
    """An attribute of a FamilySearch vocabulary concept.

    Fields:
        id:    Local identifier for this attribute.
        name:  The attribute name.
        value: The attribute value text.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/VocabConceptAttribute"

    id: Optional[str] = None
    name: Optional[str] = None
    value: Optional[str] = None


class VocabTranslation(GedcomXModel):
    """A translated label for a FamilySearch vocabulary term.

    Fields:
        id:    Local context-specific id.
        lang:  BCP 47 language tag.
        text:  The translated text.
        links: Hypermedia links map.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/VocabTranslation"

    id: Optional[str] = None
    lang: Optional[str] = None
    text: Optional[str] = None
    links: Optional[Dict[str, Any]] = None


class VocabTerm(GedcomXModel):
    """A term within a FamilySearch vocabulary concept.

    Fields:
        id:              Local identifier for this term.
        typeUri:         The URI of the term type.
        vocabConcept:    Reference to the parent vocabulary concept.
        sublistUri:      URI of a sub-list of concepts.
        sublistPosition: Position in the sub-list.
        values:          The text values (translations) for this term.
        links:           Hypermedia links map.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/VocabTerm"

    id: Optional[str] = None
    typeUri: Optional[str] = None
    vocabConcept: Optional[str] = None
    sublistUri: Optional[str] = None
    sublistPosition: Optional[int] = None
    values: List[TextValue] = Field(default_factory=list)
    links: Optional[Dict[str, Any]] = None


class VocabConcept(GedcomXModel):
    """A concept in a FamilySearch controlled vocabulary.

    Fields:
        id:          Local identifier for this concept.
        description: A description of this concept.
        note:        An explanatory note.
        gedcomxUri:  The GedcomX URI for this concept.
        vocabTerms:  The vocabulary terms associated with this concept.
        attributes:  Typed attributes of this concept.
        definitions: TextValue definitions (possibly multi-language).
        links:       Hypermedia links map.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/VocabConcept"

    id: Optional[str] = None
    description: Optional[str] = None
    note: Optional[str] = None
    gedcomxUri: Optional[str] = None
    vocabTerms: List[VocabTerm] = Field(default_factory=list)
    attributes: List[VocabConceptAttribute] = Field(default_factory=list)
    definitions: List[TextValue] = Field(default_factory=list)
    links: Optional[Dict[str, Any]] = None


class VocabConcepts(GedcomXModel):
    """A container for a list of FamilySearch vocabulary concepts.

    Fields:
        vocabConcepts: The vocabulary concepts.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/VocabConcepts"

    vocabConcepts: List[VocabConcept] = Field(default_factory=list)


log.debug(
    "fs_types_vocab extension loaded — "
    "VocabConceptAttribute, VocabTranslation, VocabTerm, VocabConcept, VocabConcepts defined"
)
