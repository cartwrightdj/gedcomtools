from enum import Enum
from typing import List,Optional, Union

"""
======================================================================
 Project: Gedcom-X
 File:    Name.py
 Author:  David J. Cartwright
 Purpose: Python Object representation of GedcomX Name, NameType, NameForm, NamePart Types

 Created: 2025-08-25
 Updated:
   - 2025-08-31: _as_dict_ to only create entries in dict for fields that hold data
   - 2025-09-03: _from_json_ refactor
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
#======================================================================
from .attribution import Attribution
from .conclusion import Conclusion, ConfidenceLevel
from .date import Date
from .document import Document
from .note import Note
from .resource import Resource
from .schemas import extensible
from .source_reference import SourceReference
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================


class NameType(Enum):
    BirthName = "http://gedcomx.org/BirthName"
    MarriedName = "http://gedcomx.org/MarriedName"
    AlsoKnownAs = "http://gedcomx.org/AlsoKnownAs"
    Nickname = "http://gedcomx.org/Nickname"
    AdoptiveName = "http://gedcomx.org/AdoptiveName"
    FormalName = "http://gedcomx.org/FormalName"
    ReligiousName = "http://gedcomx.org/ReligiousName"
    Other = "other"
    
    @property
    def description(self):
        descriptions = {
            NameType.BirthName: "Name given at birth.",
            NameType.MarriedName: "Name accepted at marriage.",
            NameType.AlsoKnownAs: "\"Also known as\" name.",
            NameType.Nickname: "Nickname.",
            NameType.AdoptiveName: "Name given at adoption.",
            NameType.FormalName: "A formal name, usually given to distinguish it from a name more commonly used.",
            NameType.ReligiousName: "A name given at a religious rite or ceremony."
        }
        return descriptions.get(self, "No description available.")

class NamePartQualifier(Enum):
    Title = "http://gedcomx.org/Title"
    Primary = "http://gedcomx.org/Primary"
    Secondary = "http://gedcomx.org/Secondary"
    Middle = "http://gedcomx.org/Middle"
    Familiar = "http://gedcomx.org/Familiar"
    Religious = "http://gedcomx.org/Religious"
    Family = "http://gedcomx.org/Family"
    Maiden = "http://gedcomx.org/Maiden"
    Patronymic = "http://gedcomx.org/Patronymic"
    Matronymic = "http://gedcomx.org/Matronymic"
    Geographic = "http://gedcomx.org/Geographic"
    Occupational = "http://gedcomx.org/Occupational"
    Characteristic = "http://gedcomx.org/Characteristic"
    Postnom = "http://gedcomx.org/Postnom"
    Particle = "http://gedcomx.org/Particle"
    RootName = "http://gedcomx.org/RootName"
    
    @property
    def description(self):
        descriptions = {
            NamePartQualifier.Title: "A designation for honorifics (e.g., Dr., Rev., His Majesty, Haji), ranks (e.g., Colonel, General), positions (e.g., Count, Chief), or other titles (e.g., PhD, MD). Name part qualifiers of type Title SHOULD NOT provide a value.",
            NamePartQualifier.Primary: "A designation for the most prominent name among names of that type (e.g., the primary given name). Name part qualifiers of type Primary SHOULD NOT provide a value.",
            NamePartQualifier.Secondary: "A designation for a name that is not primary in its importance among names of that type. Name part qualifiers of type Secondary SHOULD NOT provide a value.",
            NamePartQualifier.Middle: "Useful for cultures designating a middle name distinct from a given name and surname. Name part qualifiers of type Middle SHOULD NOT provide a value.",
            NamePartQualifier.Familiar: "A designation for one's familiar name. Name part qualifiers of type Familiar SHOULD NOT provide a value.",
            NamePartQualifier.Religious: "A name given for religious purposes. Name part qualifiers of type Religious SHOULD NOT provide a value.",
            NamePartQualifier.Family: "A name that associates a person with a group, such as a clan, tribe, or patriarchal hierarchy. Name part qualifiers of type Family SHOULD NOT provide a value.",
            NamePartQualifier.Maiden: "Original surname retained by women after adopting a new surname upon marriage. Name part qualifiers of type Maiden SHOULD NOT provide a value.",
            NamePartQualifier.Patronymic: "A name derived from a father or paternal ancestor. Name part qualifiers of type Patronymic SHOULD NOT provide a value.",
            NamePartQualifier.Matronymic: "A name derived from a mother or maternal ancestor. Name part qualifiers of type Matronymic SHOULD NOT provide a value.",
            NamePartQualifier.Geographic: "A name derived from associated geography. Name part qualifiers of type Geographic SHOULD NOT provide a value.",
            NamePartQualifier.Occupational: "A name derived from one's occupation. Name part qualifiers of type Occupational SHOULD NOT provide a value.",
            NamePartQualifier.Characteristic: "A name derived from a characteristic. Name part qualifiers of type Characteristic SHOULD NOT provide a value.",
            NamePartQualifier.Postnom: "A name mandated by law for populations in specific regions. Name part qualifiers of type Postnom SHOULD NOT provide a value.",
            NamePartQualifier.Particle: "A grammatical designation for articles, prepositions, conjunctions, and other words used as name parts. Name part qualifiers of type Particle SHOULD NOT provide a value.",
            NamePartQualifier.RootName: "The 'root' of a name part, as distinguished from prefixes or suffixes (e.g., the root of 'Wilkówna' is 'Wilk'). A RootName qualifier MUST provide a value property."
        }
        return descriptions.get(self, "No description available.")

class NamePartType(Enum):
    Prefix = "http://gedcomx.org/Prefix"
    Suffix = "http://gedcomx.org/Suffix"
    Given = "http://gedcomx.org/Given"
    Surname = "http://gedcomx.org/Surname"
    
    @property
    def description(self):
        descriptions = {
            NamePartType.Prefix: "A name prefix.",
            NamePartType.Suffix: "A name suffix.",
            NamePartType.Given: "A given name.",
            NamePartType.Surname: "A surname."
        }
        return descriptions.get(self, "No description available.")

@extensible()    
class NamePart:
    """Used to model a portion of a full name
        including the terms that make up that portion. Some name parts may have qualifiers
        to provide additional semantic meaning to the name part (e.g., "given name" or "surname").

    Args:
        type (NamePartType | None): Classification of this component of the name
            (e.g., ``Given``, ``Surname``, ``Prefix``, ``Suffix``, ``Title``, ``Particle``).
        value (str): The textual value for this part, without surrounding
            punctuation (e.g., ``"John"``, ``"van"``, ``"III"``).
        qualifiers (list[NamePartQualifier] | None): Optional qualifiers that refine
            the meaning or usage of this part (e.g., language/script variants, initials).

    Examples:
        >>> from gedcomx.Name import *
        >>> typ = NamePartType.Given
        >>> given = "Moses"
        >>> q = NamePartQualifier.Primary
        >>> name = NamePart(type=typ,value=given,qualifiers=[q])
        >>> print(name)
        NamePart(type=Given, value='Moses', qualifiers=1)

    """
    identifier = 'http://gedcomx.org/v1/NamePart'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
                 type: Optional[NamePartType] = None,
                 value: Optional[str] = None,
                 qualifiers: Optional[List[NamePartQualifier]] = None) -> None:
        self.type = type
        self.value = value
        self.qualifiers = qualifiers if qualifiers else []
    
    @property
    def to_dict(self):
        from .serialization import Serialization
        type_as_dict = {}
        if self.type:
            type_as_dict['type'] = self.type.value
        if self.value:
            type_as_dict['value'] = self.value
        if self.qualifiers:
            type_as_dict['qualifiers'] = [q.value for q in self.qualifiers]
        return type_as_dict if type_as_dict != {} else None
    
    @classmethod
    def from_json(cls, data: dict, context=None) -> "NamePart":
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__}._from_json_ expected dict, got {type(data)}")

        name_part = {}

        # Enum / type
        if (typ := data.get("type")) is not None:
            name_part["type"] = NamePartType(typ)

        # String value
        if (val := data.get("value")) is not None:
            name_part["value"] = val

        # List of qualifiers
        if (quals := data.get("qualifiers")) is not None:
            name_part["qualifiers"] = [NamePartQualifier(q) for q in quals]

        return cls(**name_part)

    def __eq__(self, other):
        if not isinstance(other, NamePart):
            return NotImplemented
        return (self.type == other.type and
                self.value == other.value and
                self.qualifiers == other.qualifiers)    

    def __str__(self) -> str:
        parts = []
        if self.type is not None:
            parts.append(f"type={getattr(self.type, 'name', str(self.type))}")
        if self.value is not None:
            parts.append(f"value={self.value!r}")
        if self.qualifiers:
            parts.append(f"qualifiers={len(self.qualifiers)}")
        return f"NamePart({', '.join(parts)})" if parts else "NamePart()"

    def __repr__(self) -> str:
        if self.type is not None:
            tcls = self.type.__class__.__name__
            tname = getattr(self.type, "name", str(self.type))
            tval = getattr(self.type, "value", self.type)
            type_repr = f"<{tcls}.{tname}: {tval!r}>"
        else:
            type_repr = "None"
        return (
            f"{self.__class__.__name__}("
            f"type={type_repr}, "
            f"value={self.value!r}, "
            f"qualifiers={self.qualifiers!r})"
        )

@extensible()
class NameForm:
    """A representation of a name (a "name form") 
        within a given cultural context, such as a given language and script.
        As names are captured (both in records or in applications), the terms
        in the name are sometimes classified by type. For example, a certificate
        of death might prompt for **"given name(s)"** and **"surname"**. The parts
        list can be used to represent the terms in the name that have been classified.

    Args:
        lang (str | None): BCP-47 language tag for this name form (e.g., "en").
        fullText (str | None): The full, unparsed name string as written in the source.
            If provided, the name SHOULD be rendered as it would normally be spoken in
            the applicable cultural context.
        parts (list[NamePart] | None): Ordered structured components of the name
            (e.g., Given, Surname). If provided, ``fullText`` may be omitted. If
            provided, the list SHOULD be ordered such that the parts are in the order
            they would normally be spoken in the applicable cultural context.

    """
    identifier = 'http://gedcomx.org/v1/NameForm'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, lang: Optional[str] = None,
                 fullText: Optional[str] = None,
                 parts: Optional[List[NamePart]] = None) -> None:
        
        self.lang = lang
        self.fullText = fullText
        self.parts = parts if parts else []
    
    @property
    def to_dict(self):
        from .serialization import Serialization
        type_as_dict = {}
        if self.lang:
            type_as_dict['lang'] = self.lang
        if self.fullText:
            type_as_dict['fullText'] = self.fullText
        if self.parts:
            type_as_dict['parts'] = [part.to_dict for part in self.parts if part is not None]
        return type_as_dict if type_as_dict != {} else None
        return Serialization.serialize_dict(type_as_dict)
    
    @classmethod
    def from_json(cls, data: dict, context=None) -> "NameForm":
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__}._from_json_ expected dict, got {type(data)}")

        name_form = {}

        # Scalars
        if (lang := data.get("lang")) is not None:
            name_form["lang"] = lang

        if (full := data.get("fullText")) is not None:
            name_form["fullText"] = full

        # List of parts
        if (parts := data.get("parts")) is not None:
            name_form["parts"] = [NamePart.from_json(p, context) for p in parts if p]

        return cls(**name_form)
    
    def _fulltext_parts(self):
        pass

@extensible()
class Name(Conclusion):
    """**Defines a name of a person.**

            A Name is intended to represent a single variant of a person's name. 
            This means that nicknames, spelling variations, or other names 
            (often distinguishable by a name type) should be modeled with 
            separate instances of Name.

    .. admonition:: Advanced details
        :class: toggle
    
        The name forms of a name contain alternate representations of the name.
        A Name MUST contain at least one name form, presumably a representation
        of the name that is considered proper and well formed in the person's native,
        historical cultural context. Other name forms MAY be included, which can be
        used to represent this name in contexts where the native name form is not easily
        recognized and interpreted. Alternate forms are more likely in situations where
        conclusions are being analyzed across cultural context boundaries that have both
        language and writing script differences.
        

    Attributes:
        type (Optional[:class:`~gedcomx.NameType`]): Classification of the name
            (e.g., BirthName, AlsoKnownAs).
        nameForms (List[:class:`~gedcomx.NameForm`]): One or more structured
            representations of the name (full text and parts).
        date (Optional[:class:`~gedcomx.Date`]): Date context for this name
            (e.g., when the name was used or recorded).
    """
    identifier = 'http://gedcomx.org/v1/Name'
    version = 'http://gedcomx.org/conceptual-model/v1'

    @staticmethod
    def simple(text: str):
        """
        Takes a string and returns a GedcomX Name Object
        """
        if text:
            text = text.replace("/","")
            parts = text.rsplit(' ', 1)
        
            # Assign val1 and val2 based on the split
            given = parts[0] if len(parts) > 1 else ""
            surname = parts[1] if len(parts) > 1 else parts[0]
            
            # Remove any '/' characters from both val1 and val2
            #given = given.replace('/', '')
            #surname = surname.replace('/', '')

            parts =[]
            if given: parts.append(NamePart(type = NamePartType.Given, value=given)) 
            if surname: parts.append(NamePart(type = NamePartType.Surname, value=surname))

            name_form = NameForm(fullText=text)
            name = Name(type=NameType.BirthName,nameForms=[name_form])
            
        else:
            name = Name()
        return name

    def __init__(self, id: Optional[str] = None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Union[Resource,Document]] = None,
                 notes: Optional[List[Note]] = None,
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,
                 type: Optional[NameType] = None,
                 nameForms: Optional[List[NameForm]]= None,
                 date: Optional[Date] = None,):
                 #links: Optional[_rsLinks] = None) -> None:
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution)
        self.type = type
        self.nameForms = nameForms if nameForms else []
        self.date = date
        self.id = id if id else None # no need for id
    
    def _add_name_part(self, namepart: NamePart):
        if namepart and isinstance(namepart, NamePart):
            for current_namepart in self.nameForms[0].parts:
                if namepart == current_namepart:
                    return False
            self.nameForms[0].parts.append(namepart)
    
    @property
    def to_dict(self):
        type_as_dict = super().to_dict or {}
        if self.type:
            type_as_dict['type'] = getattr(self.type, 'value', self.type)
        if self.nameForms:
            type_as_dict['nameForms'] = [nf.to_dict for nf in self.nameForms if nf]
        if self.date:
            type_as_dict['date'] = self.date.to_dict
        
        return type_as_dict if type_as_dict != {} else None

    
    @classmethod
    def from_json(cls, data: dict,context = None) -> "Name":
        """Build a Name from JSON-like dict."""
        name = Conclusion.dict_from_json(data)
        
        # Enum
        if (typ := data.get("type")) is not None:
            name["type"] = NameType(typ)

        # List
        if (forms := data.get("nameForms")) is not None:
            name["nameForms"] = [NameForm.from_json(f, context) for f in forms]

        # Object
        if (date := data.get("date")) is not None:
            name["date"] = Date.from_json(date, context)
        
        return cls(**name)
    
    def __str__(self) -> str:
        """Return a human-readable string for the Name-like object."""
        return f"Name(id={self.id}, type={self.type}, forms={len(self.nameForms)}, date={self.date})"

    def __repr__(self) -> str:
        """Return an unambiguous string representation of the Name-like object."""
        return (
            f"{self.__class__.__name__}("
            f"id={self.id!r}, "
            f"lang={self.lang!r}, "
            f"sources={self.sources!r}, "
            f"analysis={self.analysis!r}, "
            f"notes={self.notes!r}, "
            f"confidence={self.confidence!r}, "
            f"attribution={self.attribution!r}, "
            f"type={self.type!r}, "
            f"nameForms={self.nameForms!r}, "
            f"date={self.date!r})"
    )

class QuickName():
    def __new__(cls,name: str) -> Name:
        obj = Name(nameForms=[NameForm(fullText=name)])
        return obj
    
def ensure_list(val):
    if val is None:
        return []
    return val if isinstance(val, list) else [val]
    







