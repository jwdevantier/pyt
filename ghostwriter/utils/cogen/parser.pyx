from typing import List
from ghostwriter.utils.cogen.tokenizer cimport (
    Token, Tokenizer, token_label,
    EOF, NEWLINE, EXPR, LITERAL, CTRL_KW, CTRL_ARGS
)

cdef class Node:
    def __repr__(self):
        return f"{type(self).__name__}"


cdef class ParserError(Exception):
    def __init__(self, Location location, str error):
        super().__init__(error)
        self.error = error
        self.location = location

    def __repr__(self):
        return f"ParserError({str(self.location)}: {self.error})"

    def __str__(self):
        return f"Error parsing at {self.location.line}, column {self.location.col}: {self.error}"


cdef class UnexpectedTokenError(ParserError):
    def __init__(self, Location location, Token token):
        cdef:
            str error = f"Unexpected token (lexeme: {token.lexeme}, type: {token.type} ({token_label(token.type)}))"
        super().__init__(location, error)
        self.token = token


cdef class InvalidBlockNestingError(ParserError):
    def __init__(self, Location location, str expected, str actual):
        cdef:
            str error = f"invalid nesting of blocks, expected '{expected}', got '{actual}'"
        super().__init__(location, error)
        self.expected = expected
        self.actual = actual


cdef class InvalidEndBlockArgsError(ParserError):
    def __init__(self, Location location, str end_kw):
        cdef:
            str error = f"block end token '{end_kw}' cannot have arguments"
        super().__init__(location, error)
        self.end_kw = end_kw


cdef class Program(Node):
    def __init__(self, list lines = None):
        self.lines = lines or []

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.lines == other.lines)

    def __repr__(self):
        return f"Program({', '.join(repr(l) for l in self.lines)})"


cdef class Block(Node):
    def __init__(self, CLine header, list lines = None):
        self.header = header
        self.lines = lines or []

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and other.header == self.header
            and other.lines == self.lines
        )

    def __repr__(self):
        return f"Block({repr(self.header)}; {', '.join(repr(l) for l in self.lines)}"


cdef class If(Node):
    def __init__(self, list conds = None):
        self.conds = conds or []

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and other.conds == self.conds
        )

    def __repr__(self):
        return f"If({', '.join(repr(c) for c in self.conds)})"


cdef class Literal(Node):
    def __init__(self, str value):
        self.value = value

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.value == other.value)

    def __repr__(self):
        return f"Literal('{self.value}')"


cdef class Expr(Node):
    def __init__(self, str value):
        self.value = value

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.value == other.value)

    def __repr__(self):
        return f"Expr({self.value})"


cdef class Line(Node):
    def __init__(self, list contents = None):
        self.contents = contents or []

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.contents == other.contents)

    def __repr__(self):
        return f"Line({','.join(repr(c) for c in self.contents)})"


cdef class CLine(Node):
    def __init__(self, str keyword, str args = ''):
        super().__init__()
        self.keyword = keyword
        self.args = args

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.keyword == other.keyword
            and self.args == other.args)

    def __repr__(self):
        if self.args:
            return f"CLine({self.keyword}, {self.args})"
        else:
            return f"CLine({self.keyword})"


cdef:
    size_t IFKW_NONE = 0
    size_t IFKW_IF = 1
    size_t IFKW_ELIF = 2
    size_t IFKW_ELSE = 3
    size_t IFKW_END = 4


cdef size_t lexeme_to_ifkw(str kw):
    if kw == 'if':
        return IFKW_IF
    elif kw == 'elif':
        return IFKW_ELIF
    elif kw == 'else':
        return IFKW_ELSE
    return IFKW_NONE


cdef str ifkw_to_lexeme(size_t ifstate):
    if ifstate == 1:
        return 'if'
    elif ifstate == 2:
        return 'elif'
    elif ifstate == 3:
        return 'else'
    return None


cdef inline bint is_line_start(TokenType tok_type):
    """True iff. token type signals start of a `Line`."""
    # Lines can start with a literal OR an expression.
    return tok_type == LITERAL or tok_type == EXPR


cdef class CogenParser:
    def __init__(self, Tokenizer tokenizer):
        self.tokenizer = tokenizer
        self.curr_token = tokenizer.next()

    cdef Token peek(self):
        return self.curr_token

    cdef Token advance(self):
        self.curr_token = self.tokenizer.next()
        return self.curr_token

    cdef Block _parse_block(self, CLine header):
        cdef:
            list lines = []
            str end_kw = f"/{header.keyword}"
            TokenType tok_type
        while True:
            tok_type = self.curr_token.type
            if is_line_start(tok_type):
                lines.append(self._parse_line())
            elif tok_type == CTRL_KW:
                if self.curr_token.lexeme[0] == '/':
                    if self.curr_token.lexeme == end_kw:
                        # found the end of this block, stop here
                        self.advance() # eat token
                        if self.curr_token.type == CTRL_ARGS:
                            raise InvalidEndBlockArgsError(self.tokenizer.location(), end_kw)
                        break
                    else:
                        raise InvalidBlockNestingError(self.tokenizer.location(), end_kw, self.curr_token.lexeme)
                # => entering new ctrl block
                lines.append(self._parse_block_node(self._parse_cline()))
            elif tok_type == NEWLINE:
                self.advance()
            elif tok_type == EOF:
                # TODO: handle better
                raise RuntimeError("Unexpected EOF in block")
        return Block(header, lines)

    cdef If _parse_if_block(self, CLine header):
        cdef:
            TokenType tok_type
            If if_node = If()
            Block cond = Block(header)
            size_t state = IFKW_IF
            size_t kw_state = IFKW_NONE
        while True:
            tok_type = self.curr_token.type
            if is_line_start(tok_type):
                cond.lines.append(self._parse_line())
            elif tok_type == CTRL_KW:
                kw_state = lexeme_to_ifkw(self.curr_token.lexeme)
                if kw_state == IFKW_NONE or kw_state == IFKW_IF:
                    # => not elif/else, either '/if' (end), 'if' (nested) or some other block
                    if self.curr_token.lexeme[0] == '/':
                        # => end/close tag, '/if' or a mistake
                        if self.curr_token.lexeme != '/if':
                            raise InvalidBlockNestingError(self.tokenizer.location(), '/if', self.curr_token.lexeme)
                        self.advance()  # eat the '/if'
                        if self.curr_token.type == CTRL_ARGS:
                            raise InvalidEndBlockArgsError(self.tokenizer.location(), '/if')
                        if_node.conds.append(cond)
                        break # break while-loop
                    # => nested block
                    # TODO: handle 'if <no args>'
                    cond.lines.append(self._parse_block_node(self._parse_cline()))
                elif kw_state > state or state == IFKW_ELIF and kw_state == IFKW_ELIF:
                    state = kw_state
                    if_node.conds.append(cond)
                    cond = Block(self._parse_cline())
                    if cond.header.keyword == 'else' and cond.header.args != '':
                        raise ParserError(self.tokenizer.location(),
                                          f"invalid 'else' clause, additional arguments '{cond.header.args}' not allowed")
                    continue
                else:
                    raise ParserError(self.tokenizer.location(),
                                      f"invalid order of clauses in if-block, '{self.curr_token.lexeme}' cannot follow '{ifkw_to_lexeme(state)}'")
            elif tok_type == NEWLINE:
                self.advance()
            elif tok_type == EOF:
                # TODO: handle better
                raise RuntimeError("Unexpected EOF in if-block")
            else:
                raise UnexpectedTokenError(self.tokenizer.location(), self.curr_token)
        return if_node

    cdef Node _parse_block_node(self, CLine header):
        if header.keyword == 'if':
            return self._parse_if_block(header)
        elif header.keyword == 'body':
            return Block(header)  # no body, no end-tag
        return self._parse_block(header)

    cdef CLine _parse_cline(self):
        cdef:
            CLine cline
            str keyword
            Token tok = self.curr_token
        if tok.type != CTRL_KW:
            raise RuntimeError(f"Expected CTRL_KW({CTRL_KW}), got {token_label(tok.type)}({tok.type})")
        keyword = tok.lexeme
        tok = self.advance()
        if tok.type == CTRL_ARGS:
            cline = CLine(keyword, tok.lexeme)
            self.advance()
            return cline
        else:
            return CLine(keyword, '')

    cdef Line _parse_line(self):
        cdef:
            Line line = Line()
            Token tok = self.curr_token
        while tok.type in (LITERAL, EXPR):
            line.contents.append(
                Literal(tok.lexeme)
                if tok.type == LITERAL
                else Expr(tok.lexeme)
            )
            tok = self.advance()
        return line

    cpdef Program parse_program(self):
        cdef:
            Program prog = Program()
            TokenType toktype
        while self.curr_token.type != EOF:
            tok_type = self.curr_token.type
            if is_line_start(tok_type):
                prog.lines.append(self._parse_line())
            elif tok_type == CTRL_KW:
                prog.lines.append(self._parse_block_node(self._parse_cline()))
            elif tok_type == NEWLINE:
                self.advance()
            else:
                raise UnexpectedTokenError(self.tokenizer.location(), self.curr_token)
        return prog
