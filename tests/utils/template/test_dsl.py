import pytest
from pyt.utils.template.dsl import *
from pyt.utils.template.dsl import (
    token_stream, EvalContext, LineWriter, TokenIterator,
    dsl_eval_main)
from pyt.utils.template.tokens import *
from io import StringIO

# Do **NOT** process text snippets, let the user defining the snippet do so
# (possibly even the component code)

# TODO - if, nested (?)
# TODO - component lookup -- success
# TODO - component lookup -- failure

# TODO: dialect idea? github.com/blambeau/wlang

# TODO: <ERROR> codeblock not rendered in template
#       - take indentation level from parent (+1 ever ?)
# TODO: <FEATURE> the whitespace thing -- SEE TODO.md


TEXT_PROG_LITERAL = """
hello, world
this is awesome"""

TEXT_PROG_EXPRS = """
hello <<name>>!
thanks for purchasing <<thing>>!"""

TEXT_PROG_EXPR_ADVANCED = """
<<", ".join(names)>>"""

TEXT_PROG_COMMENT = """
something which will be escaped:
%% for x in lst"""

TEXT_PROG_IF_SIMPLEST = """
%if x is not None
x is something
%/if"""

TEXT_PROG_IF_SIMPLE = """
always intro
% if x is not None
x is something
% /if
% if x is None
x is none
% /if
always outro"""

TEXT_PROG_IF_ELSE_SIMPLE = """
always intro
% if x is not None
x is something
% else
x is none
% /if
always outro"""

TEXT_PROG_IF_ELIF_ELSE = """
intro
% if x < 0
x is negative
% elif x == 0
x is zero
% elif x > 0 and x < 100
x is positive
% else
x is a big positive number
% /if
outro"""

TEXT_PROG_FOR_SIMPLE = """
% for number in range(0, loops)
hello!
% /for"""

TEXT_PROG_FOR_LOOPVAR = """
% for number in range(1, loops+1)
<<number>>!
% /for"""

TEXT_PROG_FOR_LOOPVARS = """
% for key,val in entries.items()
'<<key>>' => '<<val>>'
% /for"""

TEXT_PROG_FOR_IF_ELSE = """
% for num in range(0,end)
% if num % 2 == 0
<<num>> is even
% else
<<num>> is odd
% /if
% /for"""

# TODO: fixup
TEXT_PROG_IF_FOR_ELSE = """
%if num < 5
%for n in range(0,num)
<<n>>...
%/for
DONE!
%else
<<num>> is a big number
%/if"""

# TODO: use or discard
TEXT_PROG_FULL = """
    % for nodetype in nodetypes
    %% testing my luck
    % AstExpr (ntype nodetype)
        var out bytes.Buffer

        elements := []string{}
        for _, el := range <<nodetype.ident>>.Elements {
            elements = append(elements, el.String())
        }

        out.WriteString("[")
        out.WriteString(strings.Join(elements, ", "))
        out.WriteString("]")

        return out.String()
    % /AstExpr
    % if smth == True
        hurray
    % /if
    % /for"""


def test_toks_prog_literal():
    assert list(token_stream(TEXT_PROG_LITERAL)) == [
        TextToken('hello, world'),
        NewlineToken(),
        TextToken('this is awesome'),
        NewlineToken()
    ]


def test_toks_prog_if_simplest():
    assert list(token_stream(TEXT_PROG_IF_SIMPLEST)) == [
        CtrlToken('', 'if', 'x is not None'),
        TextToken('x is something'),
        NewlineToken(),
        CtrlToken('', '/if', None),
    ]


def test_toks_prog_if_simple():
    assert list(token_stream(TEXT_PROG_IF_SIMPLE)) == [
        TextToken('always intro'),
        NewlineToken(),
        CtrlToken('', 'if', 'x is not None'),
        TextToken('x is something'),
        NewlineToken(),
        CtrlToken('', '/if', None),
        CtrlToken('', 'if', 'x is None'),
        TextToken('x is none'),
        NewlineToken(),
        CtrlToken('', '/if', None),
        TextToken('always outro'),
        NewlineToken(),
    ]


def test_toks_prog_for_simple_once():
    assert list(token_stream(TEXT_PROG_FOR_SIMPLE)) == [
        CtrlToken('', 'for', 'number in range(0, loops)'),
        TextToken('hello!'),
        NewlineToken(),
        CtrlToken('', '/for', None)
    ]


@pytest.mark.parametrize("label, prog, scope_vars, result", [
    # Literal lines
    ("literal", TEXT_PROG_LITERAL, {},
     "hello, world\nthis is awesome\n"),
    # TODO: literal ctrl escaping --- ensure tokenizer rewrites lines starting with '\s*%%' => '\s*%'
    # TODO: handle resolve with missing vars(?)

    # expression interpolation
    ("exprs", TEXT_PROG_EXPRS, {'name': 'john', 'thing': 'soap'},
     "hello john!\nthanks for purchasing soap!\n"),
    ("exprs", TEXT_PROG_EXPR_ADVANCED, {'names': ['peter', 'john', 'joe']},
     "peter, john, joe\n"),

    # TODO: DSL stx --- dot-lookup and optional vals ?

    # if tests
    ("if_simple:none", TEXT_PROG_IF_SIMPLE, {'x': None},
     "always intro\nx is none\nalways outro\n"),
    ("if_simple:something", TEXT_PROG_IF_SIMPLE, {'x': 3.14},
     "always intro\nx is something\nalways outro\n"),

    ("if_else_simple:if", TEXT_PROG_IF_ELSE_SIMPLE, {'x': 3.14},
     "always intro\nx is something\nalways outro\n"),
    ("if_else_simple:else", TEXT_PROG_IF_ELSE_SIMPLE, {'x': None},
     "always intro\nx is none\nalways outro\n"),

    ("if_elif_else:if", TEXT_PROG_IF_ELIF_ELSE, {'x': -2},
     "intro\nx is negative\noutro\n"),
    ("if_elif_else:elif#1", TEXT_PROG_IF_ELIF_ELSE, {'x': 0},
     "intro\nx is zero\noutro\n"),
    ("if_elif_else:elif#2", TEXT_PROG_IF_ELIF_ELSE, {'x': 40},
     "intro\nx is positive\noutro\n"),
    ("if_elif_else:else", TEXT_PROG_IF_ELIF_ELSE, {'x': 1000},
     "intro\nx is a big positive number\noutro\n"),

    # for
    ("for_simple:1", TEXT_PROG_FOR_SIMPLE, {'loops': 1},
     "hello!\n"),
    ("for_simple:3", TEXT_PROG_FOR_SIMPLE, {'loops': 3},
     "hello!\nhello!\nhello!\n"),

    ("for_loopvar:2", TEXT_PROG_FOR_LOOPVAR, {'loops': 2},
     "1!\n2!\n"),
    ("for_loopvar:3", TEXT_PROG_FOR_LOOPVAR, {'loops': 3},
     "1!\n2!\n3!\n"),

    ("for_if_else", TEXT_PROG_FOR_IF_ELSE, {'end': 3},
     "0 is even\n1 is odd\n2 is even\n"),

    ("if_for_else", TEXT_PROG_IF_FOR_ELSE, {'num': 2},
     "0...\n1...\nDONE!\n"),
    ("if_for_else", TEXT_PROG_IF_FOR_ELSE, {'num': 5},
     "5 is a big number\n"),

    #
    # # components
    # # TODO: component lookup success
    # # TODO: component lookup failure
])
def test_dsl_eval_progs(label, prog, scope_vars, result):
    buf = StringIO()
    ctx = EvalContext(LineWriter(buf), blocks={}, components={})
    tokens = TokenIterator(token_stream(prog))
    scope = Scope(scope_vars)
    dsl_eval_main(ctx, tokens, scope)

    actual = buf.getvalue()
    # print(f"actual => {actual}")
    assert actual == result, f"'{label}' failed to produce expected result"