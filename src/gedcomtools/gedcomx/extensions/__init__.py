"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/__init__.py
 Author:  David J. Cartwright
 Purpose: Package initializer exposing Gedcom-X extension modules

 Created: 2025-08-25
 Updated: 2026-04-08 — expose FamilySearch RS link types from their new fs
                       extension home

======================================================================
"""
from .fs.fs_types_rs import RsLink, RsLinks, rsLink, _rsLinks
