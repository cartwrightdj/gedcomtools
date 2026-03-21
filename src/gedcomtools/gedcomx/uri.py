from __future__ import annotations

from typing import Any, ClassVar, Optional
from urllib.parse import SplitResult, urlsplit, urlunparse, urlunsplit

from pydantic import model_serializer, model_validator
from pydantic_core import core_schema

from ..glog import get_logger
from .gx_base import GedcomXModel

log = get_logger(__name__)

_DEFAULT_SCHEME = "gedcomx"


class URI(GedcomXModel):
    """GedcomX URI — parsed into components; serializes as its string value."""

    scheme: Optional[str] = None
    authority: Optional[str] = None
    path: Optional[str] = None
    params: Optional[str] = None
    query: Optional[str] = None
    fragment: Optional[str] = None

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        """Pre-process the various construction paths into a component dict.

        Accepted forms:
            URI(value='http://...')          — parse URL string
            URI(fragment='abc')              — set fragment only
            URI(target=obj_with_id)          — extract id as fragment
            URI(target=uri_instance)         — copy components from another URI
            URI(target='http://...')         — parse string target
            URI(target=obj_with_uri)         — copy components from obj.uri
        """
        if not isinstance(data, dict):
            # Positional or non-dict — treat as a value string
            return cls._parse_value_string(str(data))

        data = dict(data)  # don't mutate the caller's dict
        target = data.pop("target", None)
        value = data.pop("value", None)

        if value is not None:
            parsed = cls._parse_value_string(value)
            # component kwargs take priority over the parsed value
            for k in ("scheme", "authority", "path", "params", "query", "fragment"):
                if data.get(k) is None:
                    data[k] = parsed.get(k)
            return data

        if target is not None:
            return cls._process_target(target, data)

        return data

    @classmethod
    def _parse_value_string(cls, s: str) -> dict:
        sp = urlsplit(s)
        return {
            "scheme": sp.scheme or _DEFAULT_SCHEME,
            "authority": sp.netloc or None,
            "path": sp.path or None,
            "query": sp.query or None,
            "fragment": sp.fragment or None,
        }

    @classmethod
    def _process_target(cls, target: Any, base: dict) -> dict:
        if isinstance(target, URI):
            return {
                **base,
                "scheme": target.scheme,
                "authority": target.authority,
                "path": target.path,
                "params": target.params,
                "query": target.query,
                "fragment": target.fragment,
            }
        if isinstance(target, str):
            parsed = cls._parse_value_string(target)
            return {**base, **{k: v for k, v in parsed.items() if v is not None}}
        if hasattr(target, "uri") and getattr(target, "uri") is not None:
            uri = target.uri
            if isinstance(uri, URI):
                return cls._process_target(uri, base)
            log.warning("target.uri is not a URI instance for {}", target)
        if hasattr(target, "id"):
            return {**base, "fragment": target.id}
        # Fallback — store as fragment string
        return {**base, "fragment": str(target)}

    @model_validator(mode="after")
    def _validate_not_empty(self) -> "URI":
        parts = [self.scheme, self.authority, self.path, self.params, self.query, self.fragment]
        if not any(parts):
            raise ValueError("URI: at least one component must be set")
        return self

    # ------------------------------------------------------------------
    # Pydantic coercion — accept strings where URI is expected
    # ------------------------------------------------------------------

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        from pydantic_core import core_schema as cs

        # handler(source_type) gives the base model schema; pydantic resolves
        # the self-reference safely via a definition-reference node.
        model_schema = handler(source_type)

        def _from_string(v: str) -> "URI":
            # model_construct bypasses the schema to avoid re-entering this validator
            components = cls._parse_value_string(v)
            return cls.model_construct(**{k: val for k, val in components.items() if val is not None})

        return cs.union_schema(
            [
                cs.is_instance_schema(cls),
                cs.chain_schema([cs.str_schema(), cs.no_info_plain_validator_function(_from_string)]),
                model_schema,   # handles dict inputs via _normalize_input
            ],
            mode="left_to_right",
        )

    # ------------------------------------------------------------------
    # Serialization — output as the string value, not a component dict
    # ------------------------------------------------------------------

    @model_serializer
    def _as_string(self) -> str:
        return str(self)

    # ------------------------------------------------------------------
    # Standard interface
    # ------------------------------------------------------------------

    @property
    def value(self) -> str | None:
        parts = [
            self.scheme or "",
            self.authority or "",
            self.path or "",
            self.params or "",
            self.query or "",
            self.fragment or "",
        ]
        if not any(parts):
            return None
        return str(urlunparse(parts))

    def split(self) -> SplitResult:
        return SplitResult(
            self.scheme or "",
            self.authority or "",
            self.path or "",
            self.query or "",
            self.fragment or "",
        )

    def __str__(self) -> str:
        return urlunsplit(self.split())

    def __repr__(self) -> str:
        return (
            f"URI(scheme={self.scheme}, authority={self.authority}, "
            f"path={self.path}, query={self.query}, fragment={self.fragment})"
        )

    @classmethod
    def from_url(cls, url: Any) -> "URI":
        return cls.model_validate({"target": url})
