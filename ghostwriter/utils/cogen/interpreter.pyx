cimport cython
from ghostwriter.utils.cogen.component import Component
from re import compile as re_compile

# TODO: want a 'def'/'set' block to update scope - can call out to functions..?

for_loop_stx = re_compile(r"^(?P<bindings>.+?)\s+in\s+(?P<iterable>.+)")


@cython.final
cdef class Writer(IWriter):
    def __init__(self, IWriter writer, str prefix = ""):
        self._writer = writer
        self._prefixes = []
        self._base_prefix = self._curr_prefix = prefix

    cpdef void indent(self, str prefix):
        cdef str indent = '\n' + self._base_prefix + prefix
        self._prefixes.append(indent)
        self._curr_prefix = indent

    cpdef void dedent(self):
        self._prefixes.pop()
        self._curr_prefix = self._prefixes[-1]

    cpdef void write(self, str contents):
        self._writer.write(contents)

    cpdef void newline(self):
        self._writer.write(self._curr_prefix)


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


cdef inline dict derived_scope(dict parent):
    return parent.copy()


cdef inline dict component_blocks(dict parent_blocks, object render_body):
    """
    
    Parameters
    ----------
    parent_blocks
        all blocks registered in the parent context
    render_body
        function which renders the body of the component if invoked.

    Returns
    -------
        a new block context which retains all the registered blocks of the parent
        and a special 'body' block which, if invoked, renders the body of the
        component.
    """
    # TODO: render_body should, at least, be a one-method class for type enforcement reasons
    cdef dict child_blocks = parent_blocks.copy()
    child_blocks['body'] = render_body
    return child_blocks


cdef inline dict dict_merge(dict d1, dict ds, ...):
    cdef dict out = d1.copy()
    for dct in ds:
        out.update(ds)
    return out


cdef inline str stringify_type(object o):
    return type(o).__name__


cdef void interp_line(Line node, Writer w, dict blocks, dict scope) except *:
    cdef Literal lit = None
    cdef Expr expr = None
    for n in node.contents:
        if isinstance(n, Literal):
            w.write((<Literal>n).value)
        elif isinstance(n, Expr):
            w.write(str(py_eval_expr(scope, (<Expr>n).value)))
        else:
            raise RuntimeError(f"Found node of type '{stringify_type(n)}' in Line.contents")
    w.write('\n')


cdef void interp_if(If ifblock, Writer w, dict blocks, dict scope) except *:
    cdef Block cond
    for cond in ifblock.conds:
        if cond.header.keyword != 'else':
            # conditional
            if py_eval_expr(scope, cond.header.args):
                for n in cond.lines:
                    interp_node(n, w, blocks, scope)
                return
        else:
            for n in cond.lines:
                interp_node(n, w, blocks, scope)
            return


cdef void interp_component(Block block, Writer w, dict blocks, dict scope) except *:
    cdef:
        dict new_scope = scope.copy()
        dict new_blocks = blocks.copy()
        # TODO: handle syntax errors here
        object component = py_eval_expr(new_scope, block.header.args)
    if not isinstance(component, Component):
        raise ValueError(f"'{block.header.args}' should evaluate to a Component, got '{stringify_type(component)}'")
    new_scope.update(component.__ghostwriter_component_scope__)
    new_scope['self'] = component
    # TODO: block.lines should be bound to 'body' somehow
    #       see dsl.py > dsl_eval_component > render_body

    # TODO: derive blocks with body -- bound to render body
    interpret(component.ast, w, new_blocks, new_scope)


cdef void interp_block(Block block, Writer w, dict blocks, dict scope) except *:
    cdef dict new_scope
    if block.header.keyword == "r": # handle component
        interp_component(block, w, blocks, scope)
        return
    elif block.header.keyword == "for": # handle for-block
        # TODO: assuming lexical scope here, OK?
        new_scope = scope.copy()
        for loop_bindings in gen_loop_iterator(block.header.args, new_scope):
            new_scope.update(loop_bindings)  # TODO: find a means of testing this - vars changed in one iter should be carried over
            for n in block.lines:
                interp_node(n, w, blocks, new_scope)
    else:
        raise RuntimeError(f"cannot handle '{block.header.keyword}' blocks yet")



cdef void interp_node(Node n, Writer w, dict blocks, dict scope) except *:
    if isinstance(n, Line):
        interp_line(<Line>n, w, blocks, scope)
    elif isinstance(n, If):
        interp_if(<If>n, w, blocks, scope)
    elif isinstance(n, Block):
        interp_block(<Block>n, w, blocks, scope)
    else:
        raise RuntimeError(f"Interpreter cannot handle '{stringify_type(n)}' nodes")


cpdef void interpret(Program program, Writer w, dict blocks, dict scope):
    cdef Node n
    for n in program.lines:
        interp_node(n, w, blocks, scope)