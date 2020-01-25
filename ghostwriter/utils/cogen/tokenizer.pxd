# cython: language_level=3
ctypedef Py_UNICODE wchar_t
ctypedef Py_ssize_t TokenizerState
ctypedef Py_ssize_t TokenType


cdef:
    TokenType EOF
    TokenType NEWLINE
    TokenType EXPR
    TokenType LITERAL
    TokenType CTRL_KW
    TokenType CTRL_ARGS


cdef:
    TokenizerState T_TOPLEVEL
    TokenizerState T_LINE
    TokenizerState T_CTRL_LINE

cdef class Location:
    cdef:
        size_t _line
        size_t _col


cdef class Token:
    cpdef public str lexeme
    cpdef public TokenType type


cdef class CtrlToken(Token):
    cpdef public str prefix


cdef class TokenFactory:
    @staticmethod
    cdef Token eof()

    @staticmethod
    cdef Token newline()

    @staticmethod
    cdef Token expr(str lexeme)

    @staticmethod
    cdef Token literal(str lexeme)

    @staticmethod
    cdef Token ctrl_kw(str lexeme, str prefix = ?)

    @staticmethod
    cdef Token ctrl_args(str lexeme)


cdef class PyTokenFactory:
    pass


cdef class Tokenizer:
    cdef:
        str prog
        Py_ssize_t prog_len
        wchar_t *buf
        # TokenType last
        TokenizerState state
        Py_ssize_t pos

    cpdef Token next(self)
    cpdef Location location(self)


cpdef str token_label(TokenType t)