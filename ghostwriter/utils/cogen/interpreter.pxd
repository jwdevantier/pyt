# cython: language_level=3

from ghostwriter.utils.iwriter cimport IWriter
from ghostwriter.utils.cogen.parser cimport (
    Program, Block, If, Literal, Expr, Line, CLine, Node
)


cdef class Writer(IWriter):
    cdef:
        IWriter _writer
        list _prefixes
        str _base_prefix
        str _curr_prefix

    cpdef void indent(self, str prefix)
    cpdef void dedent(self)
    cpdef void write(self, str contents)
    cpdef void newline(self)


cpdef void interpret(Program program, Writer w, dict blocks, dict scope) except *
