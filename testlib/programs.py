from typing import List, Any, Dict, Optional
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If,
)

Scope = Dict[str, Any]
Blocks = Dict[str, Any]


class Example:
    def __init__(self, header: str, result: List[str], scope: Scope, blocks: Blocks = None):
        self.header = header
        self.result = '\n'.join(result)
        self.scope = scope
        self.blocks = blocks or {}


class TestCase:
    def __init__(self, header: str, program: List[str], ast: Program, *examples: Example):
        self.header = header
        self.program = '\n'.join(program)
        self.ast = ast
        self.examples = examples


line_literal_simplest = TestCase(
    "line - single literal",
    [
        "hello, world\n"
    ],
    Program([
        Line([
            Literal("hello, world")])]),
    Example(
        '',
        [
            'hello, world\n'
        ],
        {},
        ))

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
        [
            'hello, world!\n'
        ],
        {'thing': 'world'}),
    Example(
        '',
        [
            'hello, people!\n'
        ],
        {'thing': 'people'},))

line_expr_first = TestCase(
    "line starting with an expression",
    [
        "<<greeting>>"
    ],
    Program([
        Line([
            Expr("greeting")
        ])
    ]),
    Example(
        "",
        [
            "hello!"
        ],
        {"greeting": "hello!"}
    )
)

line_lit_adv = TestCase(
    "line - multiple literals and expressions",
    [
        "<<name>>: <<age>> years old"
    ],
    Program([
        Line([
            Expr("name"),
            Literal(": "),
            Expr("age"),
            Literal(" years old")])]),
    Example(
        "",
        [
            "Peter: 12 years old"
        ],
        {"name": "Peter", "age": 12}
    )
)

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
        [
            "x is something\n"
        ],
        {"x": 1},
    ),
    Example(
        "x is unset",
        [
            ""
        ],
        {"x": None},
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
        [
            'foo won!\n'
        ],
        {'foo': 1},),
    Example(
        '',
        [
            'foo got second place!\n'
        ],
        {'foo': 2}),
    Example(
        '',
        [
            'meh, who cares\n'
        ],
        {'foo': 3}))

for_block_simplest = TestCase(
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
        'empty iterable',
        [
            ""
        ],
        {'y': []}),
    Example(
        'single-item iterable',
        [
            "something\n"
        ],
        {'y': [1]}),
    Example(
        'two-item iterable',
        [
            "something\n",
            "something\n"
        ],
        {'y': [1, 2]}))


for_block_use_var = TestCase(
    "for loop - block",
    [
        "%for name, age in persons",
        "<<name>>: <<age>> years old",
        "%/for"
    ],
    # [
    #     "%for name, age in persons",
    #     "<<name>>",
    #     "%/for"
    # ],
    Program([
        Block(
            CLine('for', 'name, age in persons'), [
                Line([Expr("name"), Literal(": "), Expr("age"), Literal(" years old")])])]),
    Example(
        'empty iterable',
        [
            ""
        ],
        {'persons': []}),
    Example(
        'single-item iterable',
        [
            "Peter: 12 years old\n"
        ],
        {'persons': [("peter", 12)]}),
    Example(
        'two-item iterable',
        [
            "Janet: 38 years old\n",
            "Peter: 12 years old\n"
        ],
        {'persons': [('Janet', 38), ('Peter', 12)]})
)


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
        [
            "hello, clerk!",
            "something",
            "else",
            "something",
            "else\n"
        ],
        {
            'thing': 'clerk',
            'y': [1, 2]
        }))
