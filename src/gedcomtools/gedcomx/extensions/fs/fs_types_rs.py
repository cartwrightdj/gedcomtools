"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_rs.py
 Purpose: FamilySearch RS/REST extension models shared by FS payloads.

 Types:
   RsLink, RsLinks, FamilyView, DisplayProperties, FamilyLinks

 Notes:
   These models were previously housed in the legacy `extensions.rs10`
   package. They now live under the FamilySearch extension package so
   FamilySearch JSON payloads can load their inherited RS link structures
   from the same plugin tree.

 Created: 2026-04-08
 Updated: 2026-04-08 — expand DisplayProperties to cover the observed
                       FamilySearch person display payload shape
======================================================================
"""
from __future__ import annotations

from typing import Callable, ClassVar, Dict, Iterable, List, Optional

from pydantic import Field, model_validator

from gedcomtools.gedcomx.conclusion import Conclusion
from gedcomtools.gedcomx.extensible import Extensible
from gedcomtools.gedcomx.name import Name
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.gedcomx.schemas import SCHEMA
from gedcomtools.gedcomx.uri import URI
from gedcomtools.gedcomx.exceptions import GedcomClassAttributeError


ResolveIsPerson = Callable[[URI], bool]


class RsLink(Extensible):
    """A FamilySearch RS hypermedia link."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Link"

    href: Optional[URI] = None
    template: Optional[str] = None
    type: Optional[str] = None  # pylint: disable=redefined-builtin
    accept: Optional[str] = None
    allow: Optional[str] = None
    hreflang: Optional[str] = None
    title: Optional[str] = None

    def __init__(self, **data):
        """Preserve the legacy `RsLink(href='...')` construction style."""
        href = data.get("href")
        if isinstance(href, str):
            data = dict(data)
            data["href"] = URI.from_url(href)
        super().__init__(**data)

    @model_validator(mode="before")
    @classmethod
    def _coerce_href(cls, value):
        """Accept JSON objects whose `href` value is still a string."""
        if isinstance(value, dict):
            value = dict(value)
            href = value.get("href")
            if isinstance(href, str):
                value["href"] = URI.from_url(href)
        return value

    @model_validator(mode="after")
    def _require_href_or_template(self):
        """Require at least one navigable target."""
        if self.href is None and self.template is None:
            raise GedcomClassAttributeError("href or template are required")
        return self

    def __str__(self) -> str:
        def to_text(v):
            if v is None:
                return None
            if isinstance(v, URI):
                return getattr(v, "value", None) or str(v)
            if isinstance(v, str):
                stripped = v.strip()
                return stripped or None
            return str(v)

        parts = []
        href_s = to_text(self.href)
        if href_s:
            parts.append(href_s)

        for name in ("template", "type", "accept", "allow", "hreflang", "title"):
            val = to_text(getattr(self, name, None))
            if val:
                parts.append(f"{name}={val}")

        return " | ".join(parts) if parts else "RsLink"

    def __repr__(self) -> str:
        def render(v):
            if isinstance(v, URI):
                return f"URI({v.value!r})"
            return repr(v)

        return (
            f"RsLink("
            f"href={render(self.href)}, "
            f"template={render(self.template)}, "
            f"type={render(self.type)}, "
            f"accept={render(self.accept)}, "
            f"allow={render(self.allow)}, "
            f"hreflang={render(self.hreflang)}, "
            f"title={render(self.title)}"
            f")"
        )


class RsLinks(Extensible):
    """A map of FamilySearch RS hypermedia links."""

    items: Dict[str, RsLink] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce_items(cls, value):
        """Accept plain JSON maps such as `{'child': {'href': ...}}`."""
        if isinstance(value, cls):
            return value
        if isinstance(value, dict) and "items" not in value:
            return {"items": value}
        return value

    @property
    def person(self) -> Optional[RsLink]:
        """Backward-compatible access to the RS `person` link."""
        return self.items.get("person")

    @property
    def portrait(self) -> Optional[RsLink]:
        """Backward-compatible access to the RS `portrait` link."""
        return self.items.get("portrait")

    def keys(self) -> Iterable[str]:
        """Expose mapping-style keys for callers that treat links as a map."""
        return self.items.keys()

    def get(self, key: str, default=None):
        """Return the link named *key*, or *default* if absent."""
        return self.items.get(key, default)

    def __str__(self) -> str:
        parts = [f"{name}={link}" for name, link in self.items.items()]
        inner = ", ".join(parts) if parts else "empty"
        return f"RsLinks({inner})"

    def __repr__(self) -> str:
        return f"RsLinks(items={self.items!r})"


class FamilyView(Extensible):
    """Represent FamilySearch RS family-link references for a person view."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/FamilyView"

    parent1: Optional[Resource] = None
    parent2: Optional[Resource] = None
    children: Optional[List[Resource]] = None


class DisplayProperties(Extensible):
    """Represent FamilySearch RS display-oriented properties for a person."""

    ascendancyNumber: str | None = None
    birthDate: str | None = None
    birthPlace: str | None = None
    deathDate: str | None = None
    deathPlace: str | None = None
    descendancyNumber: str | None = None
    familiesAsChild: List[FamilyView] = Field(default_factory=list)
    familiesAsParent: List[FamilyView] = Field(default_factory=list)
    name: str | None = None
    gender: str | None = None
    lifespan: str | None = None


class FamilyLinks(Extensible):
    """Family membership references for FamilySearch RS payloads."""

    parent1: Optional[URI] = None
    parent2: Optional[URI] = None
    children: Optional[List[URI]] = None

    def validate_links(self, is_person: Optional[ResolveIsPerson] = None) -> None:
        """Validate that each populated URI resolves to a Person."""
        if is_person is None:
            return

        def _check(uri: Optional[URI], label: str):
            if uri is None:
                return
            if not is_person(uri):
                raise ValueError(f"{label} MUST resolve to a Person: {uri}")

        _check(self.parent1, "parent1")
        _check(self.parent2, "parent2")

        if self.children:
            bad = [uri for uri in self.children if not is_person(uri)]
            if bad:
                raise ValueError(f"children contain non-Person references: {bad}")


SCHEMA.register_extra(Conclusion, "links", RsLinks)
SCHEMA.register_extra(Name, "prefered", bool)


# Backward-compatible aliases for legacy RS10 imports.
rsLink = RsLink
_rsLinks = RsLinks
