from typing_extensions import Protocol
import typing as t
from io import StringIO
from pyt.protocols import IWriter

from enum import Enum, unique as enum_unique_values
from re import compile as re_compile

from pyt.utils.template.scope import Scope


# Do not go templite (compiled) approach, instead write an interpreted approach
# (Django style, norvig lispy style)

# `iter_until` is important for recursively eval'ing components and passing along
# whatever embedded DSL text intended for them (their props.children)

@enum_unique_values
class Indentation(Enum):
    INDENT = 1
    DEDENT = 2


Element = t.Union[str,]
Props = t.Dict[str, t.Any]  # TODO: re-shape when defined


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
    __slots__ = ['handlers', 'buffer', 'buffer_append', 'out']

    def __init__(self, handlers: t.Dict[str, t.Callable]):
        self.handlers = handlers
        self.buffer = []
        self.buffer_append: t.Callable[[object], None] = self.buffer.append
        self.out = CodeBlock()

    def writeln(self, line: str) -> None:
        self.out.writeln(line)


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
        elif typ == TokType.EXPR:
            ctx.buffer_append(to_str(_eval_exprs(vals[0], scope)))
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
                # TODO: implement actual component rendering
                handler = ctx.handlers.get(ctrl_kw)
                if handler:
                    handler(ctx, tokens, scope, ctrl_args)
                    return
                raise RuntimeError(f"Unknown component '{ctrl_kw}'")
            elif ctrl_kw.startswith('/'):
                raise RuntimeError(
                    f"illegal nesting, got unexpected'{ctrl_kw}'")
            else:
                raise RuntimeError(f"unknown instruction '{ctrl_kw}'")


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


#
# def dsl_eval_if(ctx: EvalContext, tokens: TokenIterator, scope: Scope, cond_expr: str):
#     accepted_tags = {'elif', 'else', '/if'}
#     kw = 'if'
#     while True:
#         stop = stop_at_ctrl_tokens(accepted_tags)
#         if kw == '/if':
#             raise RuntimeError("..")
#         if kw != 'else':
#             if _eval_exprs(cond_expr, scope):
#                 dsl_eval_main(ctx, tokens, Scope(outer=scope), stop)
#                 skip_tokens(tokens, stop_at_ctrl_tokens({'/if'}))
#                 break
#             else:
#                 skip_tokens(tokens, stop)
#         else:
#             dsl_eval_main(ctx, tokens, Scope(outer=scope), stop)
#             break
#
#         # TODO: revamp once we've settled on a data structure for Tokens
#         token = tokens.current
#         if not token or token[0] != TokType.CTRL or token[1] not in accepted_tags:
#             raise RuntimeError(f"invalid nesting - expected {accepted_tags}")
#
#         _, kw, if_args = token
#         if kw == 'else':
#             accepted_tags = {'/if'}
#         elif kw == '/if':
#             break


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
