# cython: language_level=3
import typing as t
from copy import copy
from collections import Sequence, Mapping

# Inspiration: https://clojure.org/guides/spec

# Ideas
# 1) rewrite in Cython (SPEEEEED!)
# 2) implement basics (and, or)
# 3) implement basic operations
#       - validate => boolean (maybe exception)
#       - explain  => ~kinda what's done now (errors map)
#       - conform  => ~explain + data.

# TODO
#   * specify - wrap object in spec
#       * type => instanceof
#       * callable => predicate
#   * predicate - wrap single-arg function, expect Truthy
#       * [DONE]
#   * all - require all specs conform
#       * [DONE]
#   * any   - require that one/some spec conforms
#       * [DONE]
#   * type/isinstance -
#       * [DONE]
#   * seqof - seq of objs
#       * [DONE]
#   * mapof - mapping of key=>val
#       * [DONE]
#   * keys  - mapping w specified keys conforming to specified specs
#       * [DONE]
#   * required - used for mappings where keys aren't optional
#       * [DONE]
#   * null/optional

# Like clojure spec, dicts etc are OPEN

cdef class _Invalid:
    def __repr__(self):
        return "#Invalid"

Invalid = _Invalid()

cdef class _Spec:
    cdef bint valid(self, object value):
        raise NotImplementedError("valid is not implemented")

    cdef object explain(self, object value):
        raise NotImplementedError("explain is not implemented")

    cdef object conform(self, object value):
        raise NotImplementedError("conform is not implemented")

    cdef str name(self):
        return self.__repr__()

cdef class Spec(_Spec):
    cdef bint valid(self, object value: t.Any):
        return self._valid(value)

    cdef object explain(self, object value: t.Any):
        return self._explain(value)

    cdef object conform(self, object value: t.Any):
        return self._conform(value)

    cdef str name(self):
        return self._name()

cdef class Type(_Spec):
    def __init__(self, type t: t.Type):
        self.typ = t

    cdef bint valid(self, object value: t.Any):
        return isinstance(value, self.typ)

    cdef object explain(self, object value: t.Any):
        if isinstance(value, self.typ):
            return None
        return f"expected instance of '{self.typ.__name__}', got '{type(value).__name__}'"

    cdef object conform(self, object value: t.Any):
        if isinstance(value, self.typ):
            return value
        return Invalid

    cdef str name(self):
        return f"Type<{self.typ.__name__}>"

def typ(o: t.Type) -> _Spec:
    if not isinstance(o, type):
        raise ValueError("argument should be a type")
    return Type(o)

cdef class Predicate(_Spec):
    def __init__(self, predicate : t.Callable, name: t.Optional[str] = None):
        self.predicate = predicate
        if name is None:
            self.predicate_name = predicate.__name__
        else:
            self.predicate_name = name

    cdef bint valid(self, object value: t.Any):
        try:
            return self.predicate(value) == True
        except:
            return False

    cdef object explain(self, object value: t.Any):
        try:
            if self.predicate(value):
                return None
            return f"predicate '{self.predicate_name}' failed"
        except:
            return f"predicate '{self.predicate_name}' failed"

    cdef object conform(self, object value: t.Any):
        try:
            return self.predicate(value)
        except:
            return Invalid

    cdef str name(self):
        return self.predicate_name + "?"

def predicate(c: t.Callable[[t.Any], bool], name: t.Optional[str] = None) -> Predicate:
    return Predicate(c, name)

cdef class All(_Spec):
    def __init__(self, dict specs: t.Dict[str, _Spec]):
        self.specs = specs

    cdef bint valid(self, object value: t.Any):
        cdef _Spec spec
        for spec in self.specs.values():
            if not spec.valid(value):
                return False
        return True

    cdef object explain(self, object value: t.Any):
        cdef:
            dict errors = {}
            object s_errs = None
            _Spec spec
        for label, spec in self.specs.items():
            s_errs = spec.explain(value)
            if s_errs:
                errors[label] = s_errs
        if errors == {}:
            return None
        return errors

    cdef object conform(self, object value: t.Any):
        cdef _Spec spec
        for spec in self.specs.values():
            if spec.conform(value) == Invalid:
                return Invalid
        return value  # How else can one conform to all?

    cdef str name(self):
        return f"all<{', '.join(self.specs.keys())}>"

def all(dict specmap: t.Dict[str, _Spec]) -> All:
    return All(specmap)

cdef class Any(_Spec):
    def __init__(self, dict specs: t.Dict[str, _Spec]):
        self.specs = specs

    cdef bint valid(self, object value: t.Any):
        cdef:
            _Spec spec
        for spec in self.specs.values():
            if spec.valid(value):
                return True
        return False

    cdef object explain(self, object value: t.Any):
        cdef:
            dict errors = {}
            object s_errs = None
            _Spec spec
            str label
        for label, spec in self.specs.items():
            s_errs = spec.explain(value)
            if not s_errs:
                return None
            errors[label] = s_errs
        if errors == {}:
            return None
        return errors

    cdef object conform(self, object value: t.Any):
        cdef:
            _Spec spec
            str label
            object retval
        for label, spec in self.specs.items():
            retval = spec.conform(value)
            if retval != Invalid:
                return label, retval
        return Invalid

    cdef str name(self):
        return f"any<{', '.join(self.specs.keys())}>"

def any(dict specmap: t.Dict[str, _Spec]) -> Any:
    return Any(specmap)

cdef class SeqOf(_Spec):
    def __init__(self, _Spec element_spec: _Spec):
        self.element_spec = element_spec

    cdef bint valid(self, object value: t.Any):
        if not isinstance(value, Sequence):
            return False
        for elem in value:
            if not self.element_spec.valid(elem):
                return False
        return True

    cdef object explain(self, object value: t.Any):
        cdef:
            list errors = []
            object err = None
            int ndx = 0
            object elem
        if not isinstance(value, Sequence):
            return f"Not a sequence"
        for ndx, elem in enumerate(value):
            err = self.element_spec.explain(elem)
            if err:
                errors.append((ndx, err))
        if not errors:
            return None
        return errors

    cdef object conform(self, object value: t.Any):
        if not isinstance(value, Sequence):
            return Invalid
        cdef:
            list result = []
            object conformed_elem = None
        for elem in value:
            conformed_elem = self.element_spec.conform(elem)
            if conformed_elem == Invalid:
                return Invalid
            result.append(conformed_elem)
        return result

    cdef str name(self):
        return f"seq-of<{self.element_spec.name()}>"

def seqof(_Spec element_spec: _Spec) -> SeqOf:
    return SeqOf(element_spec)

cdef class MapOf(_Spec):
    def __init__(self, _Spec keyspec: _Spec, _Spec valspec: _Spec):
        self.key_spec = keyspec
        self.val_spec = valspec

    cdef bint valid(self, object value: t.Any):
        if not isinstance(value, Mapping):
            return False
        cdef:
            object key
            object val
        for key, val in value.items():
            if not self.key_spec.valid(key):
                return False
            if not self.val_spec.valid(val):
                return False
        return True

    cdef object explain(self, object value: t.Any):
        if not isinstance(value, Mapping):
            return f"expected 'Mapping', got non-mapping '{type(value)}'"
        cdef:
            object key
            object val
            object err
            dict errs = {}
            dict entry_errs
            _Spec key_spec = self.key_spec
            _Spec val_spec = self.val_spec
        for key, val in value.items():
            entry_errs = {}
            err = key_spec.explain(key)
            if err:
                entry_errs['key'] = err
            err = val_spec.explain(val)
            if err:
                entry_errs['value'] = err
            if entry_errs:
                errs[key] = entry_errs
        if errs:
            return errs
        return None

    cdef object conform(self, object value: t.Any):
        if not isinstance(value, Mapping):
            return Invalid
        cdef:
            object key
            object key_conformed
            object val
            object val_conformed
            dict conformed = {}
            _Spec key_spec = self.key_spec
            _Spec val_spec = self.val_spec
        for key, val in value.items():
            key_conformed = key_spec.conform(key)
            if key_conformed == Invalid:
                return Invalid
            val_conformed = val_spec.conform(val)
            if val_conformed == Invalid:
                return Invalid
            conformed[key_conformed] = val_conformed
        return conformed

    cdef str name(self):
        return f"map-of<{self.key_spec.name()}: {self.val_spec.name()}>"

def mapof(_Spec keyspec: _Spec, _Spec valspec: _Spec) -> MapOf:
    return MapOf(keyspec, valspec)

cdef class Keys(_Spec):
    def __init__(self, dict spec: t.Dict[t.Any, _Spec]):
        self.spec = spec

    cdef bint valid(self, value):
        if not isinstance(value, Mapping):
            return False
        cdef:
            object key
            _Spec spec
        for key, spec in self.spec.items():
            if key not in value:
                if isinstance(spec, Req):
                    return False
                continue
            if not spec.valid(value[key]):
                return False
        return True

    cdef object explain(self, value):
        if not isinstance(value, Mapping):
            return False
        cdef:
            dict errors = {}
            object errs
            object key
            _Spec spec
        for key, spec in self.spec.items():
            if key not in value:
                if isinstance(spec, Req):
                    errors[key] = "required value missing"
                continue
            errs = spec.explain(value[key])
            if errs:
                errors[key] = errs
        if errors:
            return errors
        return None

    cdef object conform(self, value):
        if not isinstance(value, Mapping):
            return False
        cdef:
            dict result = {}
            object key
            _Spec spec

        for key, spec in self.spec.items():
            if not key in value:
                if isinstance(spec, Req):
                    return Invalid
                continue
            result[key] = spec.conform(value[key])
            if result[key] == Invalid:
                return Invalid
        cdef object out = copy(value)
        out.update(result)
        return out

    cdef str name(self):
        cdef dict out = {key: spec.name() for key, spec in self.spec.items()}
        return f"keys<{out}>"

def keys(dict spec: t.Dict[t.Any, _Spec]) -> Keys:
    return Keys(spec)

cdef class Req(_Spec):
    def __init__(self, _Spec spec):
        self.spec = spec

    cdef bint valid(self, value):
        return self.spec.valid(value)

    cdef object explain(self, value):
        return self.spec.explain(value)

    cdef object conform(self, value):
        return self.spec.conform(value)

    cdef str name(self):
        return f"Req<{self.spec.name()}>"

def req(_Spec spec) -> Req:
    return Req(spec)

cdef class Opt(_Spec):
    def __init__(self, _Spec spec, object default):
        self.spec = spec
        if default is not None and not spec.valid(default):
            #raise ValueError("non-None default must validate against given Spec")
            raise ValueError(f"value '{default}' does not fulfill given Spec")
        self.default = default

    cdef bint valid(self, value):
        if value is None:
            return True
        return self.spec.valid(value)

    cdef object explain(self, value):
        if value is None:
            return None
        return self.spec.explain(value)

    cdef object conform(self, value):
        if value is None:
            return self.default
        return self.spec.conform(value)

    cdef str name(self):
        return f"Opt<{self.spec.name()}>"

def opt(_Spec spec, default = None) -> Opt:
    return Opt(spec, default)

cdef class InSeq(_Spec):
    def __init__(self, options: t.Sequence[t.Any]):
        self.opts = set(options)

    cdef bint valid(self, value: t.Any):
        return value in self.opts

    cdef object explain(self, value: t.Any):
        if value not in self.opts:
            return f"value not in {', '.join(self.opts)}"
        return None

    cdef object conform(self, value: t.Any):
        if value in self.opts:
            return value
        return Invalid

    cdef str name(self):
        return f"InSeq<{', '.join(self.opts)}>"

def inseq(seq: t.Sequence[t.Any]) -> InSeq:
    return InSeq(seq)

##################################################################


def valid(spec: _Spec, object value: t.Any) -> bool:
    return spec.valid(value)

def conform(spec: _Spec, object value: t.Any) -> t.Any:
    return spec.conform(value)

def explain(spec: _Spec, object value: t.Any) -> t.Any:
    return spec.explain(value)
