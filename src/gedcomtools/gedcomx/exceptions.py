"""
======================================================================
 Project: Gedcom-X
 File:    exceptions.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-09-12
 Updated:
   
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""

class GedcomXError(Exception):
    """Base for all app-specific errors."""

class GedcomClassAttributeError(GedcomXError):
    def __init__(self, *args: object) -> None:
        msg = f"This class need more information to be created: {args}"
        super().__init__(msg)


class TagConversionError(GedcomXError):
    def __init__(self, record,levelstack):
        msg = f"Cannot convert: #{record.line} TAG: {record.tag} {record.xref if record.xref else ''} Value:{record.value} STACK: {type(levelstack[record.level-1]).__name__}"
        super().__init__(msg)
        
class ConversionErrorDump(GedcomXError):
    pass

class GedcomXDateParseError(ValueError):
    """Raised when we cannot parse a date string into GEDCOM X Date format."""