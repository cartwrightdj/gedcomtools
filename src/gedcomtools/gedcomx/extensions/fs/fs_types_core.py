"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_core.py
 Purpose: FamilySearch GedcomX core extension types.

 Types: Error, Feature, Tag, AgentName, PersonInfo

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

from typing import ClassVar, List, Optional

from pydantic import Field

from gedcomtools.gedcomx.gx_base import GedcomXModel
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.gedcomx.schemas import SCHEMA
from gedcomtools.gedcomx.textvalue import TextValue
from gedcomtools.gedcomx.conclusion import Conclusion
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class Error(GedcomXModel):
    """A FamilySearch API error response.

    Fields:
        code:        The error code.
        label:       A text label.
        message:     A message.
        stacktrace:  The back-end stack trace.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Error"

    code: Optional[int] = None
    label: Optional[str] = None
    message: Optional[str] = None
    stacktrace: Optional[str] = None


class Feature(GedcomXModel):
    """A FamilySearch platform API feature flag.

    Fields:
        name:           The name of the feature.
        description:    A description.
        enabled:        Whether the feature is enabled.
        activationDate: Date feature activates permanently (ms timestamp).
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Feature"

    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    activationDate: Optional[int] = None


class Tag(GedcomXModel):
    """A tag on a GedcomX conclusion.

    Fields:
        resource:     A reference to the value of the tag.
        conclusionId: The conclusionId associated with this tag.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Tag"

    resource: Optional[str] = None
    conclusionId: Optional[str] = None


class AgentName(TextValue):
    """A name for a FamilySearch agent, typed for disambiguation.

    Extends TextValue with a ``type`` field.

    Fields:
        type:  The type of agent name.
        lang:  Inherited from TextValue — BCP 47 language tag.
        value: Inherited from TextValue — The name text.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/AgentName"

    type: Optional[str] = None


class PersonInfo(GedcomXModel):
    """FamilySearch-specific metadata about a person record.

    Fields:
        canUserEdit:                             If this person is editable by the current user.
        visibleToAll:                            If this person is visible to all sessions.
        visibleToAllWhenUsingFamilySearchApps:   Visible only to FS client sessions.
        treeId:                                  The tree id for this person.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/PersonInfo"

    canUserEdit: Optional[bool] = None
    visibleToAll: Optional[bool] = None
    visibleToAllWhenUsingFamilySearchApps: Optional[bool] = None
    treeId: Optional[str] = None


class FeedbackInfo(GedcomXModel):
    """Metadata about FamilySearch user feedback on a record.

    Fields:
        resolution: The resolution state of the feedback.
        status:     The current processing status.
        place:      A place resource associated with this feedback.
        details:    Detailed description of the feedback.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/FeedbackInfo"

    resolution: Optional[str] = None
    status: Optional[str] = None
    place: Optional[Resource] = None
    details: Optional[str] = None


class FsFieldInfo(GedcomXModel):
    """Metadata about a field type in the FamilySearch API.

    Note: Named ``FsFieldInfo`` to avoid collision with pydantic's ``FieldInfo``.
    Its FamilySearch identifier URI is ``http://familysearch.org/v1/FieldInfo``.

    Fields:
        fieldType:     The field type URI.
        displayLabel:  Human-readable label for this field.
        standard:      Whether this is a standard field.
        editable:      Whether this field can be edited.
        displayable:   Whether this field should be shown in the UI.
        elementTypes:  List of element types supported by this field.
        uri:           The URI of this field definition.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/FieldInfo"

    fieldType: Optional[str] = None
    displayLabel: Optional[str] = None
    standard: Optional[bool] = None
    editable: Optional[bool] = None
    displayable: Optional[bool] = None
    elementTypes: List[str] = Field(default_factory=list)
    uri: Optional[str] = None


class PltApiReadMessage(GedcomXModel):
    """An empty marker object returned by certain FamilySearch PLT API endpoints."""

    identifier: ClassVar[str] = "http://familysearch.org/v1/PltApiReadMessage"


# ---------------------------------------------------------------------------
# Register Tag as an extra field on Conclusion.
# ---------------------------------------------------------------------------
SCHEMA.register_extra(Conclusion, "tags", List[Tag])

log.debug(
    "fs_types_core extension loaded — "
    "Tag, AgentName, Feature, Error, PersonInfo, "
    "FeedbackInfo, FsFieldInfo, PltApiReadMessage defined; "
    "tags registered on Conclusion"
)
