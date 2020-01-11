import pytest
from ghostwriter.utils.cogen.tokenizer import (
    PyTokenFactory as TokenFactory,
    Tokenizer
)
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If, Node,
    ParserError, UnexpectedTokenError, InvalidBlockNestingError, InvalidEndBlockArgsError
)
from ghostwriter.utils.cogen.visitor import ASTVisitor#RewriteComponentNodes, Component
import re
import typing as t

rgx_fn_call = re.compile(r"(?P<ident>^[^\d\W]\w*)\((?P<args>.*)\)\Z", re.UNICODE)


class Component(Node):
    def __init__(self, identifier: str, args: str, lines: t.List[Node]):
        self.identifier = identifier
        self.args = args
        self.lines = lines

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and other.identifier == self.identifier
            and other.args == self.args
            and other.lines == self.lines
        )

    def __repr__(self):
        return f'r({self.identifier}: ~~{self.args}~~, {self.lines})'


class RewriteComponentNodes(ASTVisitor):
    def visit_Block(self, node: Block):
        if node.header.keyword != 'r':
            return super().visit_Block(node)
        m = rgx_fn_call.match(node.header.args)
        if not m:
            raise RuntimeError("Invalid component")
        return Component(m.group('ident'), m.group('args'), [
            self.visit(l) for l in node.lines
        ])


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