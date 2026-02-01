from enum import Enum
from typing import Any, Dict, List, Optional
"""
======================================================================
 Project: Gedcom-X
 File:    document.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactored 
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .attribution import Attribution
from .conclusion import Conclusion, ConfidenceLevel
from .note import Note
from .resource import Resource
from .schemas import extensible
from .source_reference import SourceReference
from .source_description import SourceDescription, ResourceType
from ..logging_hub import hub, logging
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
#=====================================================================

@extensible(toplevel=False)
class DocumentType(Enum):
    Abstract = "http://gedcomx.org/Abstract"
    Transcription = "http://gedcomx.org/Transcription"
    Translation = "http://gedcomx.org/Translation"
    Analysis = "http://gedcomx.org/Analysis"
    
    @property
    def description(self):
        descriptions = {
            DocumentType.Abstract: "The document is an abstract of a record or document.",
            DocumentType.Transcription: "The document is a transcription of a record or document.",
            DocumentType.Translation: "The document is a translation of a record or document.",
            DocumentType.Analysis: "The document is an analysis done by a researcher; a genealogical proof statement is an example of one kind of analysis document."
        }
        return descriptions.get(self, "No description available.")

class TextType(Enum):
    plain = 'plain'
    xhtml = 'xhtml'

class DocumentParsingContainer:
    def __init__(self,source: SourceDescription) -> None:
        self.sourceDescription = source
        self.isFile = False

    def _init_file(self):
        self._isFile = True
    
    def _set_form(self,form: str):
        if form:
            self.sourceDescription.mediaType = form
    
    def _set_type(self,type: str):
        if type == 'image':
            self.sourceDescription.resourceType = ResourceType.DigitalArtifact
        else:
            self.sourceDescription.resourceType = ResourceType.DigitalArtifact


class Document(Conclusion):
    identifier = 'http://gedcomx.org/v1/Document'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, id: Optional[str] = None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Resource] = None,
                 notes: Optional[List[Note]] = None,
                 confidence: Optional[ConfidenceLevel] = None, # ConfidenceLevel
                 attribution: Optional[Attribution] = None,
                 type: Optional[DocumentType] = None,
                 extracted: Optional[bool] = None, # Default to False
                 textType: Optional[TextType] = None,
                 text: Optional[str] = None,
                 ) -> None:
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution)
        self.type = type
        self.extracted = extracted
        self.textType = textType
        self.text = text
        self.__parsing_container = DocumentParsingContainer(self)
    
    def _get_dpc(self):
        return self.__parsing_container
