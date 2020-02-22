cimport cython
from ghostwriter.utils.cogen.component import Component
from re import compile as re_compile

# TODO: want a 'def'/'set' block to update scope - can call out to functions..?

for_loop_stx = re_compile(r"^(?P<bindings>.+?)\s+in\s+(?P<iterable>.+)")
cdef class InterpreterError(Exception):
    pass


cdef class RenderArgTypeError(InterpreterError):
    def __init__(self, str expr, object obj):
        self.expr = expr
        self.typ = stringify_type(obj)
        super().__init__(f"render block expects component, but '{expr}' evaluated to '{self.typ}'")


@cython.final
cdef class Writer(IWriter):
    def __init__(self, IWriter writer, str prefix = ""):
        self._writer = writer
        self._prefixes = [prefix]
        self._curr_prefix = prefix

    cpdef void indent(self, str prefix):
        self._curr_prefix = self._curr_prefix + prefix
        self._prefixes.append(self._curr_prefix)

    cpdef void dedent(self):
        if len(self._prefixes) > 1:
            self._prefixes.pop()
            self._curr_prefix = self._prefixes[-1]
            return
        self._curr_prefix = self._base_prefix

    cpdef void write(self, str contents):
        self._writer.write(contents)

    cpdef void write_indent(self):
        self._writer.write(self._curr_prefix)

    cpdef void newline(self):
        self._writer.write('\n')


cdef py_eval_expr(dict scope, str expr):
    """
    Evaluate Python expression and return its value

    Parameters
    ----------
    scope
        The context in which to evaluate the expression. `env` may contain
        any number of variable bindings.
    expr
        The expression to evaluate.

    Returns
    -------
        The resulting value from evaluating the expression.
    """
    # TODO: may raise SyntaxError
    cdef dict eval_locals = dict()
    exec(f"_it = {expr}", scope, eval_locals)
    return eval_locals['_it']


def gen_loop_iterator(str stx, dict scope):
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
    return py_eval_expr(
        scope,
        code)


cdef inline str stringify_type(object o):
    return type(o).__name__


cdef class BodyEnvironment:
    cdef:
        list lines
        dict blocks
        dict scope

    def __init__(self, list lines, dict blocks, dict scope):
        self.lines = lines
        self.blocks = blocks
        self.scope = scope


cdef void interp_line(Line node, Writer w, dict blocks, dict scope) except *:
    cdef Literal lit = None
    cdef Expr expr = None
    w.write_indent()
    for n in node.children:
        if isinstance(n, Literal):
            w.write((<Literal>n).value)
        elif isinstance(n, Expr):
            w.write(str(py_eval_expr(scope, (<Expr>n).value)))
        else:
            raise RuntimeError(f"Found node of type '{stringify_type(n)}' in Line.contents")
    w.newline()


cdef void interp_if(If ifblock, Writer w, dict blocks, dict scope) except *:
    cdef Block cond
    for cond in ifblock.conds:
        if cond.keyword != 'else':
            # conditional
            if py_eval_expr(scope, cond.args):
                for n in cond.children:
                    interp_node(n, w, blocks, scope)
                return
        else:
            for n in cond.children:
                interp_node(n, w, blocks, scope)
            return


cdef void interp_component(Block block, Writer w, dict blocks, dict scope) except *:
    cdef:
        dict new_scope = scope.copy()
        dict new_blocks = blocks.copy()
        # TODO: handle syntax errors here
        object component = py_eval_expr(new_scope, block.args)
    if not isinstance(component, Component):
        raise RenderArgTypeError(block.args, component)
    new_scope.update(component.__ghostwriter_component_scope__)
    new_scope['self'] = component
    new_blocks['body'] = BodyEnvironment(block.children, blocks, new_scope)
    w.indent(block.block_prefix)  # TODO: review this, component indentation SHOULDN'T work right atm (need to adjust indentation @ component time)
    interpret(component.ast, w, new_blocks, new_scope)
    w.dedent()


cdef void interp_body_block(Block body, Writer w, dict blocks, dict scope) except *:
    cdef Node n
    cdef BodyEnvironment b_env = blocks['body']
    w.indent(body.block_prefix)
    for n in b_env.lines:
        interp_node(n, w, b_env.blocks, b_env.scope)
    w.dedent()


cdef void interp_block(Block block, Writer w, dict blocks, dict scope) except *:
    cdef dict new_scope
    if block.keyword == "r": # handle component
        interp_component(block, w, blocks, scope)
    elif block.keyword == "for": # handle for-block
        # TODO: assuming lexical scope here, OK?
        new_scope = scope.copy()
        for loop_bindings in gen_loop_iterator(block.args, new_scope):
            new_scope.update(loop_bindings)  # TODO: find a means of testing this - vars changed in one iter should be carried over
            for n in block.children:
                interp_node(<Node>n, w, blocks, new_scope)
    elif block.keyword == "body":
        interp_body_block(block, w, blocks, scope)
    else:
        raise RuntimeError(f"cannot handle '{block.keyword}' blocks yet")


cdef inline void interp_node(Node n, Writer w, dict blocks, dict scope) except *:
    if isinstance(n, Line):
        interp_line(<Line>n, w, blocks, scope)
    elif isinstance(n, If):
        interp_if(<If>n, w, blocks, scope)
    elif isinstance(n, Block):
        interp_block(<Block>n, w, blocks, scope)
    else:
        raise RuntimeError(f"Interpreter cannot handle '{stringify_type(n)}' nodes")


cpdef void interpret(Program program, Writer w, dict blocks, dict scope) except *:
    cdef Node n
    for n in program.lines:
        interp_node(n, w, blocks, scope)