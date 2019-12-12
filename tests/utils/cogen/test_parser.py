import pytest
from ghostwriter.utils.cogen.tokenizer import (
    PyTokenFactory as TokenFactory,
    Tokenizer
)
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If,
)


@pytest.mark.parametrize("msg, prog, result", [
    ("line - single literal",
     "hello, world\n",
     Program([
        Line([
            Literal("hello, world")])])
     ),

    ("line - literal, multiple elements",
     "hello, <<world>>!\n",
     Program([
        Line([
            Literal("hello, "),
            Expr("world"),
            Literal("!")])])
     ),

    ("if-elif-else block",
     "\n".join([
         "%if foo == 1",
         "foo won!",
         "%elif foo == 2",
         "foo got second place!",
         "%else",
         "meh, who cares",
         "%/if"]),
     Program([
         If([Block(CLine('if', 'foo == 1'), [
             Line([Literal('foo won!')])]),
             Block(CLine('elif', 'foo == 2'), [
                 Line([Literal('foo got second place!')])]),
             Block(CLine('else'), [
                 Line([Literal('meh, who cares')])])])])
     ),

    ("a small program (nested)",
     "\n".join([
         "hello, <<world>>!",
         "%for x in y",
         "something",
         "else",
         "%/for"
     ]),
     Program([
        Line([
            Literal("hello, "),
            Expr("world"),
            Literal("!")]),

        Block(
            CLine('for', 'x in y'), [
                Line([Literal("something")]),
                Line([Literal("else")]),
            ])
     ])),
])
def test_single_lines(msg, prog, result):
    parser = CogenParser(Tokenizer(prog))
    print(parser)
    assert parser.parse_program() == result

# TODO: '% for', '%/ for' => error
# TODO: '%/if xyz' -- should not be allowed
