import typing as t

from enum import Enum, unique as enum_unique_values
from re import compile as re_compile
from functools import wraps
import inspect
import logging

from ghostwriter.utils.template.tokens import *
from ghostwriter.utils.template.scope import Scope
from ghostwriter.utils.text import deindent_str_block
from ghostwriter.utils.iwriter import IWriter

log = logging.getLogger(__name__)

Element = t.Union[str,]
Blocks = t.Dict[str, t.Callable[['EvalContext', 'TokenIterator', Scope], None]]
Components = t.Dict[str, t.Type['Component']]
ScopeLike = t.Mapping[str, t.Any]


class DSLSyntaxError(SyntaxError):
    def __init__(self, message: str, source: str, offset: int, env: t.Mapping):
        self.source = source
        self.env = env
        super().__init__(message, ('<DSL>', 1, offset, source))


# TODO: issue - %% lines aren't rewritten
# Do not go templite (compiled) approach, instead write an interpreted approach
# (Django style, norvig lispy style)


class DSLError(Exception):
    pass


class DSLBlockRenderExpressionError(DSLError):
    def __init__(self, expr: str, result: t.Any):
        super().__init__(f"error at 'r' block. '{expr}' did not yield a component - got type: '{type(result)}'")
        self.expr = expr
        self.result = result


@enum_unique_values
class Indentation(Enum):
    INDENT = 1
    DEDENT = 2


class LineWriter:
    def __init__(self, writer: IWriter, prefix: str = ''):
        self.indents = ['']
        self.writer = writer
        self.prefix = ''
        self.base_prefix = prefix

    def indent(self, prefix: str):
        self.indents.append(prefix)
        self.prefix = prefix

    def dedent(self):
        self.indents.pop()
        self.prefix = self.indents[-1]

    def writeln(self, s: str) -> None:
        self.writer.write(f"{self.base_prefix}{self.prefix}{s}\n")


_tstr = re_compile(r"(<<.*?>>)")
_cline = re_compile(r"^(?P<prefix>\s*)%\s*(?P<kw>[^%[^\s]+)\s*(?P<rest>[^%].+)?")


def token_stream(text: str):
    """Initialize lazy tokenizer on DSL code `text`.

    Parameters
    ----------
    text

    Returns
    -------

    """
    # rewritten to have a 'lead-in' phase where leading newlines is ignored.
    lines = (line for line in text.split('\n'))
    lead_in = True
    for line in lines:
        m = _cline.match(line)
        if m:
            yield CtrlToken(m['prefix'], m['kw'], m['rest'])
        else:
            for tok in _tstr.split(line):
                if tok.startswith('<<'):
                    yield ExprToken(tok[2:-2])
                    lead_in = False
                elif tok is not '':
                    yield TextToken(tok)
                    lead_in = False
            if not lead_in:
                yield NewlineToken()
        if not lead_in:
            break

    # The rest...
    for line in lines:
        m = _cline.match(line)
        if m:
            yield CtrlToken(m['prefix'], m['kw'], m['rest'])
        else:
            for tok in _tstr.split(line):
                if tok.startswith('<<'):
                    yield ExprToken(tok[2:-2])
                elif tok != '':
                    yield TextToken(tok)
                else:
                    continue
            yield NewlineToken()


class TokenIterator:
    """Implement standard peek(current)/next and a backtrack (revert) of 1."""
    __slots__ = ['tokens', '_next', '_current']

    def __init__(self, tokens: t.Iterator):
        self.tokens = tokens
        self._next = None
        self._current = None

    def __iter__(self):
        return self

    def __next__(self):
        if self._next is not None:
            nxt = self._next
            self._next = None
            return nxt

        self._current = next(self.tokens)
        return self._current

    @property
    def current(self):
        return self._current

    def revert(self):
        if self._next is not None:
            raise RuntimeError("cannot revert twice")
        self._next = self._current


class EvalContext:
    __slots__ = ['blocks', 'buffer', 'buffer_append', 'writer']

    def __init__(self, writer: LineWriter, *, blocks: Blocks = None):
        self.blocks = blocks or {}
        self.buffer = []
        self.buffer_append: t.Callable[[object], None] = self.buffer.append
        self.writer = writer

    def derived(self,
                with_blocks: t.Optional[Blocks] = None) -> 'EvalContext':
        """Make new EvalContext sharing the same blocks and handlers as this one.

        Returns
        -------
            A new EvalContext instance
        """

        if with_blocks:
            blocks = {
                **{k: v for k, v in self.blocks.items() if k != 'body'},
                **with_blocks
            }
        else:
            blocks = {k: v for k, v in self.blocks.items() if k != 'body'}
        return EvalContext(self.writer, blocks=blocks)


class ComponentMeta(type):
    def __new__(mcs, clsname, bases, clsdict):
        if '__init__' in clsdict:
            orig_init = clsdict['__init__']
        else:
            def orig_init(self, *args, **kwargs):
                pass

        @wraps(orig_init)
        def init_wrapper(self, *args, **kwargs):
            """
            Compute scope for component before invoking normal init.
            """
            # install old init to prevent re-running this multiple times
            setattr(type(self), '__init__', orig_init)

            # compute scope
            setattr(type(self), '__ghostwriter_component_scope__', {
                ident: obj
                for ident, obj
                in inspect.getmembers(inspect.getmodule(self))
                if (inspect.ismodule(obj)
                    or getattr(obj, '__ghostwriter_component__', False))})
            # call actual init function
            orig_init(self, *args, **kwargs)

        clsdict['__init__'] = init_wrapper
        typ = super().__new__(mcs, clsname, bases, clsdict)
        return typ


class Component(metaclass=ComponentMeta):
    """
    The basic template component interface.

    This class defines the interface to implement for new components.
    Note that parsing components is moved to an external function in order
    to avoid accidentally overriding this logic.
    """
    # Important to set here - cannot infer which types are components
    # in metaclass code otherwise (timing issue, attr may not yet have been set)
    __ghostwriter_component__ = True
    # Will be overwritten by one-time init function
    __ghostwriter_component_scope__ = {}

    def template(self) -> str:
        """
        Return the DSL content defining the component.

        Returns
        -------
            A string containing the DSL template making up this component.
        """
        raise NotImplementedError("'template() -> str' method not implemented")


def flush_buffer(ctx: EvalContext):
    if ctx.buffer[0][0:len(ctx.writer.prefix)] == ctx.writer.prefix:
        ctx.buffer[0] = ctx.buffer[0][len(ctx.writer.prefix):]
    ctx.writer.writeln("".join(ctx.buffer))
    del ctx.buffer[:]


def dsl_eval_main(ctx: EvalContext, tokens: TokenIterator, scope: Scope, stop: t.Optional[t.Callable] = None):
    to_str = str
    for token in tokens:
        if stop and stop(token):
            return

        typ = type(token)
        if typ == TextToken:
            ctx.buffer_append(token.text)
        elif typ == NewlineToken:
            if len(ctx.buffer) != 0:
                flush_buffer(ctx)
            else:
                ctx.writer.writeln("")
        elif typ == ExprToken:
            try:
                result = py_eval_expr(scope, token.expr)
                ctx.buffer_append(to_str(result))
            except SyntaxError as se:
                raise DSLSyntaxError(
                    "error evaluating expression",
                    token.expr, se.offset, scope) from se
        elif typ == CtrlToken:
            if len(ctx.buffer) != 0:
                flush_buffer(ctx)

            ctx.writer.indent(token.prefix)
            if token.keyword == 'r':
                # Supports initializing component instances
                # 'r MyComponent(one, two, three='wee')
                # ... and expressions evaluating to a component instance
                # 'r self.somevar['key'](one, two, three='wee')
                try:
                    component = py_eval_expr(scope, token.args)
                except SyntaxError as se:
                    raise DSLSyntaxError(
                        "error evaluating expression",
                        token.args, se.offset, scope) from se
                if not isinstance(component, Component):
                    raise DSLBlockRenderExpressionError(token.args, component)
                dsl_eval_component(ctx, tokens, scope, component)
                ctx.writer.dedent()
            elif token.keyword == 'for':
                dsl_eval_for(ctx, tokens, scope, token.args)
                ctx.writer.dedent()
            elif token.keyword == 'if':
                dsl_eval_if(ctx, tokens, scope, token.args)
                ctx.writer.dedent()
            elif not token.keyword.startswith('/'):  # must be a block
                block = ctx.blocks.get(token.keyword)
                if not block:
                    raise RuntimeError(f"Unknown block '{token.keyword}'")
                block(ctx, tokens, scope, token.args)
                ctx.writer.dedent()
            else:  # must be a close block tag - should not been seen
                raise RuntimeError(
                    f"illegal nesting, got unexpected'{token.keyword}'")


def dsl_eval_component(
        ctx: EvalContext, tokens: TokenIterator, scope: Scope,
        component: Component):
    # derive env now - means child envs and this one branch.
    # => body is rendered with no regard to env changes made later on
    body_ctx = ctx.derived()
    # Must consume the tokens making up the body of the component
    # => whether rendering the body or not, the tokens are used.
    body_tokens = []
    nesting_lvl = 1
    for tok in tokens:
        if isinstance(tok, CtrlToken):
            if tok.keyword == 'r':
                nesting_lvl += 1
            elif tok.keyword == '/r':
                nesting_lvl -= 1
                if nesting_lvl == 0:
                    break
        # existing code skips its own closing block too
        body_tokens.append(tok)

    def render_body(_, __, ___, args: str):
        if args:
            raise RuntimeError("body block cannot take arguments")
        dsl_eval_main(body_ctx,
                      TokenIterator(iter(body_tokens)),
                      Scope(outer=scope))

    component_ctx = ctx.derived(with_blocks={'body': render_body})
    # bind 'self' to the component instance
    dsl_eval_main(component_ctx,
                  TokenIterator(token_stream(deindent_str_block(
                      component.template, ltrim=True))),
                  Scope({'self': component},
                        Scope(component.__ghostwriter_component_scope__)))


def dsl_eval_for(ctx: EvalContext, tokens: TokenIterator, scope: Scope, for_args: str):
    for_tokens = []
    for token in tokens:
        if isinstance(token, CtrlToken) and token.keyword.startswith('/for'):
            break
        for_tokens.append(token)
    for loop_bindings in gen_loop_iterator(for_args, scope):
        dsl_eval_main(ctx, TokenIterator(iter(for_tokens)), Scope(loop_bindings, outer=scope))


def skip_tokens(tokens: TokenIterator, stop: t.Callable[[Token], bool]):
    """
    Skip/consume tokens from supplied token stream until some token satisfies
    the predicate function `stop`.

    Parameters
    ----------
    tokens
        A stream of tokens from parsing the DSL code.
    stop
        A predicate function taking a token and returning a truthy value if
        further consumption of the token stream should be aborted.

    Returns
    -------
        None
    """
    for token in tokens:
        if stop(token):
            break


def stop_at_ctrl_tokens(ctrl_keywords: t.Set[str]):
    """
    Yield function returning True iff. token is a CtrlToken of a matching keyword

    Helper function used to quickly generate a stop-function to limit how far e.g.
    `dsl_eval_main` should proceed along the token stream.

    Parameters
    ----------
    ctrl_keywords
        a set/list of keywords to match against the supplied token.

    Returns
    -------
        A predicate function returning True iff. supplied token is a control
        token and its keyword matches and of those in `ctrl_keywords`.
    """

    def stopfn(token: Token):
        return isinstance(token, CtrlToken) and token.keyword in ctrl_keywords

    return stopfn


def dsl_eval_if(ctx: EvalContext, tokens: TokenIterator, scope: Scope, cond_expr: str) -> None:
    """
    Evaluate '%if' blocks (and any '%elif' or '%else').

    Parameters
    ----------
    ctx
        The evaluation context
    tokens
        The stream of tokens for the DSL parsed
    scope
        The current evaluation scope
    cond_expr
        The initial conditional expression.
        Follows '%if' - the expression determining if the primary
        if-block's body is evaluated.

    Returns
    -------
        None
    """
    kw = 'if'
    accepted_tags = {'elif', 'else', '/if'}
    while True:
        if kw in {'if', 'elif'}:
            try:
                res = py_eval_expr(scope, cond_expr)
            except SyntaxError as se:
                raise DSLSyntaxError(
                    "error evaluating condition in if-block",
                    f"{kw} {cond_expr}",
                    se.offset + 1 + len(kw), scope) from se
            if res:
                dsl_eval_main(ctx, tokens, Scope(outer=scope), stop_at_ctrl_tokens(accepted_tags))

                # skip past all other branches in if-block
                if not isinstance(tokens.current, CtrlToken) or tokens.current.keyword != '/if':
                    skip_tokens(tokens, stop_at_ctrl_tokens({'/if'}))

            else:
                # skip branch
                skip_tokens(tokens, stop_at_ctrl_tokens(accepted_tags))
        elif kw == 'else':
            dsl_eval_main(ctx, tokens, Scope(outer=scope), stop_at_ctrl_tokens({'/if'}))
        elif kw == '/if':
            # TODO: I don't think this branch is ever triggered
            break
        else:
            raise RuntimeError(f"eval if error - unexpected block '{kw}'")

        # TODO: revamp once we've settled on a data structure for Tokens
        token = tokens.current
        if not token or not isinstance(token, CtrlToken) or token.keyword not in accepted_tags:
            raise RuntimeError(f"invalid nesting - expected {accepted_tags}, got: {token}")

        kw = token.keyword
        cond_expr = token.args
        if kw == 'else':
            accepted_tags = {'/if'}
        elif kw == '/if':
            break


def gen_loop_iterator(for_src, env: t.Mapping):
    """Transforms for statement into an iterable returning a dictionary of loop-specific bindings

    INPUT: for lbl, val in nodetypes
    =>
    OUTPUT: ({'lbl': lbl, 'val': val} for lbl, val in nodetypes)
    """
    bindings, iterable = (x.strip() for x in for_src.split(' in '))
    bindings_lst = (
        f"'{ident}': {ident}" for ident in (
        x.strip() for x in bindings.split(',')))
    code_prefix = "({" f"{', '.join(bindings_lst)}" "} "

    try:
        return py_eval_expr(
            env,
            code_prefix + f"for {bindings} in {iterable})")
    except SyntaxError as se:
        offset = se.offset - len(code_prefix)
        raise DSLSyntaxError(
            "syntax error in for-clause",
            f"for {for_src}", offset, env) from se


def py_eval(env: t.Mapping, prog: str) -> t.Mapping:
    """
    Evaluate Python program

    Parameters
    ----------
    env
        The context in which the program is run. `env` may contain any
        number of variable bindings.
    prog
        A stand-alone python program, where program is taken to mean
        some number of expressions or statements.

    Returns
    -------
        The resulting environment
    """
    eval_locals = {}
    exec(prog, dict(env), eval_locals)
    return eval_locals


def py_eval_expr(env: t.Mapping, expr):
    """
    Evaluate Python expression and return its value

    Parameters
    ----------
    env
        The context in which to evaluate the expression. `env` may contain
        any number of variable bindings.
    expr
        The expression to evaluate.

    Returns
    -------
        The resulting value from evaluating the expression.
    """
    try:
        eval_locals = {}
        exec(f"_it = {expr}", dict(env), eval_locals)
        return eval_locals['_it']
    except SyntaxError as se:
        se.offset -= len('_it = ')
        raise se


def snippet(blocks: t.Optional[Blocks] = None):
    """
    Create snippet from Component instance.

    Convenience decorator - wrap a function which takes a Scope instance and
    which returns a Component instance.

    Parameters
    ----------
    blocks:
        (Optional) additional blocks to use in DSL.

    Example
    -------
    @snippet()
    def my_snippet():
        foo = 'foo string'
        identity = lambda x: x
        return MyComponent(foo, identity)

    Returns
    -------
        A snippet function
    """

    def wrapper(fn: t.Callable[[], Component]):
        @wraps(fn)
        def decorator(_, prefix: str, fw: IWriter):
            scope = Scope({})
            component: Component = fn()
            if not isinstance(component, Component):
                raise ValueError(f"snippet must return a Component instance, got '{type(component)}'")
            scope['__main__'] = component
            prog = """\
            % r __main__
            % /r"""
            ctx = EvalContext(LineWriter(fw, prefix), blocks=blocks)
            tokens = TokenIterator(token_stream(deindent_str_block(prog, ltrim=True)))
            dsl_eval_main(ctx, tokens, scope)

        return decorator

    return wrapper
