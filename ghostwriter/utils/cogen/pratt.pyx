DEF BP_LOWEST = 0

cdef class UnexpectedTokenError(Exception):
    def __init__(self, str token_type, str msg = None):
        self.token_type = token_type
        super().__init__(
            f"Unexpected '{token_type}' - {msg}" if msg else f"Unexpected '{token_type}'"
        )

cdef class Definition:
    def __init__(self, str token_type, size_t lbp):
        self.token_type = token_type
        self.lbp = lbp
        self.nud_fn = None
        self.led_fn = None

    cdef NODE nud(self, TOKEN token, Parser parser):
        if self.nud_fn is None:
            raise UnexpectedTokenError(self.token_type, "no nud/prefix handler installed")
        return (<object> self.nud_fn)(token, parser)

    cdef NODE led(self, TOKEN token, Parser parser, NODE left):
        if self.led_fn is None:
            raise UnexpectedTokenError(self.token_type, "no led/infix handler installed")
        return (<object> self.led_fn)(token, parser, left)

    def __repr__(self):
        return f"Definition(type: {self.token_type}, lbp: {self.lbp}, nud: {self.nud_fn is not None}, led: {self.led_fn is not None})"

cdef class Grammar:
    def __init__(self):
        self.definitions = {}

    def symbol(self, type: str) -> None:
        if type in self.definitions:
            raise RuntimeError(f"symbol '{type}' already defined!")

        self.definitions[type] = Definition(type, BP_LOWEST)

    def nud(self, type: str, lbp=BP_LOWEST):
        def wrapper(fn):
            cdef Definition definition = self.definitions.get(type)
            if definition is None:
                definition = Definition(type, lbp)
                self.definitions[type] = definition
            elif definition.nud_fn is not None:
                raise RuntimeError("nud already defined!") # TODO refine error
            definition.nud_fn = fn
            return fn
        return wrapper

    def led(self, type: str, lbp=BP_LOWEST):
        def wrapper(fn):
            cdef Definition definition = self.definitions.get(type)
            if definition is None:
                definition = Definition(type, lbp)
                self.definitions[type] = definition
            elif definition.led_fn is not None:
                raise RuntimeError("led already defined!") # TODO refine error
            definition.led_fn = fn
            return fn
        return wrapper

    # helpers

    def literal(self, type: str):
        def decorator(fn):
            @self.nud(type)
            def null_denotation(token: TOKEN, parser: Parser) -> NODE:
                return fn(token)
            return fn
        return decorator

    def prefix(self, type: str, bp: int):
        def decorator(fn):
            @self.nud(type, bp)
            def null_denotation(token: TOKEN, parser: Parser) -> NODE:
                cdef NODE operand = parser.parse(rbp=bp)
                return fn(token, operand)
            return fn
        return decorator

    def infix(self, type, bp):
        def decorator(fn):
            @self.led(type, bp)
            def left_denotation(operator, parser, left):
                cdef NODE right = parser.parse(rbp=bp)
                return fn(operator, left, right)
            return fn
        return decorator

    def infix_r(self, type: str, bp: int):
        """
        Create a right-associative infix parsing rule.

        If '+' were right-associative, it would mean that '1 + 2 + 3' would
        be evaluated as '1 + (2 + 3)'.
        For Pratt parsers, this is achieved by parsing the RH-side of the
        expression with a lower binding power.

        Parameters
        ----------
        type
            The token type
        bp : str

        Returns
        -------

        """
        def decorator(fn):
            @self.led(type, bp)
            def left_denotation(operator, parser, left):
                cdef NODE right = parser.parse(rbp=bp - 1)
                return fn(operator, left, right)
            return fn
        return decorator

    def postfix(self, type: str, bp: int):
        def decorator(fn):
            @self.led(type, bp)
            def left_denotation(operator, parser, left):
                return fn(operator, left)
            return fn
        return decorator

    def enclosing(self, type_begin: str, type_end: str, bp: int):
        def decorator(fn):
            @self.nud(type_begin, bp)
            def null_denotation(left: TOKEN, parser: Parser) -> None:
                cdef:
                    NODE body = parser.parse()
                    TOKEN right = parser.advance(type_end)
                return fn(left, right, body) # TODO: seems odd, check arg order
            self.symbol(type_end)
            return fn
        return decorator

    def ternary(self, t_first_sep, t_second_sep, bp):
        def decorator(fn):
            @self.led(t_first_sep, bp)
            def left_denotation(first_sep: TOKEN, parser: Parser, left: NODE):
                cdef NODE second = parser.parse()
                cdef NODE n_second_sep = parser.advance(t_second_sep)
                cdef NODE third = parser.parse()
                return fn(first_sep, n_second_sep, left, second, third)
            self.symbol(t_second_sep)
            return fn
        return decorator

    # INTERNAL API

    cdef size_t rbp(self, TOKEN token):
        cdef:
            Definition definition = self.definitions.get(token.type)
        if definition is None:
            raise UnexpectedTokenError(token.type)
        return definition.lbp

    cdef NODE parse_nud(self, TOKEN token, Parser parser):
        cdef Definition definition = self.definitions.get(token.type)
        if definition is None:
            raise UnexpectedTokenError(token.type)
        return definition.nud(token, parser)

    cdef NODE parse_led(self, TOKEN token, Parser parser, NODE left):
        cdef Definition definition = self.definitions.get(token.type)
        if definition is None:
            raise UnexpectedTokenError(token.type)
        return definition.led(token, parser, left)


cdef class Parser:
    def __init__(self, Grammar grammar, object tokenizer):
        self.grammar = grammar
        self.tokenizer = tokenizer
        self.curr_token = next(tokenizer)

    cdef TOKEN advance(self, str typ):
        cdef TOKEN advanced
        if self.curr_token.type == typ:
            advanced = self.curr_token
            self.curr_token = next(self.tokenizer)
            return advanced
        return None

    cpdef NODE parse(self, size_t rbp=BP_LOWEST):
        cdef:
            TOKEN left = self.curr_token
            NODE left_node
        self.curr_token = next(self.tokenizer)
        left_node = self.grammar.parse_nud(left, self)
        while rbp < self.grammar.rbp(self.curr_token):
            left = self.curr_token
            self.curr_token = next(self.tokenizer)
            left_node = self.grammar.parse_led(left, self, left_node)
        return left_node