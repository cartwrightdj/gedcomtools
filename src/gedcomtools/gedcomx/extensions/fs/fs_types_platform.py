"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_platform.py
 Purpose: FamilySearch GedcomX platform extension types.

 Types: MatchStatus, MatchInfo, Tree, TreePersonReference, User,
        FamilySearchPlatform

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional

from pydantic import Field

from gedcomtools.gedcomx.attribution import Attribution
from gedcomtools.gedcomx.gx_base import GedcomXModel
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.glog import get_logger

if TYPE_CHECKING:
    from gedcomtools.gedcomx.extensions.fs.fs_types_merge import Merge, MergeAnalysis
    from gedcomtools.gedcomx.extensions.fs.fs_types_discussion import Discussion
    from gedcomtools.gedcomx.extensions.fs.fs_types_core import Feature

log = get_logger(__name__)


class ThirdPartyAccess(str, enum.Enum):
    """URI constants controlling third-party application access to a tree."""

    AnyApps = "http://familysearch.org/v1/AnyApps"
    CompanyApps = "http://familysearch.org/v1/CompanyApps"
    NoApps = "http://familysearch.org/v1/None"


class MatchStatus(str, enum.Enum):
    """URI constants representing the resolution state of a match."""

    Pending = "http://familysearch.org/v1/Pending"
    Accepted = "http://familysearch.org/v1/Accepted"
    Rejected = "http://familysearch.org/v1/Rejected"
    Deferred = "http://familysearch.org/v1/Deferred"


class MatchInfo(GedcomXModel):
    """Metadata about a record match result in FamilySearch.

    Fields:
        collection:                          The collection in which this match was found.
        status:                              The way this match has been resolved.
        addsPerson:                          Match adds a new person.
        addsPerson110YearRule:               Adds a person under the 110-year rule.
        addsFact:                            Match adds a fact.
        addsDateOrPlace:                     Match adds a date or place.
        hasFourOrMorePeople:                 Match involves four or more people.
        addsFather110YearRule:               Adds a father under the 110-year rule.
        addsMother110YearRule:               Adds a mother under the 110-year rule.
        addsParentUnknownGender110YearRule:  Adds a parent of unknown gender under the 110-year rule.
        addsSpouse110YearRule:               Adds a spouse under the 110-year rule.
        addsSon110YearRule:                  Adds a son under the 110-year rule.
        addsDaughter110YearRule:             Adds a daughter under the 110-year rule.
        addsChildUnknownGender110YearRule:   Adds a child of unknown gender under the 110-year rule.
        addsBirth:                           Match adds a birth event.
        addsChristening:                     Match adds a christening event.
        addsDeath:                           Match adds a death event.
        addsBurial:                          Match adds a burial event.
        addsMarriage:                        Match adds a marriage event.
        addsOtherFact:                       Match adds another fact type.
        addsDate:                            Match adds a date.
        addsPlace:                           Match adds a place.
        improvesDate:                        Match improves an existing date.
        improvesPlace:                       Match improves an existing place.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/MatchInfo"

    collection: Optional[str] = None
    status: Optional[str] = None
    addsPerson: Optional[bool] = None
    addsPerson110YearRule: Optional[bool] = None
    addsFact: Optional[bool] = None
    addsDateOrPlace: Optional[bool] = None
    hasFourOrMorePeople: Optional[bool] = None
    addsFather110YearRule: Optional[bool] = None
    addsMother110YearRule: Optional[bool] = None
    addsParentUnknownGender110YearRule: Optional[bool] = None
    addsSpouse110YearRule: Optional[bool] = None
    addsSon110YearRule: Optional[bool] = None
    addsDaughter110YearRule: Optional[bool] = None
    addsChildUnknownGender110YearRule: Optional[bool] = None
    addsBirth: Optional[bool] = None
    addsChristening: Optional[bool] = None
    addsDeath: Optional[bool] = None
    addsBurial: Optional[bool] = None
    addsMarriage: Optional[bool] = None
    addsOtherFact: Optional[bool] = None
    addsDate: Optional[bool] = None
    addsPlace: Optional[bool] = None
    improvesDate: Optional[bool] = None
    improvesPlace: Optional[bool] = None


class Tree(GedcomXModel):
    """A FamilySearch family tree.

    Fields:
        id:              The tree id.
        groupIds:        Ids of groups this tree belongs to.
        name:            The tree name.
        description:     The tree description.
        startingPersonId: The tree starting person id.
        hidden:          The hidden state of the tree.
        private:         The private state of the tree.
        collectionId:    Id of collection the tree belongs to.
        ownerAccess:     Owner third party access state.
        groupAccess:     Group third party access state.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Tree"

    id: Optional[str] = None
    groupIds: List[str] = Field(default_factory=list)
    name: Optional[str] = None
    description: Optional[str] = None
    startingPersonId: Optional[str] = None
    hidden: Optional[bool] = None
    private: Optional[bool] = None
    collectionId: Optional[str] = None
    ownerAccess: Optional[str] = None
    groupAccess: Optional[str] = None


class TreePersonReference(GedcomXModel):
    """A reference linking a person to a FamilySearch tree.

    Fields:
        id:          Local identifier for this reference.
        treePerson:  Reference to the person in the tree.
        tree:        Reference to the tree containing the person.
        attribution: Attribution metadata.
        links:       Hypermedia links map.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/TreePersonReference"

    id: Optional[str] = None
    treePerson: Optional[Resource] = None
    tree: Optional[Resource] = None
    attribution: Optional[Attribution] = None
    links: Optional[Dict[str, Any]] = None


class User(GedcomXModel):
    """A FamilySearch user account record.

    Fields:
        id:                 Local identifier.
        contactName:        The user's contact name.
        helperAccessPin:    Helper access PIN.
        fullName:           Full name.
        givenName:          Given name.
        familyName:         Family name.
        email:              Primary email address.
        alternateEmail:     Alternate email address.
        country:            Country.
        gender:             Gender.
        birthDate:          Birth date string.
        phoneNumber:        Phone number.
        mobilePhoneNumber:  Mobile phone number.
        mailingAddress:     Mailing address.
        preferredLanguage:  Preferred language (BCP 47).
        displayName:        Display name.
        personId:           Associated person id.
        treeUserId:         Tree user id.
        links:              Hypermedia links map.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/User"

    id: Optional[str] = None
    contactName: Optional[str] = None
    helperAccessPin: Optional[str] = None
    fullName: Optional[str] = None
    givenName: Optional[str] = None
    familyName: Optional[str] = None
    email: Optional[str] = None
    alternateEmail: Optional[str] = None
    country: Optional[str] = None
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    phoneNumber: Optional[str] = None
    mobilePhoneNumber: Optional[str] = None
    mailingAddress: Optional[str] = None
    preferredLanguage: Optional[str] = None
    displayName: Optional[str] = None
    personId: Optional[str] = None
    treeUserId: Optional[str] = None
    links: Optional[Dict[str, Any]] = None


class FamilySearchPlatform(GedcomXModel):
    """The top-level FamilySearch platform data envelope.

    Extends GedcomXModel directly (rather than GedcomX) to avoid circular
    import complexity.  Stores all FS-specific collection types alongside
    normal GedcomX data.

    Fields:
        childAndParentsRelationships: ChildAndParentsRelationship list.
        discussions:                  Discussions in this data set.
        trees:                        Trees in this data set.
        users:                        Users in this data set.
        merges:                       Merges for this data set.
        mergeAnalyses:                Merge analysis results.
        features:                     Features defined in platform API.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/FamilySearchPlatform"

    childAndParentsRelationships: List[Any] = Field(default_factory=list)
    discussions: List[Any] = Field(default_factory=list)
    trees: List[Tree] = Field(default_factory=list)
    users: List[User] = Field(default_factory=list)
    merges: List[Any] = Field(default_factory=list)
    mergeAnalyses: List[Any] = Field(default_factory=list)
    features: List[Any] = Field(default_factory=list)


log.debug(
    "fs_types_platform extension loaded — "
    "ThirdPartyAccess, MatchStatus, MatchInfo, Tree, TreePersonReference, User, "
    "FamilySearchPlatform defined"
)
