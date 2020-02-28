# cython: language_level=3
ctypedef Py_UNICODE wchar_t
ctypedef Py_ssize_t TokenizerState
ctypedef Py_ssize_t TokenType


cdef:
    TokenType EOF
    TokenType NEWLINE
    TokenType PREFIX
    TokenType EXPR
    TokenType LITERAL
    TokenType CTRL_KW
    TokenType CTRL_ARGS


cdef class Token:
    cpdef public str lexeme
    cpdef public TokenType type


cdef class CtrlToken(Token):
    cpdef public str prefix


cdef class TokenFactory:
    pass


cdef class Tokenizer:
    cdef:
        str prog
        Py_ssize_t prog_len
        wchar_t *buf
        TokenizerState state
        Py_ssize_t pos


        Py_ssize_t _pos_nl
    cdef public Py_ssize_t pos_line
    cdef public Py_ssize_t pos_col

    cpdef Token next(self)
    cpdef location(self)


cpdef str token_label(TokenType t)