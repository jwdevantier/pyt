import pytest
from pyt.utils.template.dsl import *
from io import StringIO

# Do **NOT** process text snippets, let the user defining the snippet do so
# (possibly even the component code)

# TODO write simpler programs to test against
# TODO definitely need to figure out how to wrap up snippet in a component
# TODO implement component "props"/formatter methods

# TODO - if, nested (?)
# TODO - for, simple
# TODO - if, for (nested)
# TODO - component lookup -- success
# TODO - component lookup -- failure


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
% for number in range(0,loops)
hello!
% /for
"""

TEXT_PROG_FOR_LOOPVAR = """
% for number in range(1,loops+1)
<<number>>!
% /for
"""

TEXT_PROG_FOR_LOOPVARS = """
% for key,val in entries.items()
'<<key>>' => '<<val>>'
% /for"""

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
        (TokType.TEXT, 'hello, world'),
        (TokType.NEWLINE,),
        (TokType.TEXT, 'this is awesome'),
        (TokType.NEWLINE,)
    ]


def test_toks_prog_if_simple():
    assert list(token_stream(TEXT_PROG_IF_SIMPLE)) == [
        (TokType.TEXT, 'always intro'),
        (TokType.NEWLINE,),
        (TokType.CTRL, 'if', 'x is not None'),
        (TokType.TEXT, "x is something"),
        (TokType.NEWLINE,),
        (TokType.CTRL, '/if', None),
        (TokType.CTRL, 'if', 'x is None'),
        (TokType.TEXT, 'x is none'),
        (TokType.NEWLINE,),
        (TokType.CTRL, '/if', None),
        (TokType.TEXT, 'always outro'),
        (TokType.NEWLINE,),
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

    ("for_loopvars", TEXT_PROG_FOR_LOOPVARS,
     {'entries': {'john': 'programmer'}},
     "'john' => 'programmer'\n"),
    #
    # # components
    # # TODO: component lookup success
    # # TODO: component lookup failure
])
def test_dsl_eval_progs(label, prog, scope_vars, result):
    ctx = EvalContext({})
    tokens = TokenIterator(token_stream(prog))
    scope = Scope(scope_vars)
    dsl_eval_main(ctx, tokens, scope)
    buf = StringIO()
    ctx.out.render(buf)
    actual = buf.getvalue()
    # print(f"actual => {actual}")
    assert actual == result, f"'{label}' failed to produce expected result"

# def test_smth():
#     out = gen_loop_iterator("lbl, val in smth['entry']", {
#         'smth': {'entry': [('one', 11), ('two', 22)]},
#         'nodetypes': [('one', 1), ('two', 2)]})
#     for env in out:
#         print(f"iter env: {env}")
