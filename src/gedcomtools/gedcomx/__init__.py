from .schemas import SCHEMA
from .extensible import Extensible, import_plugins

r = import_plugins(
    "gedcomx",
    subpackage="extensions",
    local_dir="./plugins",
    env_var="GEDCOMX_PLUGINS",
    recursive=False,
)

from .subject import Subject
from .agent import Agent
from .address import Address
from .attribution import Attribution
from .conclusion import Conclusion
from .conversion import GedcomConverter
from .coverage import Coverage
from .date import Date
from .document import Document
from .document import DocumentType
from .evidence_reference import EvidenceReference
from .extensible_enum import ExtensibleEnum
from .event import Event
from .event import EventType
from .event import EventRole

from. extensible import _ExtraField
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
SCHEMA.set_resource_class(Resource)
from .uri import URI
SCHEMA.set_uri_class(URI)

from ..gedcom7.gedcom7 import Gedcom7, GedcomStructure
#from ..xxxtranslation import g7toXtable

SCHEMA.normalize_all()

