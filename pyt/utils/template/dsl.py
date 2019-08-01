from typing_extensions import Protocol
import typing as t
from io import StringIO
from pyt.protocols import IWriter

from enum import Enum, unique as enum_unique_values
from re import compile as re_compile

from pyt.utils.template.scope import Scope
from pyt.utils.text import deindent_str_block

Element = t.Union[str,]
Blocks = t.Dict[str, t.Callable[['EvalContext', 'TokenIterator', Scope], None]]
Components = t.Dict[str, t.Type['Component']]


# Do not go templite (compiled) approach, instead write an interpreted approach
# (Django style, norvig lispy style)

# `iter_until` is important for recursively eval'ing components and passing along
# whatever embedded DSL text intended for them (their props.children)

# TODO: consider removing CodeBlock usage - seems like I can write directly ?
#       ... or will that screw up indentation stuff ?


@enum_unique_values
class Indentation(Enum):
    INDENT = 1
    DEDENT = 2


class IRender(Protocol):
    def render(self, buf: t.Union[IWriter, StringIO], indent_with: str = ' ', indent_level: int = 0):
        ...


class CodeBlock:
    def __init__(self):
        self._code: t.List[t.Union[Element, Indentation, 'CodeBlock']] = []

    def writeln(self, s: Element):
        self._code.append(s)

    def writeln_r(self, s: Element):
        self._code.extend([s, Indentation.INDENT])

    def writeln_l(self, s: Element):
        self._code.extend([s, Indentation.DEDENT])

    def writeln_lr(self, s: Element):
        self._code.extend([Indentation.DEDENT, s, Indentation.INDENT])

    def render(self, buf: t.Union[IWriter, StringIO], indent_with: str = ' ', indent_level: int = 0):
        for elem in self._code:
            if isinstance(elem, str):
                buf.write(f"{indent_with * indent_level}{elem}\n")
            elif isinstance(elem, Indentation):
                if elem is Indentation.INDENT:
                    indent_level += 1
                else:
                    indent_level -= 1
                    assert indent_level >= 0, "indentation level cannot be negative"
            elif hasattr(elem, 'render') and callable(elem.render):
                elem.render(buf, indent_with=indent_with, indent_level=indent_level)
            else:
                raise RuntimeError(f"CodeBlock unexpected '{type(elem).__name__}' element in sequence")

        return self._code[1:]  # FIRST ELEM IS A SPURIOUS NEWLINE

    def add_section(self, block: 'CodeBlock'):
        self._code.append(block)  # append, no newline needed, other options ensure those

    def __repr__(self):
        return (
            f"{type(self).__name__}<"
            f"code: [{', '.join((repr(elem) for elem in self._code))}]"
            ">")


_tstr = re_compile(r"(<<.*?>>)")
_cline = re_compile(r"^\s*%\s*(?P<kw>[^%[^\s]+)\s*(?P<rest>[^%].+)?")


@enum_unique_values
class TokType(Enum):
    TEXT = 1
    NEWLINE = 2
    CTRL = 3
    EXPR = 4


# TODO: issue - %% lines aren't rewritten

def token_stream(text: str):
    # rewritten to have a 'lead-in' phase where leading newlines is ignored.
    lines = (line for line in text.split('\n'))
    lead_in = True
    for line in lines:
        m = _cline.match(line)
        if m:
            yield (TokType.CTRL, m['kw'], m['rest'])
        else:
            for tok in _tstr.split(line):
                if tok.startswith('<<'):
                    yield (TokType.EXPR, tok[2:-2])
                    lead_in = False
                elif tok is not '':
                    yield (TokType.TEXT, tok)
                    lead_in = False
            if not lead_in:
                yield (TokType.NEWLINE,)
        if not lead_in:
            break

    # The rest...
    for line in lines:
        m = _cline.match(line)
        if m:
            yield (TokType.CTRL, m['kw'], m['rest'])
        else:
            for tok in _tstr.split(line):
                if tok.startswith('<<'):
                    yield (TokType.EXPR, tok[2:-2])
                elif tok != '':
                    yield (TokType.TEXT, tok)
                else:
                    continue
            yield (TokType.NEWLINE,)


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
    __slots__ = ['blocks', 'components', 'buffer', 'buffer_append', 'out']

    def __init__(self, *, blocks: Blocks = None, components: Components = None):
        self.blocks = blocks or {}
        self.components = components or {}
        self.buffer = []
        self.buffer_append: t.Callable[[object], None] = self.buffer.append
        self.out = CodeBlock()

    def writeln(self, line: str) -> None:
        self.out.writeln(line)

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
        dsl_eval_main(
            body_ctx, tokens, Scope(outer=scope),
            stop_at_ctrl_tokens({f'/{component_name}'}))

        # Define scope supplied to the rendering
        component_scope = Scope(outer=scope)
        cls._scope_(component_scope, component_args)

        # TODO: lazily render children
        def render_body(ctx: EvalContext, _: TokenIterator, __: Scope, args: str):
            if args:
                raise RuntimeError("body block cannot take arguments")
            ctx.out.add_section(body_ctx.out)

        component_ctx = ctx.derived(with_blocks={'body': render_body})
        # Render the component itself
        dsl_eval_main(component_ctx, TokenIterator(token_stream(
            deindent_str_block(cls.TEMPLATE, ltrim=True))),
                      component_scope)
        ctx.out.add_section(component_ctx.out)


def dsl_eval_main(ctx: EvalContext, tokens: TokenIterator, scope: Scope, stop: t.Optional[t.Callable] = None):
    to_str = str
    for token in tokens:
        if stop and stop(token):
            return
        typ, *vals = token
        if typ == TokType.TEXT:
            ctx.buffer_append(vals[0])
        elif typ == TokType.NEWLINE:
            if len(ctx.buffer) != 0:
                # flush buffer
                ctx.writeln("".join(ctx.buffer))
                del ctx.buffer[:]
            else:
                ctx.writeln("")
        elif typ == TokType.EXPR:
            result = _eval_exprs(vals[0], scope)
            # if isinstance(result, CodeBlock):
            #     # TODO: somehow make a 'body' block (w/o closing tag)
            #     print(f"!! @ indent '{''.join(ctx.buffer)}'")
            #     # result._render_(ctx, tokens, scope, 'body', '')
            # else:
            #     ctx.buffer_append(to_str(result))
            ctx.buffer_append(to_str(result))
        elif typ == TokType.CTRL:
            if len(ctx.buffer) != 0:
                # flush buffer
                ctx.writeln("".join(ctx.buffer))
                del ctx.buffer[:]

            ctrl_kw, ctrl_args = vals
            if ctrl_kw == 'for':
                dsl_eval_for(ctx, tokens, scope, ctrl_args)
            elif ctrl_kw == 'if':
                dsl_eval_if(ctx, tokens, scope, ctrl_args)
            elif ctrl_kw[0].isupper():
                # TODO - FIXME - will swallow keyerrors from user-code
                component = ctx.components.get(ctrl_kw)
                if not component:
                    raise RuntimeError(f"Unknown component '{ctrl_kw}'")

                component._render_(ctx, tokens, scope, ctrl_kw, ctrl_args)
            elif not ctrl_kw.startswith('/'):  # must be a block
                block = ctx.blocks.get(ctrl_kw)
                if not block:
                    raise RuntimeError(f"Unknown block '{ctrl_kw}'")
                block(ctx, tokens, scope, ctrl_args)
            else:  # must be a close block tag - should not been seen
                raise RuntimeError(
                    f"illegal nesting, got unexpected'{ctrl_kw}'")


def dsl_eval_for(ctx: EvalContext, tokens: TokenIterator, scope: Scope, for_args: str):
    for_tokens = []
    for token in tokens:
        if token[0] == TokType.CTRL and token[1].startswith('/for'):
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
        return token[0] == TokType.CTRL and token[1].split()[0] in tokens

    return stopfn


def dsl_eval_if(ctx: EvalContext, tokens: TokenIterator, scope: Scope, cond_expr: str):
    kw = 'if'
    accepted_tags = {'elif', 'else', '/if'}
    while True:
        if kw in {'if', 'elif'}:
            if _eval_exprs(cond_expr, scope):
                dsl_eval_main(ctx, tokens, Scope(outer=scope), stop_at_ctrl_tokens(accepted_tags))

                # TODO: refactor once a fixed structure for Tokens has been established
                # skip past all other branches in if-block
                if tokens.current[1] != '/if':
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
        if not token or token[0] != TokType.CTRL or token[1] not in accepted_tags:
            print(f"TOKEN current: {tokens.current}")
            print(f"TOKEN next: {tokens._next}")
            for token in tokens:
                print(f"TOK: {token}")
            raise RuntimeError(f"invalid nesting - expected {accepted_tags}, got: {token}")

        _, kw, cond_expr = token
        if kw == 'else':
            accepted_tags = {'/if'}
        elif kw == '/if':
            break


def dsl_eval_component(ctx: EvalContext, tokens: TokenIterator, scope: Scope, component_args: str):
    _, component, args = ctx.tokens.current
    # TODO: implement
    pass


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
