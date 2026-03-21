"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_discussion.py
 Purpose: FamilySearch GedcomX discussion extension types.

 Types: Comment, Discussion, DiscussionReference

 Registers ``discussionReferences`` as an extra list field on Conclusion.

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field

from gedcomtools.gedcomx.attribution import Attribution
from gedcomtools.gedcomx.conclusion import Conclusion
from gedcomtools.gedcomx.gx_base import GedcomXModel
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.gedcomx.schemas import SCHEMA
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class Comment(GedcomXModel):
    """A comment on a FamilySearch discussion.

    Fields:
        id:          Local identifier for this comment.
        text:        The text of the comment.
        created:     Date of comment creation (ms timestamp).
        contributor: The contributor who submitted this comment.
        links:       Hypermedia links map.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Comment"

    id: Optional[str] = None
    text: Optional[str] = None
    created: Optional[int] = None
    contributor: Optional[Resource] = None
    links: Optional[Dict[str, Any]] = None


class Discussion(GedcomXModel):
    """A FamilySearch discussion thread attached to a genealogical record.

    Fields:
        id:               Local identifier for this discussion.
        title:            One-line summary/subject of the discussion.
        details:          Detailed text content.
        created:          Timestamp of discussion creation (ms).
        contributor:      User who submitted the discussion.
        modified:         Last date of any change (ms).
        numberOfComments: Count of associated comments.
        comments:         The comments in this discussion.
        links:            Hypermedia links map.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Discussion"

    id: Optional[str] = None
    title: Optional[str] = None
    details: Optional[str] = None
    created: Optional[int] = None
    contributor: Optional[Resource] = None
    modified: Optional[int] = None
    numberOfComments: Optional[int] = None
    comments: List[Comment] = Field(default_factory=list)
    links: Optional[Dict[str, Any]] = None


class DiscussionReference(GedcomXModel):
    """A reference from a conclusion to a FamilySearch discussion.

    Fields:
        id:          Local identifier for this reference.
        resourceId:  The id of the discussion being referenced.
        resource:    The URI to the resource.
        attribution: Attribution metadata for this reference.
        links:       Hypermedia links map.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/DiscussionReference"

    id: Optional[str] = None
    resourceId: Optional[str] = None
    resource: Optional[str] = None
    attribution: Optional[Attribution] = None
    links: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Register discussionReferences as an extra field on Conclusion.
# ---------------------------------------------------------------------------
SCHEMA.register_extra(Conclusion, "discussionReferences", List[DiscussionReference])

log.debug(
    "fs_types_discussion extension loaded — "
    "Comment, Discussion, DiscussionReference defined; "
    "discussionReferences registered on Conclusion"
)
