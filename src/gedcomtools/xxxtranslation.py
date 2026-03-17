"""
======================================================================
 Project: gedcomtools
 File:    xxxtranslation.py
 Author:  David J. Cartwright
 Purpose: Mapping table for translating GEDCOM 7 tags to Gedcom-X objects

 Created: 2025-07-01
 Updated:

======================================================================
"""
from  import *
from ..mutations import GedcomXEventOrFact
import re
'''
{'type': 'Object | Objects | Propertyof',
    'Object': 'Class',
    'Objects': ['Class',...],
    'Propertyof': 'Class',
    'Args': {'argname':'value|rTextValue|rIntValue|rFloatValue|rBoolValue|id|resource'},
    'Assign': {'propertyname':'value|rTextValue|rIntValue|rFloatValue|rBoolValue|id|resource'},
    'Selectoe':callable
}

'''
g7toXtable = {
    "https://gedcom.io/terms/v7/ABBR": {},
    "https://gedcom.io/terms/v7/ADDR": {'type':'Object','Object':Address, 'Args':{'value':'value'},'addmethod':'add_address'},
    "https://gedcom.io/terms/v7/ADOP": {},
    "https://gedcom.io/terms/v7/ADOP-FAMC": {},
    "https://gedcom.io/terms/v7/ADR1": {'type':'Propertyof','propertyof':Address,'assign':{'street':'value'}},
    "https://gedcom.io/terms/v7/ADR2": {'type':'Propertyof','propertyof':Address,'assign':{'street2':'value'}},
    "https://gedcom.io/terms/v7/ADR3": {'type':'Propertyof','propertyof':Address,'assign':{'street3':'value'}},
    "https://gedcom.io/terms/v7/AGE": {},
    "https://gedcom.io/terms/v7/AGNC": {},
    "https://gedcom.io/terms/v7/ALIA": {},
    "https://gedcom.io/terms/v7/ANCI": {},
    "https://gedcom.io/terms/v7/ANUL": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/ASSO": {},
    "https://gedcom.io/terms/v7/AUTH": {},
    "https://gedcom.io/terms/v7/BAPL": {},
    "https://gedcom.io/terms/v7/BAPM": {},
    "https://gedcom.io/terms/v7/BARM": {},
    "https://gedcom.io/terms/v7/BASM": {},
    "https://gedcom.io/terms/v7/BIRT": {},
    "https://gedcom.io/terms/v7/BLES": {},
    "https://gedcom.io/terms/v7/BURI": {},
    "https://gedcom.io/terms/v7/CALN": {},
    "https://gedcom.io/terms/v7/CAST": {},
    "https://gedcom.io/terms/v7/CAUS": {},
    "https://gedcom.io/terms/v7/CENS": {},
    "https://gedcom.io/terms/v7/CHAN": {},
    "https://gedcom.io/terms/v7/CHIL": {},
    "https://gedcom.io/terms/v7/CHR": {},
    "https://gedcom.io/terms/v7/CHRA": {},
    "https://gedcom.io/terms/v7/CITY": {'type':'Propertyof','propertyof':Address,'assign':{'city':'value'}},
    "https://gedcom.io/terms/v7/CONF": {},
    "https://gedcom.io/terms/v7/CONL": {},
    "https://gedcom.io/terms/v7/CONT": {},
    "https://gedcom.io/terms/v7/COPR": {},
    "https://gedcom.io/terms/v7/CORP": {},
    "https://gedcom.io/terms/v7/CREA": {},
    "https://gedcom.io/terms/v7/CREM": {},
    "https://gedcom.io/terms/v7/CROP": {},
    "https://gedcom.io/terms/v7/CTRY": {'type':'Propertyof','propertyof':Address,'assign':{'country':'value'}},
    "https://gedcom.io/terms/v7/DATA": {},
    "https://gedcom.io/terms/v7/DATA-EVEN": {},
    "https://gedcom.io/terms/v7/DATA-EVEN-DATE": {},
    "https://gedcom.io/terms/v7/DATE": {},
    "https://gedcom.io/terms/v7/DATE-exact": {},
    "https://gedcom.io/terms/v7/DEAT": {},
    "https://gedcom.io/terms/v7/DESI": {},
    "https://gedcom.io/terms/v7/DEST": {},
    "https://gedcom.io/terms/v7/DIV": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/DIVF": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/DSCR": {},
    "https://gedcom.io/terms/v7/EDUC": {},
    "https://gedcom.io/terms/v7/EMAIL": {},
    "https://gedcom.io/terms/v7/EMIG": {},
    "https://gedcom.io/terms/v7/ENDL": {},
    "https://gedcom.io/terms/v7/ENGA": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/EVEN": {},
    "https://gedcom.io/terms/v7/EXID": {},
    "https://gedcom.io/terms/v7/EXID-TYPE": {},
    "https://gedcom.io/terms/v7/FACT": {},
    "https://gedcom.io/terms/v7/FAM": {'type':'Object','Object':Relationship,'Args':{'id':'xref'},'stackentry':['lastrelationship','lastrelationshipdata']},
    "https://gedcom.io/terms/v7/FAM-CENS": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/FAM-EVEN": {},
    "https://gedcom.io/terms/v7/FAM-FACT": {},
    "https://gedcom.io/terms/v7/FAM-HUSB": {'type':'Object','Object':Resource,'Args':{'Id':'xref'}},
    "https://gedcom.io/terms/v7/FAM-NCHI": {},
    "https://gedcom.io/terms/v7/FAM-RESI": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/FAM-WIFE": {'type':'Object','Object':Resource,'Args':{'Id':'xref'}},
    "https://gedcom.io/terms/v7/FAMC": {},
    "https://gedcom.io/terms/v7/FAMC-ADOP": {},
    "https://gedcom.io/terms/v7/FAMC-STAT": {},
    "https://gedcom.io/terms/v7/FAMS": {},
    "https://gedcom.io/terms/v7/FAX": {},
    "https://gedcom.io/terms/v7/FCOM": {},
    "https://gedcom.io/terms/v7/FILE": {},
    "https://gedcom.io/terms/v7/FILE-TRAN": {},
    "https://gedcom.io/terms/v7/FORM": {},
    "https://gedcom.io/terms/v7/GEDC": {},
    "https://gedcom.io/terms/v7/GEDC-VERS": {},
    "https://gedcom.io/terms/v7/GIVN": {},
    "https://gedcom.io/terms/v7/GRAD": {},
    "https://gedcom.io/terms/v7/HEAD": {},
    "https://gedcom.io/terms/v7/HEAD-DATE": {},
    "https://gedcom.io/terms/v7/HEAD-LANG": {},
    "https://gedcom.io/terms/v7/HEAD-PLAC": {},
    "https://gedcom.io/terms/v7/HEAD-PLAC-FORM": {},
    "https://gedcom.io/terms/v7/HEAD-SOUR": {},
    "https://gedcom.io/terms/v7/HEAD-SOUR-DATA": {},
    "https://gedcom.io/terms/v7/HEIGHT": {},
    "https://gedcom.io/terms/v7/HUSB": {},
    "https://gedcom.io/terms/v7/IDNO": {},
    "https://gedcom.io/terms/v7/IMMI": {},
    "https://gedcom.io/terms/v7/INDI": {},
    "https://gedcom.io/terms/v7/INDI-CENS": {},
    "https://gedcom.io/terms/v7/INDI-EVEN": {},
    "https://gedcom.io/terms/v7/INDI-FACT": {},
    "https://gedcom.io/terms/v7/INDI-FAMC": {},
    "https://gedcom.io/terms/v7/INDI-NAME": {},
    "https://gedcom.io/terms/v7/INDI-NCHI": {},
    "https://gedcom.io/terms/v7/INDI-RELI": {},
    "https://gedcom.io/terms/v7/INDI-RESI": {},
    "https://gedcom.io/terms/v7/INDI-TITL": {},
    "https://gedcom.io/terms/v7/INIL": {},
    "https://gedcom.io/terms/v7/LANG": {},
    "https://gedcom.io/terms/v7/LATI": {},
    "https://gedcom.io/terms/v7/LEFT": {},
    "https://gedcom.io/terms/v7/LONG": {},
    "https://gedcom.io/terms/v7/MAP": {},
    "https://gedcom.io/terms/v7/MARB": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/MARC": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/MARL": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/MARR": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/MARS": {'type':'Mutation','Object':GedcomXEventOrFact,'Args':{'value':'value'},'propertyof':[Relationship],'method':'add_fact'},
    "https://gedcom.io/terms/v7/MEDI": {},
    "https://gedcom.io/terms/v7/MIME": {},
    "https://gedcom.io/terms/v7/NAME": {},
    "https://gedcom.io/terms/v7/NAME-TRAN": {},
    "https://gedcom.io/terms/v7/NAME-TYPE": {},
    "https://gedcom.io/terms/v7/NATI": {},
    "https://gedcom.io/terms/v7/NATU": {},
    "https://gedcom.io/terms/v7/NCHI": {},
    "https://gedcom.io/terms/v7/NICK": {},
    "https://gedcom.io/terms/v7/NMR": {},
    "https://gedcom.io/terms/v7/NO": {},
    "https://gedcom.io/terms/v7/NO-DATE": {},
    "https://gedcom.io/terms/v7/NOTE": {},
    "https://gedcom.io/terms/v7/NOTE-TRAN": {},
    "https://gedcom.io/terms/v7/NPFX": {},
    "https://gedcom.io/terms/v7/NSFX": {},
    "https://gedcom.io/terms/v7/OBJE": {'type':'Object','Object':SourceReference,'Args':{'Id':'xref'}},
    "https://gedcom.io/terms/v7/OCCU": {},
    "https://gedcom.io/terms/v7/ORDN": {},
    "https://gedcom.io/terms/v7/PAGE": {},
    "https://gedcom.io/terms/v7/PEDI": {},
    "https://gedcom.io/terms/v7/PHON": {},
    "https://gedcom.io/terms/v7/PHRASE": {},
    "https://gedcom.io/terms/v7/PLAC": {},
    "https://gedcom.io/terms/v7/PLAC-FORM": {},
    "https://gedcom.io/terms/v7/PLAC-TRAN": {},
    "https://gedcom.io/terms/v7/POST": {},
    "https://gedcom.io/terms/v7/PROB": {},
    "https://gedcom.io/terms/v7/PROP": {},
    "https://gedcom.io/terms/v7/PUBL": {},
    "https://gedcom.io/terms/v7/QUAY": {},
    "https://gedcom.io/terms/v7/REFN": {},
    "https://gedcom.io/terms/v7/RELI": {},
    "https://gedcom.io/terms/v7/REPO": {'type':'Object','Object':Resource,'Args':{'Id':'xref'}},
    "https://gedcom.io/terms/v7/RESI": {},
    "https://gedcom.io/terms/v7/RESN": {},
    "https://gedcom.io/terms/v7/RETI": {},
    "https://gedcom.io/terms/v7/ROLE": {},
    "https://gedcom.io/terms/v7/SCHMA": {},
    "https://gedcom.io/terms/v7/SDATE": {},
    "https://gedcom.io/terms/v7/SEX": {},
    "https://gedcom.io/terms/v7/SLGC": {},
    "https://gedcom.io/terms/v7/SLGS": {},
    "https://gedcom.io/terms/v7/SNOTE": {},
    "https://gedcom.io/terms/v7/SOUR": {},
    "https://gedcom.io/terms/v7/SOUR-DATA": {},
    "https://gedcom.io/terms/v7/SOUR-EVEN": {},
    "https://gedcom.io/terms/v7/SPFX": {},
    "https://gedcom.io/terms/v7/SSN": {},
    "https://gedcom.io/terms/v7/STAE": {'type':'Propertyof','propertyof':Address,'assign':{'stateOrProvince':'value'}},
    "https://gedcom.io/terms/v7/STAT": {},
    "https://gedcom.io/terms/v7/SUBM": {},
    "https://gedcom.io/terms/v7/SUBM-LANG": {},
    "https://gedcom.io/terms/v7/SURN": {'class':NamePart, 
                                        'args':{'type':NamePartType.Surname,'value':'rTextValue'}
                                         },
    "https://gedcom.io/terms/v7/TAG": {},
    "https://gedcom.io/terms/v7/TEMP": {},
    "https://gedcom.io/terms/v7/TEXT": {},
    "https://gedcom.io/terms/v7/TIME": {},
    "https://gedcom.io/terms/v7/TITL": {'type':'PropertyObject','Object':TextValue,'Args':{'value':'value'},'propertyof':[SourceDescription],'method':'add_title'},
    "https://gedcom.io/terms/v7/TOP": {},
    "https://gedcom.io/terms/v7/TRAN": {},
    "https://gedcom.io/terms/v7/TRLR": {},
    "https://gedcom.io/terms/v7/TYPE": {'type':'Object','Object':Note,'Args':{'text':'value'},'propertyof':[Fact],'method':'add_note'},
    "https://gedcom.io/terms/v7/UID": {},
    "https://gedcom.io/terms/v7/VERS": {},
    "https://gedcom.io/terms/v7/WIDTH": {},
    "https://gedcom.io/terms/v7/WIFE": {},
    "https://gedcom.io/terms/v7/WILL": {},
    "https://gedcom.io/terms/v7/WWW": {},
    "https://gedcom.io/terms/v7/enumset-ADOP": {},
    "https://gedcom.io/terms/v7/enumset-EVEN": {},
    "https://gedcom.io/terms/v7/enumset-EVENATTR": {},
    "https://gedcom.io/terms/v7/enumset-FAMC-STAT": {},
    "https://gedcom.io/terms/v7/enumset-MEDI": {},
    "https://gedcom.io/terms/v7/enumset-NAME-TYPE": {},
    "https://gedcom.io/terms/v7/enumset-PEDI": {},
    "https://gedcom.io/terms/v7/enumset-QUAY": {},
    "https://gedcom.io/terms/v7/enumset-RESN": {},
    "https://gedcom.io/terms/v7/enumset-ROLE": {},
    "https://gedcom.io/terms/v7/enumset-SEX": {},
    "https://gedcom.io/terms/v7/ord-STAT": {},
    "https://gedcom.io/terms/v7/record-FAM": {'type':'TopLevelObject','Object':Relationship,'Args':{'id':'xref'}},
    "https://gedcom.io/terms/v7/record-INDI": {'type':'TopLevelObject','Object':Person,'Args':{'id':'xref'}},
    "https://gedcom.io/terms/v7/record-OBJE": {'type':'TopLevelObject','Object':SourceDescription, 'Args':{'id':'xref'}},
    "https://gedcom.io/terms/v7/record-REPO": {'type':'TopLevelObject','Object':Agent,'Args':{'id':'xref'}},
    "https://gedcom.io/terms/v7/record-SNOTE": {},
    "https://gedcom.io/terms/v7/record-SOUR": {'type':'TopLevelObject','Object':SourceDescription,'Args':{'id':'xref'}},
    "https://gedcom.io/terms/v7/record-SUBM": {'type':'Object','Object':Resource,'Args':{'Id':'xref'}},
}

from .gedcom5.parser import Gedcom5x
from .gedcom5.elements import Element as Gedcom5xRecord
from .header import Header

class Translater():
    def __init__(self,gedcom: Gedcom5x) -> None:
        self.handlers = {}
        self.gedcom: Gedcom5x = gedcom
        self.gedcomx = GedcomX()
        
        self.object_stack = []
        self.object_map = {}
        self.missing_handler_count = {}

        self.translate()


    gedcom_even_to_fact = {
    # Person Fact Types
    "ADOP": FactType.Adoption,
    "CHR": FactType.AdultChristening,
    "EVEN": FactType.Amnesty,  # and other FactTypes with no direct GEDCOM tag
    "BAPM": FactType.Baptism,
    "BARM": FactType.BarMitzvah,
    "BASM": FactType.BatMitzvah,
    "BIRT": FactType.Birth,
    "BIRT, CHR": FactType.Birth,
    "BLES": FactType.Blessing,
    "BURI": FactType.Burial,
    "CAST": FactType.Caste,
    "CENS": FactType.Census,
    "CIRC": FactType.Circumcision,
    "CONF": FactType.Confirmation,
    "CREM": FactType.Cremation,
    "DEAT": FactType.Death,
    "EDUC": FactType.Education,
    "EMIG": FactType.Emigration,
    "FCOM": FactType.FirstCommunion,
    "GRAD": FactType.Graduation,
    "IMMI": FactType.Immigration,
    "MIL": FactType.MilitaryService,
    "NATI": FactType.Nationality,
    "NATU": FactType.Naturalization,
    "OCCU": FactType.Occupation,
    "ORDN": FactType.Ordination,
    "DSCR": FactType.PhysicalDescription,
    "PROB": FactType.Probate,
    "PROP": FactType.Property,
    "RELI": FactType.Religion,
    "RESI": FactType.Residence,
    "WILL": FactType.Will,

    # Couple Relationship Fact Types
    "ANUL": FactType.Annulment,
    "DIV": FactType.Divorce,
    "DIVF": FactType.DivorceFiling,
    "ENGA": FactType.Engagement,
    "MARR": FactType.Marriage,
    "MARB": FactType.MarriageBanns,
    "MARC": FactType.MarriageContract,
    "MARL": FactType.MarriageLicense,
    "SEPA": FactType.Separation,

    # Parent-Child Relationship Fact Types
    # (Note: Only ADOPTION has a direct GEDCOM tag, others are under "EVEN")
    "ADOP": FactType.AdoptiveParent
}
    
    gedcom_even_to_evnt = {
    # Person Fact Types
    "ADOP": EventType.Adoption,
    "CHR": EventType.AdultChristening,
    "BAPM": EventType.Baptism,
    "BARM": EventType.BarMitzvah,
    "BASM": EventType.BatMitzvah,
    "BIRT": EventType.Birth,
    "BIRT, CHR": EventType.Birth,
    "BLES": EventType.Blessing,
    "BURI": EventType.Burial,
    
    "CENS": EventType.Census,
    "CIRC": EventType.Circumcision,
    "CONF": EventType.Confirmation,
    "CREM": EventType.Cremation,
    "DEAT": EventType.Death,
    "EDUC": EventType.Education,
    "EMIG": EventType.Emigration,
    "FCOM": EventType.FirstCommunion,
    
    "IMMI": EventType.Immigration,
    
    "NATU": EventType.Naturalization,
    
    "ORDN": EventType.Ordination,
    

    # Couple Relationship Fact Types
    "ANUL": EventType.Annulment,
    "DIV": EventType.Divorce,
    "DIVF": EventType.DivorceFiling,
    "ENGA": EventType.Engagement,
    "MARR": EventType.Marriage
    
}
    
    @staticmethod
    def clean_str(text: str) -> str | None:
        # Regular expression to match HTML/XML tags
        if text is None or text.strip() == '':
            return None
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        return clean_text

    def translate(self):
        for n, repository in enumerate(self.gedcom.repositories):
            print(f"Parsing Repository {n}")
            self.parse_record(repository)
        print(f"Translated {len(self.gedcomx.agents)} 'REPO' records to Agents")
        for source in self.gedcom.sources:
            self.parse_record(source)
        print(f"Translated {len(self.gedcomx.sourceDescriptions)} 'SOUR' records to SourceDescription")

        for object in self.gedcom.objects:
            self.parse_record(object)
        print(f"Translated {len(self.gedcom.objects)} 'OBJE' records to SourceDescriptions")

        for individual in self.gedcom.individuals:
            self.parse_record(individual)
        print(f"Translated {len(self.gedcomx.persons)} 'INDI' records to Persons")

        for key in self.missing_handler_count:
            print(f"{key}: {self.missing_handler_count[key]}")

        

        fam_count = len(self.gedcom.families)
        for family in self.gedcom.families:
            self.handle_fam(family)
        print(f"Translated {fam_count} 'FAM' records to {len(self.gedcomx.relationships)} Relationship")
        
        print(f"Translated {len(self.gedcomx.events)} 'EVEN' records to Events")

    def find_urls(self,text: str):
        # Regular expression pattern to match URLs
        url_pattern = re.compile(r'https?://[^\s]+')
        # Find all URLs using the pattern
        urls = url_pattern.findall(text)
        return urls

    @property
    def event_type_conversion_table(self):
        return {'BIRT':EventType.Birth,
                'OBIT':FactType.Obituary}
       
    def parse_record(self,record):
                
        handler_name = 'handle_' + record.tag.lower()
        print(record.describe())
        if hasattr(self,handler_name): 
            convert_log.info(f'Parsing Record: {record.describe()}')         
            handler = getattr(self,handler_name)            
            handler(record)
        else:
            if record.tag in self.missing_handler_count:
                self.missing_handler_count[record.tag] += 1
            else:
                self.missing_handler_count[record.tag] = 1
            
            convert_log.error(f'Failed Parsing Record: {record.describe()}')
        for sub_record in record.sub_records():
            self.parse_record(sub_record)
    
    def handle__apid(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceReference):
            self.object_map[record.level-1].description.add_identifier(Identifier(value=URI.from_url('APID://' + record.value)))
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            self.object_map[record.level-1].add_identifier(Identifier(value=URI.from_url('APID://' + record.value)))
        else:
            raise ValueError(f"Could not handle '_APID' tag in record {record.describe()}, last stack object {type(self.object_map[record.level-1])}")

    def handle__meta(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            gxobject = Note(text=Translater.clean_str(record.value))
            self.object_map[record.level-1].add_note(gxobject)
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise ValueError(f"Could not handle 'WWW' tag in record {record.describe()}, last stack object {self.object_map[record.level-1]}")

    def handle__wlnk(self, record: Gedcom5xRecord):
        return self.handle_sour(record)

    def handle_addr(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Agent):
            # TODO CHeck if URL?
            if Translater.clean_str(record.value):
                gxobject = Address(value=Translater.clean_str(record.value))
            else:
                gxobject = Address()
            self.object_map[record.level-1].address = gxobject
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise ValueError(f"I do not know how to handle an 'ADDR' tag for a {type(self.object_map[record.level-1])}")
    
    def handle_adr1(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            if Translater.clean_str(record.value):
                self.object_map[record.level-1].street = Translater.clean_str(record.value)        
        else:
            raise ValueError(f"I do not know how to handle an 'ADR1' tag for a {type(self.object_map[record.level-1])}")
    
    def handle_adr2(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            if Translater.clean_str(record.value):
                self.object_map[record.level-1].street2 = Translater.clean_str(record.value)        
        else:
            raise ValueError(f"I do not know how to handle an 'ADR2' tag for a {type(self.object_map[record.level-1])}")
    
    def handle_adr3(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            if Translater.clean_str(record.value):
                self.object_map[record.level-1].street3 = Translater.clean_str(record.value)        
        else:
            raise ValueError(f"I do not know how to handle an 'ADR3' tag for a {type(self.object_map[record.level-1])}")
    
    def handle_adr4(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            if Translater.clean_str(record.value):
                self.object_map[record.level-1].street4 = Translater.clean_str(record.value)        
        else:
            raise ValueError(f"I do not know how to handle an 'ADR4' tag for a {type(self.object_map[record.level-1])}")
    
    def handle_adr5(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            if Translater.clean_str(record.value):
                self.object_map[record.level-1].street5 = Translater.clean_str(record.value)        
        else:
            raise ValueError(f"I do not know how to handle an 'ADR5' tag for a {type(self.object_map[record.level-1])}")
    
    def handle_adr6(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            if Translater.clean_str(record.value):
                self.object_map[record.level-1].street5 = Translater.clean_str(record.value)        
        else:
            raise ValueError(f"I do not know how to handle an 'ADR6' tag for a {type(self.object_map[record.level-1])}")
        
    def handle_phon(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Agent):
            if Translater.clean_str(record.value):
                self.object_map[record.level-1].phones.append(Translater.clean_str(record.value))        
        else:
            raise ValueError(f"I do not know how to handle an '{record.tag}' tag for a {type(self.object_map[record.level-1])}")
    
    def handle_email(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Agent):
            if Translater.clean_str(record.value):
                self.object_map[record.level-1].emails.append(Translater.clean_str(record.value))        
        else:
            raise ValueError(f"I do not know how to handle an '{record.tag}' tag for a {type(self.object_map[record.level-1])}")
    
    def handle_fax(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Agent):
            if Translater.clean_str(record.value):
                self.object_map[record.level-1].emails.append('FAX:' + Translater.clean_str(record.value))        
        else:
            raise ValueError(f"I do not know how to handle an '{record.tag}' tag for a {type(self.object_map[record.level-1])}")

    def handle_adop(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Adoption)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_auth(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            if self.gedcomx.agents.by_name(record.value):
                gxobject = self.gedcomx.agents.by_name(record.value)[0]
            else:
                gxobject = Agent(names=[TextValue(record.value)])
                self.gedcomx.add_agent(gxobject)
            
            self.object_map[record.level-1].author = gxobject
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_bapm(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Baptism)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_birt(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            #gxobject = Event(type=EventType.BIRTH, roles=[EventRole(person=self.object_map[record.level-1], type=EventRoleType.Principal)])
            gxobject = Fact(type=FactType.Birth)
            #self.gedcomx.add_event(gxobject)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_buri(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Burial)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_caln(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceReference):
            self.object_map[record.level-1].description.add_identifier(Identifier(value=URI.from_url('Call Number:' + record.value)))
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            self.object_map[record.level-1].add_identifier(Identifier(value=URI.from_url('Call Number:' + record.value)))
        elif isinstance(self.object_map[record.level-1], Agent):
            pass
            # TODO Why is GEDCOM so shitty? A callnumber for a repository?
        else:
            raise ValueError(f"Could not handle 'CALN' tag in record {record.describe()}, last stack object {type(self.object_map[record.level-1])}")

    def handle_chan(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            self.object_map[record.level-1].created = Date(record.sub_record('DATE'))
        elif isinstance(self.object_map[record.level-1], Agent):
            if self.object_map[record.level-1].attribution is None:
                gxobject = Attribution()
                self.object_map[record.level-1].attribution = gxobject
                self.object_stack.append(gxobject)
                self.object_map[record.level] = gxobject
        else:
            raise ValueError()

    def handle_chr(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Christening)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_city(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            self.object_map[record.level-1].city = Translater.clean_str(record.value)
        else:
            raise ValueError(f"I do not know how to handle an 'CITY' tag for a {type(self.object_map[record.level-1])}")
        
    def handle_conc(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Note):
            gxobject = Translater.clean_str(str(record.value))
            self.object_map[record.level-1].append(gxobject)
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = str(record.value)
            self.object_map[record.level-1]._append_to_name(gxobject)
        elif isinstance(self.object_map[record.level-1], Qualifier):
            gxobject = str(record.value)
            self.object_map[record.level-2].append(gxobject)
        elif isinstance(self.object_map[record.level-1], TextValue):
            #gxobject = TextValue(value=Translater.clean_str(record.value))
            self.object_map[record.level-1]._append_to_value(record.value)
        elif isinstance(self.object_map[record.level-1], SourceReference):
            self.object_map[record.level-1].append(record.value)
        elif isinstance(self.object_map[record.level-1], Fact):
            self.object_map[record.level-1].notes[0].text += record.value
            
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_cont(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Note):
            gxobject = str("\n" + record.value if record.value else '')
            self.object_map[record.level-1].append(gxobject)
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = str("\n" + record.value if record.value else '')
        elif isinstance(self.object_map[record.level-1], Qualifier):
            gxobject = str("\n" + record.value if record.value else '')
            self.object_map[record.level-1].append(gxobject)
        elif isinstance(self.object_map[record.level-1], TextValue):
            #gxobject = TextValue(value="\n" + record.value)
            self.object_map[record.level-1]._append_to_value(record.value if record.value else '\n')
        elif isinstance(self.object_map[record.level-1], SourceReference):
            self.object_map[record.level-1].append(record.value)
        elif isinstance(self.object_map[record.level-1], Address):
            self.object_map[record.level-1]._append(record.value)
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)
    
    def handle_crea(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            self.object_map[record.level-1].created = Date(original=record.sub_record('DATE'))
            
        elif isinstance(self.object_map[record.level-1], Agent):
            if self.object_map[record.level-1].attribution is None:
                gxobject = Attribution()
                self.object_map[record.level-1].attribution = gxobject
                self.object_stack.append(gxobject)
                self.object_map[record.level] = gxobject
            else:
                convert_log.info(f"[{record.tag}] Attribution already exists for SourceDescription with id: {self.object_map[record.level-1].id}")
        else:
            raise ValueError(f"Could not handle '{record.tag}' tag in record {record.describe()}, last stack object {self.object_map[record.level-1]}")
    
    def handle_ctry(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            self.object_map[record.level-1].country = Translater.clean_str(record.value)
        else:
            raise ValueError(f"I do not know how to handle an '{record.tag}' tag for a {type(self.object_map[record.level-1])}")
     
    def handle_data(self, record: Gedcom5xRecord) -> None:
        if record.value != '' and record.value == 'None':
            assert False
        self.object_map[record.level] = self.object_map[record.level-1]

    def handle_date(self, record: Gedcom5xRecord):
        if record.parent.tag == 'PUBL': 
            self.object_map[0].published = record.value    
        elif isinstance(self.object_map[record.level-1], Event):
            self.object_map[record.level-1].date = Date(original=record.value)
        elif isinstance(self.object_map[record.level-1], Fact):
            self.object_map[record.level-1].date = Date(original=record.value)
        elif record.parent.tag == 'DATA' and isinstance(self.object_map[record.level-2], SourceReference):
            gxobject = Note(text='Date: ' + record.value)
            self.object_map[record.level-2].description.add_note(gxobject)
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            
            self.object_map[record.level-1].ctreated = record.value #TODO String to timestamp
        elif isinstance(self.object_map[record.level-1], Attribution):
            if record.parent.tag == 'CREA':
                self.object_map[record.level-1].created = record.value #TODO G7
            elif record.parent.tag == "CHAN":
                self.object_map[record.level-1].modified = record.value #TODO G7
        elif record.parent.tag in ['CREA','CHAN']:
            pass

        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_deat(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Death)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_even(self, record: Gedcom5xRecord):
        # TODO If events in a @S, check if only 1 person matches?
        if record.value and (not record.value.strip() == ''):
            values = [value.strip() for value in record.value.split(",")]
            for value in values:
                if value in Translater.gedcom_even_to_fact.keys():
                    if isinstance(self.object_map[record.level-1], Person):
                        gxobject = Fact(type=Translater.gedcom_even_to_fact[value])
                        self.object_map[record.level-1].add_fact(gxobject)

                        self.object_stack.append(gxobject)
                        self.object_map[record.level] = gxobject

                    elif isinstance(self.object_map[record.level-1], SourceDescription):
                        gxobject = Event(type=Translater.gedcom_even_to_evnt[value],sources=[self.object_map[record.level-1]])
                        self.gedcomx.add_event(gxobject)
                        self.object_stack.append(gxobject)
                        self.object_map[record.level] = gxobject
                    else:
                        convert_log.warning(f"Could not convert EVEN '{value}' for object of type {type(self.object_map[record.level-1])} in record {record.describe()}")
                        return
                        raise TagConversionError(record=record,levelstack=self.object_map)
                        assert False
                        # TODO: Fix, this. making an event to cacth subtags, why are these fact tied to a source? GEDCOM is horrible
                        gxobject = Event(type=EventType.UNKNOWN)
                        self.object_stack.append(gxobject)
                        self.object_map[record.level] = gxobject
                else:
                    raise TagConversionError(record=record,levelstack=self.object_map)

        else:
            possible_fact = FactType.guess(record.sub_record('TYPE')[0].value)
            if possible_fact:
                gxobject = Fact(type=possible_fact)
                self.object_map[record.level-1].add_fact(gxobject)

                self.object_stack.append(gxobject)
                self.object_map[record.level] = gxobject
                return
            elif EventType.guess(record.sub_record('TYPE')[0].value):
                if isinstance(self.object_map[record.level-1], Person):
                    gxobject = Event(type=EventType.guess(record.sub_record('TYPE')[0].value), roles=[EventRole(person=self.object_map[record.level-1], type=EventRoleType.Principal)])
                    self.gedcomx.add_event(gxobject)
                    self.object_stack.append(gxobject)
                    self.object_map[record.level] = gxobject
                return
            else:
                if isinstance(self.object_map[record.level-1], Person):
                    gxobject = Event(type=None, roles=[EventRole(person=self.object_map[record.level-1], type=EventRoleType.Principal)])
                    gxobject.add_note(Note(subject='Event', text=record.value))
                    self.gedcomx.add_event(gxobject)
                    self.object_stack.append(gxobject)
                    self.object_map[record.level] = gxobject
                    return
                    
                else:
                    assert False

    def handle_exid(self,record: Gedcom5xRecord):
        gxobject = Identifier(type=IdentifierType.External,value=[record.value])
        self.object_map[record.level-1].add_identifier(gxobject)

        self.object_stack.append(gxobject)
        self.object_map[record.level] = gxobject

    def handle_fam(self, record: Gedcom5xRecord) -> None:
        if record.tag != 'FAM' or record.level != 0:
            raise ValueError("Invalid record: Must be a level 0 FAM record")

        husband, wife, children = None, None, []

        husband_record = record.sub_records('HUSB')
        if husband_record:
            husband = self.gedcomx.get_person_by_id(husband_record[0].xref)

        wife_record = record.sub_records('WIFE')
        if wife_record:
            wife = self.gedcomx.get_person_by_id(wife_record[0].xref)

        children_records = record.sub_records('CHIL')
        if children_records:
            for child_record in children_records:
                child = self.gedcomx.get_person_by_id(child_record.xref)
                if child:
                    children.append(child)

        if husband:
            for child in children:
                relationship = Relationship(person1=husband, person2=child, type=RelationshipType.ParentChild)
                self.gedcomx.add_relationship(relationship)
        if wife:
            for child in children:
                relationship = Relationship(person1=wife, person2=child, type=RelationshipType.ParentChild)
                self.gedcomx.add_relationship(relationship)
        if husband and wife:
            relationship = Relationship(person1=husband, person2=wife, type=RelationshipType.Couple)
            self.gedcomx.add_relationship(relationship)

    def handle_famc(self, record: Gedcom5xRecord) -> None:
        return

    def handle_fams(self, record: Gedcom5xRecord) -> None:
        return

    def handle_file(self, record: Gedcom5xRecord):
        if record.value and record.value.strip() != '':
            #raise ValueError(f"I did not expect the 'FILE' tag to have a value: {record.value}")
            #TODO Handle files referenced here
            ...
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            ...
        self.object_map[record.level-1].resourceType = ResourceType.DigitalArtifact
           
    def handle_form(self, record: Gedcom5xRecord):
        if record.parent.tag == 'FILE' and isinstance(self.object_map[record.level-2], SourceDescription):
            if record.value and record.value.strip() != '':
                mime_type, _ = mimetypes.guess_type('placehold.' + record.value)
                if mime_type:
                    self.object_map[record.level-2].mediaType = mime_type
                else:
                    print(f"Could not determing mime type from {record.value}")
        elif isinstance(self.object_map[record.level-1], PlaceDescription):
            self.object_map[record.level-1].names.append(TextValue(value=record.value))
        elif record.parent.tag == 'TRAN':
            pass #TODO
        else:
            convert_log.error(f"raise TagConversionError(record=record,levelstack=self.object_map")

    def handle_givn(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Name):
            given_name = NamePart(value=record.value, type=NamePartType.Given)
            self.object_map[record.level-1]._add_name_part(given_name)
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_head(self,record: Gedcom5xRecord):
        header = Header()
        self.gedcomx.header = header
        self.object_stack.append(header)
        self.object_map[record.level] = header


    def handle_indi(self, record: Gedcom5xRecord):
        person = Person(id=record.xref.replace('@',''))
        self.gedcomx.add_person(person)
        self.object_stack.append(person)
        self.object_map[record.level] = person

    def handle_immi(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Immigration)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_marr(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Marriage)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_name(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Name.simple(record.value)
            #gxobject = Name(nameForms=[NameForm(fullText=record.value)], type=NameType.BirthName)
            self.object_map[record.level-1].add_name(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = TextValue(value=record.value)
            self.object_map[record.level-1].add_name(gxobject)
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_note(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            gxobject = Note(text=Translater.clean_str(record.value))
            self.object_map[record.level-1].add_note(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], SourceReference):
            gxobject = Note(text=Translater.clean_str(record.value))
            self.object_map[record.level-1].description.add_note(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Conclusion):
            gxobject = Note(text=record.value)
            self.object_map[record.level-1].add_note(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = Note(text=record.value)
            self.object_map[record.level-1].add_note(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Attribution):
            if self.object_map[record.level-1].changeMessage is None:
                self.object_map[record.level-1].changeMessage = record.value
            else:
                self.object_map[record.level-1].changeMessage = self.object_map[record.level-1].changeMessage + '' + record.value
        elif isinstance(self.object_map[record.level-1], Note):
            gxobject = Note(text=Translater.clean_str(record.value))
            self.object_map[record.level-2].add_note(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject

        else:
            raise ValueError(f"Could not handle 'NOTE' tag in record {record.describe()}, last stack object {type(self.object_map[record.level-1])}")
            assert False

    def handle_nsfx(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Name):
            surname = NamePart(value=record.value, type=NamePartType.Suffix)
            self.object_map[record.level-1]._add_name_part(surname)
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_occu(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Occupation)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_obje(self, record: Gedcom5xRecord):
        self.handle_sour(record)

    def handle_page(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceReference):
            self.object_map[record.level-1].descriptionId = record.value
            self.object_map[record.level-1].add_qualifier(KnownSourceReference(name=str(KnownSourceReference.Page),value=record.value))
            
            #self.object_stack.append(gxobject)
            #self.object_map[record.level] = gxobject
            self.object_map[record.level] = self.object_map[record.level-1]
        else:
            raise ValueError(f"Could not handle 'PAGE' tag in record {record.describe()}, last stack object {self.object_map[record.level-1]}")

    def handle_plac(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Agent):
            gxobject = Address(value=record.value)
            self.object_map[record.level-1].add_address(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Event):
            if self.gedcomx.places.by_name(record.value):
                self.object_map[record.level-1].place = PlaceReference(original=record.value, description=self.gedcomx.places.by_name(record.value)[0])
            else:
                place_des = PlaceDescription(names=[TextValue(value=record.value)])
                self.gedcomx.add_place_description(place_des)
                self.object_map[record.level-1].place = PlaceReference(original=record.value, description=place_des)
                if len(record.sub_records()) > 0:
                    self.object_map[record.level]= place_des

        elif isinstance(self.object_map[record.level-1], Fact):
            if self.gedcomx.places.by_name(record.value):
                self.object_map[record.level-1].place = PlaceReference(original=record.value, description=self.gedcomx.places.by_name(record.value)[0])
            else:
                place_des = PlaceDescription(names=[TextValue(value=record.value)])
                self.gedcomx.add_place_description(place_des)
                self.object_map[record.level-1].place = PlaceReference(original=record.value, description=place_des)
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            gxobject = Note(text='Place: ' + record.value)
            self.object_map[record.level-1].add_note(gxobject)
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_post(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            self.object_map[record.level-1].postalCode = Translater.clean_str(record.value)
        else:
            raise ValueError(f"I do not know how to handle an 'POST' tag for a {type(self.object_map[record.level-1])}")   
    
    def handle_publ(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            if record.value and self.gedcomx.agents.by_name(record.value):
                gxobject = self.gedcomx.agents.by_name(record.value)[0]
            else:
                gxobject = Agent(names=[TextValue(record.value)])
                self.gedcomx.add_agent(gxobject)
            self.object_map[record.level-1].publisher = gxobject

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_prob(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Probate)
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_uid(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Agent):
            gxobject = Identifier(value=['UID:' + record.value],type=IdentifierType.Primary)
            self.object_map[record.level-1].add_identifier(gxobject) #NOTE GC7
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject

    def handle_refn(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person) or isinstance(self.object_map[record.level-1], SourceDescription):
            gxobject = Identifier(value=[URI.from_url('Reference Number:' + record.value)])
            self.object_map[record.level-1].add_identifier(gxobject)
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = Identifier(value=['Reference Number:' + record.value])
            self.object_map[record.level-1].add_identifier(gxobject) #NOTE GC7
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise ValueError(f"Could not handle 'REFN' tag in record {record.describe()}, last stack object {type(self.object_map[record.level-1])}")

    def handle_repo(self, record: Gedcom5xRecord):

        if record.level == 0:
            
            gxobject = Agent(id=record.xref)
            self.gedcomx.add_agent(gxobject)
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
            
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            if self.gedcomx.agents.by_id(record.xref) is not None:
                
                # TODO WHere and what to add this to?
                gxobject = self.gedcomx.agents.by_id(record.xref)
                self.object_map[record.level-1].repository = gxobject
                self.object_map[record.level] = gxobject

            else:
                print(record.describe())
                raise ValueError()
                gxobject = Agent(names=[TextValue(record.value)])
        else:
            raise ValueError(f"I do not know how to handle 'REPO' tag that is not a top-level, or sub-tag of {type(self.object_map[record.level-1])}")
            

        self.object_stack.append(gxobject)
        self.object_map[record.level] = gxobject

    def handle_resi(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Residence)
            if record.value and record.value.strip() != '':
                gxobject.add_note(Note(text=record.value))
            self.object_map[record.level-1].add_fact(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_rin(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            self.object_map[record.level-1].id = record.value
            self.object_map[record.level-1].add_note(Note(text=f"Source had RIN: of {record.value}"))

        else:
            raise ValueError(f"Could not handle 'RIN' tag in record {record.describe()}, last stack object {type(self.object_map[record.level-1])}")
        
    def handle_sex(self, record: Gedcom5xRecord):
        
        if isinstance(self.object_map[record.level-1], Person):
            if record.value == 'M':
                gxobject = Gender(type=GenderType.Male)
            elif record.value == 'F':
                gxobject = Gender(type=GenderType.Female)
            else:
                gxobject = Gender(type=GenderType.Unknown)
            self.object_map[record.level-1].gender = gxobject
            
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        else:
            assert False

    def handle_sour(self, record: Gedcom5xRecord):
        if record.level == 0 or record.tag == '_WLNK' or (record.level == 0 and record.tag == 'OBJE'):
            source_description = SourceDescription(id=record.xref.replace('@','') if record.xref else None)
            self.gedcomx.add_source_description(source_description)
            self.object_stack.append(source_description)
            self.object_map[record.level] = source_description
        else:
            # This 'SOUR' is a SourceReference
            if record.xref and record.xref.strip() == '':
                import_log.warning(f"SOUR points to nothing: {record.describe()}")
                return False
            if self.gedcomx.sourceDescriptions.by_id(record.xref):
                gxobject = SourceReference(descriptionId=record.xref, description=self.gedcomx.sourceDescriptions.by_id(record.xref))
            else:
                import_log.warning(f'Could not find source with id: {record.xref}')
                source_description = SourceDescription(id=record.xref)
                gxobject = SourceReference(descriptionId=record.value, description=source_description)
            if isinstance(self.object_map[record.level-1],SourceReference):
                self.object_map[record.level-1].description.add_source(gxobject)
            elif record.parent.tag in ['NOTE']:
                pass
            else:
                self.object_map[record.level-1].add_source(gxobject)
            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
          
    def handle_stae(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Address):
            self.object_map[record.level-1].stateOrProvince = Translater.clean_str(record.value)
        else:
            raise ValueError(f"I do not know how to handle an 'STAE' tag for a {type(self.object_map[record.level-1])}")
        
    def handle_surn(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Name):
            surname = NamePart(value=record.value, type=NamePartType.Surname)
            self.object_map[record.level-1]._add_name_part(surname)
        else:
            raise TagConversionError(record=record,levelstack=self.object_map)

    def handle_text(self, record: Gedcom5xRecord):
        if record.parent.tag == 'DATA':
            if isinstance(self.object_map[record.level-2], SourceReference):
                gxobject = TextValue(value=record.value)
                self.object_map[record.level-2].description.add_description(gxobject)
                self.object_stack.append(gxobject)
                self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            gxobject = Document(text=record.value)
            self.object_map[record.level-1].analysis = gxobject
        else:
            assert False

    def handle_titl(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            
            gxobject = TextValue(value=Translater.clean_str(record.value))
            self.object_map[record.level-1].add_title(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        
        elif record.parent.tag == 'FILE' and isinstance(self.object_map[record.level-2], SourceDescription):
            gxobject = TextValue(value=record.value)
            self.object_map[record.level-2].add_title(gxobject)

            self.object_stack.append(gxobject)
            self.object_map[record.level] = gxobject
        elif self.object_map[record.level] and isinstance(self.object_map[record.level], Name):
            gxobject = NamePart(value=record.value, qualifiers=[NamePartQualifier.Title])

            self.object_map[record.level]._add_name_part(gxobject)
        else:
            convert_log.error(f"raise TagConversionError(record=record,levelstack=self.object_map)")

    def handle_tran(self, record: Gedcom5xRecord):
        pass

    def handle_type(self, record: Gedcom5xRecord):
        # peek to see if event or fact
        if isinstance(self.object_map[record.level-1], Event):
            if EventType.guess(record.value):
                self.object_map[record.level-1].type = EventType.guess(record.value)                
            else:              
                self.object_map[record.level-1].type = None
            self.object_map[record.level-1].add_note(Note(text=Translater.clean_str(record.value)))
        elif isinstance(self.object_map[record.level-1], Fact):
            if not self.object_map[record.level-1].type:
                self.object_map[0].type = FactType.guess(record.value)
        elif isinstance(self.object_map[record.level-1], Identifier):
            
            self.object_map[record.level-1].values.append(Translater.clean_str(record.value))
            self.object_map[record.level-1].type = IdentifierType.Other

        elif record.parent.tag == 'FORM':
            if not self.object_map[0].mediaType:
                self.object_map[0].mediaType = record.value

        else:
            raise ValueError(f"I do not know how to handle 'TYPE' tag for {type(self.object_map[record.level-1])}")

    def handle__url(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-2], SourceDescription):
            self.object_map[record.level-2].about = URI.from_url(record.value)
        else:
            raise ValueError(f"Could not handle '_URL' tag in record {record.describe()}, last stack object {self.object_map[record.level-1]}")
            
    def handle_www(self, record: Gedcom5xRecord):
        if isinstance(self.object_map[record.level-1], Agent):
            self.object_map[record.level-1].homepage = Translater.clean_str(record.value)
        elif isinstance(self.object_map[record.level-2], SourceReference):
            self.object_map[record.level-2].description.add_identifier(Identifier(value=URI.from_url(record.value)))
        else:
            raise ValueError(f"Could not handle 'WWW' tag in record {record.describe()}, last stack object {self.object_map[record.level-1]}")

