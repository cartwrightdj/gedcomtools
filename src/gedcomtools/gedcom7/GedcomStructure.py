from __future__ import annotations

from typing import Dict, Any
import warnings
from . import specification as g7

from typing import Dict, List,Optional,Any


gedcom_top_level_terms = ['https://gedcom.io/terms/v7/CONT',
                          'https://gedcom.io/terms/v7/record-FAM',
                          'https://gedcom.io/terms/v7/record-INDI',
                          'https://gedcom.io/terms/v7/record-SNOTE',
                          'https://gedcom.io/terms/v7/record-SUBM',
                          'https://gedcom.io/terms/v7/TRLR',
                          'https://gedcom.io/terms/v7/HEAD',
                          'https://gedcom.io/terms/v7/record-OBJE',
                          'https://gedcom.io/terms/v7/record-REPO',
                          'https://gedcom.io/terms/v7/record-SOUR']


class GedcomStructure:
    version = 'v7'

    def __init__(
        self,
        *,
        level: int | None = None,
        xref: str | None = None,
        tag: str | None = None,
        pointer: bool | None = None,
        text: str | None = None,
        parent: GedcomStructure | None = None,
        line_num: int | None = None
    ) -> None:
        """Create a GEDCOM structure node.

        Args:
            level: GEDCOM line level (0..n).
            xref: Optional cross-reference id (e.g., '@I1@').
            tag: GEDCOM tag (e.g., 'INDI', 'NAME').
            pointer: True if this line is a pointer, False if not, None if unknown.
            text: Literal text payload for this line.
            parent: Parent node in the structure tree, if any.
        """
        self.level = level
        self.xref = xref
        self.tag = tag
        self.pointer = pointer
        self.text = text
        self.parent = parent
        self.value = text
        self.pointer = pointer if pointer else False
        self.line_num = line_num
        
        if self.level and self.level > 0 and text and text.startswith('@') and text.endswith('@'):
            self.pointer = True
            self.xref = text
        
        self.parent: GedcomStructure | None = parent if parent else None
        if self.parent and isinstance(self.parent, GedcomStructure):
            parent.subtructures.append(self)

        self.extension = False if not tag else True if tag.startswith('_') else False 
        self.uri = g7.match_uri(tag,self.parent) 
        self.label = g7.get_label(self.uri)
        
        self.subtructures = []
        

    def _as_dict_(self):
        as_dict =  {}
        as_dict['level'] = self.level
        if self.xref: as_dict['xref'] = self.xref
        as_dict['tag'] = self.tag
        if self.value: as_dict['value'] = self.value
        if self.subtructures: as_dict['substructures'] = [substructure._as_dict_() for substructure in self.subtructures]
        return {g7.get_label(self.uri):as_dict}
       
    def __repr__(self):
        return (
            "GedcomStructure("
            f"level: {self.level} tag={self.tag:<6} ({self.label}), {'(Ext)' if self.extension else ''} xref:{self.xref}  pointer={self.pointer}, text='{self.value}',  "
            f"uri={self.uri} subStructures: {len(self.subtructures)}"
        )
    
    def __getitem__(self,index) -> List['GedcomStructure']:
        return [s for s in self.subtructures if s.tag == index]

    
    
    