cdef extern from "wctype.h" nogil:
    # all whitespace characters except newlines
    int iswblank(wchar_t ch ); # wint_t
    int iswspace(wchar_t ch)  # wint_t


cdef:
    TokenType EOF = 10
    TokenType NEWLINE = 11
    TokenType PREFIX = 12
    TokenType EXPR = 20
    TokenType LITERAL = 21
    TokenType CTRL_KW = 22
    TokenType CTRL_ARGS = 23


cpdef str token_label(TokenType t):
    if t == EOF:
        return "EOF"
    elif t == NEWLINE:
        return "NEWLINE"
    elif t == PREFIX:
        return "PREFIX"
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


cdef:
    TokenizerState TS_EOF = 1
    TokenizerState TS_NL = 2
    TokenizerState TS_PREFIX = 3
    TokenizerState TS_TOPLEVEL = 4
    TokenizerState TS_LITERAL = 5
    TokenizerState TS_EXPR = 6
    TokenizerState TS_CTRL_KW = 7
    TokenizerState TS_CTRL_ARGS = 8
    TS_LINE = 20
    TokenizerState TS_EMIT = 100
    TokenizerState TS_EMIT_NL = 101
    TokenizerState TS_EMIT_PREFIX = 102
    TokenizerState TS_EMIT_LITERAL = 103
    TokenizerState TS_EMIT_EXPR = 104
    TokenizerState TS_EMIT_CTRL_KW = 105
    TokenizerState TS_EMIT_CTRL_ARGS = 106


cpdef str tokenizer_state(TokenizerState tstate):
    if tstate == TS_EOF:
        return "TS_EOF"
    elif tstate == TS_NL:
        return "TS_NL"
    elif tstate == TS_PREFIX:
        return "TS_PREFIX"
    elif tstate == TS_TOPLEVEL:
        return "TS_TOPLEVEL"
    elif tstate == TS_LITERAL:
        return "TS_LITERAL"
    elif tstate == TS_EXPR:
        return "TS_EXPR"
    elif tstate == TS_CTRL_KW:
        return "TS_CTRL_KW"
    elif tstate == TS_CTRL_ARGS:
        return "TS_CTRL_ARGS"
    elif tstate == TS_LINE:
        return "TS_LINE"
    elif tstate == TS_EMIT_NL:
        return "TS_EMIT_NL"
    elif tstate == TS_EMIT_PREFIX:
        return "TS_EMIT_PREFIX"
    elif tstate == TS_EMIT_LITERAL:
        return "TS_EMIT_LITERAL"
    elif tstate == TS_EMIT_EXPR:
        return "TS_EMIT_EXPR"
    elif tstate == TS_EMIT_CTRL_KW:
        return "TS_EMIT_CTRL_KW"
    elif tstate == TS_EMIT_CTRL_ARGS:
        return "TS_EMIT_CTRL_ARGS"
    else:
        return f"UNKNOWN-STATE({tstate})"


cdef class Location:
    def __init__(self, size_t line, size_t col):
        self._line = line
        self._col = col

    def __repr__(self):
        return f"Location<Line: {self._line}, Column: {self._col}>"

    def __str__(self):
        return f"L{self._line}:{self._col}"

    def __eq__(self, other):
        return (
            isinstance(other, Location)
            and other._line == self._line
            and other._col == self._col)

    @property
    def line(self):
        return self._line

    @property
    def col(self):
        return self._col


cdef class Token:
    def __cinit__(self, TokenType type, str lexeme):
        self.lexeme = lexeme
        self.type = type

    def __eq__(self, other):
        return other.type == self.type and other.lexeme == self.lexeme

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"({token_label(self.type)}: {self.lexeme})"


cdef:
    Token TOK_EOF = Token(EOF, '<EOF>')
    Token TOK_NEWLINE = Token(NEWLINE, '<NL>')


cdef class TokenFactory:
    """Python-only wrapper for TokenFactory

    Proxies calls to TokenFactory, use TokenFactory directly from Cython"""
    @staticmethod
    def eof():
        return TOK_EOF

    @staticmethod
    def newline():
        return TOK_NEWLINE

    @staticmethod
    def prefix(str lexeme):
        return Token.__new__(Token, PREFIX, lexeme)

    @staticmethod
    def expr(str lexeme):
        return Token.__new__(Token, EXPR, lexeme)

    @staticmethod
    def literal(str lexeme):
        return Token.__new__(Token, LITERAL, lexeme)

    @staticmethod
    def ctrl_kw(str lexeme):
        return Token.__new__(Token, CTRL_KW, lexeme)

    @staticmethod
    def ctrl_args(str lexeme):
        return Token.__new__(Token, CTRL_ARGS, lexeme)


cdef inline bint peek_2(wchar_t *buf, Py_ssize_t pos, wchar_t ch1, wchar_t ch2):
    return buf[pos] == ch1 and buf[pos+1] == ch2


cdef class Tokenizer:
    def __init__(self, str prog):
        self.prog = prog
        self.prog_len = len(prog)
        self.buf = prog # get ref to underlying buffer
        self.state = TS_NL
        self.pos = 0

    cpdef Token next(self):
        cdef:
            wchar_t *buf = self.buf
            Py_ssize_t pos = self.pos
            Py_ssize_t prog_len = self.prog_len
            TokenizerState state = self.state
            Py_ssize_t start

        while True:
            # print(f"LOOP, state: {tokenizer_state(state)}")
            if state == TS_EOF:
                self.state = TS_EOF
                return TOK_EOF

            if state == TS_NL:
                # => EOF?
                if pos == self.prog_len:
                    state = TS_EOF
                    continue

                # => PREFIX?
                if iswblank(buf[pos]):
                    # scan past whitespace to find first newline/character
                    pos += 1
                    while iswblank(buf[pos]):
                        pos += 1

                if self.pos != pos:
                    # consumed some whitespace, emit prefix
                    state = TS_EMIT_PREFIX
                    continue

                # => NL?
                if buf[pos] == '\n':
                    state = TS_EMIT_NL
                    continue

                # >> TOPLEVEL
                state = TS_TOPLEVEL
                continue

            elif state == TS_PREFIX:
                # => NL?
                if buf[pos] == '\n':
                    state = TS_EMIT_NL
                    continue

                # >> TOPLEVEL
                state = TS_TOPLEVEL
                continue

            elif state == TS_TOPLEVEL:
                # => NL?
                if buf[pos] == '\n':
                    state = TS_EMIT_NL
                    continue

                if buf[pos] == '%':
                    # => LITERAL!
                    if buf[pos+1] == '%':
                        pos += 1 # consume/skip the one '%'
                        state = TS_EMIT_LITERAL
                        self.state = TS_LINE
                        continue
                    # => CTRL_KW!
                    state = TS_EMIT_CTRL_KW
                    self.state = TS_EMIT_CTRL_ARGS
                    continue

                # >> LINE
                state = TS_LINE
                continue

            elif state == TS_LINE:
                # => NL?
                if buf[pos] == '\n':
                    state = TS_EMIT_NL
                    continue

                # => EXPR
                if buf[pos] == '<' and buf[pos+1] == '<':
                    state = TS_EMIT_EXPR
                    continue

                # => LITERAL, >> TS_EMIT_LITERAL
                state = TS_EMIT_LITERAL
                continue

            elif state == TS_EMIT_NL:
                if buf[pos] == '\n':
                    self.pos = pos + 1
                    self.state = TS_NL
                    return TOK_NEWLINE ## TODO: rename to TOK_NEWLINE after refactor

            elif state == TS_EMIT_PREFIX:
                start = self.pos
                self.pos = pos
                self.state = TS_TOPLEVEL
                return Token.__new__(Token, PREFIX, buf[start:pos])

            elif state == TS_EMIT_EXPR:
                pos += 2
                start = pos
                while True:
                    if pos == prog_len or buf[pos] == '\n':
                        raise RuntimeError("error - expression not closed")
                    elif buf[pos] == '>' and buf[pos + 1] == '>':
                        self.pos = pos + 2
                        self.state = TS_LINE
                        return Token.__new__(Token, EXPR, buf[start:pos])

                    pos += 1

            elif state == TS_EMIT_LITERAL:
                start = pos
                while True:
                    # if EOF - return what we got as a literal
                    if pos == prog_len:
                        self.pos = pos
                        self.state = TS_EOF
                        break
                    # iff at start of an expression
                    elif buf[pos] == '<' and buf[pos + 1] == '<':
                        # literal ended by an expression starting
                        self.pos = pos
                        self.state = TS_EMIT_EXPR
                        break
                    # iff a newline is encountered
                    elif buf[pos] == '\n':
                        self.pos = pos
                        self.state = TS_NL
                        break
                    pos += 1
                if start == pos:
                    # prevent empty literal tokens
                    state = self.state
                    continue
                return Token.__new__(Token, LITERAL, buf[start:pos])

            elif state == TS_EMIT_CTRL_KW:
                pos += 1 # consume '%'
                while pos != prog_len and iswblank(buf[pos]):
                    pos += 1
                if pos == prog_len:
                    raise RuntimeError("EOF err - line terminated without any CtrlKW")
                # found beginning of CtrlKW
                start = pos
                while pos != prog_len and not iswspace(buf[pos]):
                    pos += 1
                self.state = TS_EMIT_CTRL_ARGS  # TODO: good idea ? can also have a newline, must handle
                self.pos = pos
                return Token.__new__(Token, CTRL_KW, buf[start:pos])

            elif state == TS_EMIT_CTRL_ARGS:
                while iswblank(buf[pos]):
                    pos += 1
                # got a ctrl line, returned a CtrlKW token, (optionally) parse args.
                start = pos
                while pos != prog_len and buf[pos] != '\n':
                    pos += 1
                self.pos = pos
                self.state = TS_NL
                if start == pos:
                    # No args were given, restart tokenization @ top-level state
                    state = self.state
                    continue
                return Token.__new__(Token, CTRL_ARGS, buf[start:pos])

            else:
                raise RuntimeError(f"unrecognized tokenizer state: {state}")


    cpdef Location location(self):
        """Compute current line and column offset of tokenizer.
        Returns
        -------
            A `Location` object describing the line number and column offset of the tokenizer's current position.
        """
        cdef:
            wchar_t *buf = self.buf
            size_t end_pos = self.pos

            size_t pos = 0

            size_t line = 1
            size_t nl_pos = 0

        while pos <= end_pos:
            if buf[pos] == '\n':
                nl_pos = pos
                line += 1
            pos += 1

        return Location(line, end_pos - nl_pos - 1)