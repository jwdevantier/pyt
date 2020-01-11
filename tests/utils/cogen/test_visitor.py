import pytest
from ghostwriter.utils.cogen.tokenizer import (
    PyTokenFactory as TokenFactory,
    Tokenizer
)
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If,
    ParserError, UnexpectedTokenError, InvalidBlockNestingError, InvalidEndBlockArgsError
)
from ghostwriter.utils.cogen.visitor import RewriteComponentNodes, Component


@pytest.mark.parametrize("msg, prog, result", [
    ("component-block",
     "\n".join([
         "%r MyFN(self.fn_name, self.fn_args)",
         'print("hello, world")',
         "%/r",
     ]),
     Program([
         Component(
             'MyFN', 'self.fn_name, self.fn_args', [
                Line([Literal('print("hello, world")')])
             ])
     ])),

    ("nested component-blocks",
     "\n".join([
         "%r MyFN(self.fn_name, self.fn_args)",
         'print("hello, world")',
         '%r MyInnerFN(self.fn_name, self.fn_args)',
         'print("hello, from inside")',
         "%/r",
         "%/r",
     ]),
     Program([
         Component(
             'MyFN', 'self.fn_name, self.fn_args', [
                Line([Literal('print("hello, world")')]),
                Component('MyInnerFN', 'self.fn_name, self.fn_args', [
                    Line([Literal('print("hello, from inside")')]),
                ])
             ])
     ])),

    ("non-component block",
     "\n".join([
         "%foo MyFN(self.fn_name, self.fn_args)",
         'print("hello, world")',
         "%/foo",
     ]),
     Program([
         Block(CLine('foo', 'MyFN(self.fn_name, self.fn_args)'), [
            Line([Literal('print("hello, world")')])
         ])
     ])),
])
def test_component(msg, prog, result):
    parser = CogenParser(Tokenizer(prog))
    v = RewriteComponentNodes()
    ast = parser.parse_program()
    assert v.visit(ast) == result, f"failed: {msg}"