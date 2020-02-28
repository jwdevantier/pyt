from typing import List
from ghostwriter.utils.cogen.tokenizer cimport (
    Token, CtrlToken, Tokenizer, token_label,
    EOF, NEWLINE, PREFIX, EXPR, LITERAL, CTRL_KW, CTRL_ARGS
)


cdef enum IF_STATE:
    IF_STATE_NONE = 0
    IF_STATE_IF = 1
    IF_STATE_ELIF = 2
    IF_STATE_ELSE = 3
    IF_STATE_END = 4


cdef inline IF_STATE tok2if_state(Token tok):
    if tok.type != CTRL_KW:
        return IF_STATE_NONE

    if tok.lexeme == 'if':
        return IF_STATE_IF
    elif tok.lexeme == 'elif':
        return IF_STATE_ELIF
    elif tok.lexeme == 'else':
        return IF_STATE_ELSE
    elif tok.lexeme == '/if':
        return IF_STATE_END
    else:
        return IF_STATE_NONE


cdef class ParserError(Exception):
    def __init__(self, (Py_ssize_t, Py_ssize_t) location, str error):
        super().__init__(error)
        self.error = error
        self.line = location[0]
        self.col = location[1]

    def __repr__(self):
        return f"ParserError(L{self.line},{self.col}: {self.error})"

    def __str__(self):
        return f"Error parsing at L{self.line},{self.col}: {self.error}"


cdef class UnhandledTokenError(ParserError):
    def __init__(self, (Py_ssize_t, Py_ssize_t) location, Token token, str state):
        cdef:
            str error = f"Unexpected token (lexeme: {token.lexeme}, type: {token.type} ({token_label(token.type)})) during {state}"
        super().__init__(location, error)
        self.token = token
        self.state = state


cdef class ExpectedTokenTypeError(ParserError):
    def __init__(self, (Py_ssize_t, Py_ssize_t) location, Token token, TokenType expected):
        cdef:
            str error = f"Expected: {expected}/{token_label(expected)}, got: {token.type}/{token_label(token.type)} (value: '{token.lexeme}')"
        super().__init__(location, error)
        self.token = token
        self.expected_type = expected


cdef class ExpectedTokenError(ParserError):
    def __init__(self, (Py_ssize_t, Py_ssize_t) location, Token token, Token expected):
        cdef:
            str error = f"Expected: {repr(expected)}, Got: {repr(token)}"
        super().__init__(location, error)
        self.token = token
        self.expected = expected


cdef class IndentationError(ParserError):
    def __init__(self, CogenParser p, str message):
        super().__init__(p.tokenizer.location(), message)
        self.block_indentation = p.prefix_block_head
        self.line_indentation = p.prefix_line


cdef class InvalidBlockNestingError(ParserError):
    def __init__(self, (Py_ssize_t, Py_ssize_t) location, str expected, str actual):
        cdef:
            str error = f"invalid nesting of blocks, expected '{expected}', got '{actual}'"
        super().__init__(location, error)
        self.expected = expected
        self.actual = actual


cdef class NodeFactory:
    @staticmethod
    def literal(str value):
        return Literal.__new__(Literal, value)

    @staticmethod
    def expr(str value):
        return Expr.__new__(Expr, value)

    @staticmethod
    def line(str indentation, list children = None):
        return Line.__new__(Line, indentation, children)

    @staticmethod
    def block(str indentation, str keyword, str args = '', list children = None):
        return Block.__new__(Block, indentation, keyword, args, children)

    @staticmethod
    def if_(list conds = None):
        return If.__new__(If, conds)

    @staticmethod
    def program(list lines = None):
        return Program.__new__(Program, lines)


# NODE DEFINITIONS
##################
cdef class Node:
    def __repr__(self):
        return f"{type(self).__name__}"


cdef class Literal(Node):
    def __cinit__(self, str value, Py_ssize_t line = 0, Py_ssize_t col = 0):
        self.value = value
        self.line = line
        self.col = col

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.value == other.value)

    def __repr__(self):
        return f"Literal('{self.value}')"


cdef class Expr(Node):
    def __cinit__(self, str value, Py_ssize_t line = 0, Py_ssize_t col = 0):
        self.value = value
        self.line = line
        self.col = col

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.value == other.value)

    def __repr__(self):
        return f"Expr({self.value})"


cdef class Line(Node):
    def __cinit__(self, str indentation, list children = None):
        self.indentation = indentation
        self.children = children or []

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and other.indentation == self.indentation
            and other.children == self.children
        )

    def __repr__(self):
        return  f"Line('{self.indentation}': {','.join(repr(child) for child in self.children)})"


cdef class Block(Node):
    def __cinit__(self, str indentation, str keyword, str args = '', list children = None,
                  Py_ssize_t line = 0, Py_ssize_t col_kw = 0, Py_ssize_t col_args = -1):
        self.block_indentation = indentation
        self.keyword = keyword
        self.args = args
        self.children = children or []

        self.line = line
        self.col_kw = col_kw
        self.col_args = col_args

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and other.block_indentation == self.block_indentation
            and other.keyword == self.keyword
            and other.args == self.args
            and other.children == self.children
        )

    def __repr__(self):
        cdef str line
        if self.args:
            line =f"keyword: '{self.keyword}', args: '{self.args}'"
        else:
            line = f"keyword: '{self.keyword}'"
        return  f"Block({line}, block_indentation: '{self.block_indentation}', children: {','.join(repr(child) for child in self.children)})"


cdef class If(Node):
    def __cinit__(self, list conds = None):
        self.conds = conds or []

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and other.conds == self.conds)

    def __repr__(self):
        return f"If({repr(self.conds)})"


cdef class Program(Node):
    def __cinit__(self, list lines = None):
        self.lines = lines or []

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.lines == other.lines)

    def __repr__(self):
        return f"Program({', '.join(repr(l) for l in self.lines)})"


# HELPER FUNCTIONS
##################
cdef inline bint elif_or_else_block(IF_STATE kw_state):
    return IF_STATE_IF < kw_state < IF_STATE_END


cdef inline bint valid_elif_or_else_block(IF_STATE state, IF_STATE kw_state):
    return state < kw_state < IF_STATE_END or (IF_STATE_ELIF == kw_state == state)


cdef inline str element_indentation(CogenParser p):
    return p.prefix_line[len(p.prefix_block_head):]


cdef inline Line empty_line(CogenParser p):
    return Line.__new__(Line, element_indentation(p), [])


cdef inline block_indent(CogenParser p):
    p.prefix_blocks.append(p.prefix_block_head)
    p.prefix_block_head = p.prefix_line


cdef inline block_dedent(CogenParser p):
    p.prefix_block_head = p.prefix_blocks.pop()  # TODO: check if popping from empty


cdef inline Token consume_expected_token(CogenParser p, TokenType typ):
    cdef Token tok = p.curr_token
    if tok.type != typ:
        raise ExpectedTokenTypeError(p.tokenizer.location(), tok, typ)
    return p.advance()  # consume the token


cdef inline validate_indentation_line(CogenParser p):
    if not p.prefix_line.startswith(p.prefix_block_head):
        raise IndentationError(p, "line - line's indentation must start with the indentation of its surrounding block")


cdef inline validate_indentation_end_block(CogenParser p, str message = "indentation of '% /<block>' must exactly match the indentation of '% <block>'"):
    if p.prefix_line != p.prefix_block_head:
        raise IndentationError(p, message)


cdef inline void expect_token_type(CogenParser p, TokenType typ):
    if p.curr_token.type != typ:
        raise ExpectedTokenTypeError(p.tokenizer.location(), p.curr_token, typ)


cdef inline void expect_token(CogenParser p, TokenType typ, str lexeme):
    cdef Token tok = p.curr_token
    if tok.type != typ or tok.lexeme != lexeme:
        raise ExpectedTokenError(p.tokenizer.location(), p.curr_token, Token(typ, lexeme))


cdef inline void skip_token_if(CogenParser p, TokenType typ):
    if p.curr_token.type == typ:
        p.advance()


# Parser Implementation
#######################
cdef class CogenParser:
    def __init__(self, Tokenizer tokenizer):
        self.tokenizer = tokenizer
        self.curr_token = tokenizer.next()
        self.prefix_blocks = []
        self.prefix_block_head = ''
        self.prefix_line = ''

    cdef Token peek(self):
        return self.curr_token

    cdef Token advance(self):
        self.curr_token = self.tokenizer.next()
        return self.curr_token

    cdef Line _parse_line(self):
        cdef:
            list children = []
            Token tok = self.curr_token

        while tok.type in (LITERAL, EXPR):
            children.append(
                Literal.__new__(Literal, tok.lexeme,
                                line=self.tokenizer.pos_line, col=self.tokenizer.pos_col)
                if tok.type == LITERAL
                else Expr.__new__(Expr, tok.lexeme,
                                  line=self.tokenizer.pos_line, col=self.tokenizer.pos_col)
            )
            tok = self.advance()
        # consume trailing newline.
        if tok.type == NEWLINE:
            self.advance()
        return Line.__new__(Line, element_indentation(self), children)

    cdef If _parse_if_block(self):
        cdef:
            IF_STATE state = IF_STATE_IF
            IF_STATE kw_state
            Token tok = self.curr_token
            str keyword
            list conds = []
            Block cond
            str parent_prefix_block_head = self.prefix_block_head
            Py_ssize_t line
            Py_ssize_t col_kw

        if tok.type != CTRL_KW or tok.lexeme != 'if':
            raise ExpectedTokenError(self.tokenizer.location(), self.curr_token, Token.__new__(Token, CTRL_KW, 'if'))

        block_indent(self)

        while state != IF_STATE_END:
            expect_token_type(self, CTRL_KW)

            keyword = tok.lexeme
            line = self.tokenizer.pos_line
            col_kw = self.tokenizer.pos_col

            tok = self.advance()

            if tok.type == CTRL_ARGS:
                cond = Block.__new__(Block, self.prefix_line[len(parent_prefix_block_head):], keyword, tok.lexeme,
                                     line=line, col_kw=col_kw, col_args=self.tokenizer.pos_col)
                tok = self.advance()
            else:
                cond = Block.__new__(Block, self.prefix_line[len(parent_prefix_block_head):], keyword,
                                     line=line, col_kw=col_kw)
            conds.append(cond)
            tok = consume_expected_token(self, NEWLINE)

            while True:  # per line
                if tok.type == PREFIX:
                    self.prefix_line = tok.lexeme
                    tok = self.advance()
                else:
                    self.prefix_line = ''

                if tok.type == CTRL_KW:
                    kw_state = tok2if_state(tok)
                    if tok.lexeme[0] == '/':
                        if tok.lexeme == '/if':
                            validate_indentation_end_block(self)
                            block_dedent(self)
                            tok = self.advance()
                            skip_token_if(self, NEWLINE)
                            state = IF_STATE_END
                            break
                        else:
                            raise InvalidBlockNestingError(self.tokenizer.location(), '/if', self.curr_token.lexeme)
                    elif valid_elif_or_else_block(state, kw_state):
                        validate_indentation_end_block(self, "all condition blocks must have the exact same indentation as the opening 'if'-block")
                        state = kw_state
                        break

                    validate_indentation_line(self)
                    if kw_state == IF_STATE_IF:  # nested if, recurse
                        cond.children.append(self._parse_if_block())
                    elif kw_state == IF_STATE_NONE and tok.lexeme[0] != '/':
                        cond.children.append(self._parse_block())
                    else:
                        raise UnhandledTokenError(self.tokenizer.location(), tok, '_parse_if_block:ctrl_kw')
                else:
                    validate_indentation_line(self)
                    if tok.type == LITERAL or tok.type == EXPR:
                        cond.children.append(self._parse_line())
                    elif tok.type == NEWLINE:
                        cond.children.append(empty_line(self))
                        self.advance()
                    else:
                        raise UnhandledTokenError(self.tokenizer.location(), self.curr_token, "_parse_if_block:else")
                tok = self.curr_token
        return If.__new__(If, conds)

    cdef Block _parse_block(self):
        cdef:
            str keyword = self.curr_token.lexeme
            str end_kw = f"/{keyword}"
            list children = []
            str args = ''
            str prefix = self.prefix_line
            Token tok
            Py_ssize_t line
            Py_ssize_t col_kw
            Py_ssize_t col_args = -1

        if keyword == 'if':
            raise UnhandledTokenError(self.tokenizer.location(), self.curr_token, "_parse_block")

        line = self.tokenizer.pos_line
        col_kw = self.tokenizer.pos_col
        if keyword == 'body':
            validate_indentation_line(self)
            self.advance()
            skip_token_if(self, NEWLINE)
            return Block.__new__(Block, element_indentation(self), keyword, line=line, col_kw=col_kw)

        block_indent(self)

        tok = self.advance()
        if tok.type == CTRL_ARGS:
            args = tok.lexeme
            col_args = self.tokenizer.pos_col
            tok = self.advance()
        tok = consume_expected_token(self, NEWLINE)

        while True:  # per line
            if tok.type == PREFIX:
                self.prefix_line = tok.lexeme
                tok = self.advance()
            else:
                self.prefix_line = ''

            if tok.type == CTRL_KW and tok.lexeme[0] == '/':
                validate_indentation_end_block(self)
                block_dedent(self)
                if tok.lexeme == end_kw:
                    # found the end of the block, stop here
                    tok = self.advance()
                    skip_token_if(self, NEWLINE)
                    break
                else:
                    raise InvalidBlockNestingError(self.tokenizer.location(), end_kw, self.curr_token.lexeme)

            validate_indentation_line(self)
            if tok.type == CTRL_KW:
                if tok.lexeme == 'if':
                    children.append(self._parse_if_block())
                else:
                    children.append(self._parse_block())
            elif tok.type == LITERAL or tok.type == EXPR:
                children.append(self._parse_line())
            elif tok.type == NEWLINE:
                children.append(empty_line(self))
                self.advance()
            else:
                raise UnhandledTokenError(self.tokenizer.location(), self.curr_token, "_parse_block")
            tok = self.curr_token
        return Block.__new__(Block, element_indentation(self), keyword, args, children,
                             line=line, col_kw=col_kw, col_args=col_args)

    # Indentation @ block-level is really as simple as registering the line prefix
    cpdef Program parse_program(self):
        cdef:
            Token tok = self.curr_token
            list children = []
        while True:
            self.prefix_line = ''
            if tok.type == PREFIX:
                self.prefix_line = tok.lexeme
                tok = self.advance()

            if tok.type == LITERAL or tok.type == EXPR:
                children.append(self._parse_line())
            elif tok.type == CTRL_KW:
                if tok.lexeme == 'if':
                    children.append(self._parse_if_block())
                else:
                    children.append(self._parse_block())
            elif tok.type == NEWLINE:
                children.append(empty_line(self))
                tok = self.advance()
            elif tok.type == EOF:
                break
            else:
                raise UnhandledTokenError(self.tokenizer.location(), self.curr_token, "parse_program")
            tok = self.curr_token

        return Program.__new__(Program, children)
