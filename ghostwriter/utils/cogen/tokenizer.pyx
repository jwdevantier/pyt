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


cdef:
    TokenizerState T_TOPLEVEL = 1
    TokenizerState T_LINE = 2
    TokenizerState T_CTRL_LINE = 3


cpdef str tokenizer_state(TokenizerState tstate):
    if tstate == T_TOPLEVEL:
        return "TOPLEVEL"
    elif tstate == T_LINE:
        return "LINE"
    elif tstate == T_CTRL_LINE:
        return "T_CTRL_LINE"
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
    def __init__(self, TokenType type, str lexeme):
        self.lexeme = lexeme
        self.type = type

    def __eq__(self, other):
        return other.type == self.type and other.lexeme == self.lexeme

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"({token_label(self.type)}: {self.lexeme})"


cdef class CtrlToken(Token):
    def __init__(self, str lexeme, str prefix):
        super().__init__(CTRL_KW, lexeme)
        self.prefix = prefix

    def __eq__(self, other):
        return other.type == self.type and other.lexeme == self.lexeme and other.prefix == self.prefix

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"({self.type}: '{self.prefix} {self.lexeme}')"


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
    cdef Token ctrl_kw(str lexeme, str prefix = ''):
        return CtrlToken(lexeme, prefix)

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
    def ctrl_kw(str lexeme, str prefix = ''):
        return TokenFactory.ctrl_kw(lexeme, prefix)

    @staticmethod
    def ctrl_args(str lexeme):
        return TokenFactory.ctrl_args(lexeme)


cdef inline bint peek_2(wchar_t *buf, Py_ssize_t pos, wchar_t ch1, wchar_t ch2):
    return buf[pos] == ch1 and buf[pos+1] == ch2


cdef class Tokenizer:
    def __init__(self, str prog):
        self.prog = prog
        self.prog_len = len(prog)
        self.buf = prog # get ref to underlying buffer
        self.state = T_TOPLEVEL
        self.pos = 0


    cpdef Token next(self):
        cdef:
            wchar_t *buf = self.buf
            Py_ssize_t pos = self.pos
            Py_ssize_t prog_len = self.prog_len
            TokenizerState state = self.state
            Py_ssize_t pos_prefix_start = pos
            Py_ssize_t pos_prefix_end
            Py_ssize_t start

        if pos == self.prog_len:
            return T_EOF

        if state == T_LINE:
            if buf[pos] == '<' and buf[pos + 1] == '<':
                pos += 2
                start = pos
                while True:
                    if pos == prog_len or buf[pos] == '\n':
                        raise RuntimeError("error - expression not closed")
                    if buf[pos] == '>' and buf[pos + 1] == '>':
                        self.pos = pos + 2
                        # retain state
                        return TokenFactory.expr(buf[start:pos])

                    pos += 1
                    # TODO: EOF check ?
            # => must be a literal or newline
            elif buf[pos] == '\n':
                self.pos = pos + 1
                self.state = T_TOPLEVEL
                return T_NEWLINE ## TODO: rename to TOK_NEWLINE after refactor
            # => a literal
            start = pos
            while True:
                # if EOF - return what we got as a literal
                if pos == prog_len:
                    self.pos = pos
                    self.state = T_TOPLEVEL # TODO: signal EOF permanently ?

                    return TokenFactory.literal(buf[start:pos])
                # iff at start of an expression
                elif buf[pos] == '<' and buf[pos + 1] == '<':
                    # literal ended by an expression starting
                    self.pos = pos
                    # retain state
                    return TokenFactory.literal(buf[start:pos])
                # iff a newline is encountered
                elif buf[pos] == '\n':
                    self.pos = pos
                    self.state = T_TOPLEVEL
                    return TokenFactory.literal(buf[start:pos])
                pos += 1

        elif state == T_TOPLEVEL:
            # scan past whitespace to find first newline/character
            if iswblank(buf[pos]):
                pos += 1
                while iswblank(buf[pos]):
                    pos += 1

            # whitespace, iff NL/EXPR follows, we must first emit a literal containing the whitespace
            if self.pos != pos:
                # got a newline? emit a literal and count on next call to emit the newline itself
                if buf[pos] == '\n':
                    self.pos = pos + 1
                    # retain state
                    return TokenFactory.literal(buf[pos_prefix_start:pos])
                # got an expression ? emit a literal and transition to the line state
                elif buf[pos] == '<' and buf[pos+1] == '<':
                    self.pos = pos
                    self.state = T_LINE
                    return TokenFactory.literal(buf[pos_prefix_start:pos])
            # no whitespace, for NL/EXPR, this means we can process and emit these directly
            else:
                if buf[pos] == '\n':
                    self.pos = pos + 1
                    # retain state
                    return T_NEWLINE
                elif buf[pos] == '<' and buf[pos+1] == '<':
                    # transition to LINE state
                    self.pos = pos
                    self.state = T_LINE
                    return self.next()

            # no whitespace/NL/EXPR token => CtrlKW/Literal
            if buf[pos] == '%':
                pos_prefix_end = pos
                pos += 1 # skip first '%' (for now)
                # '%' is escaped -> literal line, emit literal with one '%' and transition to the line state
                if buf[pos] == '%':
                    self.pos = pos + 1
                    self.state = T_LINE
                    return TokenFactory.literal(buf[pos_prefix_start:pos])

                # => Ctrl line
                # pos @ first ch past '%' - may have whitespace to skip.
                while pos != prog_len and iswblank(buf[pos]):
                    pos += 1
                if pos == prog_len:
                    raise RuntimeError("EOF err - line terminated without any CtrlKW")
                # found beginning of CtrlKW
                start = pos # TODO: keep an additional var around ?
                while pos != prog_len and not iswspace(buf[pos]):
                    pos += 1
                self.state = T_CTRL_LINE
                self.pos = pos
                return TokenFactory.ctrl_kw(buf[start:pos], buf[pos_prefix_start:pos_prefix_end])

            # => literal, do NOT update pos as whitespace should be included in literals...
            self.state = T_LINE
            return self.next()
        elif state == T_CTRL_LINE:
            while iswblank(buf[pos]):
                pos += 1
            # got a ctrl line, returned a CtrlKW token, (optionally) parse args.
            begin = pos
            while pos != prog_len and buf[pos] != '\n':
                pos += 1
            self.pos = pos
            self.state = T_TOPLEVEL
            if begin == pos:
                # No args were given, restart tokenization @ top-level state
                return self.next()
            return TokenFactory.ctrl_args(buf[begin:pos])
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