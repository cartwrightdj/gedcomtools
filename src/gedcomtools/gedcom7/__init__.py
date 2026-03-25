"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/__init__.py
 Author:  David J. Cartwright
 Purpose: Public API for the GEDCOM 7 parsing, validation, and
          serialization toolkit.

 Created: 2026-03-01
 Updated:
   - 2026-03-15: added Gedcom7Writer, g7interop helpers, __version__
   - 2026-03-16: exported get_label from specification
   - 2026-03-16: exported GedcomError and GedcomParseError from Exceptions
   - 2026-03-16: exported models (IndividualDetail, FamilyDetail, etc.)
   - 2026-03-16: imports updated Exceptions.py → exceptions.py, GedcomStructure.py → structure.py
   - 2026-03-24: exported Gedcom7Converter
======================================================================

GEDCOM 7 parsing and validation tools.

Modules:
    gedcom7: Parser and validation entry points.
    GedcomStructure: In-memory structure tree nodes.
    specification: Normalized GEDCOM 7 rule helpers.
    g7interop: GEDCOM tag and URI interoperability helpers.
    validator: Grammar and semantic validation.
    writer: GEDCOM 7 serializer.
    g7cli: Interactive browser/editor shell.
    Exceptions: GedcomError and GedcomParseError exception hierarchy.
    models: High-level detail dataclasses for INDI, FAM, SOUR, REPO, OBJE, SNOTE, SUBM.
"""

from .exceptions import GedcomError, GedcomParseError
from .g7togx import Gedcom7Converter
from .structure import GedcomStructure
from .gedcom7 import Gedcom7, GedcomValidationError
from .validator import GedcomValidator, ValidationIssue
from .writer import Gedcom7Writer
from .g7interop import (
    get_uri_for_tag,
    get_tag_for_uri,
    is_known_tag,
    is_known_uri,
    register_tag_uri,
)
from .specification import get_label
from .models import (
    EventDetail,
    NameDetail,
    SourceCitation,
    IndividualDetail,
    FamilyDetail,
    SourceDetail,
    RepositoryDetail,
    MediaDetail,
    SharedNoteDetail,
    SubmitterDetail,
    individual_detail,
    family_detail,
    source_detail,
    repository_detail,
    media_detail,
    shared_note_detail,
    submitter_detail,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Gedcom7Converter",
    "GedcomError",
    "GedcomParseError",
    "Gedcom7",
    "GedcomStructure",
    "GedcomValidationError",
    "GedcomValidator",
    "ValidationIssue",
    "Gedcom7Writer",
    "get_uri_for_tag",
    "get_tag_for_uri",
    "is_known_tag",
    "is_known_uri",
    "register_tag_uri",
    "get_label",
    # models
    "EventDetail",
    "NameDetail",
    "SourceCitation",
    "IndividualDetail",
    "FamilyDetail",
    "SourceDetail",
    "RepositoryDetail",
    "MediaDetail",
    "SharedNoteDetail",
    "SubmitterDetail",
    "individual_detail",
    "family_detail",
    "source_detail",
    "repository_detail",
    "media_detail",
    "shared_note_detail",
    "submitter_detail",
]
