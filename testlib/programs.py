from typing import List, Any, Dict, Optional
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If,
)

Scope = Dict[str, Any]


class Example:
    def __init__(self, header: str, scope: Scope, result: List[str], ):
        self.header = header
        self.scope = scope
        self.result = '\n'.join(result)


class TestCase:
    def __init__(self, header: str, program: List[str], ast: Program, *examples: Example):
        self.header = header
        self.program = '\n'.join(program)
        self.ast = ast
        self.examples = examples


line_literal = TestCase(
    "line - single literal",
    [
        "hello, world\n"
    ],
    Program([
        Line([
            Literal("hello, world")])]),
    Example(
        '',
        {},
        [
            'hello, world\n'
        ]))

line_lit_var = TestCase(
    "line - literal, multiple elements (& variable)",
    [
        "hello, <<thing>>!\n"
    ],
    Program([
        Line([
            Literal("hello, "),
            Expr("thing"),
            Literal("!")])]),
    Example(
        '',
        {'thing': 'world'},
        [
            'hello, world!\n'
        ]),
    Example(
        '',
        {'thing': 'people'},
        [
            'hello, people!\n'
        ]))

if_simplest = TestCase(
    "if-simplest",
    [
        "%if x is not None",
        "x is something",
        "%/if"
    ],
    Program([
        If([Block(CLine('if', 'x is not None'), [
            Line([Literal("x is something")])])])]),
    Example(
        "set x",
        {"x": 1},
        [
            "x is something"
        ]
    ),
    Example(
        "x is unset",
        {"x": None},
        [
            "\n"
        ]
    )
)

if_elif_else = TestCase(
    "if-elif-else block",
    [
        "%if foo == 1",
        "foo won!",
        "%elif foo == 2",
        "foo got second place!",
        "%else",
        "meh, who cares",
        "%/if"
    ],
    Program([
        If([Block(CLine('if', 'foo == 1'), [
            Line([Literal('foo won!')])]),
            Block(CLine('elif', 'foo == 2'), [
                Line([Literal('foo got second place!')])]),
            Block(CLine('else'), [
                Line([Literal('meh, who cares')])])])]),
    Example(
        '',
        {'foo': 1},
        [
            'foo won!\n'
        ]),
    Example(
        '',
        {'foo': 2},
        [
            'foo got second place!\n'
        ]),
    Example(
        '',
        {'foo': '3'},
        [
            'meh, who cares\n'
        ]))

for_block = TestCase(
    "for loop - block",
    [
        "%for x in y",
        "something",
        "%/for"
    ],
    Program([
        Block(
            CLine('for', 'x in y'), [
                Line([Literal("something")])])]),
    Example(
        '',
        {'y': []},
        [
            "\n"
        ]),
    Example(
        '',
        {'y': [1]},
        [
            "something\n"
        ]),
    Example(
        '',
        {'y': [1, 2]},
        [
            "something\n",
            "something\n"
        ]))

# TODO: need to embed / resolve components somehow (Add ComponentScope to examples)
component_block = TestCase(
    "A sample component block",
    [
        "%r MyFN(self.fn_name, self.fn_args)",
        'print("hello, world")',
        "%/r",
    ],
    Program([
        Block(
            CLine('r', 'MyFN(self.fn_name, self.fn_args)'), [
                Line([Literal('print("hello, world")')])
            ])
    ])
    # TODO: missing examples
)

prog1 = TestCase(
    "A small program",
    [
        "hello, <<thing>>!",
        "%for x in y",
        "something",
        "else",
        "%/for"
    ],
    Program([
        Line([
            Literal("hello, "),
            Expr("thing"),
            Literal("!")]),

        Block(
            CLine('for', 'x in y'), [
                Line([Literal("something")]),
                Line([Literal("else")]),
            ])
    ]),
    Example(
        '',
        {
            'thing': 'clerk',
            'y': [1, 2]
        },
        [
            "hello, clerk!",
            "something",
            "else",
            "something",
            "else\n"
        ]))
