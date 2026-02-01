
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Iterable
from collections import defaultdict


from .GedcomStructure import GedcomStructure
from . import specification as g7specs
from .logger import get_logger


from typing import Dict, List, Optional



class Gedcom7:
    def __init__(self, filepath: Optional[str] = None):
        self.persons: List[Any] = []
        self.families: List[Any] = []
        self.sources: List[Any] = []
        self.records: List['GedcomStructure'] = []
        self._tag_index: Dict[str, List[int]] = defaultdict(list)  # tag -> list of record indices

    # ---- indexing helpers -------------------------------------------------
    @staticmethod
    def _norm_tag(tag: str) -> str:
        return tag.upper()

    def _rebuild_index(self) -> None:
        self._tag_index.clear()
        for i, rec in enumerate(self.records):
            if getattr(rec, "tag", None):
                self._tag_index[self._norm_tag(rec.tag)].append(i)

    # Optional: keep index in sync if you append records elsewhere
    def _append_record(self, rec: 'GedcomStructure') -> None:
        self.records.append(rec)
        if getattr(rec, "tag", None):
            self._tag_index[self._norm_tag(rec.tag)].append(len(self.records) - 1)

    # ---- Python container protocol ----------------------------------------
    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self) -> Iterable['GedcomStructure']:
        return iter(self.records)

    def __contains__(self, key: Union[str, 'GedcomStructure']) -> bool:
        if isinstance(key, str):
            return self._norm_tag(key) in self._tag_index
        return key in self.records

    def __getitem__(self, key: Union[int, slice, str, tuple]) -> Union['GedcomStructure', List['GedcomStructure']]:
        # by position
        if isinstance(key, (int, slice)):
            return self.records[key]

        # by tag
        if isinstance(key, str):
            idxs = self._tag_index.get(self._norm_tag(key), [])
            return [self.records[i] for i in idxs]

        # combo: ('INDI', 0) or ('INDI', 0:5)
        if isinstance(key, tuple) and len(key) == 2 and isinstance(key[0], str):
            tag, sub = key
            items = self[tag]  # list for that tag
            if isinstance(sub, int) or isinstance(sub, slice):
                return items[sub]
            raise TypeError(f"Unsupported sub-key type: {type(sub)!r}")

        raise TypeError(f"Unsupported key type: {type(key)!r}")

    # ---- your existing methods (trimmed) ----------------------------------
    @staticmethod   
    def parse_gedcom_line(line: str) -> Optional[Dict[str, Any]]:
                
        line = line.lstrip('\ufeff').rstrip('\r\n')
        if not line:
            return None

        parts = line.split(maxsplit=3)
        if len(parts) < 2:
            return None  # not even "0 HEAD"

        # 1) Level
        try:
            level = int(parts[0])
        except ValueError:
            return None

        # 2) Is parts[1] an XREF?
        xref = None
        if parts[1].startswith('@') and parts[1].endswith('@'):
            xref = parts[1]

        # 3) Where is the tag?
        if xref:
            # must have at least ["0", "@X@", "TAG"]
            if len(parts) < 3:
                return None
            tag = parts[2]
            # everything after index 2 is the value
            value_parts = parts[3:]  # could be empty or one-element
        else:
            tag = parts[1]
            # everything after index 1 is the value
            value_parts = parts[2:]  # could be empty, one- or two-element
            

        # 4) re-assemble the full value
        value = " ".join(value_parts)  # empty string if value_parts == []
        if value.startswith('@') and value.endswith('@'):
            xref = parts[1]

        if tag == 'TAG':
            xtag, uri = value.split()
            g7specs.g7_structure_specs[xtag] = uri
            g7specs.g7_structure_specs[uri] = {'label': 'Extension_' + xtag}
            
        return {
            "level": level,
            "xref": xref,
            "tag": tag,
            "value": value
        }


    def loadfile(self, filepath: str) -> None:
        log = get_logger('importlog')
        context: Dict[int, GedcomStructure] = {}
        records: List[GedcomStructure] = []

        with open(filepath, 'r', encoding='utf8') as file:
            for lineno, raw in enumerate(file, start=1):
                record = Gedcom7.parse_gedcom_line(raw)
                if record is None:
                    log.error(f'empty line at {lineno}: {raw}')
                    continue

                level = int(record["level"])
                if record["tag"] == g7specs.CONT:
                    context[level - 1].value += "\n" + record["value"]
                    continue

                structure = GedcomStructure(
                    level=level,
                    tag=record["tag"],
                    xref=record["xref"],
                    text=record["value"],
                    parent=context[level - 1] if level > 0 else None,
                    line_num=lineno
                )

                if level == 0:
                    records.append(structure)

                context[level] = structure

        self.records = records
        self._rebuild_index()  # <-- build fast tag index once
