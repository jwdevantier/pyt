# cython: language_level=3
# Clojure Spec API
# https://clojure.github.io/spec.alpha/clojure.spec.alpha-api.html#clojure.spec.alpha/explain

# Clojure Spec Guide
# https://clojure.org/guides/spec

# file:///home/pseud/repos/codegen/pyt/pyt/utils/spec.html
import typing as t

cdef class Spec:
    cdef bint valid(self, object value: t.Any)
    cdef object explain(self, object value: t.Any)
    cdef object conform(self, object value: t.Any)
    cdef str name(self)

cdef class SpecBase(Spec):
    pass

cdef class Type(Spec):
    cdef type typ

cdef class Predicate(Spec):
    cdef unicode predicate_name
    cdef object predicate

cdef class AllOf(Spec):
    cdef dict specs

cdef class AnyOf(Spec):
    cdef dict specs

cdef class SeqOf(Spec):
    cdef Spec element_spec

cdef class MapOf(Spec):
    cdef Spec key_spec
    cdef Spec val_spec

cdef class Keys(Spec):
    cdef dict spec

cdef class Req(Spec):
    cdef Spec spec

cdef class Opt(Spec):
    cdef Spec spec
    cdef object default

cdef class InSeq(Spec):
    cdef set opts