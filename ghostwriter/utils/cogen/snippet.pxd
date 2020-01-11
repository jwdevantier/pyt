# cython: language_level=3
from ghostwriter.parser.fileparser cimport Context, SnippetCallbackFn
from ghostwriter.utils.iwriter cimport IWriter


cdef class ComponentSnippet(SnippetCallbackFn):
    cdef:
        object component
        dict blocks

    cpdef void apply(self, Context ctx, str snippet, str prefix, IWriter fw) except *