from __future__ import annotations
from typing import ClassVar, Optional

from .gx_base import GedcomXModel


class SourceCitation(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/SourceCitation"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    lang: Optional[str] = "en"
    value: str = ""
