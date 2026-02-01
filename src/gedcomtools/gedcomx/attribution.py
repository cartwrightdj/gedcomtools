
from datetime import datetime
from typing import Optional, Dict, Any

"""
======================================================================
 Project: Gedcom-X
 File:    Attribution.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-08-31: fixed _as_dict_ to deal with Resources and ignore empty fields
   - 2025-09-03: _from_json_ refactor
   - 2025-09-09: added schema_class
   - 2025-11-12: removed old code, changes __str__ __repr__ to deal with date items that make not be datetime

   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .agent import Agent
from .resource import Resource
from .schemas import extensible
from ..logging_hub import hub, logging
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
#=====================================================================

@extensible()
class Attribution:
    """Attribution Information for a Genealogy, Conclusion, Subject and child classes

    Args:
        contributor (Agent, optional):            Contributor to object being attributed.
        modified (timestamp, optional):           timestamp for when this record was modified.
        changeMessage (str, optional):            Birth date (YYYY-MM-DD).
        creator (Agent, optional):      Creator of object being attributed.
        created (timestamp, optional):            timestamp for when this record was created

    Raises:
        
    """
    identifier = 'http://gedcomx.org/v1/Attribution'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,contributor: Optional[Agent | Resource] = None,
                 modified: Optional[datetime] = None,
                 changeMessage: Optional[str] = None,
                 creator: Optional[Agent | Resource] = None,
                 created: Optional[datetime] = None) -> None:
               
        self.contributor = contributor
        self.modified = modified
        self.changeMessage = changeMessage
        self.creator = creator
        self.created = created
    
    @staticmethod
    def _fmt_ts(value: Any) -> str:
        """
        Safely format a timestamp-like value.

        - datetime  → isoformat()
        - None      → ''
        - other     → str(value)
        """
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def __str__(self) -> str:
        """Human-readable representation."""
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
        # unchanged
        return (
            f"Attribution("
            f"contributor={self.contributor!r}, "
            f"modified={self.modified!r}, "
            f"changeMessage={self.changeMessage!r}, "
            f"creator={self.creator!r}, "
            f"created={self.created!r}"
            f")"
        )

