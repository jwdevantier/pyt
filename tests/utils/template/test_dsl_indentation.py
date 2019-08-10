import pytest
from pyt.utils.template.dsl import *
from pyt.utils.template.dsl import (
    token_stream, TokenIterator,
    EvalContext, LineWriter,
    dsl_eval_main
)
from io import StringIO
import typing as t
from pyt.utils.text import deindent_str_block


# TODO: consider omitting the trailing newline - can be expressed in the template if needed(?)


def render_prog(prog: str, scope_vars: t.Optional[t.Dict[str, t.Any]] = None) -> str:
    buf = StringIO()
    ctx = EvalContext(LineWriter(buf), blocks={}, components={})
    tokens = TokenIterator(token_stream(prog))
    scope = Scope(scope_vars or {})
    dsl_eval_main(ctx, tokens, scope)

    return buf.getvalue()


def assert_prog(actual, expected, msg: str = ""):
    expected = deindent_str_block(expected, ltrim=True)
    if actual != expected:
        print("Expected:")
        print("-------------------")
        print(expected)
        print("Actual:")
        print("-------------------")
        print(actual)
    assert actual == expected, msg


PROG_TOPLEVEL_LITERAL = """\
something
    else"""


def test_toplevel_literal():
    # getting a trailing newline
    assert render_prog(PROG_TOPLEVEL_LITERAL) == PROG_TOPLEVEL_LITERAL + '\n'


PROG_TOPLEVEL_IF_FLAT = """\
hello
% if True
world
% /if"""


def test_toplevel_if():
    assert render_prog(PROG_TOPLEVEL_IF_FLAT) == deindent_str_block("""
    hello
    world
    """, ltrim=True)


PROG_TOPLEVEL_IF_INDENT_BLOCK = """\
hello
    % if True
if line 1
if line 2
% /if
world"""


def test_toplevel_if_indent_block():
    assert render_prog(PROG_TOPLEVEL_IF_INDENT_BLOCK) == deindent_str_block("""
    hello
        if line 1
        if line 2
    world
    """, ltrim=True)


PROG_TOPLEVEL_IF_INDENT_BLOCK_NESTED = """\
hello
    % if True
    if line 1
    if line 2
        % if True
        if line 3
        % /if
    % /if
world"""


def test_toplevel_if_indent_block_nested():
    actual = render_prog(PROG_TOPLEVEL_IF_INDENT_BLOCK_NESTED)
    expected = """
    hello
        if line 1
        if line 2
            if line 3
    world
    """
    assert_prog(actual, expected)


PROG_TOPLEVEL_NESTED_BLOCKS = """\
hello
    % if True
    if line 1
        % for line in lines
        for:<<line>>
        % /for
    % /if
world"""


# TODO: broken, for loop complains of too many values to unpack ?
def test_toplevel_nested_blocks():
    scope = {
        'lines': ['line1', 'line2']
    }
    actual = render_prog(PROG_TOPLEVEL_NESTED_BLOCKS, scope)
    expected = """
    hello
        if line 1
            for:line1
            for:line2
    world
"""
    assert_prog(actual, expected)

# TODO: components, body, indentation
# Component, if, indentation
