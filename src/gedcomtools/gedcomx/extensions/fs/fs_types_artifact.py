"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_artifact.py
 Purpose: FamilySearch GedcomX artifact extension types.

 Types: ArtifactDisplayState, ArtifactScreeningState, ArtifactMetadata

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

import enum
from typing import Any, ClassVar, List, Optional

from pydantic import Field

from gedcomtools.gedcomx.gx_base import GedcomXModel
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class ArtifactDisplayState(str, enum.Enum):
    """URI constants representing the display state of a FamilySearch artifact."""

    Processing = "http://familysearch.org/v1/Processing"
    UploadFailed = "http://familysearch.org/v1/UploadFailed"
    ProcessingFailed = "http://familysearch.org/v1/ProcessingFailed"
    Restricted = "http://familysearch.org/v1/Restricted"
    Approved = "http://familysearch.org/v1/Approved"


class ArtifactScreeningState(str, enum.Enum):
    """URI constants representing the screening state of a FamilySearch artifact."""

    Pending = "http://familysearch.org/v1/Pending"
    Approved = "http://familysearch.org/v1/Approved"
    Restricted = "http://familysearch.org/v1/Restricted"


class ArtifactMetadata(GedcomXModel):
    """Metadata describing a FamilySearch artifact (uploaded media file).

    Fields:
        filename:       The original filename of the artifact.
        qualifiers:     Qualifiers on the artifact.
        width:          The width of the artifact in pixels.
        height:         The height of the artifact in pixels.
        size:           The file size in bytes.
        screeningState: The current content-screening state.
        displayState:   The current processing/display state.
        editable:       Whether this artifact may be edited.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/ArtifactMetadata"

    filename: Optional[str] = None
    qualifiers: List[Any] = Field(default_factory=list)
    width: Optional[int] = None
    height: Optional[int] = None
    size: Optional[int] = None
    screeningState: Optional[str] = None
    displayState: Optional[str] = None
    editable: Optional[bool] = None


log.debug(
    "fs_types_artifact extension loaded — "
    "ArtifactDisplayState, ArtifactScreeningState, ArtifactMetadata defined"
)
