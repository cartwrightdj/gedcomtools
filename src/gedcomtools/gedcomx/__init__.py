"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/__init__.py
 Author:  David J. Cartwright
 Purpose: Package initializer for the Gedcom-X module exposing all public classes

 Created: 2025-08-25
 Updated: 2026-03-31 — added GxConverterBase, G5ToGxConverter alias; added
                        belt-and-suspenders model_rebuild() calls after all imports

======================================================================
"""
from .gx_base import GedcomXModel
from .extensible import (
    Extensible,
    import_plugins,
    plugin_registry,
    set_trust_level,
    TrustLevel,
    PluginRegistry,
    PluginEntry,
    PluginStatus,
    PluginBlockedError,
    RegistryLockedError,
)

from .subject import Subject
from .agent import Agent
from .address import Address
from .attribution import Attribution
from .conclusion import Conclusion
from .converter_base import GxConverterBase
from .conversion import GedcomConverter
G5ToGxConverter = GedcomConverter  # preferred alias; GedcomConverter kept for backward compat
from .coverage import Coverage
from .date import Date
from .document import Document
from .document import DocumentType
from .evidence_reference import EvidenceReference
from .extensible_enum import ExtensibleEnum
from .event import Event
from .event import EventType
from .event import EventRole

from .fact import Fact
from .fact import FactQualifier
from .fact import FactType
#from .gedcom import Gedcom
from ..gedcom5.parser import Gedcom5x
from .gedcomx import GedcomX
from .gender import Gender, GenderType
from .group import Group, GroupRole
from .identifier import Identifier, IdentifierType, IdentifierList
from .name import Name, NameForm, NamePart, NamePartType, NameType, NamePartQualifier
from .note import Note
from .online_account import OnlineAccount
from .person import Person, QuickPerson
from .place_description import PlaceDescription
from .place_reference import PlaceReference
from .qualifier import Qualifier
from .relationship import Relationship, RelationshipType
from .serialization import Serialization
from .source_citation import SourceCitation
from .source_description import SourceDescription
from .source_description import ResourceType
from .source_reference import SourceReference
from .zip import GedcomZip

from .textvalue import TextValue

from .resource import Resource
from .uri import URI
from .validation import ValidationIssue, ValidationResult

from ..gedcom7.gedcom7 import Gedcom7, GedcomStructure

# Belt-and-suspenders: ensure forward references are resolved for any import
# path (direct submodule imports bypass the bottom-of-file rebuilds in
# event.py and relationship.py).  model_rebuild() is idempotent in pydantic v2.
EventRole.model_rebuild(_types_namespace={"Person": Person})
Relationship.model_rebuild(_types_namespace={"Person": Person})
Person.model_rebuild()
