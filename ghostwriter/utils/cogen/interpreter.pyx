import typing as t
import io
import colorama as clr
cimport cython
from ghostwriter.utils.cogen.component import Component
from re import compile as re_compile

# TODO: want a 'def'/'set' block to update scope - can call out to functions..?

for_loop_stx = re_compile(r"^(?P<bindings>.+?)\s+in\s+(?P<iterable>.+)")


cdef inline str type_name(object o):
    return type(o).__name__


cdef class InterpreterError(Exception):
    pass


cdef class StackErrorCause:
    cpdef error_message(self):
        pass


cdef class InterpreterSyntaxError(StackErrorCause):
    cdef:
        str text
        int offset

    def __init__(self, str text, int offset):
        self.text = text.rstrip("\n")
        self.offset = offset

    def error_message(self):
        header = f"Syntax error in: {self.text}"
        err_loc = len(header) - len(self.text) + self.offset - 1   # -1 to make space for ^ character
        return f"""{header}\n{' ' * err_loc}^\n"""


cdef class InterpStackTrace(InterpreterError):
    def __init__(self, Py_ssize_t line, Py_ssize_t col, object reason):
        self.line = line
        self.col = col
        self.reason = reason

        # Set by exception handler in program
        self.component = None
        self.filepath = None

    def __repr__(self):
        if not self.component or not self.filepath and isinstance(self.reason, InterpStackTrace):
            return repr(self.reason)

        buf = io.StringIO()
        reason = self.reason
        buf.write(f"Exception in component {clr.Style.BRIGHT}{clr.Fore.GREEN}{self.component}{clr.Style.RESET_ALL}, line {clr.Style.BRIGHT}{clr.Fore.CYAN}{self.line}{clr.Style.RESET_ALL}, offset {clr.Style.BRIGHT}{clr.Fore.CYAN}{self.col}{clr.Style.RESET_ALL}\n")
        buf.write(f"  in {self.filepath}\n")
        while True:
            if isinstance(reason, InterpStackTrace):
                buf.write(f"Caused by component {clr.Style.BRIGHT}{clr.Fore.GREEN}{reason.component}{clr.Style.RESET_ALL}, line {clr.Style.BRIGHT}{clr.Fore.CYAN}{reason.line}{clr.Style.RESET_ALL}, offset {clr.Style.BRIGHT}{clr.Fore.CYAN}{reason.col}{clr.Style.RESET_ALL}\n")
                buf.write(f"  in {reason.filepath}\n")
                reason = reason.reason
            else:
                if hasattr(reason, 'error_message'):
                    buf.write("Caused by:\n")
                    buf.write(reason.error_message())
                elif isinstance(reason, Exception):
                    buf.write(f"Caused by exception: {type(reason).__qualname__}\n")
                    buf.write(repr(reason))
                else:
                    buf.write(f"Caused by:\n")
                    buf.write(repr(reason))
                buf.write("\n")
                break
        return buf.getvalue()


cdef class RenderArgTypeError(InterpreterError):
    def __init__(self, str expr, object obj):
        self.expr = expr
        self.typ = type_name(obj)
        super().__init__(f"render block expects component, but '{expr}' evaluated to '{self.typ}'")


cdef class UnknownNodeType(InterpreterError):
    def __init__(self, Node n):
        cdef str msg = f"Unknown node '{type_name(n)}'"
        self.node = n
        super().__init__(msg)


cdef class UnknownBlockType(InterpreterError):
    def __init__(self, Block b):
        cdef str msg = f"Unknown block type '{b.keyword}' not supported"
        self.block = b
        super().__init__(msg)


@cython.final
cdef class Writer(IWriter):
    def __init__(self, IWriter writer, str prefix = ""):
        self._writer = writer
        self._prefixes = []
        self._curr_prefix = prefix

    cpdef void indent(self, str prefix):
        self._prefixes.append(self._curr_prefix)
        self._curr_prefix += prefix

    cpdef void dedent(self):
        if len(self._prefixes) == 0:
            raise RuntimeError("interpreter error: writer indent/dedent mismatched, cannot dedent further")
        self._curr_prefix = self._prefixes.pop()

    cpdef void write(self, str contents):
        self._writer.write(contents)

    cpdef void write_prefix(self):
        self._writer.write(self._curr_prefix)

    cpdef void newline(self):
        self._writer.write('\n')


cdef py_eval_expr(dict scope, str expr, Py_ssize_t line, Py_ssize_t col):
    """
    Evaluate Python expression and return its value

    Parameters
    ----------
    scope:
        The context in which to evaluate the expression. `env` may contain
        any number of variable bindings.
    expr:
        The expression to evaluate.
    line:
        line location of expression being evaluated
    col:
        column location of expression being evaluated

    Returns
    -------
        The resulting value from evaluating the expression.
    """
    cdef dict eval_locals = dict()
    try:
        exec(f"_it = {expr}", scope, eval_locals)
        return eval_locals['_it']
    except SyntaxError as se:
        # subtract leading 6 characters because they correspond to "_it = "
        raise InterpStackTrace(line, col, InterpreterSyntaxError(se.text[6:], se.offset - 6)) from se


def gen_loop_iterator(str stx, dict scope, Py_ssize_t line, Py_ssize_t col):
    """Transforms for statement into an iterable returning a dictionary of loop-specific bindings

    INPUT: for lbl, val in nodetypes
    =>
    OUTPUT: ({'lbl': lbl, 'val': val} for lbl, val in nodetypes)

    Parameters
    ----------
    stx: str
        The actual loop syntax, e.g. 'x in y', 'num in [1, 2, 3]' 'k, v in mydict.items()' and so on.
    scope: dict
        The scope in which to evaluate the code. This should contain the bindings referenced by `stx`
    line:
        line location of for-loop input
    col:
        column location of for-loop input

    Returns
    -------
        A generator where each item yielded is a a dictionary whose entries are str -> Any where
        the str corresponds to the loop identifier.
    """
    cdef:
        str bindings,
        str iterable,
        object match = for_loop_stx.match(stx)
        str code
    if not match:
        raise RuntimeError("wrong stx - not a valid for loop.")
    bindings = match["bindings"]
    iterable = match["iterable"]
    bindings_lst = (
        f"'{ident}': {ident}" for ident in (
        x.strip() for x in bindings.split(',')))

    code = f"({{ {', '.join(bindings_lst)} }} for {bindings} in {iterable})"
    return py_eval_expr(scope, code, line, col)


cdef class BodyEnvironment:
    cdef:
        list children  # type: t.List[Node]
        dict blocks
        dict scope  # type: t.Dict[str, t.Any]

    def __init__(self, list children, dict blocks, dict scope):
        self.children = children
        self.blocks = blocks
        self.scope = scope


cdef void interp_line(Line node, Writer w, dict blocks, dict scope) except *:
    cdef Literal lit = None
    cdef Expr expr = None
    w.write_prefix()
    w.write(node.indentation)
    for n in node.children:
        if isinstance(n, Literal):
            w.write((<Literal>n).value)
        elif isinstance(n, Expr):
            w.write(str(py_eval_expr(scope, n.value, n.line, n.col)))
        else:
            raise RuntimeError(f"Found node of type '{type_name(n)}' in Line.contents")
    w.newline()


cdef void interp_if(If ifblock, Writer w, dict blocks, dict scope) except *:
    cdef Block cond
    # all if/elif/else clauses/conditions MUST have the same indentation
    # and an if-block has at least one condition, the 'if' itself.
    w.indent((<Block>ifblock.conds[0]).block_indentation)
    for cond in ifblock.conds:
        if cond.keyword != 'else':
            # conditional
            if py_eval_expr(scope, cond.args, cond.line, cond.col_args):
                for n in cond.children:
                    interp_node(n, w, blocks, scope)
                w.dedent()
                return
        else:
            for n in cond.children:
                interp_node(n, w, blocks, scope)
            w.dedent()
            return


cdef void interp_block_component(Block block, Writer w, dict blocks, dict scope) except *:
    cdef:
        dict new_scope = scope.copy()
        dict new_blocks = blocks.copy()
        # TODO: handle syntax errors here
        object component = py_eval_expr(new_scope, block.args, block.line, block.col_args)
    if not isinstance(component, Component):
        raise RenderArgTypeError(block.args, component)
    new_scope.update(component.__ghostwriter_component_scope__)
    new_scope['self'] = component
    new_blocks['body'] = BodyEnvironment(block.children, blocks, new_scope)
    try:
        interpret(component.ast, w, new_blocks, new_scope)
    except InterpStackTrace as ist:
        raise InterpStackTrace(block.line, block.col_kw, ist) from ist


cdef void interp_block_body(Block body, Writer w, dict blocks, dict scope) except *:
    cdef Node n
    cdef BodyEnvironment b_env = blocks['body']
    for n in b_env.children:
        interp_node(n, w, b_env.blocks, b_env.scope)


cdef void interp_block(Block block, Writer w, dict blocks, dict scope) except *:
    cdef dict new_scope
    w.indent(block.block_indentation)
    if block.keyword == "r": # handle component
        interp_block_component(block, w, blocks, scope)
    elif block.keyword == "for": # handle for-block
        new_scope = scope.copy()
        for loop_bindings in gen_loop_iterator(block.args, new_scope, block.line, block.col_args):
            new_scope.update(loop_bindings)  # TODO: find a means of testing this - vars changed in one iter should be carried over
            for n in block.children:
                interp_node(<Node>n, w, blocks, new_scope)
    elif block.keyword == "body":
        interp_block_body(block, w, blocks, scope)
    else:
        raise UnknownBlockType(block)
    w.dedent()


cdef inline void interp_node(Node n, Writer w, dict blocks, dict scope) except *:
    if isinstance(n, Line):
        interp_line(<Line>n, w, blocks, scope)
    elif isinstance(n, If):
        interp_if(<If>n, w, blocks, scope)
    elif isinstance(n, Block):
        interp_block(<Block>n, w, blocks, scope)
    else:
        raise UnknownNodeType(n)


cpdef void interpret(Program program, Writer w, dict blocks, dict scope) except *:
    cdef Node n
    try:
        for n in program.lines:
            interp_node(n, w, blocks, scope)
    except InterpStackTrace as ist:
        if ist.component is None and ist.filepath is None:
            ist.component = program.component
            ist.filepath = program.file_path
        raise ist