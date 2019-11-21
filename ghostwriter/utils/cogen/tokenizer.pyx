
# comments (??)
# ... literal line
# % ... ctrl line
# %% ... => '% ...' line

# BREAK INTO NEWLINES

# cdef enum ParseState:
#     PSTATE_DEFAULT, PSTATE_ARGS

cdef extern from "wctype.h" nogil:
    # all whitespace characters except newlines
    int iswblank(wchar_t ch ); # wint_t
    int iswspace(wchar_t ch)  # wint_t


cdef Newline NL = Newline()
cdef EndOfFile EOF = EndOfFile()
cdef Token NONE = Token('none')


cdef class Token:
    def __init__(self, str lexeme):
        self.lexeme = lexeme

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.lexeme == other.lexeme)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"({type(self).__name__}: {self.lexeme})"


cdef class CtrlKw(Token):
    pass

cdef class CtrlArgs(Token):
    pass

cdef class Expr(Token):
    pass

cdef class Literal(Token):
    def __init__(self, str lexeme):
        super().__init__(lexeme)

cdef class Newline(Token):
    def __init__(self):
        super().__init__('')

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __repr__(self):
        return "(Newline)"

cdef class EndOfFile(Token):
    def __init__(self):
        super().__init__('')

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __repr__(self):
        return "(EOF)"

cdef class Tokenizer:
    def __init__(self, str prog):
        self.prog = prog
        self.prog_len = len(prog)
        self.buf = prog # get ref to underlying buffer
        self.last = NewlineTok
        self.pos = 0

    cdef Token _parse_literal(self, Py_ssize_t start):
        cdef:
            wchar_t *buf = self.buf
            Py_ssize_t pos = start
            Py_ssize_t prog_len = self.prog_len

        #raise RuntimeError("so far (_parse_literal 1)")
        self.last = LiteralTok
        while True:
            if pos == prog_len:
                self.pos = pos
                return Literal(buf[start:pos])
            if buf[pos] == '<' and buf[pos + 1] == '<':
                # ended by start of expression
                self.pos = pos + 2
                if start != pos:
                    return Literal(buf[start:pos])
                return self.next()
            elif buf[pos] == '\n':
                # ended by a newline
                self.pos = pos
                return Literal(buf[start:pos])
            pos += 1

    cpdef Token next(self):
        cdef:
            wchar_t *buf = self.buf
            Py_ssize_t pos = self.pos
            Py_ssize_t start
            Py_ssize_t prog_len = self.prog_len

        if pos == self.prog_len:
            return EOF

        # always skip whitespace (except \n)
        while iswblank(buf[pos]):
            pos += 1

        # emit newline token if needed
        if buf[pos] == '\n':
            self.pos = pos + 1
            self.last = NewlineTok
            return NL

        if self.last == NewlineTok:
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
                self.last = CtrlKwTok
                self.pos = pos
                return CtrlKw(buf[start:pos])
        elif self.last == CtrlKwTok:
            # => Ctrl args
            start = pos
            while pos != prog_len and buf[pos] != '\n':
                pos += 1
            self.pos = pos
            if start == pos:
                return self.next()
            self.last = CtrlArgsTok
            return CtrlArgs(buf[start:pos])
        elif self.last == LiteralTok:
            # => expression (newlines are already handled)
            start = pos
            while True:
                if buf[pos] == '>' and buf[pos + 1] == '>':
                    self.pos = pos + 2
                    self.last = ExprTok
                    return Expr(buf[start:pos])
                pos += 1
                # TODO: EOF check ?
        elif self.last == ExprTok:
            # => literal (newlines are already handled)
            return self._parse_literal(pos)
        else:
            if pos == len(self.prog):
                return EOF
            raise RuntimeError("Invalid parse-state")