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
    creator: Optional[Union[Agent, Resource]] = None
    created: Optional[datetime] = None

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
