# cython: language_level=3
ctypedef Py_UNICODE wchar_t

cdef enum TokenType:
    CtrlKwTok, CtrlArgsTok, ExprTok, LiteralTok, NewlineTok, EOFTok

cdef class Token:
    cpdef public str lexeme
    cpdef public str type

cdef class CtrlKw(Token):
    pass

cdef class CtrlArgs(Token):
    pass

cdef class Expr(Token):
    pass

cdef class Literal(Token):
    pass

cdef class Newline(Token):
    pass

cdef class EndOfFile(Token):
    pass

# cdef Newline NL
# cdef EndOfFile EOF

cdef class Tokenizer:
    cdef:
        str prog
        Py_ssize_t prog_len
        wchar_t *buf
        TokenType last
        Py_ssize_t pos

        Token _parse_literal(self, Py_ssize_t start)
    cpdef Token next(self)