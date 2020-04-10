import pytest
from testlib.bufferwriter import BufferWriter
from testlib.components import modulea

from ghostwriter.utils.cogen.component import Component
from ghostwriter.utils.cogen.tokenizer import Tokenizer
from ghostwriter.utils.cogen.interpreter import Writer, interpret
from ghostwriter.utils.cogen.parser import CogenParser, Program
from ghostwriter.utils.iwriter import IWriter
from ghostwriter.parser.fileparser import Context, SnippetCallbackFn
from ghostwriter.utils.cogen.interpreter import RenderArgTypeError, InterpStackTrace


prog: Program = CogenParser(Tokenizer("""\
% r __main__
% /r""".lstrip())).parse_program()


class ComponentSnippet(SnippetCallbackFn):
    def __init__(self, component: Component, blocks = None):
        if not isinstance(component, Component):
            raise ValueError(f"component must be of instance component, got: '{type(component)}'")
        self.component = component
        self.blocks = blocks or {}

    def apply(self, ctx: Context, snippet: str, prefix: str, fw: IWriter):
        # TODO: could I use 'body' instead of '__main__' to avoid polluting scope?
        interpret(prog, Writer(fw), {}, {'__main__': self.component})


def snippet_eval(snippet: ComponentSnippet) -> str:
    ctx = Context(None, "<no-src>")
    buf = BufferWriter()
    snippet.apply(ctx, "", "", buf)
    return buf.getvalue()


def test_simple_component():
    """Test a minimal component"""

    class HelloWorld(Component):
        template = """
        hello, world!"""

    assert snippet_eval(ComponentSnippet(HelloWorld())) == "hello, world!\n"


@pytest.mark.parametrize("thing", ['world', 'mother'])
def test_component_arg(thing):
    """Ensure arguments can be passed to a component and that they are received"""

    class HelloThing(Component):
        def __init__(self, thing: str):
            self.thing = thing

        template = """
        hello, <<self.thing>>!"""

    assert snippet_eval(ComponentSnippet(HelloThing(thing))) == f"hello, {thing}!\n"


def test_component_resolution_same_file():
    """Ensure a component can automatically refer other components in the
    same file by name."""

    assert snippet_eval(ComponentSnippet(modulea.ComponentResolutionSameFile())) == "hi\n"


def test_component_resolution_same_file_err():
    """Ensure an error is raised when failing to render some component"""

    with pytest.raises(InterpStackTrace) as exc_info:
        snippet_eval(ComponentSnippet(modulea.ComponentResolutionSameFileErr()))
    assert 'DefinitelyNotExistingComponent' in str(exc_info.value)


def test_component_resolution_different_file():
    """Ensure a component can automatically refer to components in another
    module."""

    assert snippet_eval(ComponentSnippet(modulea.ComponentResolutionViaModule())) == "hi from module b\n"


def test_attempt_render_non_component():
    """Test to capture result of attempting to render a non-component"""

    class MyComponent(Component):
        def __init__(self, value):
            self.value = value

        template = """
        something
        % r self.value
        % /r"""

    with pytest.raises(RenderArgTypeError) as exc_info:
        snippet_eval(ComponentSnippet(MyComponent({'one': 1})))
        pytest.fail("Expected an error")


def test_rendering_initalized_component_instance():
    """Test that a component can receive and render an already initialized
    component instance."""

    class Outer(Component):
        def __init__(self, child: Component):
            self.child = child

        template = """
        before
        % r self.child
        % /r
        after"""

    class Inner(Component):
        def __init__(self, msg: str):
            self.msg = msg

        template = """
        I say: <<self.msg>>"""

    assert snippet_eval(ComponentSnippet(Outer(child=Inner("hello")))) == '\n'.join([
        "before",
        "I say: hello",
        "after",
        ""
    ])


def test_component_expr():
    """
    Test computing a (non-trivial) expression which yields a component
    """

    class HelloWorld(Component):
        template = """
        hello, world!"""

    class Main(Component):
        def __init__(self):
            self.mydict = {
                'hello': HelloWorld
            }
            self.key = "olleh"

        template = """
        % r self.mydict[self.key[::-1]]()
        %/r
        """

    assert snippet_eval(ComponentSnippet(Main())) == '\n'.join([
        "hello, world!",
        ""
    ])


def test_scoping_nesting_simple():
    # tests that
    # 1) the inner scope cannot affect the outer ('thing' isn't changed)
    # 2) only explicitly passed variables are passed to the inner scope

    assert snippet_eval(ComponentSnippet(modulea.OuterScopeVar(thing='x'))) == '\n'.join([
        "outer before: thing is x!",
        "inner: thing is y!",
        "inner: other is UNSET",
        "outer after: thing is still x!",
        ""  # trailing newline
    ])
