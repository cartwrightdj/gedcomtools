"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_group.py
 Purpose: FamilySearch GedcomX group extension types.

 Types: GroupMember, Group

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
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class GroupMember(GedcomXModel):
    """A member of a FamilySearch group.

    Fields:
        groupId:     The id of the group this member belongs to.
        cisId:       The Church Information System id of this member.
        contactName: The contact name of this member.
        status:      The membership status.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/GroupMember"

    groupId: Optional[str] = None
    cisId: Optional[str] = None
    contactName: Optional[str] = None
    status: Optional[str] = None


class Group(GedcomXModel):
    """A FamilySearch group of users collaborating on family history.

    Fields:
        id:           Local identifier for this group.
        name:         The group name.
        description:  A description of the group.
        codeOfConduct: The code of conduct for this group.
        treeIds:      Ids of trees associated with this group.
        members:      The members of this group.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Group"

    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    codeOfConduct: Optional[str] = None
    treeIds: List[str] = Field(default_factory=list)
    members: List[GroupMember] = Field(default_factory=list)


log.debug(
    "fs_types_group extension loaded — "
    "GroupMember, Group defined"
)
