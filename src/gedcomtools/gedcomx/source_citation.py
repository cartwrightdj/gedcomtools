"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/source_citation.py
 Author:  David J. Cartwright
 Purpose: GedcomX SourceCitation model

 Created: 2025-08-25
 Updated:
======================================================================
"""
# GedcomX SourceCitation model.
# Spec: http://gedcomx.org/v1/SourceCitation
#
# value  — REQUIRED. Plain text, MAY include a single xhtml <cite> element.
#          If <cite> is present it MUST represent the title of a work per
#          https://html.spec.whatwg.org/multipage/text-level-semantics.html#the-cite-element
# lang   — OPTIONAL IETF BCP 47 locale tag. If absent the locale is determined
#          per Internationalization Considerations.

from __future__ import annotations

import re
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from .gx_base import GedcomXModel

# Matches any HTML/XML tag other than <cite> or </cite>
_NON_CITE_TAG_RE = re.compile(r"<(?!/?cite\b)[^>]+>", re.IGNORECASE)


class SourceCitation(GedcomXModel):
    """A container for the metadata necessary to identify a source.

    Spec: http://gedcomx.org/v1/SourceCitation
    """

    identifier: ClassVar[str] = "http://gedcomx.org/v1/SourceCitation"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    lang: Optional[str] = None
    value: str = Field(..., description="The bibliographic metadata rendered as a full citation.")

    @field_validator("value")
    @classmethod
    def _value_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("SourceCitation.value is REQUIRED and must not be empty")
        return v

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_lang
        check_lang(result, "lang", self.lang)
        # value is guaranteed non-empty by the field validator above, but
        # check for non-cite HTML tags (spec allows only <cite>)
        if "<" in self.value and _NON_CITE_TAG_RE.search(self.value):
            result.warn(
                "value",
                "Citation value contains HTML tags other than <cite>; "
                "only the xhtml <cite> element is permitted by the spec",
            )
