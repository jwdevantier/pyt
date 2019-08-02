import typing as t
from io import StringIO
from enum import Enum, unique as enum_unique_values
from re import compile as re_compile

from pyt.utils.template.tokens import *
from pyt.utils.template.scope import Scope
from pyt.utils.text import deindent_str_block
from pyt.protocols import IWriter


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
    def __init__(self, writer: IWriter):
        self.indents = []
        self._indent = ""
        self.writer = writer

    def indent(self, indent_by: str):
        self.indents.append(indent_by)
        self._indent += indent_by

    def dedent(self):
        self.indents.pop()
        self._indent = "".join(self.indents)

    def writeln(self, s: str) -> None:
        self.writer.write(f"{self._indent}{s}\n")


_tstr = re_compile(r"(<<.*?>>)")
_cline = re_compile(r"^(?P<prefix>\s*)%\s*(?P<kw>[^%[^\s]+)\s*(?P<rest>[^%].+)?")


def token_stream(text: str):
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


# one method for prepping props
# optional hooks for specs
# TODO: do I *HAVE* to rely on people implementing _scope_ ?
class Component:
    TEMPLATE = ""

    @classmethod
    def _scope_(cls, scope: Scope, component_args: str) -> None:
        """

        Parameters
        ----------
        component_args
            any arguments given after the component name - parsing this string
            is up to the component.

        Returns
        -------
            A new scope
        """
        pass

    @classmethod
    def _render_(cls, ctx: EvalContext, tokens: TokenIterator, scope: Scope,
                 component_name: str, component_args: str):
        # Evaluate 'body' the DSL contained inside the component block
        # => solves the issue of the surrounding component DSL scope
        #    polluting the scope for the body supplied the component
        body_ctx = ctx.derived()
        body_rendered = False

        # Define scope supplied to the rendering
        component_scope = Scope(outer=scope)
        cls._scope_(component_scope, component_args)

        # TODO: lazily render children
        def render_body(_: EvalContext, __: TokenIterator, ___: Scope, args: str):
            nonlocal body_rendered
            if args:
                raise RuntimeError("body block cannot take arguments")

            if not body_rendered:
                dsl_eval_main(
                    body_ctx, tokens, Scope(outer=scope),
                    stop_at_ctrl_tokens({f'/{component_name}'}))
                body_rendered = True

        component_ctx = ctx.derived(with_blocks={'body': render_body})
        # Render the component itself
        dsl_eval_main(component_ctx, TokenIterator(token_stream(
            deindent_str_block(cls.TEMPLATE, ltrim=True))),
                      component_scope)


def dsl_eval_main(ctx: EvalContext, tokens: TokenIterator, scope: Scope, stop: t.Optional[t.Callable] = None):
    to_str = str
    for token in tokens:
        if stop and stop(token):
            if isinstance(token, CtrlToken) and token.keyword.startswith('/'):
                ctx.writer.dedent()
            return
        # typ, *vals = token
        # if typ == TokType.TEXT:
        typ = type(token)
        if typ == TextToken:
            ctx.buffer_append(token.text)
        elif typ == NewlineToken:
            if len(ctx.buffer) != 0:
                # flush buffer
                ctx.writer.writeln("".join(ctx.buffer))
                del ctx.buffer[:]
            else:
                ctx.writer.writeln("")
        elif typ == ExprToken:
            result = _eval_exprs(token.expr, scope)
            ctx.buffer_append(to_str(result))
        elif typ == CtrlToken:
            if len(ctx.buffer) != 0:
                # flush buffer
                ctx.writer.writeln("".join(ctx.buffer))
                del ctx.buffer[:]

            ctx.writer.indent(token.prefix)
            if token.keyword == 'for':
                dsl_eval_for(ctx, tokens, scope, token.args)
            elif token.keyword == 'if':
                dsl_eval_if(ctx, tokens, scope, token.args)
            elif token.keyword[0].isupper():
                component = ctx.components.get(token.keyword)
                if not component:
                    raise RuntimeError(f"Unknown component '{token.keyword}'")

                component._render_(ctx, tokens, scope, token.keyword, token.args)
            elif not token.keyword.startswith('/'):  # must be a block
                # TODO: indent here
                block = ctx.blocks.get(token.keyword)
                if not block:
                    raise RuntimeError(f"Unknown block '{token.keyword}'")
                block(ctx, tokens, scope, token.args)
            else:  # must be a close block tag - should not been seen
                raise RuntimeError(
                    f"illegal nesting, got unexpected'{token.keyword}'")


def dsl_eval_for(ctx: EvalContext, tokens: TokenIterator, scope: Scope, for_args: str):
    for_tokens = []
    for token in tokens:
        if isinstance(token, CtrlToken) and token.keyword.startswith('/for'):
            break
        for_tokens.append(token)
    for loop_bindings in gen_loop_iterator(for_args, scope):
        dsl_eval_main(ctx, TokenIterator(iter(for_tokens)), Scope(loop_bindings, outer=scope))


def skip_tokens(tokens: TokenIterator, stop):
    for token in tokens:
        if stop(token):
            break


def stop_at_ctrl_tokens(tokens: t.Set[str]):
    def stopfn(token):
        return isinstance(token, CtrlToken) and token.keyword in tokens

    return stopfn


def dsl_eval_if(ctx: EvalContext, tokens: TokenIterator, scope: Scope, cond_expr: str):
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
            print("/IF reached")
            break
        else:
            raise RuntimeError("UNEXPECTED")

        # TODO: revamp once we've settled on a data structure for Tokens
        token = tokens.current
        if not token or not isinstance(token, CtrlToken) or token.keyword not in accepted_tags:
            print(f"TOKEN current: {tokens.current}")
            print(f"TOKEN next: {tokens._next}")
            for token in tokens:
                print(f"TOK: {token}")
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
    # TODO: ? if we provide the dict directly, would the builtins entry be written into it?
    env_globals = dict(env)
    bindings, iterable = (x.strip() for x in for_src.split('in'))
    env_locals = {}
    bindings_lst = (f"'{ident}': {ident}" for ident in (x.strip() for x in bindings.split(',')))
    exec(
        "_it = ({" f"{', '.join(bindings_lst)}" "} " f"for {bindings} in {iterable})"
        , env_globals, env_locals)

    return env_locals['_it']
