# cython: language_level=3
ctypedef Py_UNICODE wchar_t

# cdef enum TokenType:
#     CtrlKwTok, CtrlArgsTok, ExprTok, LiteralTok, NewlineTok, EOFTok
ctypedef Py_ssize_t TokenType


cdef:
    TokenType EOF
    TokenType NEWLINE
    TokenType EXPR
    TokenType LITERAL
    TokenType CTRL_KW
    TokenType CTRL_ARGS


cdef class Token:
    cpdef public str lexeme
    cpdef public TokenType type


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
    cdef Token ctrl_kw(str lexeme)

    @staticmethod
    cdef Token ctrl_args(str lexeme)

cdef class PyTokenFactory:
    pass


cdef class Tokenizer:
    cdef:
        str prog
        Py_ssize_t prog_len
        wchar_t *buf
        TokenType last
        Py_ssize_t pos

        Token _parse_literal(self, Py_ssize_t start)
    cpdef Token next(self)

cpdef str token_label(TokenType t)