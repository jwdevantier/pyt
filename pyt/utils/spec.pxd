# cython: language_level=3
# Clojure Spec API
# https://clojure.github.io/spec.alpha/clojure.spec.alpha-api.html#clojure.spec.alpha/explain

# Clojure Spec Guide
# https://clojure.org/guides/spec

# file:///home/pseud/repos/codegen/pyt/pyt/utils/spec.html
import typing as t

# cdef class Spec:
#     cdef bint valid(self, value: t.Any)
#     cdef object explain(self, value: t.Any)
#     cdef object conform(self, value: t.Any)
#     cdef str name(self)
#
# cdef class XSpec(Spec):
#     pass

cdef class _Spec:
    cdef bint valid(self, object value: t.Any)
    cdef object explain(self, object value: t.Any)
    cdef object conform(self, object value: t.Any)
    cdef str name(self)

cdef class Spec(_Spec):
    pass

cdef class Type(_Spec):
    cdef type typ

cdef class Predicate(_Spec):
    cdef unicode predicate_name
    cdef object predicate

cdef class All(_Spec):
    cdef dict specs

cdef class Any(_Spec):
    cdef dict specs

cdef class SeqOf(_Spec):
    cdef _Spec element_spec

cdef class MapOf(_Spec):
    cdef _Spec key_spec
    cdef _Spec val_spec

cdef class Keys(_Spec):
    cdef dict spec

cdef class Req(_Spec):
    cdef Spec spec

cdef class Opt(_Spec):
    cdef Spec spec