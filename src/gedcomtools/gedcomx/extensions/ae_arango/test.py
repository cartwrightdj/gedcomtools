"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/test/test.py
 Author:  David J. Cartwright
 Purpose: Test class using the extensible decorator for extension development testing

 Created: 2025-08-25
 Updated:

======================================================================
"""
from gedcomtools.gedcomx.schemas import extensible

@extensible()
class TestClass:
    """Provide a lightweight extensible class used by extension tests."""
    def __init__(self,arg1: str,arg2: str) -> None:
        self.arg1 = arg1
        self.arg2 = arg2
