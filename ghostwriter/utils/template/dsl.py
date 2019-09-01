import typing as t

from abc import ABC, abstractmethod
from enum import Enum, unique as enum_unique_values
from re import compile as re_compile
from functools import wraps

from ghostwriter.utils.template.tokens import *
from ghostwriter.utils.template.scope import Scope
from ghostwriter.utils.text import deindent_str_block
from ghostwriter.protocols import IWriter

__all__ = ['Component', 'Scope', 'template', 'render']

Element = t.Union[str,]
Blocks = t.Dict[str, t.Callable[['EvalContext', 'TokenIterator', Scope], None]]
Components = t.Dict[str, t.Type['Component']]


# TODO: issue - %% lines aren't rewritten
# Do not go templite (compiled) approach, instead write an interpreted approach
# (Django style, norvig lispy style)


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


def _eval_exprs(expr: str, scope: Scope):
    # TODO: add some code to enable dot lookups and whatnot (?)
    # Signature: eval(expr: str, globals: dict, locals: dict)
    return eval(expr, {}, scope)


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
    __slots__ = ['blocks', 'components', 'buffer', 'buffer_append', 'writer']

    def __init__(self, writer: LineWriter, *, blocks: Blocks = None, components: Components = None):
        self.blocks = blocks or {}
        self.components = components or {}
        self.buffer = []
        self.buffer_append: t.Callable[[object], None] = self.buffer.append
        self.writer = writer

    def derived(self,
                with_blocks: t.Optional[Blocks] = None,
                with_components: t.Optional[Components] = None) -> 'EvalContext':
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
        return EvalContext(
            self.writer,
            blocks=blocks,
            components={**self.components, **(with_components or {})})


class Component(ABC):
    """
    The basic template component interface.

    This class defines the interface to implement for new components.
    Note that parsing components is moved to an external function in order
    to avoid accidentally overriding this logic.
    """

    @property
    @abstractmethod
    def template(self) -> str:
        """
        Return the DSL content defining the component.

        Returns
        -------
            A string containing the DSL template making up this component.
        """
        pass


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
            result = _eval_exprs(token.expr, scope)
            ctx.buffer_append(to_str(result))
        elif typ == CtrlToken:
            if len(ctx.buffer) != 0:
                flush_buffer(ctx)

            ctx.writer.indent(token.prefix)
            if token.keyword == 'for':
                dsl_eval_for(ctx, tokens, scope, token.args)
                ctx.writer.dedent()
            elif token.keyword == 'if':
                dsl_eval_if(ctx, tokens, scope, token.args)
                ctx.writer.dedent()
            elif token.keyword[0].isupper():
                component_class = ctx.components.get(token.keyword)
                if not component_class:
                    raise RuntimeError(f"Unknown component '{token.keyword}'")

                component = py_eval(
                    Scope({token.keyword: component_class}, scope),
                    f"_it = {token.keyword}({token.args if token.args else ''})")['_it']
                dsl_eval_component(ctx, tokens, scope, component, token.keyword)
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
        component: Component, name: str):
    # Need to
    # * eval the 'body' of the component (the DSL contained within
    #   the start and end component block) in the context of the
    #   component parent.
    #
    #   => Ensures bindings & components aren't redefined or missing
    #
    # * consume the tokens of the body right away, store in a list
    #   => Ensures body can be rendered multiple times
    #
    # * Initialise component - take component args and turn
    #   % Foo one, two='three'
    #   into:
    #   Foo(one, two='three')
    #
    #   => Enables full Python exprs
    #   => Ensures DSL is close to vanilla Python
    #
    # * bind 'self' to the component instance
    body_ctx = ctx.derived()
    body_tokens = []
    for tok in tokens:
        if isinstance(tok, CtrlToken) and tok.keyword == f"/{name}":
            break
        body_tokens.append(tok)

    def render_body(_: EvalContext, __: TokenIterator, ___: Scope, args: str):
        if args:
            raise RuntimeError("body block cannot take arguments")

        dsl_eval_main(
            body_ctx, TokenIterator(iter(body_tokens)), Scope(outer=scope),
            stop_at_ctrl_tokens({f'/{name}'}))

    component_ctx = ctx.derived(with_blocks={'body': render_body})
    # Render the component itself
    # (note: we are now supplying an almost empty scope, only explicitly passed
    # (arguments are carried into the context of the "called" component.)
    dsl_eval_main(component_ctx, TokenIterator(token_stream(
        deindent_str_block(component.template, ltrim=True))),
                  Scope({'self': component}))


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
    def stopfn(token):
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
            if _eval_exprs(cond_expr, scope):
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
    return py_eval(
        env,
        "_it = ({" f"{', '.join(bindings_lst)}" "} " f"for {bindings} in {iterable})",
    )['_it']


def py_eval(env: t.Mapping, prog: str) -> t.Mapping:
    eval_locals = {}
    exec(prog, dict(env), eval_locals)
    return eval_locals


def template(components: t.Optional[Components] = None, blocks: t.Optional[Blocks] = None):
    def wrapper(fn: t.Callable[[Scope], str]):
        @wraps(fn)
        def decorator(ctx, prefix: str, fw: IWriter):
            scope = Scope()
            render(fw, fn(scope), scope, components=components, blocks=blocks, prefix=prefix)

        return decorator

    return wrapper


def render(buf: IWriter, prog: str, scope: Scope,
           blocks: t.Optional[Blocks] = None,
           components: t.Optional[Components] = None,
           prefix: str = ''):
    ctx = EvalContext(
        LineWriter(buf, prefix),
        blocks=blocks or {},
        components=components or {})
    tokens = TokenIterator(token_stream(deindent_str_block(prog, ltrim=True)))

    dsl_eval_main(ctx, tokens, scope)
