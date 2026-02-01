from typing import Optional, Union

"""
======================================================================
 Project: Gedcom-X
 File:    Resource.py
 Author:  David J. Cartwright
 Purpose: References TopLevel Types for Serialization

 Created: 2025-08-25
 Updated:
   - 2025-08-31: working on target=Resource and deserialization issues
   - 2025-09-03: _from_json_ refactor, arguments changed
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""

from .uri import URI
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


@extensible()    
class Resource:
    """
    Class used to track and resolve URIs and references between datastores.

    Parameters
    ----------
    
    Raises
    ------
    ValueError
        If `id` is not a valid UUID.
    """
    # TODO, Deal with a resouce being passed, as it may be unresolved.
    #def __init__(self,resource: Union[URI, None] = None,resourceId: str | None = None, target: object = None) -> None:
    def __init__(self,resource: Union[URI, None] = None) -> None:
        
        #if (resource is None) and (target is None): #TODO
        #    raise ValueError('Resource object must point to something.')

        self.resource = resource
        self.__id = None
        self.__type = None
        self.__resolved = False
        self.__remote: bool | None = None    # is the resource pointed to persitent on a remote datastore?
        self.__resourceId = None
        self.__target = None

        '''
        if target:
            if isinstance(target,Resource):
                self.resource = target.resource
                self.resourceId = target.resourceId
                self.target = target.target
            elif isinstance(target,URI):
                if hub.logEnabled: log.debug(f"Making a 'Resource' from '{type(target).__name__}': {target.value} ")
                assert False
            else:
                if hub.logEnabled: log.debug(f"Target of type: {type(target)}")
                if hasattr(target,'uri'):
                    self.resource = target.uri
                else:
                    self.resourceId = URI(fragment=target.id)
                    self.resourceId = target.id
            if hub.logEnabled: log.debug(f"Resource '{self.value} ")
        '''

    @property
    def uri(self):
        return self.resource
    
    @property
    def value(self):
        res_dict = {}
        if self.resource: res_dict['resource'] = self.resource
        #if self.resourceId: res_dict['resourceId'] = self.resourceId
        return res_dict if res_dict != {} else None
    
    @property
    def _as_dict_(self):
        raise NotImplemented
    
    @property
    def _target(self):
        return self.__target
    
    @_target.setter
    def _target(self,target):
        self.__target = target

    @classmethod
    def _of_object(cls, target):
        if isinstance(target,Resource):
            resource = target.resource
            target = target._target
        elif isinstance(target,URI):
            if hub.logEnabled: log.debug(f"Making a 'Resource' from '{type(target).__name__}': {target.value} ")
            assert False
        else:
            if hub.logEnabled: log.debug(f"Target of type: {type(target)}")
            if hasattr(target,'_uri'):
                resource = target._uri
            else:
                resource = URI(fragment=target.id)
        if hub.logEnabled: log.debug(f"Resource '{resource} ")
        return Resource(resource=resource)

    @classmethod
    def _from_json_(cls, data: dict, context=None) -> "Resource":
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__}._from_json_ expected dict, got {type(data)} {data}")
        resource = {}

        # Scalars
        if (res := data.get("resource")) is not None:
            resource["resource"] = res

        return cls(**resource)

    def __repr__(self) -> str:
        return f"Resource(resource={self.resource}, resourceId={self.__resourceId}, target={self.__target})"
    
    def __str__(self) -> str:
        return f"resource={self.resource}{f', resourceId={self.__resourceId}' if self.__resourceId else ''} {f', target={self.__target}' if self.__target else ''}"
    
#SCHEMA.set_resource_class(Resource)

