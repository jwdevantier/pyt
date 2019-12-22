import pytest
from ghostwriter.utils.cogen.tokenizer import (
    PyTokenFactory as TokenFactory,
    Tokenizer
)
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If,
    ParserError, UnexpectedTokenError, InvalidBlockNestingError, InvalidEndBlockArgsError
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

    ("for block",
     "\n".join([
         "%for x in y",
         "something",
         "%/for"
     ]),
     Program([
        Block(
            CLine('for', 'x in y'), [
                Line([Literal("something")]),
            ])
     ])),

    ("component-block",
     "\n".join([
         "%r MyFN(self.fn_name, self.fn_args)",
         'print("hello, world")',
         "%/r",
     ]),
     Program([
         Block(
             CLine('r', 'MyFN(self.fn_name, self.fn_args)'), [
                 Line([Literal('print("hello, world")')])
             ])
     ])),

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
def test_progs(msg, prog, result):
    parser = CogenParser(Tokenizer(prog))
    print(parser)
    assert parser.parse_program() == result, f"failed: {msg}"


@pytest.mark.parametrize("msg, prog, err", [
    ("for end-block w arguments",
     "\n".join([
         "%for person in persons",
         "%/for smth"
     ]),
     {'type': InvalidEndBlockArgsError, 'match': ".*'/for' cannot have arguments",
      'line': 2, 'col': 10}),

    ("if end-block w arguments",
     "\n".join([
         "%if a != 2",
         "%/if smth"
     ]),
     {'type': InvalidEndBlockArgsError, 'match': ".*'/if' cannot have arguments",
      'line': 2, 'col': 9})
])
def test_prog_parse_errors(msg, prog, err):
    """Ensure end block cannot have arguments"""
    parser = CogenParser(Tokenizer(prog))
    with pytest.raises(err['type'], match=err['match']) as excinfo:
        parser.parse_program()
    line = err.get('line')
    col = err.get('col')
    if line:
        assert excinfo.value.location.line == line, "unexpected line"
    if col:
        assert excinfo.value.location.col == col, "unexpected column"

# TODO: '% for', '%/ for' => error
# TODO: '%/if xyz' -- should not be allowed
