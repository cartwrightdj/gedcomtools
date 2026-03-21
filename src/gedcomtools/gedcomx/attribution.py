from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Optional, Union

from .agent import Agent
from .gx_base import GedcomXModel
from .resource import Resource


class Attribution(GedcomXModel):
    """Attribution metadata — who contributed data and when."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Attribution"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    contributor: Optional[Union[Agent, Resource]] = None
    modified: Optional[datetime] = None
    changeMessage: Optional[str] = None
    changeMessageResource: Optional[str] = None
    creator: Optional[Union[Agent, Resource]] = None
    created: Optional[datetime] = None

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance, check_nonempty
        check_instance(result, "contributor", self.contributor, Agent, Resource)
        check_instance(result, "creator", self.creator, Agent, Resource)
        if self.modified is not None and not isinstance(self.modified, datetime):
            result.warn("modified", f"Expected datetime, got {type(self.modified).__name__}")
        if self.created is not None and not isinstance(self.created, datetime):
            result.warn("created", f"Expected datetime, got {type(self.created).__name__}")
        if self.changeMessage is not None:
            check_nonempty(result, "changeMessage", self.changeMessage)
        if self.changeMessageResource is not None:
            check_nonempty(result, "changeMessageResource", self.changeMessageResource)

    @staticmethod
    def _fmt_ts(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def __str__(self) -> str:
        parts = []
        if self.contributor:
            parts.append(f"contributor={self.contributor}")
        if self.modified is not None:
            parts.append(f"modified={self._fmt_ts(self.modified)}")
        if self.changeMessage:
            parts.append(f"changeMessage='{self.changeMessage}'")
        if self.changeMessageResource:
            parts.append(f"changeMessageResource='{self.changeMessageResource}'")
        if self.creator:
            parts.append(f"creator={self.creator}")
        if self.created is not None:
            parts.append(f"created={self._fmt_ts(self.created)}")
        inner = ", ".join(parts) if parts else "no attribution data"
        return f"Attribution({inner})"

    def __repr__(self) -> str:
        return (
            f"Attribution("
            f"contributor={self.contributor!r}, "
            f"modified={self.modified!r}, "
            f"changeMessage={self.changeMessage!r}, "
            f"creator={self.creator!r}, "
            f"created={self.created!r})"
        )
