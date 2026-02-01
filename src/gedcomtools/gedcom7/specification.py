import json
from typing import Dict, Any


g7_structure_specs = {
    "https://gedcom.io/terms/v7/ABBR": {
        "label": "Abbreviation",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Abbreviation A short name of a title, description, or name used for sorting, filing, and retrieving records.",
        "standard_tag": "ABBR",
        "substructures": {},
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/ADDR": {
        "label": "Address",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Address The location of, or most relevant to, the subject of the superstructure. See `ADDRESS_STRUCTURE` for more details. A specific building, plot, or location. The payload is the full formatted\naddress as it would appear on a mailing label, including appropriate line\nbreaks (encoded using `CONT` tags). The expected order of address components\nvaries by region; the address should be organized as expected by the addressed\nregion.\n\nOptionally, additional substructures such as `STAE` and `CTRY` are provided to\nbe used by systems that have structured their addresses for indexing and\nsorting. If the substructures and `ADDR` payload disagree, the `ADDR` payload\nshall be taken as correct. Because the regionally-correct order and formatting\nof address components cannot be determined from the substructures alone, the\n`ADDR` payload is required, even if its content appears to be redundant with\nthe substructures.\n\n&lt;div class=\"deprecation\"&gt;\n\n`ADR1` and `ADR2` were introduced in version 5.5 (1996) and `ADR3` in version\n5.5.1 (1999), defined as \"The first/second/third line of an address.\" Some\napplications interpreted ADR1 as \"the first line of the *street* address\", but\nmost took the spec as-written and treated it as a straight copy of a line of\ntext already available in the `ADDR` payload.\n\nDuplicating information bloats files and introduces the potential for\nself-contradiction. `ADR1`, `ADR2`, and `ADR3` should not be added to new\nfiles.\n\n&lt;/div&gt;",
        "standard_tag": "ADDR",
        "substructures": {
            "ADR1": "https://gedcom.io/terms/v7/ADR1",
            "ADR2": "https://gedcom.io/terms/v7/ADR2",
            "ADR3": "https://gedcom.io/terms/v7/ADR3",
            "CITY": "https://gedcom.io/terms/v7/CITY",
            "CTRY": "https://gedcom.io/terms/v7/CTRY",
            "POST": "https://gedcom.io/terms/v7/POST",
            "STAE": "https://gedcom.io/terms/v7/STAE"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CORP": "https://gedcom.io/terms/v7/CORP",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/ADOP": {
        "label": "Adoption",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Adoption An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. adoption Creation of a legally approved child-parent relationship that does not exist biologically.",
        "standard_tag": "ADOP",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAMC": "https://gedcom.io/terms/v7/ADOP-FAMC",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/ADOP-FAMC": {
        "label": "Family child",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-FAM&gt;@",
        "specification": "Family child The individual or couple that adopted this individual.\n\nAdoption by an individual, rather than a couple, may be represented either by\npointing to a `FAM` where that individual is a `HUSB` or `WIFE` and using a\n`https://gedcom.io/terms/v7/FAMC-ADOP` substructure to indicate which 1\nperformed the adoption; or by using a `FAM` where the adopting individual is\nthe only `HUSB`/`WIFE`.",
        "standard_tag": "FAMC",
        "substructures": {
            "ADOP": "https://gedcom.io/terms/v7/FAMC-ADOP"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP"
        }
    },
    "https://gedcom.io/terms/v7/ADR1": {
        "label": "Address Line 1",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Address Line 1 The first line of the address, used for indexing. This structure's payload\nshould be a single line of text equal to the first line of the corresponding\n`ADDR`. See `ADDRESS_STRUCTURE` for more details.\n\n&lt;div class=\"deprecation\"&gt;\n\n`ADR1` should not be added to new files; see `ADDRESS_STRUCTURE` for more\ndetails.\n\n&lt;/div&gt;",
        "standard_tag": "ADR1",
        "substructures": {},
        "superstructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR"
        }
    },
    "https://gedcom.io/terms/v7/ADR2": {
        "label": "Address Line 2",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Address Line 2 The second line of the address, used for indexing. This structure's payload\nshould be a single line of text equal to the second line of the corresponding\n`ADDR`. See `ADDRESS_STRUCTURE` for more details.\n\n&lt;div class=\"deprecation\"&gt;\n\n`ADR2` should not be added to new files; see `ADDRESS_STRUCTURE` for more\ndetails.\n\n&lt;/div&gt;",
        "standard_tag": "ADR2",
        "substructures": {},
        "superstructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR"
        }
    },
    "https://gedcom.io/terms/v7/ADR3": {
        "label": "Address Line 3",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Address Line 3 The third line of the address, used for indexing. This structure's payload\nshould be a single line of text equal to the third line of the corresponding\n`ADDR`. See `ADDRESS_STRUCTURE` for more details.\n\n&lt;div class=\"deprecation\"&gt;\n\n`ADR3` should not be added to new files; see `ADDRESS_STRUCTURE` for more\ndetails.\n\n&lt;/div&gt;",
        "standard_tag": "ADR3",
        "substructures": {},
        "superstructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR"
        }
    },
    "https://gedcom.io/terms/v7/AGE": {
        "label": "Age at event",
        "payload": "https://gedcom.io/terms/v7/type-Age",
        "specification": "Age at event The age of the individual at the time an event occurred, or the age listed in the document.",
        "standard_tag": "AGE",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/AGNC": {
        "label": "Responsible agency",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Responsible agency The organization, institution, corporation, person, or other entity that has responsibility for the associated context. Examples are an employer of a person of an associated occupation, or a church that administered rites or events, or an organization responsible for creating or archiving records.",
        "standard_tag": "AGNC",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DATA": "https://gedcom.io/terms/v7/DATA",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/ALIA": {
        "label": "Alias",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-INDI&gt;@",
        "specification": "Alias A single individual may have facts distributed across multiple individual\nrecords, connected by `ALIA` pointers (named after \"alias\" in the computing\nsense, not the pseudonym sense).\n\n&lt;div class=\"note\"&gt;\n\nThis specification does not define how to connect `INDI` records with `ALIA`.\nSome systems organize `ALIA` pointers to create a tree structure, with the root\n`INDI` record containing the composite view of all facts in the leaf `INDI`\nrecords. Others distribute events and attributes between `INDI` records\nmutually linked by symmetric pairs of `ALIA` pointers. A future version of this\nspecification may adjust the definition of `ALIA`.\n\n&lt;/div&gt;",
        "standard_tag": "ALIA",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/ANCI": {
        "label": "Ancestor interest",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-SUBM&gt;@",
        "specification": "Ancestor interest Indicates an interest in additional research for ancestors of this individual. (See also `DESI`).",
        "standard_tag": "ANCI",
        "substructures": {},
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/ANUL": {
        "label": "Annulment",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Annulment A [Family Event]. See also `FAMILY_EVENT_STRUCTURE`. annulment Declaring a marriage void from the beginning (never existed).",
        "standard_tag": "ANUL",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/ASSO": {
        "label": "Associates",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-INDI&gt;@",
        "specification": "Associates A pointer to an associated individual. See `ASSOCIATION_STRUCTURE` for more details. An individual associated with the subject of the superstructure. The nature of\nthe association is indicated in the `ROLE` substructure.\n\nA `voidPtr` and `PHRASE` can be used to describe associations to people not\nreferenced by any `INDI` record.\n\n&lt;div class=\"example\"&gt;\n\nThe following indicates that \"Mr Stockdale\" was the individual's teacher and\nthat individual `@I2@` was the clergy officiating at their baptism.\n\n```gedcom\n0 @I1@ INDI\n1 ASSO @VOID@\n2 PHRASE Mr Stockdale\n2 ROLE OTHER\n3 PHRASE Teacher\n1 BAPM\n2 DATE 1930\n2 ASSO @I2@\n3 ROLE CLERGY\n```\n\n&lt;/div&gt;",
        "standard_tag": "ASSO",
        "substructures": {
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE",
            "ROLE": "https://gedcom.io/terms/v7/ROLE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/AUTH": {
        "label": "Author",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Author The person, agency, or entity who created the record. For a published work, this could be the author, compiler, transcriber, abstractor, or editor. For an unpublished source, this may be an individual, a government agency, church organization, or private organization.",
        "standard_tag": "AUTH",
        "substructures": {},
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/BAPL": {
        "label": "Baptism, Latter-Day Saint",
        "payload": "null",
        "specification": "Baptism, Latter-Day Saint A [Latter-Day Saint Ordinance]. See also `LDS_INDIVIDUAL_ORDINANCE`. baptism The event of baptism performed at age 8 or later by priesthood authority of The Church of Jesus Christ of Latter-day Saints. (See also [`BAPM`])",
        "standard_tag": "BAPL",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "STAT": "https://gedcom.io/terms/v7/ord-STAT",
            "TEMP": "https://gedcom.io/terms/v7/TEMP"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/BAPM": {
        "label": "Baptism",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Baptism An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. baptism Baptism, performed in infancy or later. (See also [`BAPL`] and `CHR`.)",
        "standard_tag": "BAPM",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/BARM": {
        "label": "Bar Mitzvah",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Bar Mitzvah An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. Bar Mitzvah The ceremonial event held when a Jewish boy reaches age 13.",
        "standard_tag": "BARM",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/BASM": {
        "label": "Bas Mitzvah",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Bas Mitzvah An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. Bas Mitzvah The ceremonial event held when a Jewish girl reaches age 13, also known as \"Bat Mitzvah.\"",
        "standard_tag": "BASM",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/BIRT": {
        "label": "Birth",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Birth An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. birth Entering into life.",
        "standard_tag": "BIRT",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAMC": "https://gedcom.io/terms/v7/FAMC",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/BLES": {
        "label": "Blessing",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Blessing An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. blessing Bestowing divine care or intercession. Sometimes given in connection with a naming ceremony.",
        "standard_tag": "BLES",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/BURI": {
        "label": "Depositing remains",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Depositing remains An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`.\n\nAlthough defined as any depositing of remains since it was introduced in the\nfirst version of GEDCOM, this tag is a shortened form of the English word\n\"burial\" and has been interpreted to mean \"depositing of remains by burial\" by\nsome applications and users. In the absence of a clarifying `TYPE` substructure\nit is likely, but not guaranteed, that a `BURI` structure refers to a burial\nrather than another form of depositing remains. depositing remains Depositing the mortal remains of a deceased person.",
        "standard_tag": "BURI",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/CALN": {
        "label": "Call number",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Call number An identification or reference description used to file and retrieve items from the holdings of a repository. Despite the word \"number\" in the name, may contain any character, not just digits.",
        "standard_tag": "CALN",
        "substructures": {
            "MEDI": "https://gedcom.io/terms/v7/MEDI"
        },
        "superstructures": {
            "REPO": "https://gedcom.io/terms/v7/REPO"
        }
    },
    "https://gedcom.io/terms/v7/CAST": {
        "label": "Caste",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Caste An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. caste The name of an individual's rank or status in society which is sometimes based on racial or religious differences, or differences in wealth, inherited rank, profession, or occupation.",
        "standard_tag": "CAST",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/CAUS": {
        "label": "Cause",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Cause The reasons which precipitated an event. It is often used subordinate to a death event to show cause of death, such as might be listed on a death certificate.",
        "standard_tag": "CAUS",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/CHAN": {
        "label": "Change",
        "payload": "null",
        "specification": "Change The most recent change to the superstructure. This is metadata about the structure itself, not data about its subject. See `CHANGE_DATE` for more details. The date of the most recent modification of the superstructure, optionally with\nnotes about that modification.\n\nThe `NOTE` substructure may describe previous changes as well as the most\nrecent, although only the most recent change is described by the `DATE`\nsubstructure.",
        "standard_tag": "CHAN",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE-exact",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "SNOTE": "https://gedcom.io/terms/v7/record-SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM"
        }
    },
    "https://gedcom.io/terms/v7/CHIL": {
        "label": "Child",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-INDI&gt;@",
        "specification": "Child The child in a family, whether biological, adopted, foster, sealed, or other relationship.",
        "standard_tag": "CHIL",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/CHR": {
        "label": "Christening",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Christening An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. christening Baptism or naming events for a child.",
        "standard_tag": "CHR",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAMC": "https://gedcom.io/terms/v7/FAMC",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/CHRA": {
        "label": "Christening, adult",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Christening, adult An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. adult christening Baptism or naming events for an adult person.",
        "standard_tag": "CHRA",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/CITY": {
        "label": "City",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "City The name of the city used in the address. See `ADDRESS_STRUCTURE` for more details.",
        "standard_tag": "CITY",
        "substructures": {},
        "superstructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR"
        }
    },
    "https://gedcom.io/terms/v7/CONF": {
        "label": "Confirmation",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Confirmation An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. confirmation Conferring full church membership.",
        "standard_tag": "CONF",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/CONL": {
        "label": "Confirmation, Latter-Day Saint",
        "payload": "null",
        "specification": "Confirmation, Latter-Day Saint A [Latter-Day Saint Ordinance]. See also `LDS_INDIVIDUAL_ORDINANCE`. confirmation The religious event by which a person receives membership in The Church of Jesus Christ of Latter-day Saints. (See also [`CONF`])",
        "standard_tag": "CONL",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "STAT": "https://gedcom.io/terms/v7/ord-STAT",
            "TEMP": "https://gedcom.io/terms/v7/TEMP"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/CONT": {
        "label": "Continued",
        "payload": "null",
        "specification": "Continued A pseudo-structure to indicate a line break. The `CONT` tag is generated during serialization and is never present in parsed datasets. See [Lines] for more details.",
        "standard_tag": "CONT",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/COPR": {
        "label": "Copyright",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Copyright A copyright statement, as appropriate for the copyright laws applicable to this data.",
        "standard_tag": "COPR",
        "substructures": {},
        "superstructures": {
            "DATA": "https://gedcom.io/terms/v7/HEAD-SOUR-DATA",
            "HEAD": "https://gedcom.io/terms/v7/HEAD"
        }
    },
    "https://gedcom.io/terms/v7/CORP": {
        "label": "Corporate name",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Corporate name The name of the business, corporation, or person that produced or commissioned the product.",
        "standard_tag": "CORP",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/HEAD-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/CREA": {
        "label": "Creation",
        "payload": "null",
        "specification": "Creation The initial creation of the superstructure. This is metadata about the structure itself, not data about its subject. See `CREATION_DATE` for more details. The date of the initial creation of the superstructure. Because this refers to the initial creation, it should not be modified after the structure is created.",
        "standard_tag": "CREA",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE-exact"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "SNOTE": "https://gedcom.io/terms/v7/record-SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM"
        }
    },
    "https://gedcom.io/terms/v7/CREM": {
        "label": "Cremation",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Cremation An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. cremation The act of reducing a dead body to ashes by fire.",
        "standard_tag": "CREM",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/CROP": {
        "label": "Crop",
        "payload": "null",
        "specification": "Crop A subregion of an image to display. It is only valid when the superstructure\nlinks to a `MULTIMEDIA_RECORD` with at least 1 `FILE` substructure that refers\nto an external file with a defined pixel unit.\n\n`LEFT` and `TOP` indicate the top-left corner of the region to display. `WIDTH`\nand `HEIGHT` indicate how many pixels wide and tall the region to display is.\nIf omitted, `LEFT` and `TOP` each default to 0; `WIDTH` defaults to the image\nwidth minus `LEFT`; and `HEIGHT` defaults to the image height minus `TOP`.\n\nIf the superstructure links to a `MULTIMEDIA_RECORD` that includes multiple\n`FILE` substructures, the `CROP` applies to the first `FILE` to which it can\napply, namely the first external file with a defined pixel unit.\n\nIt is recommended that `CROP` be used only with a single-FILE\n`MULTIMEDIA_RECORD`.\n\nThe following are errors:\n\n- `LEFT` or `LEFT` + `WIDTH` exceed the image width.\n- `TOP` or `TOP` + `HEIGHT` exceed the image height.\n- `CROP` applied to a non-image or image without a defined pixel unit.",
        "standard_tag": "CROP",
        "substructures": {
            "HEIGHT": "https://gedcom.io/terms/v7/HEIGHT",
            "LEFT": "https://gedcom.io/terms/v7/LEFT",
            "TOP": "https://gedcom.io/terms/v7/TOP",
            "WIDTH": "https://gedcom.io/terms/v7/WIDTH"
        },
        "superstructures": {
            "OBJE": "https://gedcom.io/terms/v7/OBJE"
        }
    },
    "https://gedcom.io/terms/v7/CTRY": {
        "label": "Country",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Country The name of the country that pertains to the associated address. See `ADDRESS_STRUCTURE` for more details.",
        "standard_tag": "CTRY",
        "substructures": {},
        "superstructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR"
        }
    },
    "https://gedcom.io/terms/v7/DATA": {
        "label": "Data",
        "payload": "null",
        "specification": "Data A structure with no payload used to distinguish a description of something from metadata about it. For example, `SOUR` and its other substructures describe a source itself, while `SOUR`.`DATA` describes the content of the source.",
        "standard_tag": "DATA",
        "substructures": {
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "EVEN": "https://gedcom.io/terms/v7/DATA-EVEN",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE"
        },
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/DATA-EVEN": {
        "label": "Event",
        "payload": "https://gedcom.io/terms/v7/type-List#Enum",
        "specification": "Event A list of enumerated values from set `https://gedcom.io/terms/v7/enumset-EVENATTR` indicating the types of events that were recorded in a particular source. Each event type is separated by a comma and space. For example, a parish register of births, deaths, and marriages would be `BIRT, DEAT, MARR`.",
        "standard_tag": "EVEN",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATA-EVEN-DATE",
            "PLAC": "https://gedcom.io/terms/v7/PLAC"
        },
        "superstructures": {
            "DATA": "https://gedcom.io/terms/v7/DATA"
        }
    },
    "https://gedcom.io/terms/v7/DATA-EVEN-DATE": {
        "label": "Date",
        "payload": "https://gedcom.io/terms/v7/type-Date#period",
        "specification": "Date The `DatePeriod` covered by the entire source; the period during which this source recorded events.",
        "standard_tag": "DATE",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "EVEN": "https://gedcom.io/terms/v7/DATA-EVEN"
        }
    },
    "https://gedcom.io/terms/v7/DATE": {
        "label": "Date",
        "payload": "https://gedcom.io/terms/v7/type-Date",
        "specification": "Date The principal date of the subject of the superstructure. The payload is a\n`DateValue`.\n\nWhen the superstructure is an event, the principal date indicates when the\nevent took place.\n\nWhen the superstructure is an attribute, the principal date indicates when the\nattribute was observed, asserted, or applied. A date period might put bounds on\nthe attributes applicability, but other date forms assume that the attribute\nmay have also applied on other dates too.\n\nWhen the superstructure is a `https://gedcom.io/terms/v7/SOUR-DATA`, the\nprincipal date indicates when the data was entered into the source; or, for a\nsource like a website that changes over time, a date on which the source\ncontained the data.\n\nSee `DATE_VALUE` for more details. A date, optionally with a time and/or a phrase. If there is a `TIME`, it\nasserts that the event happened at a specific time on a single day. `TIME`\nshould not be used with `DatePeriod` but may be used with other date types.\n\n&lt;div class=\"note\"&gt;\n\nThere is currently no provision for approximate times or time phrases. Time\nphrases are expected to be added in version 7.1.\n\n&lt;/div&gt;",
        "standard_tag": "DATE",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE",
            "TIME": "https://gedcom.io/terms/v7/TIME"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPL": "https://gedcom.io/terms/v7/BAPL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CONL": "https://gedcom.io/terms/v7/CONL",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DATA": "https://gedcom.io/terms/v7/SOUR-DATA",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENDL": "https://gedcom.io/terms/v7/ENDL",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INIL": "https://gedcom.io/terms/v7/INIL",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SLGC": "https://gedcom.io/terms/v7/SLGC",
            "SLGS": "https://gedcom.io/terms/v7/SLGS",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/DATE-exact": {
        "label": "Date",
        "payload": "https://gedcom.io/terms/v7/type-Date#exact",
        "specification": "Date The principal date of the subject of the superstructure. The payload is a `DateExact`.",
        "standard_tag": "DATE",
        "substructures": {
            "TIME": "https://gedcom.io/terms/v7/TIME"
        },
        "superstructures": {
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CREA": "https://gedcom.io/terms/v7/CREA",
            "DATA": "https://gedcom.io/terms/v7/HEAD-SOUR-DATA",
            "STAT": "https://gedcom.io/terms/v7/ord-STAT"
        }
    },
    "https://gedcom.io/terms/v7/DEAT": {
        "label": "Death",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Death An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. death Mortal life terminates.",
        "standard_tag": "DEAT",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/DESI": {
        "label": "Descendant Interest",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-SUBM&gt;@",
        "specification": "Descendant Interest Indicates an interest in research to identify additional descendants of this individual. See also `ANCI`.",
        "standard_tag": "DESI",
        "substructures": {},
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/DEST": {
        "label": "Destination",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Destination An identifier for the system expected to receive this document. See `HEAD`.`SOUR` for guidance on choosing identifiers.",
        "standard_tag": "DEST",
        "substructures": {},
        "superstructures": {
            "HEAD": "https://gedcom.io/terms/v7/HEAD"
        }
    },
    "https://gedcom.io/terms/v7/DIV": {
        "label": "Divorce",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Divorce A [Family Event]. See also `FAMILY_EVENT_STRUCTURE`. divorce Dissolving a marriage through civil action.",
        "standard_tag": "DIV",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/DIVF": {
        "label": "Divorce filing",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Divorce filing A [Family Event]. See also `FAMILY_EVENT_STRUCTURE`. divorce filed Filing for a divorce by a spouse.",
        "standard_tag": "DIVF",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/DSCR": {
        "label": "Description",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Description An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. physical description The physical characteristics of a person.",
        "standard_tag": "DSCR",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/EDUC": {
        "label": "Education",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Education An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. education Indicator of a level of education attained.",
        "standard_tag": "EDUC",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/EMAIL": {
        "label": "Email",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Email An electronic mail address, as defined by any relevant standard such as [RFC\n3696], [RFC 5321], or [RFC 5322].\n\nIf an invalid email address is present upon import, it should be preserved\nas-is on export.\n\n&lt;div class=\"note\"&gt;\n\nThe version 5.5.1 specification contained a typo where this tag was sometimes\nwritten `EMAI` and sometimes written `EMAIL`. `EMAIL` should be used in version\n7.0 and later.\n\n&lt;/div&gt;",
        "standard_tag": "EMAIL",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CORP": "https://gedcom.io/terms/v7/CORP",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/EMIG": {
        "label": "Emigration",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Emigration An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. emigration Leaving one's homeland with the intent of residing elsewhere.",
        "standard_tag": "EMIG",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/ENDL": {
        "label": "Endowment, Latter-Day Saint",
        "payload": "null",
        "specification": "Endowment, Latter-Day Saint A [Latter-Day Saint Ordinance]. See also `LDS_INDIVIDUAL_ORDINANCE`. endowment A religious event where an endowment ordinance for an individual was performed by priesthood authority in a temple of The Church of Jesus Christ of Latter-day Saints.",
        "standard_tag": "ENDL",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "STAT": "https://gedcom.io/terms/v7/ord-STAT",
            "TEMP": "https://gedcom.io/terms/v7/TEMP"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/ENGA": {
        "label": "Engagement",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Engagement A [Family Event]. See also `FAMILY_EVENT_STRUCTURE`. engagement Recording or announcing an agreement between 2 people to become married.",
        "standard_tag": "ENGA",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/EXID": {
        "label": "External Identifier",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "External Identifier An identifier for the subject of the superstructure. The identifier is\nmaintained by some external authority; the authority owning the identifier is\nprovided in the TYPE substructure; see `EXID`.`TYPE` for more details.\n\nDepending on the maintaining authority, an `EXID` may be a unique identifier\nfor the subject, an identifier for 1 of several views of the subject, or an\nidentifier for the externally-maintained copy of the same information as is\ncontained in this structure. However, unlike `UID` and `REFN`, `EXID` does not\nidentify a structure; structures with the same `EXID` may have originated\nindependently rather than by edits from the same starting point.\n\n`EXID` identifiers are expected to be unique. Once assigned, an `EXID`\nidentifier should never be re-used for any other purpose.",
        "standard_tag": "EXID",
        "substructures": {
            "TYPE": "https://gedcom.io/terms/v7/EXID-TYPE"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "SNOTE": "https://gedcom.io/terms/v7/record-SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM"
        }
    },
    "https://gedcom.io/terms/v7/EXID-TYPE": {
        "label": "Type",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Type The authority issuing the `EXID`, represented as a URI. It is recommended that\nthis be a URL.\n\nIf the authority maintains stable URLs for each identifier it issues, it is\nrecommended that the `TYPE` payload be selected such that appending the `EXID`\npayload to it yields that URL. However, this is not required and a different\nURI for the set of issued identifiers may be used instead.\n\nRegistered URIs are listed in the [exid-types registry], where fields are\ndefined using the [YAML file format].\n\nAdditional type URIs can be registered by filing a [GitHub pull request].",
        "standard_tag": "TYPE",
        "substructures": {},
        "superstructures": {
            "EXID": "https://gedcom.io/terms/v7/EXID"
        }
    },
    "https://gedcom.io/terms/v7/FAM-CENS": {
        "label": "Census",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Census An [Family Event]. census Periodic count of the population for a designated locality, such as a national or state census.",
        "standard_tag": "CENS",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/FAM-EVEN": {
        "label": "Event",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Event See `https://gedcom.io/terms/v7/INDI-EVEN`.",
        "standard_tag": "EVEN",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/FAM-FACT": {
        "label": "Fact",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Fact See `https://gedcom.io/terms/v7/INDI-FACT`.",
        "standard_tag": "FACT",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/FAM-HUSB": {
        "label": "Husband",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-INDI&gt;@",
        "specification": "Husband This is a partner in a `FAM` record. See `FAMILY_RECORD` for more details.",
        "standard_tag": "HUSB",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/FAM-NCHI": {
        "label": "Number of children",
        "payload": "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
        "specification": "Number of children A [Family Attribute]. See also `FAMILY_ATTRIBUTE_STRUCTURE`. number of children The number of children that belong to this family.",
        "standard_tag": "NCHI",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/FAM-RESI": {
        "label": "Residence",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Residence A [Family Attribute]. See also `FAMILY_ATTRIBUTE_STRUCTURE`.\n\nSee `https://gedcom.io/terms/v7/INDI-RESI` for comments on the use of payload\nstrings in `RESI` structures. residence An address or place of residence where a family resided.",
        "standard_tag": "RESI",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/FAM-WIFE": {
        "label": "Wife",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-INDI&gt;@",
        "specification": "Wife A partner in a `FAM` record. See `FAMILY_RECORD` for more details.",
        "standard_tag": "WIFE",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/FAMC": {
        "label": "Family child",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-FAM&gt;@",
        "specification": "Family child The family with which this individual event is associated.",
        "standard_tag": "FAMC",
        "substructures": {},
        "superstructures": {
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "SLGC": "https://gedcom.io/terms/v7/SLGC"
        }
    },
    "https://gedcom.io/terms/v7/FAMC-ADOP": {
        "label": "Adoption",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Adoption An enumerated value from set `https://gedcom.io/terms/v7/enumset-ADOP` indicating which parent(s) in the family adopted this individual.",
        "standard_tag": "ADOP",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "FAMC": "https://gedcom.io/terms/v7/ADOP-FAMC"
        }
    },
    "https://gedcom.io/terms/v7/FAMC-STAT": {
        "label": "Status",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Status An enumerated value from set `https://gedcom.io/terms/v7/enumset-FAMC-STAT` assessing of the state or condition of a researcher's belief in a family connection.",
        "standard_tag": "STAT",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "FAMC": "https://gedcom.io/terms/v7/INDI-FAMC"
        }
    },
    "https://gedcom.io/terms/v7/FAMS": {
        "label": "Family spouse",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-FAM&gt;@",
        "specification": "Family spouse The family in which an individual appears as a partner. See `FAMILY_RECORD` for more details.",
        "standard_tag": "FAMS",
        "substructures": {
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/FAX": {
        "label": "Facsimile",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Facsimile A fax telephone number appropriate for sending data facsimiles. See `PHON` for additional comments on telephone numbers.",
        "standard_tag": "FAX",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CORP": "https://gedcom.io/terms/v7/CORP",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/FCOM": {
        "label": "First communion",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "First communion An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. first communion The first act of sharing in the Lord's supper as part of church worship.",
        "standard_tag": "FCOM",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/FILE": {
        "label": "File reference",
        "payload": "https://gedcom.io/terms/v7/type-FilePath",
        "specification": "File reference A reference to an external file. See the [File Path datatype] for more details.",
        "standard_tag": "FILE",
        "substructures": {
            "FORM": "https://gedcom.io/terms/v7/FORM",
            "TITL": "https://gedcom.io/terms/v7/TITL",
            "TRAN": "https://gedcom.io/terms/v7/FILE-TRAN"
        },
        "superstructures": {
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE"
        }
    },
    "https://gedcom.io/terms/v7/FILE-TRAN": {
        "label": "Translation",
        "payload": "https://gedcom.io/terms/v7/type-FilePath",
        "specification": "Translation A type of `TRAN` for external media files. Each\n`https://gedcom.io/terms/v7/NOTE-TRAN` must have a `FORM` substructure. See\nalso `FILE` and the [File Path datatype].\n\n&lt;div class=\"example\"&gt;\n\nIf an mp3 audio file has been transcoded as an ogg file and a timestamped\ntranscript has been extracted as a WebVTT file, the resulting set of files\nmight be presented as follows:\n\n```gedcom\n0 @EX@ OBJE\n1 FILE media/original.mp3\n2 FORM audio/mp3\n2 TRAN media/derived.oga\n3 FORM audio/ogg\n2 TRAN media/transcript.vtt\n3 FORM text/vtt\n```\n\n&lt;/div&gt;\n\nNote that `FILE`.`TRAN` refers to translation to a different digital format,\nnot to translation to a different human language. Files that differ in the\nhuman language of their content should each be given their own `FILE`\nstructure. A representation of the superstructure's data in a different format.\n\nIn some situations it is desirable to provide the same semantic content in\nmultiple formats. Where this is desirable, a `TRAN` substructure is used, where\nthe specific format is given in its language tag substructure, media type\nsubstructure, or both.\n\nDifferent `TRAN` structures are used in different contexts to fully capture the\nstructure of the information being presented in multiple formats. In all cases,\na `TRAN` structure's payload and substructures should provide only information\nalso contained in the `TRAN` structures' superstructure, but provide it in a\nnew language, script, or media type.\n\nEach `TRAN` substructure must have either a language tag or a media type or\nboth. Each `TRAN` structure must differ from its superstructure and from every\nother `TRAN` substructure of its superstructure in either its language tag or\nits media type or both.",
        "standard_tag": "TRAN",
        "substructures": {
            "FORM": "https://gedcom.io/terms/v7/FORM"
        },
        "superstructures": {
            "FILE": "https://gedcom.io/terms/v7/FILE"
        }
    },
    "https://gedcom.io/terms/v7/FORM": {
        "label": "Format",
        "payload": "http://www.w3.org/ns/dcat#mediaType",
        "specification": "Format The [media type] of the file referenced by the superstructure.",
        "standard_tag": "FORM",
        "substructures": {
            "MEDI": "https://gedcom.io/terms/v7/MEDI"
        },
        "superstructures": {
            "FILE": "https://gedcom.io/terms/v7/FILE",
            "TRAN": "https://gedcom.io/terms/v7/FILE-TRAN"
        }
    },
    "https://gedcom.io/terms/v7/GEDC": {
        "label": "GEDCOM",
        "payload": "null",
        "specification": "GEDCOM A container for information about the entire document.\n\nIt is recommended that applications write `GEDC` with its required substructure\n`https://gedcom.io/terms/v7/GEDC-VERS` as the first substructure of `HEAD`.",
        "standard_tag": "GEDC",
        "substructures": {
            "VERS": "https://gedcom.io/terms/v7/GEDC-VERS"
        },
        "superstructures": {
            "HEAD": "https://gedcom.io/terms/v7/HEAD"
        }
    },
    "https://gedcom.io/terms/v7/GEDC-VERS": {
        "label": "Version",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Version The version number of the official specification that this document's data conforms to. This must include the major and minor version (for example, \"`7.0`\"); it may include the patch as well (for example, \"`7.0.1`\"), but doing so is not required. See [A Guide to Version Numbers] for more details about version numbers.",
        "standard_tag": "VERS",
        "substructures": {},
        "superstructures": {
            "GEDC": "https://gedcom.io/terms/v7/GEDC"
        }
    },
    "https://gedcom.io/terms/v7/GIVN": {
        "label": "Given name",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Given name A given or earned name used for official identification of a person.",
        "standard_tag": "GIVN",
        "substructures": {},
        "superstructures": {
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "TRAN": "https://gedcom.io/terms/v7/NAME-TRAN"
        }
    },
    "https://gedcom.io/terms/v7/GRAD": {
        "label": "Graduation",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Graduation An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. graduation Awarding educational diplomas or degrees to individuals.",
        "standard_tag": "GRAD",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/HEAD": {
        "label": "Header",
        "payload": "null",
        "specification": "Header A pseudo-structure for storing metadata about the document. See [The Header and Trailer] for more details. The header pseudo-structure provides metadata about the entire dataset. A few\nsubstructures of note:\n\n- `GEDC` identifies the specification that this document conforms to. It is\n  recommended that `GEDC` be the first substructure of the header.\n- `SCHMA` gives the meaning of extension tags; see [Extensions] for more\n  details.\n- `SOUR` describes the originating software.\n  - `CORP` describes the corporation creating the software.\n  - `HEAD`.`SOUR`.`DATA` describes a larger database, electronic data source,\n    or digital repository this data is extracted from.\n- `LANG` and `PLAC` give a default value for the rest of the document.\n\n&lt;div class=\"deprecation\"&gt;\n\n`HEAD`.`SOUR`.`DATA` is now deprecated and applications should use\n`HEAD`.`SOUR`.`NAME` instead.\n\n&lt;/div&gt;",
        "standard_tag": "HEAD",
        "substructures": {
            "COPR": "https://gedcom.io/terms/v7/COPR",
            "DATE": "https://gedcom.io/terms/v7/HEAD-DATE",
            "DEST": "https://gedcom.io/terms/v7/DEST",
            "GEDC": "https://gedcom.io/terms/v7/GEDC",
            "LANG": "https://gedcom.io/terms/v7/HEAD-LANG",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PLAC": "https://gedcom.io/terms/v7/HEAD-PLAC",
            "SCHMA": "https://gedcom.io/terms/v7/SCHMA",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/HEAD-SOUR",
            "SUBM": "https://gedcom.io/terms/v7/SUBM"
        },
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/HEAD-DATE": {
        "label": "Date",
        "payload": "https://gedcom.io/terms/v7/type-Date#exact",
        "specification": "Date The `DateExact` that this document was created.",
        "standard_tag": "DATE",
        "substructures": {
            "TIME": "https://gedcom.io/terms/v7/TIME"
        },
        "superstructures": {
            "HEAD": "https://gedcom.io/terms/v7/HEAD"
        }
    },
    "https://gedcom.io/terms/v7/HEAD-LANG": {
        "label": "Language",
        "payload": "http://www.w3.org/2001/XMLSchema#Language",
        "specification": "Language A default language which may be used to interpret any `Text`-typed payloads\nthat lack a specific language tag from a `https://gedcom.io/terms/v7/LANG`\nstructure. An application may choose to use a different default based on its\nknowledge of the language preferences of the user.\n\nThe payload of the `LANG` structure is a language tag, as defined by [BCP 47].\n\n&lt;div class=\"note\"&gt;\n\nSome algorithms on text are language-specific. Examples include sorting\nsequences, name comparison and phonetic name matching algorithms,\nspell-checking, computer-synthesized speech, Braille transcription, and\nlanguage translation. When the language of the text is given through a\n`https://gedcom.io/terms/v7/LANG`, that should be used. When\n`https://gedcom.io/terms/v7/LANG` is not available,\n`https://gedcom.io/terms/v7/HEAD-LANG` provides the file creator's suggested\ndefault language. For some language-specific algorithms, the user's preferred\nlanguage may be a more appropriate default than the file's default language.\nUser language preferences can be found in a variety of platform-specific\nplaces, such as the default language from operating system settings, user\nlocales, Input Method Editors (IMEs), etc.\n\n&lt;/div&gt;",
        "standard_tag": "LANG",
        "substructures": {},
        "superstructures": {
            "HEAD": "https://gedcom.io/terms/v7/HEAD"
        }
    },
    "https://gedcom.io/terms/v7/HEAD-PLAC": {
        "label": "Place",
        "payload": "null",
        "specification": "Place This is a placeholder for providing a default `PLAC`.`FORM`, and must not have a payload.",
        "standard_tag": "PLAC",
        "substructures": {
            "FORM": "https://gedcom.io/terms/v7/HEAD-PLAC-FORM"
        },
        "superstructures": {
            "HEAD": "https://gedcom.io/terms/v7/HEAD"
        }
    },
    "https://gedcom.io/terms/v7/HEAD-PLAC-FORM": {
        "label": "Format",
        "payload": "https://gedcom.io/terms/v7/type-List#Text",
        "specification": "Format Any `PLAC` with no [`FORM`] shall be treated as if it has this [`FORM`].",
        "standard_tag": "FORM",
        "substructures": {},
        "superstructures": {
            "PLAC": "https://gedcom.io/terms/v7/HEAD-PLAC"
        }
    },
    "https://gedcom.io/terms/v7/HEAD-SOUR": {
        "label": "Source",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Source An identifier for the product producing this dataset. A registration process for these identifiers existed for a time, but no longer does. If an existing identifier is known, it should be used. Otherwise, a URI owned by the product should be used instead.",
        "standard_tag": "SOUR",
        "substructures": {
            "CORP": "https://gedcom.io/terms/v7/CORP",
            "DATA": "https://gedcom.io/terms/v7/HEAD-SOUR-DATA",
            "NAME": "https://gedcom.io/terms/v7/NAME",
            "VERS": "https://gedcom.io/terms/v7/VERS"
        },
        "superstructures": {
            "HEAD": "https://gedcom.io/terms/v7/HEAD"
        }
    },
    "https://gedcom.io/terms/v7/HEAD-SOUR-DATA": {
        "label": "Data",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Data The database, electronic data source, or digital repository from which this dataset was exported. The payload is the name of the database, electronic data source, or digital repository, with substructures providing additional details about it (not about the export).",
        "standard_tag": "DATA",
        "substructures": {
            "COPR": "https://gedcom.io/terms/v7/COPR",
            "DATE": "https://gedcom.io/terms/v7/DATE-exact"
        },
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/HEAD-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/HEIGHT": {
        "label": "Height in pixels",
        "payload": "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
        "specification": "Height in pixels How many pixels to display vertically for the image. See `CROP` for more\ndetails.\n\n&lt;div class=\"note\"&gt;\n\n`HEIGHT` is a number of pixels. The correct tag for the height of an individual\nis the `DSCR` attribute.\n\n&lt;div class=\"example\"&gt;\n\n```gedcom\n0 @I45@ INDI\n1 DSCR brown eyes, 5ft 10in, 198 pounds\n```\n\n&lt;/div&gt;\n\n&lt;/div&gt;",
        "standard_tag": "HEIGHT",
        "substructures": {},
        "superstructures": {
            "CROP": "https://gedcom.io/terms/v7/CROP"
        }
    },
    "https://gedcom.io/terms/v7/HUSB": {
        "label": "Husband",
        "payload": "null",
        "specification": "Husband A container for information relevant to the subject of the superstructure specific to the individual described by the associated `FAM`'s `HUSB` substructure.",
        "standard_tag": "HUSB",
        "substructures": {
            "AGE": "https://gedcom.io/terms/v7/AGE"
        },
        "superstructures": {
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "CENS": "https://gedcom.io/terms/v7/FAM-CENS",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/FAM-EVEN",
            "FACT": "https://gedcom.io/terms/v7/FAM-FACT",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NCHI": "https://gedcom.io/terms/v7/FAM-NCHI",
            "RESI": "https://gedcom.io/terms/v7/FAM-RESI"
        }
    },
    "https://gedcom.io/terms/v7/IDNO": {
        "label": "Identification number",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Identification number An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. identifying number A number or other string assigned to identify a person within some significant external system. It must have a `TYPE` substructure to define what kind of identification number is being provided.",
        "standard_tag": "IDNO",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/IMMI": {
        "label": "Immigration",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Immigration An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. immigration Entering into a new locality with the intent of residing there.",
        "standard_tag": "IMMI",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INDI-CENS": {
        "label": "Census",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Census An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. census Periodic count of the population for a designated locality, such as a national or state census.",
        "standard_tag": "CENS",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INDI-EVEN": {
        "label": "Event",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Event An event: a noteworthy happening related to an individual or family. If a\nspecific event type exists, it should be used instead of a generic `EVEN`\nstructure. Each `EVEN` must be classified by a subordinate use of the `TYPE`\ntag and may be further described in the structure's payload.\n\n&lt;div class=\"example\"&gt;\n\nA person that signed a lease for land dated October 2, 1837 and a lease for\nmining equipment dated November 4, 1837 would be written as:\n\n```gedcom\n0 @I1@ INDI\n1 EVEN\n2 TYPE Land Lease\n2 DATE 2 OCT 1837\n1 EVEN Mining equipment\n2 TYPE Equipment Lease\n2 DATE 4 NOV 1837\n```\n\n&lt;/div&gt;",
        "standard_tag": "EVEN",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INDI-FACT": {
        "label": "Fact",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Fact A noteworthy attribute or fact concerning an individual or family. If a\nspecific attribute type exists, it should be used instead of a generic `FACT`\nstructure. Each `FACT` must be classified by a subordinate use of the `TYPE`\ntag and may be further described in the structure's payload.\n\n&lt;div class=\"example\"&gt;\n\nIf the attribute being defined was 1 of the person's skills, such as\nwoodworking, the `FACT` tag would have the value of \"Woodworking\", followed by\na subordinate `TYPE` tag with the value \"Skills\".\n\n```gedcom\n0 @I1@ INDI\n1 FACT Woodworking\n2 TYPE Skills\n```\n\n&lt;/div&gt;",
        "standard_tag": "FACT",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INDI-FAMC": {
        "label": "Family child",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-FAM&gt;@",
        "specification": "Family child The family in which an individual appears as a child. It is also used with a `https://gedcom.io/terms/v7/FAMC-STAT` substructure to show individuals who are not children of the family. See `FAMILY_RECORD` for more details.",
        "standard_tag": "FAMC",
        "substructures": {
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PEDI": "https://gedcom.io/terms/v7/PEDI",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "STAT": "https://gedcom.io/terms/v7/FAMC-STAT"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INDI-NAME": {
        "label": "Name",
        "payload": "https://gedcom.io/terms/v7/type-Name",
        "specification": "Name A `PERSONAL_NAME_STRUCTURE` with parts, translations, sources, and so forth. Names of individuals are represented in the manner the name is normally spoken,\nwith the family name, surname, or nearest cultural parallel thereunto separated\nby slashes (U+002F `/`). Based on the dynamic nature or unknown compositions of\nnaming conventions, it is difficult to provide a more detailed name piece\nstructure to handle every case. The `PERSONAL_NAME_PIECES` are provided\noptionally for systems that cannot operate effectively with less structured\ninformation. The Personal Name payload shall be seen as the primary name\nrepresentation, with name pieces as optional auxiliary information; in\nparticular it is recommended that all name parts in `PERSONAL_NAME_PIECES`\nappear within the `PersonalName` payload in some form, possibly adjusted for\ngender-specific suffixes or the like. It is permitted for the payload to\ncontain information not present in any name piece substructure.\n\nThe name may be translated or transliterated into different languages or\nscripts using the `TRAN` substructure. It is recommended, but not required,\nthat if the name pieces are used, the same pieces are used in each translation\nand transliteration.\n\nA `TYPE` is used to specify the particular variation that this name is. For\nexample; it could indicate that this name is a name taken at immigration or\nthat it could be an ‘also known as’ name. See\n`https://gedcom.io/terms/v7/enumset-NAME-TYPE` for more details.\n\n&lt;div class=\"note\"&gt;\n\nAlternative approaches to representing names are being considered for future\nversions of this specification.\n\n&lt;/div&gt;",
        "standard_tag": "NAME",
        "substructures": {
            "GIVN": "https://gedcom.io/terms/v7/GIVN",
            "NICK": "https://gedcom.io/terms/v7/NICK",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "NPFX": "https://gedcom.io/terms/v7/NPFX",
            "NSFX": "https://gedcom.io/terms/v7/NSFX",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "SPFX": "https://gedcom.io/terms/v7/SPFX",
            "SURN": "https://gedcom.io/terms/v7/SURN",
            "TRAN": "https://gedcom.io/terms/v7/NAME-TRAN",
            "TYPE": "https://gedcom.io/terms/v7/NAME-TYPE"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INDI-NCHI": {
        "label": "Number of children",
        "payload": "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
        "specification": "Number of children An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. number of children The number of children that this person is known to be the parent of (all marriages).",
        "standard_tag": "NCHI",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INDI-RELI": {
        "label": "Religion",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Religion An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. religion A religious denomination to which a person is affiliated or for which a record applies.",
        "standard_tag": "RELI",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INDI-RESI": {
        "label": "Residence",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Residence An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`.\n\nWhere possible, the residence should be identified in `PLAC` and/or `ADDR`\nsubstructures of the `RESI` structure. The payload text should not duplicate\n`PLAC` or `ADDR` information, but may be used for residence information that\ncannot be expressed by those structures.\n\n&lt;div class=\"example\"&gt;\n\nThe following two examples show situations where a `RESI` payload may be\nappropriate:\n\n```gedcom\n1 RESI living with an aunt\n2 DATE ABT MAR 1894\n```\n\n```gedcom\n1 RESI in a mobile caravan\n2 PLAC , , Austro-Hungarian Empire\n3 FORM City, County, Country\n```\n\n&lt;/div&gt; residence An address or place of residence where an individual resided.",
        "standard_tag": "RESI",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INDI-TITL": {
        "label": "Title",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Title An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. title A formal designation used by an individual in connection with positions of royalty or other social status, such as Grand Duke.",
        "standard_tag": "TITL",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/INIL": {
        "label": "Initiatory, Latter-Day Saint",
        "payload": "null",
        "specification": "Initiatory, Latter-Day Saint A [Latter-Day Saint Ordinance]. See also `LDS_INDIVIDUAL_ORDINANCE`. Previously, GEDCOM versions 3.0 through 5.3 called this `WAC`; it was not part of 5.4 through 5.5.1. FamilySearch GEDCOM 7.0 reintroduced it with the name `INIL` for consistency with `BAPL`, `CONL`, and `ENDL`. initiatory A religious event where an initiatory ordinance for an individual was performed by priesthood authority in a temple of The Church of Jesus Christ of Latter-day Saints.",
        "standard_tag": "INIL",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "STAT": "https://gedcom.io/terms/v7/ord-STAT",
            "TEMP": "https://gedcom.io/terms/v7/TEMP"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/LANG": {
        "label": "Language",
        "payload": "http://www.w3.org/2001/XMLSchema#Language",
        "specification": "Language The primary human language of the superstructure. The primary language in which\nthe `Text`-typed payloads of the superstructure and its substructures appear.\n\nThe payload of the `LANG` structure is a language tag, as defined by [BCP 47].\nA [registry of component subtags] is maintained publicly by the IANA.\n\nIn the absence of a `LANG` structure, the language is assumed to be\nunspecified; that may also be recorded explicitly with language tag `und`\n(meaning \"undetermined\"). See `https://gedcom.io/terms/v7/HEAD-LANG` for\ninformation about applying language-specific algorithms to text in an\nunspecified language.\n\nIf the text is primarily in one language with a few parts in a different\nlanguage, it is recommended that a language tag identifying the primary\nlanguage be used. If no one language is primary, the language tag `mul`\n(meaning \"multiple\") may be used, but most language-specific algorithms will\ntreat `mul` the same way they do `und`.\n\n&lt;div class=\"note\"&gt;\n\nConversations are ongoing about adding part-of-payload language tagging in a\nfuture version of the specification to provide more fidelity for multilingual\ntext.\n\n&lt;/div&gt;\n\nIf the text is not in any human language and should not be treated as lingual\ncontent, the language tag `zxx` (meaning \"no linguistic content\" or \"not\napplicable\") may be used. An example of `zxx` text might be a diagram\napproximated using characters for their shape, not their meaning.\n\n&lt;div class=\"note\"&gt;\n\nThis specification does not permit `LANG` in every place where human language\ntext might appear. Conversations are ongoing about adding it in more places in\na future version of the specification. Using the current specification,\nadditional language tagging can be accomplished using a [documented extension\ntag] by including the following in the header:\n\n```gedcom\n1 SCHEMA\n2 TAG _LANG https://gedcom.io/terms/v7/LANG\n```\n\nand using the extension tag like so:\n\n```gedcom\n2 DATE 31 AUG 2018\n3 PHRASE 2018年8月31日\n4 _LANG cmn\n```\n\n&lt;/div&gt;",
        "standard_tag": "LANG",
        "substructures": {},
        "superstructures": {
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "SNOTE": "https://gedcom.io/terms/v7/record-SNOTE",
            "TEXT": "https://gedcom.io/terms/v7/TEXT",
            "TRAN": "https://gedcom.io/terms/v7/PLAC-TRAN"
        }
    },
    "https://gedcom.io/terms/v7/LATI": {
        "label": "Latitude",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Latitude A latitudinal coordinate. The payload is either `N` (for a coordinate north of\nthe equator) or `S` (for a coordinate south of the equator) followed by a\ndecimal number of degrees. Minutes and seconds are not used and should be\nconverted to fractional degrees prior to encoding.\n\n&lt;div class=\"example\"&gt;\n\n18 degrees, 9 minutes, and 3.4 seconds North would be formatted as\n`N18.150944`.\n\n&lt;/div&gt;",
        "standard_tag": "LATI",
        "substructures": {},
        "superstructures": {
            "MAP": "https://gedcom.io/terms/v7/MAP"
        }
    },
    "https://gedcom.io/terms/v7/LEFT": {
        "label": "Left crop width",
        "payload": "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
        "specification": "Left crop width Left is a number of pixels to not display from the left side of the image. See `CROP` for more details.",
        "standard_tag": "LEFT",
        "substructures": {},
        "superstructures": {
            "CROP": "https://gedcom.io/terms/v7/CROP"
        }
    },
    "https://gedcom.io/terms/v7/LONG": {
        "label": "Longitude",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Longitude A longitudinal coordinate. The payload is either `E` (for a coordinate east of\nthe prime meridian) or `W` (for a coordinate west of the prime meridian)\nfollowed by a decimal number of degrees. Minutes and seconds are not used and\nshould be converted to fractional degrees prior to encoding.\n\n&lt;div class=\"example\"&gt;\n\n168 degrees, 9 minutes, and 3.4 seconds East would be formatted as\n`E168.150944`.\n\n&lt;/div&gt;",
        "standard_tag": "LONG",
        "substructures": {},
        "superstructures": {
            "MAP": "https://gedcom.io/terms/v7/MAP"
        }
    },
    "https://gedcom.io/terms/v7/MAP": {
        "label": "Map",
        "payload": "null",
        "specification": "Map A representative point for a location, as defined by `LATI` and `LONG`\nsubstructures.\n\nNote that `MAP` provides neither a notion of accuracy (for example, the `MAP`\nfor a birth event may be some distance from the point where the birth occurred)\nnor a notion of region size (for example, the `MAP` for a place \"Belarus\" may\nbe anywhere within that nation's 200,000 square kilometer area).",
        "standard_tag": "MAP",
        "substructures": {
            "LATI": "https://gedcom.io/terms/v7/LATI",
            "LONG": "https://gedcom.io/terms/v7/LONG"
        },
        "superstructures": {
            "PLAC": "https://gedcom.io/terms/v7/PLAC"
        }
    },
    "https://gedcom.io/terms/v7/MARB": {
        "label": "Marriage banns",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Marriage banns A [Family Event]. See also `FAMILY_EVENT_STRUCTURE`. marriage bann Official public notice given that 2 people intend to marry.",
        "standard_tag": "MARB",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/MARC": {
        "label": "Marriage contract",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Marriage contract A [Family Event]. See also `FAMILY_EVENT_STRUCTURE`. marriage contract Recording a formal agreement of marriage, including the prenuptial agreement in which marriage partners reach agreement about the property rights of 1 or both, securing property to their children.",
        "standard_tag": "MARC",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/MARL": {
        "label": "Marriage license",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Marriage license A [Family Event]. See also `FAMILY_EVENT_STRUCTURE`. marriage license Obtaining a legal license to marry.",
        "standard_tag": "MARL",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/MARR": {
        "label": "Marriage",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Marriage A [Family Event]. See also `FAMILY_EVENT_STRUCTURE`. marriage A legal, common-law, or customary event such as a wedding or marriage ceremony that joins 2 partners to create or extend a family unit.",
        "standard_tag": "MARR",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/MARS": {
        "label": "Marriage settlement",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Marriage settlement A [Family Event]. See also `FAMILY_EVENT_STRUCTURE`. marriage settlement Creating an agreement between 2 people contemplating marriage, at which time they agree to release or modify property rights that would otherwise arise from the marriage.",
        "standard_tag": "MARS",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "HUSB": "https://gedcom.io/terms/v7/HUSB",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/WIFE",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/MEDI": {
        "label": "Medium",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Medium An enumerated value from set `https://gedcom.io/terms/v7/enumset-MEDI`\nproviding information about the media or the medium in which information is\nstored.\n\nWhen `MEDI` is a substructure of a `https://gedcom.io/terms/v7/CALN`, it is\nrecommended that its payload describes the medium directly found at that call\nnumber rather than a medium from which it was derived.\n\n&lt;div class=\"example\"&gt;\n\nConsider an asset in a repository that is a digital scan of a book of compiled\nnewspapers; for this asset, the `CALN`.`MEDI` is recommended to be `ELECTRONIC`\nrather than `BOOK` or `NEWSPAPER`.\n\n&lt;/div&gt;\n\nWhen `MEDI` is a substructure of a `https://gedcom.io/terms/v7/FORM`, it is\nrecommended that its payload describes the medium from which it was derived.\n\n&lt;div class=\"example\"&gt;\n\nConsider a digital photo in a multimedia record; for this asset, the\n`FORM`.`MEDI` is recommended to be `PHOTO` rather than `ELECTRONIC`.\n\n&lt;/div&gt;",
        "standard_tag": "MEDI",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "CALN": "https://gedcom.io/terms/v7/CALN",
            "FORM": "https://gedcom.io/terms/v7/FORM"
        }
    },
    "https://gedcom.io/terms/v7/MIME": {
        "label": "Media type",
        "payload": "http://www.w3.org/ns/dcat#mediaType",
        "specification": "Media type Indicates the [media type] of the payload of the superstructure.\n\nAs of version 7.0, only 2 media types are supported by this structure:\n\n- `text/plain` shall be presented to the user as-is, preserving all spacing,\n  line breaks, and so forth.\n\n- `text/html` uses HTML tags to provide presentation information. Applications\n  should support at least the following:\n\n  - `p` and `br` elements for paragraphing and line breaks.\n  - `b`, `i`, `u`, and `s` elements for bold, italic, underlined, and\n    strike-through text (or corresponding display in other locales; see [HTML\n    §4.5] for more).\n  - `sup` and `sub` elements for super- and sub-script.\n  - The 3 XML entities that appear in text: `&amp;amp;`, `&amp;lt;` `&amp;gt;`. Note that\n    `&amp;quote;` and `&amp;apos;` are only needed in attributes. Other entities should\n    be represented as their respective Unicode characters instead.\n\n  Supporting more of HTML is encouraged. Unsupported tags should be ignored\n  during display.\n\n&lt;div class=\"note\"&gt;\n\nApplications are welcome to support more XML entities or HTML character\nreferences in their user interface. However, exporting must only use the core\nXML entities, translating any other entities into their corresponding Unicode\ncharacters.\n\n&lt;/div&gt;\n\n&lt;div class=\"note\"&gt;\n\nApplications are welcome to support additional HTML elements, but they should\nensure that content is meaningful if those extra elements are ignored and only\ntheir content text is displayed.\n\n&lt;/div&gt;\n\n&lt;div class=\"note\"&gt;\n\nMedia types are also used by external files, as described under `FORM`.\nExternal file media types are not limited to `text/plain` and `text/html`.\n\n&lt;/div&gt;\n\nIf needed, `text/html` can be converted to `text/plain` using the following\nsteps:\n\n1. Replace any sequence of 1 or more spaces, tabs, and line breaks with a\n   single space\n2. Case-insensitively replace each `&lt;p`...`&gt;`, `&lt;/p`...`&gt;`, and `&lt;br`...`&gt;`\n   with a line break\n3. Remove all other `&lt;`...`&gt;` tags\n4. Replace each `&amp;lt;` with `&lt;` and `&amp;gt;` with `&gt;`\n5. Replace each `&amp;amp;` with `&amp;`",
        "standard_tag": "MIME",
        "substructures": {},
        "superstructures": {
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "SNOTE": "https://gedcom.io/terms/v7/record-SNOTE",
            "TEXT": "https://gedcom.io/terms/v7/TEXT",
            "TRAN": "https://gedcom.io/terms/v7/NOTE-TRAN"
        }
    },
    "https://gedcom.io/terms/v7/NAME": {
        "label": "Name",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Name The name of the superstructure's subject, represented as a simple string.",
        "standard_tag": "NAME",
        "substructures": {},
        "superstructures": {
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "SOUR": "https://gedcom.io/terms/v7/HEAD-SOUR",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM"
        }
    },
    "https://gedcom.io/terms/v7/NAME-TRAN": {
        "label": "Translation",
        "payload": "https://gedcom.io/terms/v7/type-Name",
        "specification": "Translation A type of `TRAN` substructure specific to [Personal Names]. Each `NAME`.`TRAN`\nmust have a `LANG` substructure. See also `INDI`.`NAME`.\n\n&lt;div class=\"example\"&gt;\n\nThe following presents a name in Mandarin, transliterated using Pinyin\n\n```gedcom\n1 NAME /孔/德庸\n2 GIVN 德庸\n2 SURN 孔\n2 TRAN /Kǒng/ Déyōng\n3 GIVN Déyōng\n3 SURN Kǒng\n3 LANG zh-pinyin\n```\n\n&lt;/div&gt; A representation of the superstructure's data in a different format.\n\nIn some situations it is desirable to provide the same semantic content in\nmultiple formats. Where this is desirable, a `TRAN` substructure is used, where\nthe specific format is given in its language tag substructure, media type\nsubstructure, or both.\n\nDifferent `TRAN` structures are used in different contexts to fully capture the\nstructure of the information being presented in multiple formats. In all cases,\na `TRAN` structure's payload and substructures should provide only information\nalso contained in the `TRAN` structures' superstructure, but provide it in a\nnew language, script, or media type.\n\nEach `TRAN` substructure must have either a language tag or a media type or\nboth. Each `TRAN` structure must differ from its superstructure and from every\nother `TRAN` substructure of its superstructure in either its language tag or\nits media type or both.",
        "standard_tag": "TRAN",
        "substructures": {
            "GIVN": "https://gedcom.io/terms/v7/GIVN",
            "LANG": "https://gedcom.io/terms/v7/LANG",
            "NICK": "https://gedcom.io/terms/v7/NICK",
            "NPFX": "https://gedcom.io/terms/v7/NPFX",
            "NSFX": "https://gedcom.io/terms/v7/NSFX",
            "SPFX": "https://gedcom.io/terms/v7/SPFX",
            "SURN": "https://gedcom.io/terms/v7/SURN"
        },
        "superstructures": {
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME"
        }
    },
    "https://gedcom.io/terms/v7/NAME-TYPE": {
        "label": "Type",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Type An enumerated value from set `https://gedcom.io/terms/v7/enumset-NAME-TYPE` indicating the type of the name.",
        "standard_tag": "TYPE",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME"
        }
    },
    "https://gedcom.io/terms/v7/NATI": {
        "label": "Nationality",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Nationality An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. nationality An individual's national heritage or origin, or other folk, house, kindred, lineage, or tribal interest.",
        "standard_tag": "NATI",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/NATU": {
        "label": "Naturalization",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Naturalization An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. naturalization Obtaining citizenship.",
        "standard_tag": "NATU",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/NICK": {
        "label": "Nickname",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Nickname A descriptive or familiar name that is used instead of, or in addition to,\none’s official or legal name.\n\n&lt;div class=\"note\"&gt;\n\nThe label \"nickname\" and description text of this structure were introduced\nwith version 5.5 in 1996, but are understood differently by different users.\nSome use `NICK` only for names that would be inappropriate in formal settings.\nSome use it for pseudonyms regardless of where they are used. Some use it for\nany variant of a name that is not the one used on legal documents. Because all\nof these uses, and likely others as well, are common in existing data, no\nfurther clarification of the meaning of the `NICK` structure is possible\nwithout contradicting some existing data.\n\n&lt;/div&gt;",
        "standard_tag": "NICK",
        "substructures": {},
        "superstructures": {
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "TRAN": "https://gedcom.io/terms/v7/NAME-TRAN"
        }
    },
    "https://gedcom.io/terms/v7/NMR": {
        "label": "Number of marriages",
        "payload": "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
        "specification": "Number of marriages An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. number of marriages The number of times this person has participated in a family as a spouse or parent.",
        "standard_tag": "NMR",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/NO": {
        "label": "Did not happen",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Did not happen An enumerated value from set `https://gedcom.io/terms/v7/enumset-EVEN`\nidentifying an event type which did not occur to the superstructure's subject.\nA specific payload `NO XYZ` should only appear where `XYZ` would be legal.\n\nSee `NON_EVENT_STRUCTURE` for more details. Indicates that a specific type of event, given in the payload, did not happen\nwithin a given date period (or never happened if there is no `DATE`\nsubstructure).\n\nSubstructures may provide discussion about the non-occurrence of the event but\nmust not limit the meaning of what did not occur. No substructure other than\n`DATE` may restrict the breadth of that negative assertion.\n\n&lt;div class=\"example\"&gt;\n\n`1 NO MARR` means \"no marriage occurred\"\n\n&lt;/div&gt;\n\n&lt;div class=\"example\"&gt;\n\n```gedcom\n1 NO MARR\n2 DATE TO 24 MAR 1880\n```\n\nmeans \"no marriage had occurred as of March 24^th^, 1880\"\n\n&lt;/div&gt;",
        "standard_tag": "NO",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/NO-DATE",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/NO-DATE": {
        "label": "Date",
        "payload": "https://gedcom.io/terms/v7/type-Date#period",
        "specification": "Date The `DatePeriod` during which the event did not occur or the attribute did not apply.",
        "standard_tag": "DATE",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "NO": "https://gedcom.io/terms/v7/NO"
        }
    },
    "https://gedcom.io/terms/v7/NOTE": {
        "label": "Note",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Note A `NOTE_STRUCTURE`, containing additional information provided by the submitter\nfor understanding the enclosing data.\n\nWhen a substructure of `HEAD`, it should describe the contents of the document\nin terms of \"ancestors or descendants of\" so that the person receiving the data\nknows what genealogical information the document contains.",
        "standard_tag": "NOTE",
        "substructures": {
            "LANG": "https://gedcom.io/terms/v7/LANG",
            "MIME": "https://gedcom.io/terms/v7/MIME",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TRAN": "https://gedcom.io/terms/v7/NOTE-TRAN"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "BAPL": "https://gedcom.io/terms/v7/BAPL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CONL": "https://gedcom.io/terms/v7/CONL",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DATA": "https://gedcom.io/terms/v7/DATA",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENDL": "https://gedcom.io/terms/v7/ENDL",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "FAMC": "https://gedcom.io/terms/v7/INDI-FAMC",
            "FAMS": "https://gedcom.io/terms/v7/FAMS",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "HEAD": "https://gedcom.io/terms/v7/HEAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "INIL": "https://gedcom.io/terms/v7/INIL",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "NO": "https://gedcom.io/terms/v7/NO",
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SLGC": "https://gedcom.io/terms/v7/SLGC",
            "SLGS": "https://gedcom.io/terms/v7/SLGS",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/NOTE-TRAN": {
        "label": "Translation",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Translation A type of `TRAN` for unstructured human-readable text, such as is found in\n`NOTE` and `SNOTE` payloads. Each `https://gedcom.io/terms/v7/NOTE-TRAN` must\nhave either a `LANG` substructure or a `MIME` substructure or both. If either\nis missing, it is assumed to have the same value as the superstructure. See\nalso `NOTE` and `SNOTE`.\n\n&lt;div class=\"example\"&gt;\n\nThe following presents the same note in HTML-format English; in plain-text with\nthe same language as the superstructure (English); and in Spanish with the same\nmedia type as the superstructure (HTML).\n\n```gedcom\n1 NAME Arete /Hernandez/\n2 NOTE Named after Arete from &lt;i&gt;The Odyssey&lt;/i&gt;\n3 LANG en\n3 MIME text/html\n3 TRAN Named after Arete from \"The Odyssey\"\n4 MIME text/plain\n3 TRAN Nombrada en honor a Arete de &lt;i&gt;La Odisea&lt;/i&gt;\n4 LANG es\n```\n\n&lt;/div&gt;\n\nIt is recommended that text given in `text/html` should only be translated into\n`text/plain` if the resulting text is different from the text created by the\nHTML-to-text conversion process defined in `https://gedcom.io/terms/v7/MIME`. A representation of the superstructure's data in a different format.\n\nIn some situations it is desirable to provide the same semantic content in\nmultiple formats. Where this is desirable, a `TRAN` substructure is used, where\nthe specific format is given in its language tag substructure, media type\nsubstructure, or both.\n\nDifferent `TRAN` structures are used in different contexts to fully capture the\nstructure of the information being presented in multiple formats. In all cases,\na `TRAN` structure's payload and substructures should provide only information\nalso contained in the `TRAN` structures' superstructure, but provide it in a\nnew language, script, or media type.\n\nEach `TRAN` substructure must have either a language tag or a media type or\nboth. Each `TRAN` structure must differ from its superstructure and from every\nother `TRAN` substructure of its superstructure in either its language tag or\nits media type or both.",
        "standard_tag": "TRAN",
        "substructures": {
            "LANG": "https://gedcom.io/terms/v7/LANG",
            "MIME": "https://gedcom.io/terms/v7/MIME"
        },
        "superstructures": {
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "SNOTE": "https://gedcom.io/terms/v7/record-SNOTE"
        }
    },
    "https://gedcom.io/terms/v7/NPFX": {
        "label": "Name prefix",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Name prefix Text that appears on a name line before the given and surname parts of a name.",
        "standard_tag": "NPFX",
        "substructures": {},
        "superstructures": {
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "TRAN": "https://gedcom.io/terms/v7/NAME-TRAN"
        }
    },
    "https://gedcom.io/terms/v7/NSFX": {
        "label": "Name suffix",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Name suffix Text which appears on a name line after or behind the given and surname parts of a name.",
        "standard_tag": "NSFX",
        "substructures": {},
        "superstructures": {
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "TRAN": "https://gedcom.io/terms/v7/NAME-TRAN"
        }
    },
    "https://gedcom.io/terms/v7/OBJE": {
        "label": "Object",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-OBJE&gt;@",
        "specification": "Object See `MULTIMEDIA_LINK`. Links the superstructure to the `MULTIMEDIA_RECORD` with the given pointer.\n\nThe optional `CROP` substructure indicates that a subregion of an image\nrepresents or applies to the superstructure.\n\nThe optional `TITL` substructure supersedes any `OBJE.FILE.TITL` substructures\nincluded in the `MULTIMEDIA_RECORD`.",
        "standard_tag": "OBJE",
        "substructures": {
            "CROP": "https://gedcom.io/terms/v7/CROP",
            "TITL": "https://gedcom.io/terms/v7/TITL"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/OCCU": {
        "label": "Occupation",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Occupation An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. occupation The type of work or profession of an individual.",
        "standard_tag": "OCCU",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/ORDN": {
        "label": "Ordination",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Ordination An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. ordination Receiving authority to act in religious matters.",
        "standard_tag": "ORDN",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/PAGE": {
        "label": "Page",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Page A specific location within the information referenced. For a published work,\nthis could include the volume of a multi-volume work and the page number or\nnumbers. For a periodical, it could include volume, issue, and page numbers.\nFor a newspaper, it could include a date, page number, and column number. For\nan unpublished source or microfilmed works, this could be a film or sheet\nnumber, page number, or frame number. A census record might have an enumerating\ndistrict, page number, line number, dwelling number, and family number.\n\nIt is recommended that the data in this field be formatted comma-separated with\nlabel: value pairs\n\n&lt;div class=\"example\"&gt;\n\n```gedcom\n2 SOUR @S1@\n3 PAGE Film: 1234567, Frame: 344, Line: 28\n```\n\n&lt;/div&gt;\n\nIf the superstructure's pointer is `@VOID@` then there is no information\nreferenced and the `PAGE` may describe the entire source.\n\n&lt;div class=\"example\"&gt;\n\n```gedcom\n1 DSCR Tall enough his head touched the ceiling\n2 SOUR @VOID@\n3 PAGE His grand-daughter Lydia told me this in 1980\n```\n\n&lt;/div&gt;",
        "standard_tag": "PAGE",
        "substructures": {},
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/SOUR"
        }
    },
    "https://gedcom.io/terms/v7/PEDI": {
        "label": "Pedigree",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Pedigree An enumerated value from set `https://gedcom.io/terms/v7/enumset-PEDI` indicating the type of child-to-family relationship represented by the superstructure.",
        "standard_tag": "PEDI",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "FAMC": "https://gedcom.io/terms/v7/INDI-FAMC"
        }
    },
    "https://gedcom.io/terms/v7/PHON": {
        "label": "Phone",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Phone A telephone number. Telephone numbers have many regional variations and can\ncontain non-digit characters. Users should be encouraged to use\ninternationalized telephone numbers rather than local versions. As a starting\npoint for this recommendation, there are international standards that use a\n\"'+'\" shorthand for the international prefix (for example, in place of \"011\" in\nthe US or \"00\" in the UK). Examples are `+1 (555) 555-1234` (US) or\n`+44 20 1234 1234` (UK).\n\nSee ITU standards [E.123] and [E.164] for more information.",
        "standard_tag": "PHON",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CORP": "https://gedcom.io/terms/v7/CORP",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/PHRASE": {
        "label": "Phrase",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Phrase Textual information that cannot be expressed in the superstructure due to the\nlimitations of its data type. A `PHRASE` may restate information contained in\nthe superstructure, but doing so is not recommended unless it is needed for\nclarity.\n\n&lt;div class=\"example\"&gt;\n\nA date interpreted from the phrase \"The Feast of St John\" might be\n\n```gedcom\n2 DATE 24 JUN 1852\n3 PHRASE During the feast of St John\n```\n\n&lt;/div&gt;\n\n&lt;div class=\"example\"&gt;\n\nA record using `1648/9` to indicate a change in new year might become\n\n```gedcom\n2 DATE 30 JAN 1649\n3 PHRASE 30th of January, 1648/9\n```\n\n&lt;/div&gt;\n\n&lt;div class=\"example\"&gt;\n\nA record using `1648/9` to indicate uncertainty in the year might become\n\n```gedcom\n2 DATE BET 1648 AND 1649\n3 PHRASE 1648/9\n```\n\n&lt;/div&gt;\n\n&lt;div class=\"example\"&gt;\n\nA record using `Q1 1867` to indicate an event occurred sometime within the\nfirst quarter of 1867 might become\n\n```gedcom\n2 DATE BET 1 JAN 1867 AND 31 MAR 1867\n3 PHRASE Q1 1867\n```\n\n&lt;/div&gt;\n\n&lt;div class=\"example\"&gt;\n\nA record defining the Maid of Honor in a marriage might become\n\n```gedcom\n1 MARR\n2 ASSO @I2@\n3 ROLE OTHER\n4 PHRASE Maid of Honor\n```\n\n&lt;/div&gt;\n\n&lt;div class=\"example\"&gt;\n\nA name given to a foundling orphan might be\n\n```gedcom\n1 NAME Mary //\n2 GIVN Mary\n2 TYPE OTHER\n3 PHRASE given by orphanage\n```\n\n&lt;/div&gt;",
        "standard_tag": "PHRASE",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/FAMC-ADOP",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "ALIA": "https://gedcom.io/terms/v7/ALIA",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CHIL": "https://gedcom.io/terms/v7/CHIL",
            "DATE": "https://gedcom.io/terms/v7/NO-DATE",
            "EVEN": "https://gedcom.io/terms/v7/SOUR-EVEN",
            "HUSB": "https://gedcom.io/terms/v7/FAM-HUSB",
            "MEDI": "https://gedcom.io/terms/v7/MEDI",
            "PEDI": "https://gedcom.io/terms/v7/PEDI",
            "ROLE": "https://gedcom.io/terms/v7/ROLE",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "STAT": "https://gedcom.io/terms/v7/FAMC-STAT",
            "TYPE": "https://gedcom.io/terms/v7/NAME-TYPE",
            "WIFE": "https://gedcom.io/terms/v7/FAM-WIFE"
        }
    },
    "https://gedcom.io/terms/v7/PLAC": {
        "label": "Place",
        "payload": "https://gedcom.io/terms/v7/type-List#Text",
        "specification": "Place The principal place in which the superstructure's subject occurred, represented\nas a [List] of jurisdictional entities in a sequence from the lowest to the\nhighest jurisdiction, where \"jurisdiction\" includes units in a political,\necclesiastical, and geographical hierarchies and may include units of any size,\nsuch as a continent, \"at sea\", or a specific building, farm, or cemetery. As\nwith other lists, the jurisdictions are separated by commas. Any jurisdiction's\nname that is missing is still accounted for by an empty string in the list.\n\nThe type of each jurisdiction is given in the `PLAC`.`FORM` substructure, if\npresent, or in the `HEAD`.`PLAC`.`FORM` structure. If neither is present, the\njurisdictional types are unspecified beyond the lowest-to-highest order noted\nabove. &lt;div class=\"deprecation\"&gt;\n\nHaving an `EXID` without an `EXID`.`TYPE` substructure is deprecated. The\nmeaning of an `EXID` depends on its `EXID`.`TYPE`. The cardinality of\n`EXID`.`TYPE` will be changed to `{1:1}` in version 8.0.\n\n&lt;/div&gt;\n\nA place, which can be represented in several ways:\n\n- The payload contains a comma-separated list of region names, ordered from\n  smallest to largest. The specific meaning of each element is given by the\n  `FORM` substructure, or in the `HEAD`.`PLAC`.`FORM` if there is no `FORM`\n  substructure. If neither `FORM` exists, the meaning of the elements are not\n  defined in this specification beyond being names of jurisdictions of some\n  kind, ordered from smallest to largest.\n\n  &lt;div class=\"note\"&gt;\n    Some applications and users have defaulted to assuming a `FORM` of \"City, County, State, Country\",\n    and some applications even ignore any `FORM` substructures and treat payloads with a smaller number of\n    elements as if they had additional blank elements at the end.\n    &lt;/div&gt;\n\n  Elements should be left blank if they are unknown, do not apply to the\n  location, or are too specific for the region in question.\n\n  &lt;div class=\"example\"&gt;\n    A record describing births throughout Oneida county could be recorded as\n\n  ```gedcom\n  0 @S1@ SOUR\n  1 DATA\n  2 EVEN BIRT\n  3 PLAC , Oneida, Idaho, USA\n  4 FORM City, County, State, Country\n  ```\n\n  &lt;/div&gt;\n\n- The payload may be translated or transliterated into different languages or\n  scripts using the `TRAN` substructure. It should use the same `FORM` as the\n  payload.\n\n- Global coordinates may be presented in the `MAP` substructure\n\n&lt;div class=\"note\"&gt;\n\nThis specification does not support places where a region name contains a\ncomma. An alternative system for representing locations is likely to be added\nin a later version.\n\n&lt;/div&gt;",
        "standard_tag": "PLAC",
        "substructures": {
            "EXID": "https://gedcom.io/terms/v7/EXID",
            "FORM": "https://gedcom.io/terms/v7/PLAC-FORM",
            "LANG": "https://gedcom.io/terms/v7/LANG",
            "MAP": "https://gedcom.io/terms/v7/MAP",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "TRAN": "https://gedcom.io/terms/v7/PLAC-TRAN"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPL": "https://gedcom.io/terms/v7/BAPL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CONL": "https://gedcom.io/terms/v7/CONL",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENDL": "https://gedcom.io/terms/v7/ENDL",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INIL": "https://gedcom.io/terms/v7/INIL",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SLGC": "https://gedcom.io/terms/v7/SLGC",
            "SLGS": "https://gedcom.io/terms/v7/SLGS",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/PLAC-FORM": {
        "label": "Format",
        "payload": "https://gedcom.io/terms/v7/type-List#Text",
        "specification": "Format A comma-separated list of jurisdictional titles, which has the same number of\nelements and in the same order as the `PLAC` structure. As with `PLAC`, this\nshall be ordered from lowest to highest jurisdiction.\n\n&lt;div class=\"example\"&gt;\n\nThe following represents Baltimore, a city that is not within a county.\n\n```gedcom\n2 PLAC Baltimore, , Maryland, USA\n3 FORM City, County, State, Country\n```\n\n&lt;/div&gt;",
        "standard_tag": "FORM",
        "substructures": {},
        "superstructures": {
            "PLAC": "https://gedcom.io/terms/v7/PLAC"
        }
    },
    "https://gedcom.io/terms/v7/PLAC-TRAN": {
        "label": "Translation",
        "payload": "https://gedcom.io/terms/v7/type-List#Text",
        "specification": "Translation A type of `TRAN` substructure specific to places. Each `PLAC`.`TRAN` must have\na `LANG` substructure. See also `PLAC`.\n\n&lt;div class=\"example\"&gt;\n\nThe following presents a place in Japanese with a romaji transliteration and\nEnglish translation\n\n```gedcom\n2 PLAC 千代田, 東京, 日本\n3 FORM 区, 都, 国\n3 LANG ja\n3 TRAN Chiyoda, Tokyo, Nihon\n4 LANG ja-Latn\n3 TRAN Chiyoda, Tokyo, Japan\n4 LANG en\n```\n\n&lt;/div&gt; A representation of the superstructure's data in a different format.\n\nIn some situations it is desirable to provide the same semantic content in\nmultiple formats. Where this is desirable, a `TRAN` substructure is used, where\nthe specific format is given in its language tag substructure, media type\nsubstructure, or both.\n\nDifferent `TRAN` structures are used in different contexts to fully capture the\nstructure of the information being presented in multiple formats. In all cases,\na `TRAN` structure's payload and substructures should provide only information\nalso contained in the `TRAN` structures' superstructure, but provide it in a\nnew language, script, or media type.\n\nEach `TRAN` substructure must have either a language tag or a media type or\nboth. Each `TRAN` structure must differ from its superstructure and from every\nother `TRAN` substructure of its superstructure in either its language tag or\nits media type or both.",
        "standard_tag": "TRAN",
        "substructures": {
            "LANG": "https://gedcom.io/terms/v7/LANG"
        },
        "superstructures": {
            "PLAC": "https://gedcom.io/terms/v7/PLAC"
        }
    },
    "https://gedcom.io/terms/v7/POST": {
        "label": "Postal code",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Postal code A code used by a postal service to identify an area to facilitate mail handling. See `ADDRESS_STRUCTURE` for more details.",
        "standard_tag": "POST",
        "substructures": {},
        "superstructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR"
        }
    },
    "https://gedcom.io/terms/v7/PROB": {
        "label": "Probate",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Probate An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. probate Judicial determination of the validity of a will. It may indicate several related court activities over several dates.",
        "standard_tag": "PROB",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/PROP": {
        "label": "Property",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Property An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. property Pertaining to possessions such as real estate or other property of interest.",
        "standard_tag": "PROP",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/PUBL": {
        "label": "Publication",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Publication When and where the record was created. For published works, this includes\ninformation such as the city of publication, name of the publisher, and year of\npublication.\n\nFor an unpublished work, it includes the date the record was created and the\nplace where it was created, such as the county and state of residence of a\nperson making a declaration for a pension or the city and state of residence of\nthe writer of a letter.",
        "standard_tag": "PUBL",
        "substructures": {},
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/QUAY": {
        "label": "Quality of data",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Quality of data An enumerated value from set `https://gedcom.io/terms/v7/enumset-QUAY` indicating the credibility of a piece of information, based on its supporting evidence. Some systems use this feature to rank multiple conflicting opinions for display of most likely information first. It is not intended to eliminate the receivers' need to evaluate the evidence for themselves.",
        "standard_tag": "QUAY",
        "substructures": {},
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/SOUR"
        }
    },
    "https://gedcom.io/terms/v7/REFN": {
        "label": "Reference",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Reference A user-defined number or text that the submitter uses to identify the\nsuperstructure. For instance, it may be a record number within the submitter's\nautomated or manual system, or it may be a page and position number on a\npedigree chart.\n\nThis is metadata about the structure itself, not data about its subject.\nMultiple structures describing different aspects of the same subject must not\nhave the same `REFN` value.",
        "standard_tag": "REFN",
        "substructures": {
            "TYPE": "https://gedcom.io/terms/v7/TYPE"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "SNOTE": "https://gedcom.io/terms/v7/record-SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM"
        }
    },
    "https://gedcom.io/terms/v7/RELI": {
        "label": "Religion",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Religion A religious denomination associated with the event or attribute described by the superstructure.",
        "standard_tag": "RELI",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/REPO": {
        "label": "Repository",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-REPO&gt;@",
        "specification": "Repository See `SOURCE_REPOSITORY_CITATION`. This structure is used within a source record to point to a name and address record of the holder of the source document. Formal and informal repository name and addresses are stored in the `REPOSITORY_RECORD`. More formal repositories, such as the Family History Library, should show a call number of the source at that repository. The call number of that source should be recorded using a `CALN` substructure.",
        "standard_tag": "REPO",
        "substructures": {
            "CALN": "https://gedcom.io/terms/v7/CALN",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE"
        },
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/RESN": {
        "label": "Restriction",
        "payload": "https://gedcom.io/terms/v7/type-List#Enum",
        "specification": "Restriction A [List] of enumerated values from set\n`https://gedcom.io/terms/v7/enumset-RESN` signifying access to information may\nbe denied or otherwise restricted.\n\nThe `RESN` structure is provided to assist software in filtering data that\nshould not be exported or otherwise used in a particular context. It is\nrecommended that tools provide an interface to allow users to filter data on\nexport such that certain `RESN` structure payload entries result in the `RESN`\nstructure and its superstructure being removed from the export. Such removal\nmust abide by some constraints: see [Removing data] for more details.\n\nThis is metadata about the structure itself, not data about its subject.",
        "standard_tag": "RESN",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/RETI": {
        "label": "Retirement",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Retirement An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. retirement Exiting an occupational relationship with an employer after a qualifying time period.",
        "standard_tag": "RETI",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/ROLE": {
        "label": "Role",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Role An enumerated value from set `https://gedcom.io/terms/v7/enumset-ROLE`\nindicating what role this person played in an event or person's life.\n\n&lt;div class=\"example\"&gt;\n\nThe following indicates a child's birth record as the source of the mother's\nname:\n\n```gedcom\n0 @I1@ INDI\n1 NAME Mary //\n2 SOUR @S1@\n3 EVEN BIRT\n4 ROLE MOTH\n```\n\n&lt;/div&gt;\n\n&lt;div class=\"example\"&gt;\n\nThe following indicates that a person's best friend was a witness at their\nbaptism:\n\n```gedcom\n0 @I2@ INDI\n1 ASSO @I3@\n2 ROLE FRIEND\n3 PHRASE best friend\n1 BAPM\n2 ASSO @I3@\n3 ROLE WITN\n```\n\n&lt;/div&gt;",
        "standard_tag": "ROLE",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE"
        },
        "superstructures": {
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "EVEN": "https://gedcom.io/terms/v7/SOUR-EVEN"
        }
    },
    "https://gedcom.io/terms/v7/SCHMA": {
        "label": "Extension schema",
        "payload": "null",
        "specification": "Extension schema A container for storing meta-information about the extension tags used in this document. See [Extensions] for more details.",
        "standard_tag": "SCHMA",
        "substructures": {
            "TAG": "https://gedcom.io/terms/v7/TAG"
        },
        "superstructures": {
            "HEAD": "https://gedcom.io/terms/v7/HEAD"
        }
    },
    "https://gedcom.io/terms/v7/SDATE": {
        "label": "Sort date",
        "payload": "https://gedcom.io/terms/v7/type-Date",
        "specification": "Sort date A date to be used as a sorting hint. It is intended for use when the actual\ndate is unknown, but the display order may be dependent on date.\n\nIf both a `DATE` and `SDATE` are present in the same structure, the `SDATE`\nshould be used for sorting and positioning while the `DATE` should be displayed\nas the date of the structure.\n\n`SDATE` and its substructures (including `PHRASE`, `TIME`, and any extension\nstructures) should be used only as sorting hints, not to convey historical\nmeaning.\n\nIt is recommended to use a payload that matches\n`[[day D] month D] year [D epoch]`. Other DateValue forms may have unreliable\neffects on sorting. Including a month and day is encouraged to help different\napplications sort dates the same way, as the relative ordering of dates with\ndifferent levels of precision is not well defined.",
        "standard_tag": "SDATE",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE",
            "TIME": "https://gedcom.io/terms/v7/TIME"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/SEX": {
        "label": "Sex",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Sex An enumerated value from set `https://gedcom.io/terms/v7/enumset-SEX` that indicates the sex of the individual at birth.",
        "standard_tag": "SEX",
        "substructures": {},
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/SLGC": {
        "label": "Sealing, child",
        "payload": "null",
        "specification": "Sealing, child A [Latter-Day Saint Ordinance]. See also `LDS_INDIVIDUAL_ORDINANCE`. sealing child A religious event pertaining to the sealing of a child to his or her parents in a temple ceremony of The Church of Jesus Christ of Latter-day Saints.",
        "standard_tag": "SLGC",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "FAMC": "https://gedcom.io/terms/v7/FAMC",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "STAT": "https://gedcom.io/terms/v7/ord-STAT",
            "TEMP": "https://gedcom.io/terms/v7/TEMP"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/SLGS": {
        "label": "Sealing, spouse",
        "payload": "null",
        "specification": "Sealing, spouse A [Latter-Day Saint Ordinance]. See also `LDS_SPOUSE_SEALING`. Ordinances performed by members of The Church of Jesus Christ of Latter-day Saints; see [Latter-day Saint Ordinances] for descriptions of each ordinance type. sealing spouse A religious event pertaining to the sealing of a husband and wife in a temple ceremony of The Church of Jesus Christ of Latter-day Saints. (See also [`MARR`])",
        "standard_tag": "SLGS",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "STAT": "https://gedcom.io/terms/v7/ord-STAT",
            "TEMP": "https://gedcom.io/terms/v7/TEMP"
        },
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM"
        }
    },
    "https://gedcom.io/terms/v7/SNOTE": {
        "label": "Shared note",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-SNOTE&gt;@",
        "specification": "Shared note A pointer to a note that is shared by multiple structures. See `NOTE_STRUCTURE` for more details.",
        "standard_tag": "SNOTE",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "BAPL": "https://gedcom.io/terms/v7/BAPL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CONL": "https://gedcom.io/terms/v7/CONL",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DATA": "https://gedcom.io/terms/v7/DATA",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENDL": "https://gedcom.io/terms/v7/ENDL",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "FAMC": "https://gedcom.io/terms/v7/INDI-FAMC",
            "FAMS": "https://gedcom.io/terms/v7/FAMS",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "HEAD": "https://gedcom.io/terms/v7/HEAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "INIL": "https://gedcom.io/terms/v7/INIL",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "NO": "https://gedcom.io/terms/v7/NO",
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SLGC": "https://gedcom.io/terms/v7/SLGC",
            "SLGS": "https://gedcom.io/terms/v7/SLGS",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/SOUR": {
        "label": "Source",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-SOUR&gt;@",
        "specification": "Source A description of the relevant part of a source to support the superstructure's data. See `SOURCE_CITATION` for more details. A citation indicating that the pointed-to source record supports the claims\nmade in the superstructure. Substructures provide additional information about\nhow that source applies to the subject of the citation's superstructure:\n\n- `PAGE`: where in the source the relevant material can be found.\n- `DATA`: the relevant data from the source.\n- `EVEN`: what event the relevant material was recording.\n- `QUAY`: an estimation of the reliability of the source in regard to these\n  claims.\n- `MULTIMEDIA_LINK`: digital copies of the cited part of the source\n\nIt is recommended that every `SOURCE_CITATION` point to a `SOURCE_RECORD`.\nHowever, a `voidPtr` can be used with the citation text in a `PAGE`\nsubstructure. The `PAGE` is defined to express a \"specific location within the\ninformation referenced;\" with a `voidPtr` there is no information referenced,\nso the `PAGE` may describe the entire source.\n\nA `SOURCE_CITATION` can contain a `NOTE_STRUCTURE`, which in turn can contain a\n`SOURCE_CITATION`, allowing potentially unbounded nesting of structures.\nBecause each dataset is finite, this nesting is also guaranteed to be finite.",
        "standard_tag": "SOUR",
        "substructures": {
            "DATA": "https://gedcom.io/terms/v7/SOUR-DATA",
            "EVEN": "https://gedcom.io/terms/v7/SOUR-EVEN",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PAGE": "https://gedcom.io/terms/v7/PAGE",
            "QUAY": "https://gedcom.io/terms/v7/QUAY",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE"
        },
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "BAPL": "https://gedcom.io/terms/v7/BAPL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CONL": "https://gedcom.io/terms/v7/CONL",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENDL": "https://gedcom.io/terms/v7/ENDL",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "INIL": "https://gedcom.io/terms/v7/INIL",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "NO": "https://gedcom.io/terms/v7/NO",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SLGC": "https://gedcom.io/terms/v7/SLGC",
            "SLGS": "https://gedcom.io/terms/v7/SLGS",
            "SNOTE": "https://gedcom.io/terms/v7/record-SNOTE",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/SOUR-DATA": {
        "label": "Data",
        "payload": "null",
        "specification": "Data See `https://gedcom.io/terms/v7/DATA`.",
        "standard_tag": "DATA",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "TEXT": "https://gedcom.io/terms/v7/TEXT"
        },
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/SOUR"
        }
    },
    "https://gedcom.io/terms/v7/SOUR-EVEN": {
        "label": "Event",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Event An enumerated value from set `https://gedcom.io/terms/v7/enumset-EVENATTR` indicating the type of event or attribute which was responsible for the source entry being recorded. For example, if the entry was created to record a birth of a child, then the type would be `BIRT` regardless of the assertions made from that record, such as the mother's name or mother's birth date.",
        "standard_tag": "EVEN",
        "substructures": {
            "PHRASE": "https://gedcom.io/terms/v7/PHRASE",
            "ROLE": "https://gedcom.io/terms/v7/ROLE"
        },
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/SOUR"
        }
    },
    "https://gedcom.io/terms/v7/SPFX": {
        "label": "Surname prefix",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Surname prefix A name piece used as a non-indexing pre-part of a surname.",
        "standard_tag": "SPFX",
        "substructures": {},
        "superstructures": {
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "TRAN": "https://gedcom.io/terms/v7/NAME-TRAN"
        }
    },
    "https://gedcom.io/terms/v7/SSN": {
        "label": "Social security number",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Social security number An [Individual Attribute]. See also `INDIVIDUAL_ATTRIBUTE_STRUCTURE`. social security number A number assigned by the United States Social Security Administration, used for tax identification purposes. It is a type of `IDNO`.",
        "standard_tag": "SSN",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/STAE": {
        "label": "State",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "State A geographical division of a larger jurisdictional area, such as a state within the United States of America. See `ADDRESS_STRUCTURE` for more details.",
        "standard_tag": "STAE",
        "substructures": {},
        "superstructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR"
        }
    },
    "https://gedcom.io/terms/v7/SUBM": {
        "label": "Submitter",
        "payload": "@&lt;https://gedcom.io/terms/v7/record-SUBM&gt;@",
        "specification": "Submitter A contributor of information in the substructure. This is metadata about the structure itself, not data about its subject.",
        "standard_tag": "SUBM",
        "substructures": {},
        "superstructures": {
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "HEAD": "https://gedcom.io/terms/v7/HEAD",
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/SUBM-LANG": {
        "label": "Language",
        "payload": "http://www.w3.org/2001/XMLSchema#Language",
        "specification": "Language A language the subject of that record understands.\n\nThe payload of the `LANG` structure is a language tag, as defined by [BCP 47].",
        "standard_tag": "LANG",
        "substructures": {},
        "superstructures": {
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM"
        }
    },
    "https://gedcom.io/terms/v7/SURN": {
        "label": "Surname",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Surname A family name passed on or used by members of a family.",
        "standard_tag": "SURN",
        "substructures": {},
        "superstructures": {
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "TRAN": "https://gedcom.io/terms/v7/NAME-TRAN"
        }
    },
    "https://gedcom.io/terms/v7/TAG": {
        "label": "Extension tag",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Extension tag Information relating to a single extension tag as used in this document. See [Extensions] for more details.",
        "standard_tag": "TAG",
        "substructures": {},
        "superstructures": {
            "SCHMA": "https://gedcom.io/terms/v7/SCHMA"
        }
    },
    "https://gedcom.io/terms/v7/TEMP": {
        "label": "Temple",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Temple The name of a temple of The Church of Jesus Christ of Latter-day Saints. Previous versions recommended using a set of abbreviations for temple names, but the list of abbreviations is no longer published by the Church and using abbreviations is no longer recommended.",
        "standard_tag": "TEMP",
        "substructures": {},
        "superstructures": {
            "BAPL": "https://gedcom.io/terms/v7/BAPL",
            "CONL": "https://gedcom.io/terms/v7/CONL",
            "ENDL": "https://gedcom.io/terms/v7/ENDL",
            "INIL": "https://gedcom.io/terms/v7/INIL",
            "SLGC": "https://gedcom.io/terms/v7/SLGC",
            "SLGS": "https://gedcom.io/terms/v7/SLGS"
        }
    },
    "https://gedcom.io/terms/v7/TEXT": {
        "label": "Text from Source",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Text from Source A verbatim copy of any description contained within the source. This indicates notes or text that are actually contained in the source document, not the submitter's opinion about the source. This should be, from the evidence point of view, \"what the original record keeper said\" as opposed to the researcher's interpretation.",
        "standard_tag": "TEXT",
        "substructures": {
            "LANG": "https://gedcom.io/terms/v7/LANG",
            "MIME": "https://gedcom.io/terms/v7/MIME"
        },
        "superstructures": {
            "DATA": "https://gedcom.io/terms/v7/SOUR-DATA",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/TIME": {
        "label": "Time",
        "payload": "https://gedcom.io/terms/v7/type-Time",
        "specification": "Time A `Time` value in a 24-hour clock format.",
        "standard_tag": "TIME",
        "substructures": {},
        "superstructures": {
            "DATE": "https://gedcom.io/terms/v7/HEAD-DATE",
            "SDATE": "https://gedcom.io/terms/v7/SDATE"
        }
    },
    "https://gedcom.io/terms/v7/TITL": {
        "label": "Title",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Title The title, formal or informal, of the superstructure.\n\nA published work, such as a book, might have a title plus the title of the\nseries of which the book is a part. A magazine article would have a title plus\nthe title of the magazine that published the article.\n\nFor an unpublished work, including most digital files, titles should be\ndescriptive and appropriate to the work.\n\n&lt;div class=\"example\"&gt;\n\n&lt;p&gt;&lt;/p&gt;\n\n- The `TITL` of a letter might include the date, the sender, and the receiver.\n- The `TITL` of a transaction between a buyer and seller might have their names\n  and the transaction date.\n- The `TITL` of a family Bible containing genealogical information might have\n  past and present owners and a physical description of the book.\n- The `TITL` of a personal interview would cite the informant and interviewer.\n\n&lt;/div&gt;\n\nSome sources may have a citation text that cannot readily be represented using\nthe `SOURCE_RECORD` substructures `AUTH`, `PUBL`, `REPO`, and so on. In such\ncases, the entire citation text may be presented as the payload of the\n`SOUR`.`TITL`.",
        "standard_tag": "TITL",
        "substructures": {},
        "superstructures": {
            "FILE": "https://gedcom.io/terms/v7/FILE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/TOP": {
        "label": "Top crop width",
        "payload": "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
        "specification": "Top crop width A number of pixels to not display from the top side of the image. See `CROP` for more details.",
        "standard_tag": "TOP",
        "substructures": {},
        "superstructures": {
            "CROP": "https://gedcom.io/terms/v7/CROP"
        }
    },
    "https://gedcom.io/terms/v7/TRLR": {
        "label": "Trailer",
        "payload": "null",
        "specification": "Trailer A pseudo-structure marking the end of a dataset. See [The Header and Trailer] for more details.",
        "standard_tag": "TRLR",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/TYPE": {
        "label": "Type",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Type A descriptive word or phrase used to further classify the superstructure.\n\nWhen both a `NOTE` and free-text `TYPE` are permitted as substructures of the\nsame structure, the displaying systems should always display the `TYPE` value\nwhen they display the data from the associated structure; `NOTE` will typically\nbe visible only in a detailed view.\n\n`TYPE` must be used whenever the generic `EVEN`, `FACT` and `IDNO` tags are\nused. It may also be used for any other event or attribute.\n\nUsing the subordinate `TYPE` classification method provides a further\nclassification of the superstructure but does not change its basic meaning.\n\n&lt;div class=\"example\"&gt;\n\nA `ORDN` with a `TYPE` could clarify what kind of ordination was performed:\n\n```gedcom\n0 @I1@ INDI\n1 ORDN\n2 TYPE Bishop\n```\n\nThis classifies the entry as an ordination as a bishop, which is still a\nordination event. The event could be further clarified with `RELI`, `DATE`, and\nother substructures.\n\nOther descriptor values might include, for example,\n\n- \"Stillborn\" as a qualifier to `BIRT` (birth)\n- \"Civil\" as a qualifier to `MARR` (marriage)\n- \"College\" as a qualifier to `GRAD` (graduation)\n- \"Oral\" as a qualifier to `WILL`\n\nSee also `FACT` and `EVEN` for additional examples.\n\n&lt;/div&gt;",
        "standard_tag": "TYPE",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "REFN": "https://gedcom.io/terms/v7/REFN",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/UID": {
        "label": "Unique Identifier",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Unique Identifier A globally-unique identifier of the superstructure, to be preserved across\nedits. If a globally-unique identifier for the record already exists, it should\nbe used without modification, not even whitespace or letter case normalization.\nNew globally unique identifiers should be created and formatted as described in\n[RFC 4122].\n\nThis is metadata about the structure itself, not data about its subject.\nMultiple structures describing different aspects of the same subject would have\ndifferent `UID` values.\n\nBecause the `UID` identifies a structure, it can facilitate inter-tool\ncollaboration by distinguishing between a structure being edited and a new\nstructure being created. If an application allows structures to be edited in a\nway that completely changes their meaning (e.g., changing all the contents of\nan `INDI` record to have it describe a completely different person) then any\n`UID`s should also be changed.\n\n&lt;div class=\"note\"&gt;\n\nSome systems used a 16-byte UUID with a custom 2-byte checksum for a total of\n18 bytes:\n\n- checksum byte 1 = (sum of (byte~*i*~) for *i* 1 through 16) mod 256\n- checksum byte 2 = (sum of ((16 − *i*) × (byte~*i*~)) for *i* 1 through 16)\n  mod 256\n\nUse of checksums for UIDs is discouraged except in cases where error-prone\ninput is expected and an appropriate action to take in case of an error is\nknown.\n\n&lt;/div&gt;",
        "standard_tag": "UID",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FAM": "https://gedcom.io/terms/v7/record-FAM",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INDI": "https://gedcom.io/terms/v7/record-INDI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OBJE": "https://gedcom.io/terms/v7/record-OBJE",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SNOTE": "https://gedcom.io/terms/v7/record-SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/record-SOUR",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/VERS": {
        "label": "Version",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Version An identifier that represents the version level assigned to the associated product. It is defined and changed by the creators of the product.",
        "standard_tag": "VERS",
        "substructures": {},
        "superstructures": {
            "SOUR": "https://gedcom.io/terms/v7/HEAD-SOUR"
        }
    },
    "https://gedcom.io/terms/v7/WIDTH": {
        "label": "Width in pixels",
        "payload": "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
        "specification": "Width in pixels How many pixels to display horizontally for the image. See `CROP` for more details.",
        "standard_tag": "WIDTH",
        "substructures": {},
        "superstructures": {
            "CROP": "https://gedcom.io/terms/v7/CROP"
        }
    },
    "https://gedcom.io/terms/v7/WIFE": {
        "label": "Wife",
        "payload": "null",
        "specification": "Wife A container for information relevant to the subject of the superstructure specific to the individual described by the associated `FAM`'s `WIFE` substructure.",
        "standard_tag": "WIFE",
        "substructures": {
            "AGE": "https://gedcom.io/terms/v7/AGE"
        },
        "superstructures": {
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "CENS": "https://gedcom.io/terms/v7/FAM-CENS",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/FAM-EVEN",
            "FACT": "https://gedcom.io/terms/v7/FAM-FACT",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NCHI": "https://gedcom.io/terms/v7/FAM-NCHI",
            "RESI": "https://gedcom.io/terms/v7/FAM-RESI"
        }
    },
    "https://gedcom.io/terms/v7/WILL": {
        "label": "Will",
        "payload": "Y|&lt;NULL&gt;",
        "specification": "Will An [Individual Event]. See also `INDIVIDUAL_EVENT_STRUCTURE`. will A legal document treated as an event, by which a person disposes of his or her estate. It takes effect after death. The event date is the date the will was signed while the person was alive. (See also `PROB`)",
        "standard_tag": "WILL",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "AGE": "https://gedcom.io/terms/v7/AGE",
            "AGNC": "https://gedcom.io/terms/v7/AGNC",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CAUS": "https://gedcom.io/terms/v7/CAUS",
            "DATE": "https://gedcom.io/terms/v7/DATE",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "PLAC": "https://gedcom.io/terms/v7/PLAC",
            "RELI": "https://gedcom.io/terms/v7/RELI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SDATE": "https://gedcom.io/terms/v7/SDATE",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TYPE": "https://gedcom.io/terms/v7/TYPE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {
            "INDI": "https://gedcom.io/terms/v7/record-INDI"
        }
    },
    "https://gedcom.io/terms/v7/WWW": {
        "label": "Web address",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Web address A URL or other locator for a World Wide Web page of the subject of the\nsuperstructure, as defined by any relevant standard such as [whatwg/url], [RFC\n3986], [RFC 3987], and so forth.\n\nLike other substructures, the `WWW` structure provides details about the\nsubject of its superstructure. For example, a `MARR`.`WWW` is a world wide web\npage of the marriage event, not the personal website of the couple or an entry\nin an online database serving as a source documenting the marriage. However,\nthe meaning of `WWW` was only implicit when it was introduced in version 5.5.1\nand many files were created that use `WWW` to store a more tangentially-related\nweb address, so applications are recommended to interpret the `WWW` structure's\nmeaning cautiously.\n\nIf an invalid or no longer existing web address is present upon import, it\nshould be preserved as-is on export.",
        "standard_tag": "WWW",
        "substructures": {},
        "superstructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CORP": "https://gedcom.io/terms/v7/CORP",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "REPO": "https://gedcom.io/terms/v7/record-REPO",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/record-SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        }
    },
    "https://gedcom.io/terms/v7/enumset-ADOP": {
        "label": "ENUMSET-ADOP",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-ADOP",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-EVEN": {
        "label": "ENUMSET-EVEN",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-EVEN",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-EVENATTR": {
        "label": "ENUMSET-EVENATTR",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-EVENATTR",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-FAMC-STAT": {
        "label": "ENUMSET-FAMC-STAT",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-FAMC-STAT",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-MEDI": {
        "label": "ENUMSET-MEDI",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-MEDI",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-NAME-TYPE": {
        "label": "ENUMSET-NAME-TYPE",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-NAME-TYPE",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-PEDI": {
        "label": "ENUMSET-PEDI",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-PEDI",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-QUAY": {
        "label": "ENUMSET-QUAY",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-QUAY",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-RESN": {
        "label": "ENUMSET-RESN",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-RESN",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-ROLE": {
        "label": "ENUMSET-ROLE",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-ROLE",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/enumset-SEX": {
        "label": "ENUMSET-SEX",
        "payload": "null",
        "specification": "",
        "standard_tag": "ENUMSET-SEX",
        "substructures": {},
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/ord-STAT": {
        "label": "Status",
        "payload": "https://gedcom.io/terms/v7/type-Enum",
        "specification": "Status An enumerated value from set `https://gedcom.io/terms/v7/enumset-ord-STAT` assessing of the state or condition of an ordinance.",
        "standard_tag": "STAT",
        "substructures": {
            "DATE": "https://gedcom.io/terms/v7/DATE-exact"
        },
        "superstructures": {
            "BAPL": "https://gedcom.io/terms/v7/BAPL",
            "CONL": "https://gedcom.io/terms/v7/CONL",
            "ENDL": "https://gedcom.io/terms/v7/ENDL",
            "INIL": "https://gedcom.io/terms/v7/INIL",
            "SLGC": "https://gedcom.io/terms/v7/SLGC",
            "SLGS": "https://gedcom.io/terms/v7/SLGS"
        }
    },
    "https://gedcom.io/terms/v7/record-FAM": {
        "label": "Family record",
        "payload": "null",
        "specification": "Family record See `FAMILY_RECORD`\n\n&lt;div class=\"note\"&gt;\n\nThe common case is that each couple has one `FAM` record, but that is not\nalways the case.\n\nA couple that separates and then gets together again can be represented either\nas a single `FAM` with multiple events (`MARR`, `DIV`, etc.) or as a separate\n`FAM` for each time together. Some user interfaces may display these two in\ndifferent ways and the two admit different semantics in sourcing. A single\n`FAM` with two `MARR` with distinct dates might also represent uncertainty\nabout dates and a pair of `FAM` with same spouses might also be the result of\nmerging multiple files.\n\nImplementers should support both representations, and should choose between\nthem based on user input or other context beyond that provided in the datasets\nthemselves.\n\n&lt;/div&gt; The `FAM` record was originally structured to represent families where a male\n`HUSB` (husband or father) and female `WIFE` (wife or mother) produce `CHIL`\n(children). The `FAM` record may also be used for cultural parallels to this,\nincluding nuclear families, marriage, cohabitation, fostering, adoption, and so\non, regardless of the gender of the partners. Sex, gender, titles, and roles of\npartners should not be inferred based on the partner that the `HUSB` or `WIFE`\nstructure points to.\n\nThe individuals pointed to by the `HUSB` and `WIFE` are collectively referred\nto as \"partners\", \"parents\" or \"spouses\".\n\nSome displays may be unable to display more than 2 partners. Displays may use\n`HUSB` and `WIFE` as layout hints, for example, by consistently displaying the\n`HUSB` on the same side of the `WIFE` in a tree view. Family structures with\nmore than 2 partners may either use several `FAM` records or use\n`ASSOCIATION_STRUCTURE`s to indicate additional partners. `ASSO` should not be\nused for relationships that can be expressed using `HUSB`, `WIFE`, or `CHIL`\ninstead.\n\n&lt;div class=\"note\"&gt;\n\nThe `FAM` record will be revised in a future version to more fully express the\ndiversity of human family relationships.\n\n&lt;/div&gt;\n\nThe order of the `CHIL` (children) pointers within a `FAM` (family) structure\nshould be chronological by birth; this is an exception to the usual \"most\npreferred value first\" rule. A `CHIL` with a `voidPtr` indicates a placeholder\nfor an unknown child in this birth order.\n\nIf a `FAM` record uses `HUSB` or `WIFE` to point to an `INDI` record, the\n`INDI` record must use `FAMS` to point to the `FAM` record. If a `FAM` record\nuses `CHIL` to point to an `INDI` record, the `INDI` record must use a `FAMC`\nto point to the `FAM` record.\n\nAn `INDI` record should not have multiple `FAMS` substructures pointing to the\nsame `FAM`.\n\nA `FAM` record should not have multiple `CHIL` substructures pointing to the\nsame `INDI`; doing so implies a nonsensical birth order. An `INDI` record may\nhave multiple `FAMC` substructures pointing to the same `FAM`, but doing so is\nnot recommended.\n\nSource citations and notes related to the start of a specific child\nrelationship should be placed under the child's `BIRT`, `CHR`, or `ADOP` event,\nrather than under the `FAM` record.",
        "standard_tag": "FAM",
        "substructures": {
            "ANUL": "https://gedcom.io/terms/v7/ANUL",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "CENS": "https://gedcom.io/terms/v7/FAM-CENS",
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CHIL": "https://gedcom.io/terms/v7/CHIL",
            "CREA": "https://gedcom.io/terms/v7/CREA",
            "DIV": "https://gedcom.io/terms/v7/DIV",
            "DIVF": "https://gedcom.io/terms/v7/DIVF",
            "ENGA": "https://gedcom.io/terms/v7/ENGA",
            "EVEN": "https://gedcom.io/terms/v7/FAM-EVEN",
            "EXID": "https://gedcom.io/terms/v7/EXID",
            "FACT": "https://gedcom.io/terms/v7/FAM-FACT",
            "HUSB": "https://gedcom.io/terms/v7/FAM-HUSB",
            "MARB": "https://gedcom.io/terms/v7/MARB",
            "MARC": "https://gedcom.io/terms/v7/MARC",
            "MARL": "https://gedcom.io/terms/v7/MARL",
            "MARR": "https://gedcom.io/terms/v7/MARR",
            "MARS": "https://gedcom.io/terms/v7/MARS",
            "NCHI": "https://gedcom.io/terms/v7/FAM-NCHI",
            "NO": "https://gedcom.io/terms/v7/NO",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "REFN": "https://gedcom.io/terms/v7/REFN",
            "RESI": "https://gedcom.io/terms/v7/FAM-RESI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SLGS": "https://gedcom.io/terms/v7/SLGS",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "SUBM": "https://gedcom.io/terms/v7/SUBM",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WIFE": "https://gedcom.io/terms/v7/FAM-WIFE"
        },
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/record-INDI": {
        "label": "Individual",
        "payload": "null",
        "specification": "Individual See `INDIVIDUAL_RECORD`. The individual record is a compilation of facts or hypothesized facts about an\nindividual. These facts may come from multiple sources. Source citations and\nnotes allow documentation of the source where each of the facts were\ndiscovered.\n\nA single individual may have facts distributed across multiple individual\nrecords, connected by `ALIA` (alias, in the computing sense not the pseudonym\nsense) pointers. See `ALIA` for more details.\n\nIndividual records are linked to Family records by use of bi-directional\npointers. Details about those links are stored as substructures of the pointers\nin the individual record. Source citations and notes related to the start of\nthe individual's relationship to parents should be placed under the\nindividual's `BIRT`, `CHR`, or `ADOP` event, rather than directly under the\n`INDI` record, since the former permits explicitly identifying the family\nrecord whereas the latter does not.\n\nOther associations or relationships are represented by the `ASSO` (association)\ntag. The person's relation or associate is the person being pointed to. The\nassociation or relationship is stated by the value on the subordinate `ROLE`\nline. `ASSO` should not be used for relationships that can be expressed using\n`FAMS` or `FAMC` instead.\n\n&lt;div class=\"example\"&gt;\n\nThe following example refers to 2 individuals, `@I1@` and `@I2@`, where `@I2@`\nis a godparent of `@I1@`:\n\n```gedcom\n0 @I1@ INDI\n1 ASSO @I2@\n2 ROLE GODP\n```\n\n&lt;/div&gt;\n\nEvents stored as facts within an `INDI` record may also have `FAMC` or `ASSO`\ntags to indicate families and individuals that participated in those events.\nFor example, a `FAMC` pointer subordinate to an adoption event indicates a\nrelationship to family by adoption; biological parents can be shown by a `FAMC`\npointer subordinate to the birth event; the eulogist at a funeral can be shown\nby an `ASSO` pointer subordinate to the burial event; and so on. A subordinate\n`FAMC` pointer is allowed to refer to a family where the individual does not\nappear as a child.",
        "standard_tag": "INDI",
        "substructures": {
            "ADOP": "https://gedcom.io/terms/v7/ADOP",
            "ALIA": "https://gedcom.io/terms/v7/ALIA",
            "ANCI": "https://gedcom.io/terms/v7/ANCI",
            "ASSO": "https://gedcom.io/terms/v7/ASSO",
            "BAPL": "https://gedcom.io/terms/v7/BAPL",
            "BAPM": "https://gedcom.io/terms/v7/BAPM",
            "BARM": "https://gedcom.io/terms/v7/BARM",
            "BASM": "https://gedcom.io/terms/v7/BASM",
            "BIRT": "https://gedcom.io/terms/v7/BIRT",
            "BLES": "https://gedcom.io/terms/v7/BLES",
            "BURI": "https://gedcom.io/terms/v7/BURI",
            "CAST": "https://gedcom.io/terms/v7/CAST",
            "CENS": "https://gedcom.io/terms/v7/INDI-CENS",
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CHR": "https://gedcom.io/terms/v7/CHR",
            "CHRA": "https://gedcom.io/terms/v7/CHRA",
            "CONF": "https://gedcom.io/terms/v7/CONF",
            "CONL": "https://gedcom.io/terms/v7/CONL",
            "CREA": "https://gedcom.io/terms/v7/CREA",
            "CREM": "https://gedcom.io/terms/v7/CREM",
            "DEAT": "https://gedcom.io/terms/v7/DEAT",
            "DESI": "https://gedcom.io/terms/v7/DESI",
            "DSCR": "https://gedcom.io/terms/v7/DSCR",
            "EDUC": "https://gedcom.io/terms/v7/EDUC",
            "EMIG": "https://gedcom.io/terms/v7/EMIG",
            "ENDL": "https://gedcom.io/terms/v7/ENDL",
            "EVEN": "https://gedcom.io/terms/v7/INDI-EVEN",
            "EXID": "https://gedcom.io/terms/v7/EXID",
            "FACT": "https://gedcom.io/terms/v7/INDI-FACT",
            "FAMC": "https://gedcom.io/terms/v7/INDI-FAMC",
            "FAMS": "https://gedcom.io/terms/v7/FAMS",
            "FCOM": "https://gedcom.io/terms/v7/FCOM",
            "GRAD": "https://gedcom.io/terms/v7/GRAD",
            "IDNO": "https://gedcom.io/terms/v7/IDNO",
            "IMMI": "https://gedcom.io/terms/v7/IMMI",
            "INIL": "https://gedcom.io/terms/v7/INIL",
            "NAME": "https://gedcom.io/terms/v7/INDI-NAME",
            "NATI": "https://gedcom.io/terms/v7/NATI",
            "NATU": "https://gedcom.io/terms/v7/NATU",
            "NCHI": "https://gedcom.io/terms/v7/INDI-NCHI",
            "NMR": "https://gedcom.io/terms/v7/NMR",
            "NO": "https://gedcom.io/terms/v7/NO",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "OCCU": "https://gedcom.io/terms/v7/OCCU",
            "ORDN": "https://gedcom.io/terms/v7/ORDN",
            "PROB": "https://gedcom.io/terms/v7/PROB",
            "PROP": "https://gedcom.io/terms/v7/PROP",
            "REFN": "https://gedcom.io/terms/v7/REFN",
            "RELI": "https://gedcom.io/terms/v7/INDI-RELI",
            "RESI": "https://gedcom.io/terms/v7/INDI-RESI",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "RETI": "https://gedcom.io/terms/v7/RETI",
            "SEX": "https://gedcom.io/terms/v7/SEX",
            "SLGC": "https://gedcom.io/terms/v7/SLGC",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "SSN": "https://gedcom.io/terms/v7/SSN",
            "SUBM": "https://gedcom.io/terms/v7/SUBM",
            "TITL": "https://gedcom.io/terms/v7/INDI-TITL",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WILL": "https://gedcom.io/terms/v7/WILL"
        },
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/record-OBJE": {
        "label": "Object",
        "payload": "null",
        "specification": "Object See `MULTIMEDIA_RECORD`. The multimedia record refers to 1 or more external digital files, and may\nprovide some additional information about the files and the media they encode.\n\nThe file reference can occur more than once to group multiple files together.\nGrouped files should each pertain to the same context. For example, a sound\nclip and a photo both of the same event might be grouped in a single `OBJE`.\n\nThe change and creation dates should be for the `OBJE` record itself, not the\nunderlying files.",
        "standard_tag": "OBJE",
        "substructures": {
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CREA": "https://gedcom.io/terms/v7/CREA",
            "EXID": "https://gedcom.io/terms/v7/EXID",
            "FILE": "https://gedcom.io/terms/v7/FILE",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "REFN": "https://gedcom.io/terms/v7/REFN",
            "RESN": "https://gedcom.io/terms/v7/RESN",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "UID": "https://gedcom.io/terms/v7/UID"
        },
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/record-REPO": {
        "label": "Repository",
        "payload": "null",
        "specification": "Repository See `REPOSITORY_RECORD`. The repository record provides information about an institution or person that\nhas a collection of sources. Informal repositories include the owner of an\nunpublished work or of a rare published source, or a keeper of personal\ncollections. An example would be the owner of a family Bible containing\nunpublished family genealogical entries.\n\nLayered repositories, such as an archive containing copies of a subset of\nrecords from another archive or archives that have moved or been bought by\nother archives, are not modeled in this version of the specification. It is\nexpected they will be added in a later version. Until such time, it is\nrecommended that the repository record store current contact information, if\nknown.",
        "standard_tag": "REPO",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CREA": "https://gedcom.io/terms/v7/CREA",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "EXID": "https://gedcom.io/terms/v7/EXID",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "NAME": "https://gedcom.io/terms/v7/NAME",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "REFN": "https://gedcom.io/terms/v7/REFN",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/record-SNOTE": {
        "label": "Shared note",
        "payload": "http://www.w3.org/2001/XMLSchema#string",
        "specification": "Shared note A note that is shared by multiple structures. See `SHARED_NOTE_RECORD` for more details. A catch-all location for information that does not fully fit within other\nstructures. It may include research notes, additional context, alternative\ninterpretations, reasoning, and so forth.\n\nA shared note record may be pointed to by multiple other structures. Shared\nnotes should only be used if editing the note in one place should edit it in\nall other places or if the note itself requires an `IDENTIFIER_STRUCTURE`. If\neach instance of the note may be edited separately and no identifier is needed,\na `NOTE` should be used instead.\n\nEach [`SNOTE`.`TRAN`] must have either a `MIME` or `LANG` substructure or\nboth.\n\n&lt;div class=\"example\"&gt;\n\nThe origin of a name might be a reasonable shared note, while the reason a\nparticular person was given that name may make more sense as a non-shared note.\n\n```gedcom\n0 @GORDON@ SNOTE \"Gordon\" is a traditional Scottish surname.\n1 CONT It became a given name in honor of Charles George Gordon.\n0 @I1@ INDI\n1 NAME Gordon /Jones/\n2 NOTE Named after the astronaut Gordon Cooper\n2 SNOTE @GORDON@\n```\n\n&lt;/div&gt;\n\n&lt;div class=\"note\"&gt;\n\nThe ability to have multiple structures share a single note using pointers was\nintroduced in version 5.0 in 1991. However, as of 2021 relatively few\napplications have a user interface that presents shared notes as such to users.\nIt is recommended that `SNOTE` be avoided when `NOTE` will suffice.\n\n&lt;/div&gt;\n\nA `SHARED_NOTE_RECORD` may contain a pointer to a `SOURCE_RECORD` and vice\nversa. Applications must not create datasets where these mutual pointers form a\ncycle. Applications should also ensure they can handle invalid files with such\ncycles in a safe manner.",
        "standard_tag": "SNOTE",
        "substructures": {
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CREA": "https://gedcom.io/terms/v7/CREA",
            "EXID": "https://gedcom.io/terms/v7/EXID",
            "LANG": "https://gedcom.io/terms/v7/LANG",
            "MIME": "https://gedcom.io/terms/v7/MIME",
            "REFN": "https://gedcom.io/terms/v7/REFN",
            "SOUR": "https://gedcom.io/terms/v7/SOUR",
            "TRAN": "https://gedcom.io/terms/v7/NOTE-TRAN",
            "UID": "https://gedcom.io/terms/v7/UID"
        },
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/record-SOUR": {
        "label": "Source",
        "payload": "null",
        "specification": "Source A description of an entire source. See `SOURCE_RECORD` for more details. A source record describes an entire source. A source may also point to `REPO`s\nto describe repositories or archives where the source document may be found.\nThe part of a source relevant to a specific fact, such as a specific page or\nentry, is indicated in a `SOURCE_CITATION` that points to the source record.\n\n&lt;div class=\"note\"&gt;\n\nThis sourcing model is known to be insufficient for some use cases and may be\nrefined in a future version of this specification.\n\n&lt;/div&gt;\n\nA `SOURCE_RECORD` may contain a pointer to a `SHARED_NOTE_RECORD` and vice\nversa. Applications must not create datasets where these mutual pointers form a\ncycle. Applications should also ensure they can handle invalid files with such\ncycles in a safe manner.",
        "standard_tag": "SOUR",
        "substructures": {
            "ABBR": "https://gedcom.io/terms/v7/ABBR",
            "AUTH": "https://gedcom.io/terms/v7/AUTH",
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CREA": "https://gedcom.io/terms/v7/CREA",
            "DATA": "https://gedcom.io/terms/v7/DATA",
            "EXID": "https://gedcom.io/terms/v7/EXID",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PUBL": "https://gedcom.io/terms/v7/PUBL",
            "REFN": "https://gedcom.io/terms/v7/REFN",
            "REPO": "https://gedcom.io/terms/v7/REPO",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "TEXT": "https://gedcom.io/terms/v7/TEXT",
            "TITL": "https://gedcom.io/terms/v7/TITL",
            "UID": "https://gedcom.io/terms/v7/UID"
        },
        "superstructures": {}
    },
    "https://gedcom.io/terms/v7/record-SUBM": {
        "label": "Submitter",
        "payload": "null",
        "specification": "Submitter A description of a contributor of information to the document. See `SUBMITTER_RECORD` for more details. The submitter record identifies an individual or organization that contributed information contained in the dataset. All records in the document are assumed to be contributed by the submitter referenced in the `HEAD`, unless a `SUBM` structure inside a specific record points at a different submitter record.",
        "standard_tag": "SUBM",
        "substructures": {
            "ADDR": "https://gedcom.io/terms/v7/ADDR",
            "CHAN": "https://gedcom.io/terms/v7/CHAN",
            "CREA": "https://gedcom.io/terms/v7/CREA",
            "EMAIL": "https://gedcom.io/terms/v7/EMAIL",
            "EXID": "https://gedcom.io/terms/v7/EXID",
            "FAX": "https://gedcom.io/terms/v7/FAX",
            "LANG": "https://gedcom.io/terms/v7/SUBM-LANG",
            "NAME": "https://gedcom.io/terms/v7/NAME",
            "NOTE": "https://gedcom.io/terms/v7/NOTE",
            "OBJE": "https://gedcom.io/terms/v7/OBJE",
            "PHON": "https://gedcom.io/terms/v7/PHON",
            "REFN": "https://gedcom.io/terms/v7/REFN",
            "SNOTE": "https://gedcom.io/terms/v7/SNOTE",
            "UID": "https://gedcom.io/terms/v7/UID",
            "WWW": "https://gedcom.io/terms/v7/WWW"
        },
        "superstructures": {}
    }
}

def load_spec(file_path: str) -> Dict[str, Any]:
    """
    Load the JSON spec file into a Python dict.
    
    :param file_path: Path to your spec.json
    :return: A dict mapping each URI to its structure-definition dict.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_substructures(key: str) -> Dict[str, Any]:
    """
    Return the 'substructures' dict for the given key.
    """
    struct = g7_structure_specs.get(key)
    if struct is None:
        return {}
        raise KeyError(f"No entry for key {key!r} in spec.json")
    return struct.get("substructures", {})

def get_label(key: str) -> Dict[str, Any]:
    """
    Return the label for the given key.
    """
    struct = g7_structure_specs.get(key)
    if struct is None:
        raise KeyError(f"No entry for key {key!r} in spec.json")
        return 'None'
        
    return struct.get("label", 'No Label')

def match_uri(tag: str,parent):
    uri = None
    if tag.startswith("_"):
        uri = g7_structure_specs.get(tag)
    elif parent:
        valid_substrutures = get_substructures(parent.uri)
        uri = valid_substrutures.get(tag)  
    elif 'https://gedcom.io/terms/v7/record-' + tag in g7_structure_specs.keys():
        uri = 'https://gedcom.io/terms/v7/record-' + tag
    elif 'https://gedcom.io/terms/v7/' + tag in g7_structure_specs.keys():
        uri = 'https://gedcom.io/terms/v7/' + tag
    if uri == None:
        raise ValueError(f'Could not get uri for tag: {tag}, parent: {parent}')
    return uri

'''
MIT License

Copyright (c) 2022 David Straub

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
# TODO: https://github.com/DavidMStraub

# GEDCOM 7 regex patterns thanks@DavidMStraub

# --- Common primitives ---
d = '\\ '                             # GEDCOM delimiter (escaped space)
integer = '[0-9]+'                    # One or more digits
nonzero = '[1-9]'                     # Digits 1–9

# --- Duration units ---
years  = f'{integer}y'
months = f'{integer}m'
weeks  = f'{integer}w'
days   = f'{integer}d'

# --- Age format ---
agebound = '[<>]'  # Optional boundary indicator (less than, greater than)
ageduration = (
    f'((?P<years>{years})({d}(?P<months1>{months}))?({d}(?P<weeks1>{weeks}))?'
    f'({d}(?P<days1>{days}))?|(?P<months2>{months})({d}(?P<weeks2>{weeks}))?'
    f'({d}(?P<days2>{days}))?|(?P<weeks3>{weeks})({d}(?P<days3>{days}))?|'
    f'(?P<days4>{days}))'
)
age = f'((?P<agebound>{agebound}){d})?{ageduration}'

# --- Tags and Enums ---
underscore = '_'
ucletter = '[A-Z]'
tagchar = f'({ucletter}|[0-9]|{underscore})'
exttag = f'{underscore}({tagchar})+'
stdtag = f'{ucletter}({tagchar})*'
tag = f'({stdtag}|{exttag})'
enum = tag

# --- Dates ---
daterestrict = 'FROM|TO|BET|AND|BEF|AFT|ABT|CAL|EST'
calendar = f'(?!{daterestrict})(GREGORIAN|JULIAN|FRENCH_R|HEBREW|{exttag})'
day = integer
month = f'(?!{daterestrict})({stdtag}|{exttag})'
year = integer
epoch = f'(?!{daterestrict})(BCE|{exttag})'

date = f'({calendar}{d})?(({day}{d})?{month}{d})?{year}({d}{epoch})?'

# --- Date variants with captures ---
date_capture = (
    f'((?P<calendar>{calendar}){d})?(((?P<day>{day}){d})?'
    f'(?P<month>{month}){d})?(?P<year>{year})({d}(?P<epoch>{epoch}))?'
)

dateapprox = f'(?P<qualifier>ABT|CAL|EST){d}(?P<dateapprox>{date})'
dateexact  = f'(?P<day>{day}){d}(?P<month>{month}){d}(?P<year>{year})'
dateperiod = f'((TO{d}(?P<todate1>{date}))?|FROM{d}(?P<fromdate>{date})({d}TO{d}(?P<todate2>{date}))?)'
daterange  = f'(BET{d}(?P<between>{date}){d}AND{d}(?P<and>{date})|AFT{d}(?P<after>{date})|BEF{d}(?P<before>{date}))'
datevalue  = f'({date}|{dateperiod}|{daterange}|{dateapprox})?'

# --- Media types ---
mt_char = "[ -!#-'*-+\\--.0-9A-Z^-~]"
mt_token = f'({mt_char})+'
mt_type = mt_token
mt_subtype = mt_token
mt_attribute = mt_token
mt_qtext = '[\t-\n -!#-\\[\\]-~]'
mt_qpair = '\\\\[\t-~]'
mt_qstring = f'"({mt_qtext}|{mt_qpair})*"'
mt_value = f'({mt_token}|{mt_qstring})'
mt_parameter = f'{mt_attribute}={mt_value}'
mediatype = f'{mt_type}/{mt_subtype}(;{mt_parameter})*'

# --- Line structure (GEDCOM record lines) ---
atsign = '@'
xref = f'{atsign}({tagchar})+{atsign}'
voidptr = '@VOID@'
pointer = f'(?P<pointer>{voidptr}|{xref})'
nonat = '[\t -?A-\\U0010ffff]'
noneol = '[\t -\\U0010ffff]'
linestr = f'(?P<linestr>({nonat}|{atsign}{atsign})({noneol})*)'
lineval = f'({pointer}|{linestr})'

level = f'(?P<level>0|{nonzero}[0-9]*)'
eol = '(\\\r(\\\n)?|\\\n)'
line = f'{level}{d}((?P<xref>{xref}){d})?(?P<tag>{tag})({d}{lineval})?{eol}'

# --- List formats ---
nocommasp = '[\t-\\x1d!-+\\--\\U0010ffff]'
nocomma = '[\t-+\\--\\U0010ffff]'
listitem = f'({nocommasp}|{nocommasp}({nocomma})*{nocommasp})?'
listdelim = f'({d})*,({d})*'
list = f'{listitem}({listdelim}{listitem})*'
list_enum = f'{enum}({listdelim}{enum})*'
list_text = list

# --- Names ---
namechar = '[ -.0-\\U0010ffff]'
namestr = f'({namechar})+'
personalname = f'({namestr}|({namestr})?/(?P<surname>{namestr})?/({namestr})?)'

# --- Time format ---
fraction = '[0-9]+'
second = '[012345][0-9]'
minute = '[012345][0-9]'
hour = '([0-9]|[01][0-9]|2[0123])'
time = f'(?P<hour>{hour}):(?P<minute>{minute})(:(?P<second>{second})(\\.(?P<fraction>{fraction}))?)?(?P<tz>Z)?'

# --- Text and special ---
anychar = '[\t-\\U0010ffff]'
text = f'({anychar})*'
special = text

# --- Boolean ---
boolean = 'Y'

# --- Banned Unicode Ranges ---
'''
banned = %x00-08 / %x0B-0C / %x0E-1F ; C0 other than LF CR and Tab
       / %x7F                        ; DEL
       / %x80-9F                     ; C1
       / %xD800-DFFF                 ; Surrogates
       / %xFFFE-FFFF                 ; invalid
; All other rules assume the absence of any banned characters
'''
banned = (
    '[\\x00-\\x08\\x0b-\\x0c\\x0e-\\x1f\\x7f\\x80-\\x9f\\ud800-\\udfff'
    '\\ufffe-\\uffff]'
)




# TAGS
CONT = "CONT"
HEAD = "HEAD"
ABBR = "ABBR"
ADDR = "ADDR"
ADOP = "ADOP"
ADR1 = "ADR1"
ADR2 = "ADR2"
ADR3 = "ADR3"
AGE = "AGE"
AGNC = "AGNC"
ALIA = "ALIA"
ANCI = "ANCI"
ANUL = "ANUL"
ASSO = "ASSO"
AUTH = "AUTH"
BAPL = "BAPL"
BAPM = "BAPM"
BARM = "BARM"
BASM = "BASM"
BIRT = "BIRT"
BLES = "BLES"
BURI = "BURI"
CALN = "CALN"
CAST = "CAST"
CAUS = "CAUS"
CENS = "CENS"
CHAN = "CHAN"
CHIL = "CHIL"
CHR = "CHR"
CHRA = "CHRA"
CITY = "CITY"
CONF = "CONF"
CONL = "CONL"
COPR = "COPR"
CORP = "CORP"
CREA = "CREA"
CREM = "CREM"
CROP = "CROP"
CTRY = "CTRY"
DATA = "DATA"
DATE = "DATE"
DEAT = "DEAT"
DESI = "DESI"
DEST = "DEST"
DIV = "DIV"
DIVF = "DIVF"
DSCR = "DSCR"
EDUC = "EDUC"
EMAIL = "EMAIL"
EMIG = "EMIG"
ENDL = "ENDL"
ENGA = "ENGA"
EVEN = "EVEN"
EXID = "EXID"
FACT = "FACT"
FAM = "FAM"
FAMC = "FAMC"
FAMS = "FAMS"
FAX = "FAX"
FCOM = "FCOM"
FILE = "FILE"
FORM = "FORM"
GEDC = "GEDC"
GIVN = "GIVN"
GRAD = "GRAD"
HEIGHT = "HEIGHT"
HUSB = "HUSB"
IDNO = "IDNO"
IMMI = "IMMI"
INDI = "INDI"
INIL = "INIL"
LANG = "LANG"
LATI = "LATI"
LEFT = "LEFT"
LONG = "LONG"
MAP = "MAP"
MARB = "MARB"
MARC = "MARC"
MARL = "MARL"
MARR = "MARR"
MARS = "MARS"
MEDI = "MEDI"
MIME = "MIME"
NAME = "NAME"
NATI = "NATI"
NATU = "NATU"
NCHI = "NCHI"
NICK = "NICK"
NMR = "NMR"
NO = "NO"
NOTE = "NOTE"
NPFX = "NPFX"
NSFX = "NSFX"
OBJE = "OBJE"
OCCU = "OCCU"
ORDN = "ORDN"
PAGE = "PAGE"
PEDI = "PEDI"
PHON = "PHON"
PHRASE = "PHRASE"
PLAC = "PLAC"
POST = "POST"
PROB = "PROB"
PROP = "PROP"
PUBL = "PUBL"
QUAY = "QUAY"
REFN = "REFN"
RELI = "RELI"
REPO = "REPO"
RESI = "RESI"
RESN = "RESN"
RETI = "RETI"
ROLE = "ROLE"
SCHMA = "SCHMA"
SDATE = "SDATE"
SEX = "SEX"
SLGC = "SLGC"
SLGS = "SLGS"
SNOTE = "SNOTE"
SOUR = "SOUR"
SPFX = "SPFX"
SSN = "SSN"
STAE = "STAE"
STAT = "STAT"
SUBM = "SUBM"
SURN = "SURN"
TAG = "TAG"
TEMP = "TEMP"
TEXT = "TEXT"
TIME = "TIME"
TITL = "TITL"
TOP = "TOP"
TRAN = "TRAN"
TRLR = "TRLR"
TYPE = "TYPE"
UID = "UID"
VERS = "VERS"
WIDTH = "WIDTH"
WIFE = "WIFE"
WILL = "WILL"
WWW = "WWW"