from __future__ import annotations
from typing import Any, Optional, List

from dataclasses import dataclass, field, fields, MISSING, make_dataclass

"""
======================================================================
 Project: Gedcom-X
 File:    rsLink.py
 Author:  David J. Cartwright
 Purpose: Link type of GedcomX RS 1.0 (Extension)
 https://github.com/FamilySearch/gedcomx-rs/blob/master/specifications/rs-specification.md

 Created: 2025-08-25
 Updated:
   - 
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from gedcomtools.gedcomx.conclusion import Conclusion
from gedcomtools.gedcomx.name import Name
from ...exceptions import GedcomClassAttributeError
from gedcomtools.logging_hub import hub, logging
from gedcomtools.gedcomx.schemas import extensible, SCHEMA
from gedcomtools.gedcomx.extensible import Extensible
from gedcomtools.gedcomx.uri import URI
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.gedcomx.person import Person
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
deserial_log = "gedcomx.deserialization"
#=====================================================================


@extensible()
class rsLink:
    """A link description object. RS Extension to GedcomX by FamilySearch."""
    identifier = "http://gedcomx.org/v1/Link"

    def __init__(self,
                 href:  Optional[URI] = None,
                 template: Optional[str] = None,
                 type: Optional[str] = None,
                 accept: Optional[str] = None,
                 allow: Optional[str] = None,
                 hreflang: Optional[str] = None,
                 title: Optional[str] = None) -> None:

        self.href = href if isinstance(href, URI) else URI.from_url(href) if isinstance(href, str) else None
        self.template = template
        self.type = type
        self.accept = accept
        self.allow = allow
        self.hreflang = hreflang
        self.title = title

        if self.href is None and self.template is None:
            raise GedcomClassAttributeError("href or template are required")

    # -----------------------------------------------
    # Human readable
    # -----------------------------------------------
    def __str__(self) -> str:
        def to_text(v):
            if v is None:
                return None
            if isinstance(v, URI):
                return getattr(v, "value", None) or str(v)
            if isinstance(v, str):
                s = v.strip()
                return s or None
            return str(v)

        parts = []

        href_s = to_text(self.href)
        if href_s:
            parts.append(href_s)

        for name in ("template", "type", "accept", "allow", "hreflang", "title"):
            val = to_text(getattr(self, name, None))
            if val:
                parts.append(f"{name}={val}")

        return " | ".join(parts) if parts else "rsLink"

    # -----------------------------------------------
    # Full debug/developer form
    # -----------------------------------------------
    def __repr__(self) -> str:
        def r(v):
            if isinstance(v, URI):
                return f"URI({v.value!r})"
            return repr(v)

        return (
            f"rsLink("
            f"href={r(self.href)}, "
            f"template={r(self.template)}, "
            f"type={r(self.type)}, "
            f"accept={r(self.accept)}, "
            f"allow={r(self.allow)}, "
            f"hreflang={r(self.hreflang)}, "
            f"title={r(self.title)}"
            f")"
        )

    @classmethod
    def _from_json_(cls, data: Any, context: Any = None) -> "rsLink":
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__}._from_json_ expected dict, got {type(data)}")

        return cls(
            href=data.get("href"),
            template=data.get("template"),
            type=data.get("type"),
            accept=data.get("accept"),
            allow=data.get("allow"),
            hreflang=data.get("hreflang"),
            title=data.get("title"),
        )

@extensible()
class _rsLinks:
    def __init__(self,
                 person: Optional[rsLink] = None,
                 portrait: Optional[rsLink] = None) -> None:

        self.person = person
        self.portrait = portrait

    # -----------------------------------------------
    # Human readable
    # -----------------------------------------------
    def __str__(self) -> str:
        parts = []
        if self.person:
            parts.append(f"person={self.person}")
        if self.portrait:
            parts.append(f"portrait={self.portrait}")

        inner = ", ".join(parts) if parts else "empty"
        return f"rsLinks({inner})"

    # -----------------------------------------------
    # Debug / constructor accurate
    # -----------------------------------------------
    def __repr__(self) -> str:
        return (
            f"_rsLinks("
            f"person={repr(self.person)}, "
            f"portrait={repr(self.portrait)}"
            f")"
        )


@extensible()
@dataclass
class FamilyView():
    identifier = "http://gedcomx.org/v1/FamilyView"
    """
    Family membership references.

    Fields:
      parent1: OPTIONAL URI. If provided, MUST resolve to an instance of http://gedcomx.org/v1/Person
      parent2: OPTIONAL URI. If provided, MUST resolve to an instance of http://gedcomx.org/v1/Person
      children: OPTIONAL list of URIs. Each MUST resolve to an instance of http://gedcomx.org/v1/Person
    """
    parent1: Optional[Resource] = None
    parent2: Optional[Resource] = None
    children: Optional[List[Resource]] = None

@extensible()
@dataclass
class DisplayProperties():
    name: str | None = None
    gender: str | None = None
    lifespan: str | None = None
    birthDate: str | None = None


@extensible()
@dataclass
class FamilyLinks(Extensible):
    """
    Family membership references.

    Fields:
      parent1: OPTIONAL URI. If provided, MUST resolve to an instance of http://gedcomx.org/v1/Person
      parent2: OPTIONAL URI. If provided, MUST resolve to an instance of http://gedcomx.org/v1/Person
      children: OPTIONAL list of URIs. Each MUST resolve to an instance of http://gedcomx.org/v1/Person
    """
    parent1: Optional[URI] = None
    parent2: Optional[URI] = None
    children: Optional[List[URI]] = None

    def validate(self, is_person: Optional[ResolveIsPerson] = None) -> None:
        """
        Validate constraints using the provided `is_person` resolver.
        If no resolver is provided, this function does a no-op.

        Raises:
          ValueError if any provided reference does not resolve to a Person.
        """
        if is_person is None:
            return  # No validation possible without a resolver

        def _check(uri: Optional[URI], label: str):
            if uri is None:
                return
            if not is_person(uri):
                raise ValueError(f"{label} MUST resolve to a Person: {uri}")

        _check(self.parent1, "parent1")
        _check(self.parent2, "parent2")

        if self.children:
            bad = [u for u in self.children if not is_person(u)]
            if bad:
                raise ValueError(f"children contain non-Person references: {bad}")

SCHEMA.register_extra(Conclusion,'links',_rsLinks)
SCHEMA.register_extra(Name,"prefered",bool)             #3.3 Whether the name is considered the "preferred" name for display purposes.
SCHEMA.register_extra(Person,"living",bool)
SCHEMA.register_extra(Person,"_display",DisplayProperties)

def display_properies(self):
    return DisplayProperties()

SCHEMA.register_extra(Person,"display",DisplayProperties)