from typing import List, Any, Dict, Optional
from ghostwriter.utils.cogen.parser import NodeFactory as nf
from ghostwriter.utils.cogen.parser import Program
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
    nf.program([
        nf.line('', [
            nf.literal("hello, world")])]),
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
    nf.program([
        nf.line('', [
            nf.literal("hello, "),
            nf.expr("thing"),
            nf.literal("!")])]),
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
    nf.program([
        nf.line('', [
            nf.expr("greeting")
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
    nf.program([
        nf.line('', [
            nf.expr("name"),
            nf.literal(": "),
            nf.expr("age"),
            nf.literal(" years old")])]),
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
        "% if x is not None",
        "x is something",
        "%/if"
    ],
    nf.program([
        nf.if_([nf.block('', 'if', 'x is not None', [
            nf.line('', [nf.literal("x is something")])])])]),
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
    nf.program([
        nf.if_([nf.block('', 'if', 'foo == 1', [
            nf.line('', [nf.literal('foo won!')])]),
            nf.block('', 'elif', 'foo == 2', [
                nf.line('', [nf.literal('foo got second place!')])]),
            nf.block('', 'else', '', [
                nf.line('', [nf.literal('meh, who cares')])])])]),
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
    nf.program([
        nf.block('', 'for', 'x in y', [
            nf.line('', [nf.literal("something")])])]),
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
    nf.program([
        nf.block('', 'for', 'name, age in persons', [
                nf.line('', [nf.expr("name"), nf.literal(": "), nf.expr("age"), nf.literal(" years old")])])]),
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
    nf.program([
        nf.block('', 'r', 'MyComponent()', [])
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
    nf.program([
        nf.block('', 'r', 'MyComponent(name)', [])
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
    nf.program([
        nf.block('', 'r', 'MyComponent()', [])
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


class StoryTimeComponent(Component):
    template = """
    ~~ one upon a time ~~
    % body
    ~~ the end ~~
    """


component_block_w_body = TestCase(
    "A sample component block given a body",
    [
        "%r storytime()",
        "there lived a woman in a hut",
        "%/r",
    ],
    nf.program([
        nf.block('', 'r', 'storytime()', [
                nf.line('', [nf.literal("there lived a woman in a hut")])])
    ]),
    Example(
        '',
        [
            "~~ one upon a time ~~",
            "there lived a woman in a hut",
            "~~ the end ~~\n"
        ],
        {
            "storytime": StoryTimeComponent,
        }
    )
)

# TODO: showcase component calling function as part of transformation

indent_text_lines = TestCase(
    "show how indentation among text lines is respected",
    [
        "   line 1",
        "line 2",
        "line 3",
        "   line 4",
        "      line 5",
    ],
    nf.program([
        nf.line('   ', [nf.literal("line 1")]),
        nf.line('', [nf.literal("line 2")]),
        nf.line('', [nf.literal("line 3")]),
        nf.line('   ', [nf.literal("line 4")]),
        nf.line('      ', [nf.literal("line 5")]),
    ]),
    Example(
        '',
        [
            "   line 1",
            "line 2",
            "line 3",
            "   line 4",
            "      line 5\n",
        ],
        {}
    )
)

# TODO: a variant of this where the if-block's contents are deindented will produce an 'invalid indentation' error
indent_is_wysiwyg_if = TestCase(
    "show how indentation is wysiwyg relative to the base indentation level",
    [
        "hello",
        "   % if True",
        "   if line 1",
        "   if line 2",
        "   %/if",
        "world"
    ],
    nf.program([
        nf.line('', [nf.literal("hello")]),
        nf.if_([nf.block('   ', 'if', 'True', [
            nf.line('   ', [nf.literal("if line 1")]),
            nf.line('   ', [nf.literal("if line 2")])])]),
        nf.line('', [nf.literal("world")])
    ]),
    Example(
        '',
        [
            "hello",
            "if line 1",
            "if line 2",
            "world\n"
        ],
        {}
    )
)


indent_is_wysiwyg_for = TestCase(
    "show how a for-block's opening line determine base indentation of its children",
    [
        "hello",
        "   % for x in range(0,2)",
        "   line <<x>>",
        "   %/for",
        "world"
    ],
    nf.program([
        nf.line('', [nf.literal("hello")]),
        nf.block('   ', 'for', 'x in range(0,2)', [
                nf.line('   ', [nf.literal("line "), nf.expr("x")])]),
        nf.line('', [nf.literal("world")])
    ]),
    Example(
        '',
        [
            "hello",
            "line 0",
            "line 1",
            "world\n"
        ],
        {}
    )
)


class IndentExample1(Component):
    template = """
    before body
    % body
    after body
    """


indent_component_1 = TestCase(
    "show how component children is indented by the indentation level of the component block",
    [
        "hello",
        "   % r Example()",
        "   body line 1",
        "      body line 2",
        "   %/r",
        "world"
    ],
    nf.program([
        nf.line('', [nf.literal("hello")]),
        nf.block('   ', 'r', 'Example()', [
                nf.line('   ', [nf.literal('body line 1')]),
                nf.line('      ', [nf.literal('body line 2')])
            ]),
        nf.line('', [nf.literal("world")])
    ]),
    Example(
        '',
        [
            "hello",
            "   before body",
            "   body line 1",
            "         body line 2",
            "   after body",
            "world\n"
        ],
        {'Example': IndentExample1}
    )
)


class IndentExampleComponent(Component):
    template = """
    before body
       % body
    after body
    """


# TODO: this is probably the hardest to grasp, but r-indent, body-indent and line-indent is all purely additive
indent_component_block_to_ctrl_line = TestCase(
    "show how a component-block's opening line determine base indentation of its children",
    [
        "hello",
        "   % r Example()",
        "   body line 1",
        "      body line 2",
        "   %/r",
        "world"
    ],
    nf.program([
        nf.line('', [nf.literal("hello")]),
        nf.block('   ', 'r', 'Example()', [
                nf.line('   ', [nf.literal("body line 1")]),
                nf.line('      ', [nf.literal("body line 2")])
            ]),
        nf.line('', [nf.literal("world")])
    ]),
    Example(
        '',
        [
            "hello",
            "   before body",
            "      body line 1",
            "         body line 2",
            "   after body",
            "world\n"
        ],
        {'Example': IndentExampleComponent}
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
    nf.program([
        nf.line('', [
            nf.literal("hello, "),
            nf.expr("thing"),
            nf.literal("!")]),

        nf.block('', 'for', 'x in y', [
                nf.line('', [nf.literal("something")]),
                nf.line('', [nf.literal("else")]),
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
