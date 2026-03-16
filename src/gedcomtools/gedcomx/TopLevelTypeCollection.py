from .textvalue import TextValue

class TopLevelTypeCollection:
    def __init__(self):
        self.items = {}
        self.items_by_type = {}
        self._id_idx ={}     # Hash Table for searching for item by id
        self._name_idx = {}
        self._uri_idx = {}
        self.authority = 'NewGedcomX'
        self.len = 0
    

    def append(self, item) -> bool:
        if item._uri._authority == '' or item._uri._authority is None:
            item._uri._authority = self.authority
        if item._uri._path == '' or item._uri._path is None:
            item._uri._path = f'{item.__class__.__name__}s'

        self.items[item._uri] = item
        self._update_indexes(item)
        self.len += 1
    
    def _update_indexes(self, item):
        # Update the id index
        if hasattr(item, 'id'):
            self._id_idx[item.id] = item
        if hasattr(item, 'names'):
            for name in item.names:
                if isinstance(name,TextValue):
                    self._name_idx[name] = item
                else:
                    break
        if item.__class__.__name__ in self.items_by_type.keys():
            self.items_by_type[item.__class__.__name__].append(item)
        else:
            self.items_by_type[item.__class__.__name__] = [item]

    
    def _dump_uris(self):
        for uri in self.items.keys():
            print(uri._uri)
    
    def __len__(self):
        return self.len
        
        
