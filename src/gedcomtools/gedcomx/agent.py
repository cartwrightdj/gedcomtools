from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from .person import Person
"""
======================================================================
 Project: Gedcom-X
 File:    agent.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactor
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Type Imports
======================================================================
"""
from .address import Address
from .identifier import Identifier, IdentifierList
from .online_account import OnlineAccount
from .resource import Resource
from .schemas import extensible
from .textvalue import TextValue
from .uri import URI
from .identifier import make_uid
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

@extensible(toplevel=True)
class Agent:
    """A GedcomX Agent Data Type.

    Represents an agent entity such as a person, organization, or software 
    responsible for creating or modifying genealogical data, as defined in 
    the GedcomX conceptual model.

    Static Methods:
    

    Args:
        id (str, optional): A unique identifier for this agent. If not provided, 
            one may be generated automatically using `default_id_generator()`.
        identifiers (IdentifierList, optional): A list of alternate identifiers for this agent.
        names (List[TextValue], optional): Names associated with the agent. Defaults to an empty list.
        homepage (URI, optional): A link to the agent's homepage or primary website.
        openid (URI, optional): The OpenID identifier for the agent.
        accounts (List[OnlineAccount], optional): Online accounts associated with the agent.
            Defaults to an empty list.
        emails (List[URI], optional): Email addresses associated with the agent.
            Defaults to an empty list.
        phones (List[Resource], optional): Phone numbers associated with the agent.
            Defaults to an empty list.
        addresses (List[Address], optional): Postal addresses associated with the agent.
            Defaults to an empty list.
        person (Person, optional): A reference to the person represented 
            by the agent. Accepts a `Person` object or a `Resource` reference. 
            Declared as `object` to avoid circular imports.
        attribution (Attribution, optional): Attribution information related to the agent.
        uri (Resource, optional): A URI reference for this agent.
    """
        
    def __init__(self, id: Optional[str] = None,
                    identifiers: Optional[IdentifierList] = None, 
                    names: Optional[List[TextValue]] = None,
                    homepage: Optional[URI] = None,
                    openid: Optional[URI] = None,
                    accounts: Optional[List[OnlineAccount]] = None,
                    emails: Optional[List[URI]] = None,
                    phones: Optional[List[URI]] = None,
                    addresses: Optional[List[Address]] = None, 
                    person: Optional[Union[Resource,Person]] = None, # should be of Type 'Person', 'object' to avoid circular imports
                    attribution: Optional[object] = None, # Added for compatibility with GEDCOM5/7 Imports
                    ): 
        
        
        self.id = id if id else make_uid()
        self.identifiers = identifiers or IdentifierList()
        self.names = names if names else []
        self.homepage = homepage or None
        self.openid = openid or None
        self.accounts = accounts or []
        self.emails = emails or []
        self.phones = phones or []
        self.addresses = addresses if addresses else []
        self.person = person
        self.xnotes = []
        self.attribution = attribution or None
        self._uri = URI(fragment=self.id) if self.id else None
  
    def _append_to_name(self, text_to_append: str):
        if self.names and self.names[0] and self.names[0].value:
            self.names[0].value = self.names[0].value + text_to_append
        elif self.names and self.names[0]:
            self.names[0].value = text_to_append
        else:
            raise ValueError() #TODO

    def add_address(self, address_to_add: Address):
        if address_to_add and isinstance(address_to_add, Address):
            for current_address in self.addresses:
                if address_to_add == current_address:
                    return False
            self.addresses.append(address_to_add)
        else:
            raise ValueError(f"address must be of type Address, not {type(address_to_add)}")
        
    def add_name(self, name_to_add: TextValue):
        if isinstance(name_to_add,str): name_to_add = TextValue(value=name_to_add)
        if name_to_add and isinstance(name_to_add,TextValue):
            for current_name in self.names:
                if name_to_add == current_name:
                    assert False
            if name_to_add.value is None or name_to_add == '':
                assert False
            self.names.append(name_to_add)
        else:
            raise ValueError(f'name must be of type str or TextValue, recived {type(name_to_add)}')
    
    def add_note(self, note_to_add):
        from .note import Note
        if note_to_add and isinstance(note_to_add,Note):
            self.xnotes.append(note_to_add)
        else:
            raise ValueError(f'note must be of type Note, recived {type(note_to_add)}')
    
    def add_identifier(self, identifier_to_add: Identifier):
        self.identifiers.append(identifier_to_add)
    
    def __str__(self):
        """
        Return a human-readable string representation of the Agent.

        Returns:
            str: A concise description including ID, primary name (if any), and type of agent.
        """
        primary_name = self.names[0].value if self.names else "Unnamed Agent"
        homepage_str = f", homepage={self.homepage}" if self.homepage else ""
        return f"Agent(id={self.id}, name='{primary_name}'{homepage_str})"

    def __eq__(self, other):
        """
        Determine equality between two Agent instances.

        Args:
            other (Agent): The other object to compare against.

        Returns:
            bool: True if both objects represent the same agent, False otherwise.
        """
        '''
        if not isinstance(other, Agent):
            return NotImplemented
        
        return (
            self.id == other.id and
            self.identifiers == other.identifiers and
            self.names == other.names and
            self.homepage == other.homepage and
            self.openid == other.openid and
            self.accounts == other.accounts and
            self.emails == other.emails and
            self.phones == other.phones and
            self.addresses == other.addresses and
            self.person == other.person and
            self.attribution == other.attribution and
            self.uri == other.uri
        )
        '''
        #TODO clean this up
        self_names = {n.value for n in self.names if hasattr(n, "value")}
        other_names = {n.value for n in other.names if hasattr(n, "value")}
        if self_names & other_names:  # intersection not empty
            return True

        return False
