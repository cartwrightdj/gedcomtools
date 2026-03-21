"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_node.py
 Purpose: FamilySearch GedcomX node/tree-navigation extension types.

 Types: Template, Templates, NameFormInfo, NameFormOrder, NameSearchInfo,
        Child, ChildrenData, NodeData, Facet, SearchInfo

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

import enum
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field

from gedcomtools.gedcomx.gx_base import GedcomXModel
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class Template(GedcomXModel):
    """A URI template used to build navigation links in the FS tree API.

    Fields:
        name:     The name (key) of this template.
        template: The RFC 6570 URI template string.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Template"

    name: Optional[str] = None
    template: Optional[str] = None


class Templates(GedcomXModel):
    """A collection of URI templates.

    Fields:
        links:     Hypermedia links map.
        templates: The list of templates.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Templates"

    links: Optional[Dict[str, Any]] = None
    templates: List[Template] = Field(default_factory=list)


class NameFormInfo(GedcomXModel):
    """Metadata about a name form in the FamilySearch API.

    Fields:
        order: The preferred display order for this name form.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/NameFormInfo"

    order: Optional[str] = None


class NameFormOrder(str, enum.Enum):
    """URI constants for name-form display order."""

    Eurotypic = "http://familysearch.org/v1/Eurotypic"
    Sinotypic = "http://familysearch.org/v1/Sinotypic"


class NameSearchInfo(GedcomXModel):
    """Search-result metadata about a matched name.

    Fields:
        text:         The text of the matched name.
        nameId:       The id of the matched name conclusion.
        namePartType: The matched name-part type URI.
        weight:       The relevance weight (higher is better).
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/NameSearchInfo"

    text: Optional[str] = None
    nameId: Optional[str] = None
    namePartType: Optional[str] = None
    weight: Optional[float] = None


class Child(GedcomXModel):
    """A child entry in a children-data response.

    Fields:
        name:    The display name of the child.
        apid:    The FS ARK identifier (Persistent ID) for the child person.
        locator: An opaque locator for use with the children-data API.
        order:   The display order of this child among its siblings.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Child"

    name: Optional[str] = None
    apid: Optional[str] = None
    locator: Optional[str] = None
    order: Optional[int] = None


class ChildrenData(GedcomXModel):
    """A paginated list of children for a tree navigation node.

    Fields:
        position:  The requested start position in the list.
        children:  The children in this page.
        baseUrl:   The base URL for child links.
        templates: URI templates for building navigation links.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/ChildrenData"

    position: Optional[int] = None
    children: List[Child] = Field(default_factory=list)
    baseUrl: Optional[str] = None
    templates: List[Template] = Field(default_factory=list)


class NodeData(GedcomXModel):
    """Metadata for a single node in the FamilySearch tree navigation API.

    Fields:
        name:        The display name of the node.
        apid:        The FS ARK identifier (Persistent ID) for this node.
        templates:   URI templates for navigation.
        childCount:  The number of children of this node.
        streamCount: The number of stream entries for this node.
        lastMod:     The last-modified timestamp (ms).
        link:        Hypermedia links for this node.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/NodeData"

    name: Optional[str] = None
    apid: Optional[str] = None
    templates: List[Template] = Field(default_factory=list)
    childCount: Optional[int] = None
    streamCount: Optional[int] = None
    lastMod: Optional[int] = None
    link: List[Any] = Field(default_factory=list)


class Facet(GedcomXModel):
    """A search-facet entry for refinement of search results.

    Fields:
        displayName:  The human-readable facet label.
        displayCount: A display count string.
        params:       Query-string parameters to apply this facet.
        count:        The number of results matching this facet.
        facets:       Nested sub-facets.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Facet"

    displayName: Optional[str] = None
    displayCount: Optional[str] = None
    params: Optional[str] = None
    count: Optional[int] = None
    facets: List[Facet] = Field(default_factory=list)


# Allow self-referential field
Facet.model_rebuild()


class SearchInfo(GedcomXModel):
    """Summary statistics for a FamilySearch search response.

    Fields:
        totalHits: Total number of records matching the query.
        closeHits: Number of close (approximate) matches.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/SearchInfo"

    totalHits: Optional[int] = None
    closeHits: Optional[int] = None


log.debug(
    "fs_types_node extension loaded — "
    "Template, Templates, NameFormInfo, NameFormOrder, NameSearchInfo, "
    "Child, ChildrenData, NodeData, Facet, SearchInfo defined"
)
