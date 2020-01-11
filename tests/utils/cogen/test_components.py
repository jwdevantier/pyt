import pytest
from testlib.bufferwriter import BufferWriter

from ghostwriter.parser import Context
from ghostwriter.utils.cogen.component import Component
from ghostwriter.utils.cogen.snippet import ComponentSnippet
from testlib.components import modulea


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
#
#
# def test_component_resolution_same_file():
#     """Ensure a component can automatically refer other components in the
#     same file by name."""
#
#     @snippet()
#     def main():
#         return modulea.ComponentResolutionSameFile()
#
#     assert snippet_eval(main) == "hi\n"
#
#
# def test_component_resolution_same_file_err():
#     """Ensure an error is raised when failing to render some component"""
#
#     @snippet()
#     def main():
#         return modulea.ComponentResolutionSameFileErr()
#
#     with pytest.raises(NameError) as exc_info:
#         snippet_eval(main)
#     assert 'DefinitelyNotExistingComponent' in str(exc_info.value)
#
#
# def test_component_resolution_different_file():
#     """Ensure a component can automatically refer to components in another
#     module."""
#
#     @snippet()
#     def main():
#         return modulea.ComponentResolutionViaModule()
#
#     assert snippet_eval(main) == "hi from module b\n"
#
#
# def test_attempt_render_non_component():
#     """Test to capture result of attempting to render a non-component"""
#
#     class MyComponent(Component):
#         def __init__(self, value):
#             self.value = value
#
#         template = """
#         something
#         % r self.value
#         % /r"""
#
#     @snippet()
#     def main():
#         return MyComponent({'one': 1})
#
#     with pytest.raises(DSLBlockRenderExpressionError) as exc_info:
#         snippet_eval(main)
#         pytest.fail("Expected an error")
#
#
# def test_rendering_initalized_component_instance():
#     """Test that a component can receive and render an already initialized
#     component instance."""
#
#     class Outer(Component):
#         def __init__(self, child: Component):
#             self.child = child
#
#         template = """
#         before
#         % r self.child
#         % /r
#         after"""
#
#     class Inner(Component):
#         def __init__(self, msg: str):
#             self.msg = msg
#
#         template = """
#         I say: <<self.msg>>"""
#
#     @snippet()
#     def main():
#         return Outer(child=Inner("hello"))
#
#     assert snippet_eval(main) == '\n'.join([
#         "before",
#         "I say: hello",
#         "after",
#         ""
#     ])
#
#
# def test_component_expr():
#     """
#     Test computing a (non-trivial) expression which yields a component
#     """
#
#     class HelloWorld(Component):
#         template = """
#         hello, world!"""
#
#     class Main(Component):
#         def __init__(self):
#             self.mydict = {
#                 'hello': HelloWorld
#             }
#             self.key = "olleh"
#
#         template = """
#         % r self.mydict[self.key[::-1]]()
#         %/r
#         """
#
#     @snippet()
#     def main():
#         return Main()
#
#     assert snippet_eval(main) == '\n'.join([
#         "hello, world!",
#         ""
#     ])
#
#
# def test_scoping_nesting_simple():
#     # tests that
#     # 1) the inner scope cannot affect the outer ('thing' isn't changed)
#     # 2) only explicitly passed variables are passed to the inner scope
#     @snippet()
#     def main():
#         return modulea.OuterScopeVar(thing='x')
#
#     assert snippet_eval(main) == '\n'.join([
#         "outer before: thing is x!",
#         "inner: thing is y!",
#         "inner: other is UNSET",
#         "outer after: thing is still x!",
#         ""  # trailing newline
#     ])
