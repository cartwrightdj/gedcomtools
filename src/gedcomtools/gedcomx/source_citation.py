from __future__ import annotations
from typing import ClassVar, Optional

from .gx_base import GedcomXModel


class SourceCitation(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/SourceCitation"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    lang: Optional[str] = "en"
    value: str = ""

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_lang, check_nonempty
        check_lang(result, "lang", self.lang)
        check_nonempty(result, "value", self.value)
