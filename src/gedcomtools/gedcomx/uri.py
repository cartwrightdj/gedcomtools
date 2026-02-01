from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Sequence, Tuple, Union, Iterable
from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qsl, SplitResult
from urllib.parse import urlunparse

"""
======================================================================
 Project: Gedcom-X
 File:    uri.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactor 
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from ..logging_hub import hub, logging
from .schemas import extensible, SCHEMA
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
#=====================================================================

_DEFAULT_SCHEME = "gedcomx"

# ---------- typing helpers for urlencode (Option A) ----------
QuerySeq = Sequence[Tuple[str, str]]
QueryMap = Mapping[str, str]
QueryLike = Union[str, QueryMap, QuerySeq]

def _encode_query(q: QueryLike) -> str:
    """Return a properly encoded query string."""
    if isinstance(q, str):
        return q
    if isinstance(q, Mapping):
        return urlencode(q, doseq=True)          # mapping is fine
    return urlencode(list(q), doseq=True)        # coerce iterable to a sequence

@extensible()
class URI():
    def __init__(self,
                 
                 target=None,
                 scheme: str | None = None,
                 authority: str | None = None,
                 path: str | None = None,
                 params: str | None = None,
                 query: str | None = None,
                 fragment: str | None = None,
                 value: str | None = None
                 ) -> None:
        
        self.target = target

        self.scheme = scheme 
        self.authority = authority
        self.path = path
        self.params = params
        self.query = query
        self.fragment = fragment     
        
        self._value = value

        if self._value:
            s = urlsplit(self._value)
            self.scheme = s.scheme or _DEFAULT_SCHEME
            self.authority=s.netloc
            self.path=s.path
            self.query=s.query
            self.fragment=s.fragment

        if self.target is not None:
            #log.debug(f"Creating URI from Target {target}, most likely for serialization")
            if hasattr(self.target,'id'):
                if hub.logEnabled:log.debug(f"'{type(target).__name__}.id' found {target.id}, using as fragment")
                self.fragment = self.target.id
            if hasattr(self.target,'uri'):
                log.debug(f"'{target}.uri' found, copying")
                if getattr(self.target,'uri') is not None:
                    if target:
                        self._value = target.uri._value
                        self.scheme = target.uri.scheme
                        self.authority = target.uri.authority 
                        self.path = target.uri.path 
                        self.query = target.uri.query
                        self.fragment = target.uri.fragment
                    #TODO Log
                else:
                    log.warning(f"'{target}.uri' was None")
            elif isinstance(target,URI):
                #log.debug(f"'{target} is a URI, copying")
                if target:
                    self._value = target._value
                    self.scheme = target.scheme
                    self.authority = target.authority 
                    self.path = target.path 
                    self.query = target.query
                    self.fragment = target.fragment
                #TODO Log
            
            
            
            elif isinstance(self.target,str):
                #log.warning(f"Creating a URI from target type {type(target)} with data: {target}.")
                s = urlsplit(self.target)
                self.scheme = s.scheme or _DEFAULT_SCHEME
                self.authority=s.netloc
                self.path=s.path
                self.query=s.query
                self.fragment=s.fragment
            else:
                #log.warning(f"Unable to create URI from target type {type(target)} with data: {target}.")
                self._value = target
        #log.info(f"self.scheme = {self.scheme} self.authority={self.authority} self.path={self.path} self.query={self.query}  self.fragment={self.fragment}")

        parts = [
        self.scheme or "",
        self.authority or "",
        self.path or "",
        self.params or "",
        self.query or "",
        self.fragment or "",
        ]
        if not any(parts) and target is None:
            raise ValueError()   

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
        return (f"scheme = {self.scheme}, authority={self.authority}, path={self.path}, query={self.query}, fragment={self.fragment}")
    
    @property
    def _as_dict_(self):
        return self.value or self._value    
    
       
    @classmethod
    def from_url(cls,url):
        return cls(target=url)
    
    @classmethod
    def _from_json_(cls,data,context=None):
        return cls(value=data)

#SCHEMA.set_uri_class(URI)    

    
@dataclass(slots=True)
class _URI:
    scheme: str = field(default=_DEFAULT_SCHEME)
    authority: str = field(default="")
    path: str = field(default="")
    query: str = field(default="")
    fragment: str = field(default="")

    # ---------- constructors ----------
    @classmethod
    def from_url(cls, url: str, *, default_scheme: str = _DEFAULT_SCHEME) -> URI:
        s = urlsplit(url)
        scheme = s.scheme or default_scheme
        return cls(scheme=scheme, authority=s.netloc, path=s.path, query=s.query, fragment=s.fragment)

    @classmethod
    def parse(cls, value: str) -> URI:
        return cls.from_url(value)

    @classmethod
    def from_parts(
        cls,
        *,
        scheme: str | None = None,
        authority: str = "",
        path: str = "",
        query: QueryLike = "",
        fragment: str = "",
    ) -> URI:
        q = _encode_query(query)
        return cls(scheme=scheme or _DEFAULT_SCHEME, authority=authority, path=path, query=q, fragment=fragment)

    # ---------- views ----------
    @property
    def uri(self) -> str:
        return str(self)
    
    @property
    def value(self) -> str:
        return str(self)

    def split(self) -> SplitResult:
        return SplitResult(self.scheme, self.authority, self.path, self.query, self.fragment)

    def __str__(self) -> str:
        return urlunsplit(self.split())

    @property
    def _as_dict_(self) -> dict[str, object]:
        return {
            "scheme": self.scheme,
            "authority": self.authority,
            "path": self.path,
            "query": self.query,
            "fragment": self.fragment,
            "value": str(self),
        }

    # Accepts {'resource': '...'} or a plain string
    @classmethod
    def _from_json_(cls, data: str | Mapping[str, object],context=None) -> URI:
        return cls.from_parts(fragment="NOT IMPLIMENTED")
        if isinstance(data, str):
            return cls.from_parts(fragment="NOT IMPLIMENTED")
        if isinstance(data, Mapping):
            raw = data.get("resource") or data.get("value") or ""
            if isinstance(raw, str) and raw:
                return cls.from_url(raw)
        raise ValueError(f"Cannot build URI from: {data!r}")

    # ---------- functional updaters ----------
    def with_scheme(self, scheme: str) -> URI: return self.replace(scheme=scheme)
    def with_authority(self, authority: str) -> URI: return self.replace(authority=authority)
    def with_path(self, path: str, *, join: bool = False) -> URI:
        new_path = (self.path.rstrip("/") + "/" + path.lstrip("/")) if join else path
        return self.replace(path=new_path)
    def with_fragment(self, fragment: str | None) -> URI:
        return self.replace(fragment=(fragment or ""))
    def without_fragment(self) -> URI: return self.replace(fragment="")
    def with_query(self, query: QueryLike) -> URI:
        return self.replace(query=_encode_query(query))
    def add_query_params(self, params: Mapping[str, Union[str, Iterable[str]]]) -> URI:
        existing = parse_qsl(self.query, keep_blank_values=True)
        for k, v in params.items():
            if isinstance(v, str):
                existing.append((k, v))
            else:
                for vv in v:
                    existing.append((k, vv))
        return self.replace(query=urlencode(existing, doseq=True))

    # ---------- helpers ----------
    def replace(self, **kwargs) -> URI:
        cls = type(self)
        return cls(
            scheme=kwargs.get("scheme", self.scheme or _DEFAULT_SCHEME),
            authority=kwargs.get("authority", self.authority),
            path=kwargs.get("path", self.path),
            query=kwargs.get("query", self.query),
            fragment=kwargs.get("fragment", self.fragment),
        )
