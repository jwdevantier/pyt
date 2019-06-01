# cython: language_level=3
import typing as t
from copy import copy
from collections import Sequence, Mapping

# Inspiration: https://clojure.org/guides/spec
# Like clojure spec, dicts etc are OPEN

cdef class _Invalid:
    def __repr__(self):
        return "#Invalid"

Invalid = _Invalid()

cdef class Spec:
    cdef bint valid(self, object value):
        raise NotImplementedError("valid is not implemented")

    cdef object explain(self, object value):
        raise NotImplementedError("explain is not implemented")

    cdef object conform(self, object value):
        raise NotImplementedError("conform is not implemented")

    cdef str name(self):
        return self.__repr__()

cdef class SpecBase(Spec):
    cdef bint valid(self, object value: t.Any):
        return self._valid(value)

    cdef object explain(self, object value: t.Any):
        return self._explain(value)

    cdef object conform(self, object value: t.Any):
        return self._conform(value)

    cdef str name(self):
        return self._name()

cdef class Type(Spec):
    def __init__(self, type t: type):
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

def typ(o: t.Type) -> Spec:
    if not isinstance(o, type):
        raise ValueError("argument should be a type")
    return Type(o)

cdef class Predicate(Spec):
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

cdef class AllOf(Spec):
    def __init__(self, dict specs: t.Dict[str, Spec]):
        self.specs = specs

    cdef bint valid(self, object value: t.Any):
        cdef Spec spec
        for spec in self.specs.values():
            if not spec.valid(value):
                return False
        return True

    cdef object explain(self, object value: t.Any):
        cdef:
            dict errors = {}
            object s_errs = None
            Spec spec
        for label, spec in self.specs.items():
            s_errs = spec.explain(value)
            if s_errs:
                errors[label] = s_errs
        if errors == {}:
            return None
        return errors

    cdef object conform(self, object value: t.Any):
        cdef Spec spec
        for spec in self.specs.values():
            if spec.conform(value) == Invalid:
                return Invalid
        return value  # How else can one conform to all?

    cdef str name(self):
        return f"all<{', '.join(self.specs.keys())}>"

def allof(dict specmap: t.Dict[str, Spec]) -> AllOf:
    return AllOf(specmap)

cdef class AnyOf(Spec):
    def __init__(self, dict specs: t.Dict[str, Spec]):
        self.specs = specs

    cdef bint valid(self, object value: t.Any):
        cdef:
            Spec spec
        for spec in self.specs.values():
            if spec.valid(value):
                return True
        return False

    cdef object explain(self, object value: t.Any):
        cdef:
            dict errors = {}
            object s_errs = None
            Spec spec
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
            Spec spec
            str label
            object retval
        for label, spec in self.specs.items():
            retval = spec.conform(value)
            if retval != Invalid:
                return label, retval
        return Invalid

    cdef str name(self):
        return f"any<{', '.join(self.specs.keys())}>"

def anyof(dict specmap: t.Dict[str, Spec]) -> AnyOf:
    return AnyOf(specmap)

cdef class SeqOf(Spec):
    def __init__(self, Spec element_spec: Spec):
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

def seqof(Spec element_spec: Spec) -> SeqOf:
    return SeqOf(element_spec)

cdef class MapOf(Spec):
    def __init__(self, Spec keyspec: Spec, Spec valspec: Spec):
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
            Spec key_spec = self.key_spec
            Spec val_spec = self.val_spec
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
            Spec key_spec = self.key_spec
            Spec val_spec = self.val_spec
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

def mapof(Spec keyspec: Spec, Spec valspec: Spec) -> MapOf:
    return MapOf(keyspec, valspec)

cdef class Keys(Spec):
    def __init__(self, dict spec: t.Dict[t.Any, Spec]):
        self.spec = spec

    cdef bint valid(self, value):
        if not isinstance(value, Mapping):
            return False
        cdef:
            object key
            Spec spec
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
            Spec spec
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
            Spec spec

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

def keys(dict spec: t.Dict[t.Any, Spec]) -> Keys:
    return Keys(spec)

cdef class Req(Spec):
    def __init__(self, Spec spec):
        self.spec = spec

    cdef bint valid(self, value):
        return self.spec.valid(value)

    cdef object explain(self, value):
        return self.spec.explain(value)

    cdef object conform(self, value):
        return self.spec.conform(value)

    cdef str name(self):
        return f"Req<{self.spec.name()}>"

def req(Spec spec) -> Req:
    return Req(spec)

cdef class Opt(Spec):
    def __init__(self, Spec spec, object default):
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

def opt(Spec spec, default = None) -> Opt:
    return Opt(spec, default)

cdef class InSeq(Spec):
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

cdef class Any(Spec):
    def __init__(self):
        pass

    cdef bint valid(self, value):
        return True

    cdef object explain(self, value):
        return None

    cdef object conform(self, value):
        return value

def any() -> Any:
    return Any()

################################################################################
# Base Types -- exported in spec/__init__.py
################################################################################
# All of these types are aliased in spec/__init__.py because they shadow
# built-in functionality.

cdef class Int(Spec):
    cdef bint valid(self, value: t.Any):
        return isinstance(value, int)

    cdef object explain(self, value: t.Any):
        if not isinstance(value, int):
            return f"expected 'int', got '{type(value).__name__}'"

    cdef object conform(self, value: t.Any):
        try:
            return int(value)
        except (ValueError, TypeError):
            return Invalid

    cdef str name(self):
        return "Int"

cdef class Float(Spec):
    cdef bint valid(self, value: t.Any):
        return isinstance(value, float)

    cdef object explain(self, value: t.Any):
        if not isinstance(value, float):
            return f"expected 'float', got '{type(value).__name__}'"

    cdef object conform(self, value: t.Any):
        try:
            return float(value)
        except (ValueError, TypeError):
            return Invalid

    cdef str name(self):
        return "Float"

cdef class Str(Spec):
    cdef bint valid(self, value: t.Any):
        return isinstance(value, str)

    cdef object explain(self, value: t.Any):
        if not isinstance(value, str):
            return f"expected 'str', got '{type(value).__name__}'"

    cdef object conform(self, value: t.Any):
        return str(value)

    cdef str name(self):
        return "Str"

cdef class Bool(Spec):
    cdef bint valid(self, value: t.Any):
        return isinstance(value, bool)

    cdef object explain(self, value: t.Any):
        if not isinstance(value, bool):
            return f"expected 'bool', got '{type(value).__name__}'"

    cdef object conform(self, value: t.Any):
        try:
            return bool(value)
        except (ValueError, TypeError):
            return Invalid

    cdef str name(self):
        return "Bool"


################################################################################


def valid(spec: Spec, object value: t.Any) -> bool:
    return spec.valid(value)

def conform(spec: Spec, object value: t.Any) -> t.Any:
    return spec.conform(value)

def explain(spec: Spec, object value: t.Any) -> t.Any:
    return spec.explain(value)
