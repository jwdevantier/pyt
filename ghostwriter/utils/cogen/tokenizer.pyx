cdef extern from "wctype.h" nogil:
    # all whitespace characters except newlines
    int iswblank(wchar_t ch ); # wint_t
    int iswspace(wchar_t ch)  # wint_t

cdef:
    TokenType EOF = 10
    TokenType NEWLINE = 11
    TokenType EXPR = 12
    TokenType LITERAL = 13
    TokenType CTRL_KW = 14
    TokenType CTRL_ARGS = 15

cpdef str token_label(TokenType t):
    if t == EOF:
        return "EOF"
    elif t == NEWLINE:
        return "NEWLINE"
    elif t == EXPR:
        return "EXPR"
    elif t == LITERAL:
        return "LITERAL"
    elif t == CTRL_KW:
        return "CTRL_KW"
    elif t == CTRL_ARGS:
        return "CTRL_ARGS"
    else:
        return f"UNKNOWN({t})"


cdef class Token:
    def __init__(self, TokenType type, str lexeme):
        self.lexeme = lexeme
        self.type = type

    def __eq__(self, other):
        return other.type == self.type and other.lexeme == self.lexeme

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"({self.type}: {self.lexeme})"

cdef:
    Token T_EOF = Token(EOF, '<EOF>')
    Token T_NEWLINE = Token(NEWLINE, '<NL>')

cdef class TokenFactory:
    @staticmethod
    cdef Token eof():
        return T_EOF

    @staticmethod
    cdef Token newline():
        return T_NEWLINE

    @staticmethod
    cdef Token expr(str lexeme):
        return Token(EXPR, lexeme)

    @staticmethod
    cdef Token literal(str lexeme):
        return Token(LITERAL, lexeme)

    @staticmethod
    cdef Token ctrl_kw(str lexeme):
        return Token(CTRL_KW, lexeme)

    @staticmethod
    cdef Token ctrl_args(str lexeme):
        return Token(CTRL_ARGS, lexeme)

cdef class PyTokenFactory:
    """Python-only wrapper for TokenFactory

    Proxies calls to TokenFactory, use TokenFactory directly from Cython"""
    @staticmethod
    def eof():
        return TokenFactory.eof()

    @staticmethod
    def newline():
        return TokenFactory.newline()

    @staticmethod
    def expr(str lexeme):
        return TokenFactory.expr(lexeme)

    @staticmethod
    def literal(str lexeme):
        return TokenFactory.literal(lexeme)

    @staticmethod
    def ctrl_kw(str lexeme):
        return TokenFactory.ctrl_kw(lexeme)

    @staticmethod
    def ctrl_args(str lexeme):
        return TokenFactory.ctrl_args(lexeme)


cdef class Tokenizer:
    def __init__(self, str prog):
        self.prog = prog
        self.prog_len = len(prog)
        self.buf = prog # get ref to underlying buffer
        self.last = NEWLINE
        self.pos = 0

    cdef Token _parse_literal(self, Py_ssize_t start):
        cdef:
            wchar_t *buf = self.buf
            Py_ssize_t pos = start
            Py_ssize_t prog_len = self.prog_len

        self.last = LITERAL
        while True:
            if pos == prog_len:
                self.pos = pos
                return TokenFactory.literal(buf[start:pos])
            if buf[pos] == '<' and buf[pos + 1] == '<':
                # ended by start of expression
                self.pos = pos + 2
                if start != pos:
                    return TokenFactory.literal(buf[start:pos])
                return self.next()
            elif buf[pos] == '\n':
                # ended by a newline
                self.pos = pos
                return TokenFactory.literal(buf[start:pos])
            pos += 1

    cpdef Token next(self):
        cdef:
            wchar_t *buf = self.buf
            Py_ssize_t pos = self.pos
            Py_ssize_t start
            Py_ssize_t prog_len = self.prog_len

        if pos == self.prog_len:
            return T_EOF

        # always skip whitespace (except \n)
        while iswblank(buf[pos]):
            pos += 1

        # emit newline token if needed
        if buf[pos] == '\n':
            self.pos = pos + 1
            self.last = NEWLINE
            return T_NEWLINE

        if self.last == NEWLINE:
            if buf[pos] != '%' or buf[pos + 1] == '%':
                # => Literal
                return self._parse_literal(
                    # advance past first '%' if '%' was escaped
                    (pos + 1) if buf[pos] == '%' else pos)
            else:
                # => Start of CTRL line (CtrlKW)
                pos += 1 # skip past '%'
                while pos != prog_len and iswblank(buf[pos]):
                    pos += 1
                if pos == prog_len:
                    raise RuntimeError("EOF err - iswblank")
                start = pos
                while pos != prog_len and not iswspace(buf[pos]):
                    pos += 1
                self.last = CTRL_KW
                self.pos = pos
                return TokenFactory.ctrl_kw(buf[start:pos])
        elif self.last == CTRL_KW:
            # => Ctrl args
            start = pos
            while pos != prog_len and buf[pos] != '\n':
                pos += 1
            self.pos = pos
            if start == pos:
                return self.next()
            self.last = CTRL_ARGS
            return TokenFactory.ctrl_args(buf[start:pos])
        elif self.last == LITERAL:
            # => expression (newlines are already handled)
            start = pos
            while True:
                if buf[pos] == '>' and buf[pos + 1] == '>':
                    self.pos = pos + 2
                    self.last = EXPR
                    return TokenFactory.expr(buf[start:pos])
                pos += 1
                # TODO: EOF check ?
        elif self.last == EXPR:
            # => literal (newlines are already handled)
            return self._parse_literal(pos)
        else:
            if pos == len(self.prog):
                return T_EOF
            raise RuntimeError("Invalid parse-state")