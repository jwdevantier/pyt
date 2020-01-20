from typing import List, Any, Dict, Optional
from ghostwriter.utils.cogen.parser import (
    CogenParser, Program, Literal, Expr, Line, CLine, Block, If,
)
from ghostwriter.utils.cogen.component import Component

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

    def __repr__(self):
        return f"TestCase({self.header})"


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
            "hello!\n"
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
            "Peter: 12 years old\n"
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
            "something",
            "something\n"
        ],
        {'y': [1, 2]}))


for_block_use_var = TestCase(
    "for loop using vars - block",
    [
        "%for name, age in persons",
        "<<name>>: <<age>> years old",
        "%/for"
    ],
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
        {'persons': [("Peter", '12')]}),
    Example(
        'two-item iterable',
        [
            "Janet: 38 years old",
            "Peter: 12 years old\n"
        ],
        {'persons': [('Janet', 38), ('Peter', 12)]})
)


class HelloWorldComponent(Component):
    template = "hello, world"


component_block_simplest = TestCase(
    "A sample component block",
    [
        "%r MyComponent()",
        "%/r",
    ],
    Program([
        Block(
            CLine('r', 'MyComponent()'), [])
    ]),
    Example(
        '',
        [
            "hello, world\n"
        ],
        {
            'MyComponent': HelloWorldComponent,
        }
    )
)


class HelloComponent(Component):
    def __init__(self, thing):
        self.thing = thing

    template = "hello, <<self.thing>>"


component_block_simple_var = TestCase(
    "A sample component block using vars from arguments",
    [
        "%r MyComponent(name)",
        "%/r",
    ],
    Program([
        Block(
            CLine('r', 'MyComponent(name)'), [])
    ]),
    Example(
        '',
        [
            "hello, Arthur\n"
        ],
        {
            'MyComponent': HelloComponent,
            'name': 'Arthur'
        }
    ),
    Example(
        '',
        [
            "hello, Joan\n"
        ],
        {
            'MyComponent': HelloComponent,
            'name': 'Joan'
        }
    )
)


class HelloScopeVarComponent(Component):
    template = "hello, <<thing>>"


component_block_simple_var_from_scope = TestCase(
    "A sample component block using var from inherited scope",
    [
        "%r MyComponent()",
        "%/r",
    ],
    Program([
        Block(
            CLine('r', 'MyComponent()'), [])
    ]),
    Example(
        '',
        [
            "hello, Arthur\n"
        ],
        {
            'MyComponent': HelloScopeVarComponent,
            'thing': 'Arthur'
        }
    ),
    Example(
        '',
        [
            "hello, Joan\n"
        ],
        {
            'MyComponent': HelloScopeVarComponent,
            'thing': 'Joan'
        }
    )
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
