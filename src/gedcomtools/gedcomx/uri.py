from __future__ import annotations
from urllib.parse import urlsplit, urlunsplit, urlunparse, SplitResult

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
            if hasattr(self.target, 'id'):
                log.debug("'{}.id' = {}, using as fragment", type(target).__name__, target.id)
                self.fragment = self.target.id
            if hasattr(self.target, 'uri'):
                if getattr(self.target, 'uri') is not None:
                    if target:
                        self._value = target.uri._value
                        self.scheme = target.uri.scheme
                        self.authority = target.uri.authority 
                        self.path = target.uri.path 
                        self.query = target.uri.query
                        self.fragment = target.uri.fragment
                    #TODO Log
                else:
                    log.warning("target.uri was None for {}", target)
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
    
    @classmethod
    def from_url(cls,url):
        return cls(target=url)

#SCHEMA.set_uri_class(URI)
