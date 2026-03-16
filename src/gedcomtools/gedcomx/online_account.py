from typing import Optional
"""
======================================================================
 Project: Gedcom-X
 File:    online_account.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .resource import Resource
from .schemas import extensible
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

@extensible()
class OnlineAccount:
    identifier = 'http://gedcomx.org/v1/OnlineAccount'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, serviceHomepage: Resource, accountName: str) -> None:
        pass