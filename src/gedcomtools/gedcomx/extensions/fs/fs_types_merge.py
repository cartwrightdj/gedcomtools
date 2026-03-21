"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_merge.py
 Purpose: FamilySearch GedcomX merge extension types.

 Types: MergeConflict, MergeAnalysis, Merge

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
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class MergeConflict(GedcomXModel):
    """A resource conflict identified during a FamilySearch merge analysis.

    Fields:
        survivorResource:  Resource that survives the merge.
        duplicateResource: Resource identified as duplicate.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/MergeConflict"

    survivorResource: Optional[Resource] = None
    duplicateResource: Optional[Resource] = None


class MergeAnalysis(GedcomXModel):
    """Analysis results from a FamilySearch merge operation.

    Fields:
        survivor:              Primary resource retained after merge.
        duplicate:             Resource identified as duplicate.
        survivorResources:     Resources retained in the merge.
        duplicateResources:    Duplicate resources.
        conflictingResources:  Data conflicts between survivor and duplicate.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/MergeAnalysis"

    survivor: Optional[Resource] = None
    duplicate: Optional[Resource] = None
    survivorResources: List[Resource] = Field(default_factory=list)
    duplicateResources: List[Resource] = Field(default_factory=list)
    conflictingResources: List[MergeConflict] = Field(default_factory=list)


class Merge(GedcomXModel):
    """Instructions for a FamilySearch record merge.

    Fields:
        resourcesToDelete: Resources to remove from the survivor.
        resourcesToCopy:   Resources to copy from duplicate to survivor.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Merge"

    resourcesToDelete: List[Resource] = Field(default_factory=list)
    resourcesToCopy: List[Resource] = Field(default_factory=list)


log.debug(
    "fs_types_merge extension loaded — "
    "MergeConflict, MergeAnalysis, Merge defined"
)
