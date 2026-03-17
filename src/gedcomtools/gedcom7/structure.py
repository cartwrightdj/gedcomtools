"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/structure.py
 Author:  David J. Cartwright
 Purpose: In-memory GEDCOM 7 structure node used by the parser,
          validator, and writer.

 Created: 2026-03-01
 Updated:
   - 2026-03-15: added get_path(), depth property, get_ancestor()
======================================================================

This module defines the in-memory node representation used by the GEDCOM 7
parser and validator.

The design goals are:

- preserve the original GEDCOM line semantics
- keep xref ids separate from pointer payloads
- make parent/child traversal easy
- support validation against the GEDCOM 7 specification registry

The docstrings are written in Google style so they render well with
Sphinx Napoleon.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .g7interop import get_uri_for_tag


class GedcomStructure:
    """Represents a single GEDCOM structure node.

    Attributes:
        level: GEDCOM nesting level for the structure.
        tag: GEDCOM tag such as ``INDI`` or ``NAME``.
        xref_id: Optional xref id defined on the line, such as ``@I1@``.
        payload: Raw payload text following the tag.
        payload_is_pointer: Whether the payload is a pointer such as ``@F1@``.
        parent: Parent structure, if any.
        children: Child structures.
        line_num: Original source line number.
        uri: Resolved GEDCOM 7 URI where available.
        extension: Whether the tag is an extension tag.
    """

    version = "v7"

    def __init__(
        self,
        *,
        level: int,
        tag: str,
        xref_id: Optional[str] = None,
        payload: Optional[str] = None,
        payload_is_pointer: bool = False,
        parent: Optional["GedcomStructure"] = None,
        line_num: Optional[int] = None,
    ) -> None:
        """Initialize the GEDCOM structure node.

        Args:
            level: GEDCOM line level.
            tag: GEDCOM tag.
            xref_id: Optional xref id defined on the line.
            payload: Optional payload text.
            payload_is_pointer: Whether the payload is a pointer.
            parent: Parent structure.
            line_num: Source line number.
        """
        self.level = level
        self.tag = tag.upper()
        self.xref_id = xref_id
        self.payload = payload or ""
        self.payload_is_pointer = payload_is_pointer
        self.parent = parent
        self.children: List[GedcomStructure] = []
        self.line_num = line_num

        self.uri = get_uri_for_tag(self.tag)
        self.extension = self.tag.startswith("_")

        if self.parent is not None:
            self.parent.children.append(self)

    @property
    def value(self) -> str:
        """Return the line payload."""
        return self.payload

    @value.setter
    def value(self, new_value: Optional[str]) -> None:
        """Set the line payload.

        Args:
            new_value: New payload value.
        """
        self.payload = new_value or ""

    @property
    def pointer_target(self) -> Optional[str]:
        """Return the payload if it is a pointer."""
        return self.payload if self.payload_is_pointer else None

    def add_child(self, child: "GedcomStructure") -> None:
        """Attach a child node.

        Args:
            child: Child structure to attach.
        """
        child.parent = self
        self.children.append(child)

    def get_children(self, tag: str) -> List["GedcomStructure"]:
        """Return direct children for a tag.

        Args:
            tag: GEDCOM tag.

        Returns:
            Matching child structures.
        """
        wanted = tag.upper()
        return [child for child in self.children if child.tag == wanted]

    def first_child(self, tag: str) -> Optional["GedcomStructure"]:
        """Return the first direct child matching a tag.

        Args:
            tag: GEDCOM tag.

        Returns:
            First matching child or ``None``.
        """
        matches = self.get_children(tag)
        return matches[0] if matches else None

    @property
    def depth(self) -> int:
        """Return the nesting depth (0 for top-level records).

        Returns:
            Number of ancestor nodes above this node.
        """
        n = 0
        node = self.parent
        while node is not None:
            n += 1
            node = node.parent
        return n

    def get_path(self) -> str:
        """Return a human-readable path from the root to this node.

        Returns:
            Slash-separated path of tags and xref ids.
        """
        parts: list[str] = []
        node: Optional["GedcomStructure"] = self
        while node is not None:
            label = node.xref_id if node.xref_id else node.tag
            parts.append(label)
            node = node.parent
        parts.reverse()
        return "/" + "/".join(parts)

    def get_ancestor(self, tag: str) -> Optional["GedcomStructure"]:
        """Walk up the tree and return the first ancestor with the given tag.

        Args:
            tag: GEDCOM tag to search for.

        Returns:
            Matching ancestor node or ``None``.
        """
        wanted = tag.upper()
        node = self.parent
        while node is not None:
            if node.tag == wanted:
                return node
            node = node.parent
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the node and descendants to a serializable dictionary.

        Returns:
            Nested dictionary representation of the structure tree.
        """
        data: Dict[str, Any] = {
            "level": self.level,
            "tag": self.tag,
            "uri": self.uri,
        }

        if self.xref_id:
            data["xref_id"] = self.xref_id
        if self.payload:
            data["payload"] = self.payload
        if self.payload_is_pointer:
            data["payload_is_pointer"] = True
        if self.line_num is not None:
            data["line_num"] = self.line_num
        if self.children:
            data["children"] = [child.to_dict() for child in self.children]

        return data

    def __getitem__(self, tag: str) -> List["GedcomStructure"]:
        """Return direct children by tag.

        Args:
            tag: GEDCOM tag.

        Returns:
            Matching child structures.
        """
        return self.get_children(tag)

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return (
            "GedcomStructure("
            f"level={self.level}, "
            f"tag={self.tag!r}, "
            f"xref_id={self.xref_id!r}, "
            f"payload={self.payload!r}, "
            f"payload_is_pointer={self.payload_is_pointer}, "
            f"uri={self.uri!r}, "
            f"children={len(self.children)}, "
            f"line_num={self.line_num}"
            ")"
        )
