from collections.abc import MutableMapping
import typing as t


class Scope(MutableMapping):
    def __init__(self, mapping: t.Optional[t.Mapping] = None, outer: t.Optional['Scope'] = None):
        self._outer = outer
        self._data = {}
        if mapping:
            self._data.update(mapping)

    def __getitem__(self, key):
        curr: 'Scope' = self
        while curr is not None:
            if key in curr._data:
                return curr._data[key]
            curr = curr._outer
        raise KeyError(key)

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]
        if self._outer:
            del self._outer[key]

    def __iter__(self):
        dcts = []
        curr = self
        while curr:
            dcts.append(curr._data)
            curr = curr._outer
        merged = {}
        dcts.reverse()
        for dct in dcts:
            merged.update(dct)
        return iter(merged)

    def __len__(self):
        keys = set()
        curr = self
        while curr is not None:
            keys.update(curr._data.keys())
            curr = curr._outer
        return len(keys)

    def __repr__(self):
        outer = self._outer
        if outer:
            return f"Scope({repr(self._data)}, outer={repr(outer)})"
        else:
            return f"Scope({repr(self._data)})"
