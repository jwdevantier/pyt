from collections.abc import MutableMapping
import typing as t


class ScopeError(Exception):
    pass


class ScopeInvalidIdentifier(ScopeError):
    def __init__(self, scope: 'Scope', identifier: str):
        self.scope = scope
        self.identifier = identifier
        super().__init__(f"cannot bind '{identifier}' - name not allowed")


class Scope(MutableMapping):
    __slots__ = ['_outer', '_data', '_allow_leading_upper']

    def __init__(self,
                 mapping: t.Optional[t.Mapping] = None,
                 outer: t.Optional['Scope'] = None,
                 allow_leading_upper=False):
        self._outer = outer
        self._data = {}
        self._allow_leading_upper = allow_leading_upper
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
        if key[0].isupper() and not self._allow_leading_upper:
            raise ScopeInvalidIdentifier(self, key)
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
