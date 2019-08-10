import pytest
from pyt.utils.template.dsl import *
from pyt.utils.template.dsl import(
    token_stream, TokenIterator,
    LineWriter, EvalContext, dsl_eval_main
)
from io import StringIO


def component_test(start_component: str, blocks=None, components=None, scope=None) -> str:
    buf = StringIO()

    ctx = EvalContext(
        LineWriter(buf),
        blocks=blocks or {},
        components=components or {})
    tokens = TokenIterator(token_stream((
        f"%{start_component}"
        f"%/{start_component}")))

    dsl_eval_main(ctx, tokens, Scope(scope or {}))
    return buf.getvalue()


class Outer(Component):
    TEMPLATE = """
    % MyFN
    print("hello, world")
    print("more...")
    % /MyFN
    print("done")"""


class MyFN(Component):
    @classmethod
    def _scope_(cls, scope: Scope, component_args: str) -> None:
        scope['args'] = ", ".join(scope['args'])

    TEMPLATE = """
    def <<name>>(<<args>>):
        print("<<name>> invoked")
        % body
        print("<<name>> invoked")"""


def test_c1():
    actual = component_test('Outer', components={
        'MyFN': MyFN,
        'Outer': Outer
    }, scope={
        'name': 'foo',
        'args': ['one', 'two', 'three']
    })
    expected = """\
def foo(one, two, three):
    print("foo invoked")
    print("hello, world")
    print("more...")
    print("foo invoked")
print("done")
"""
    print(actual)
    assert actual == expected, "failed to produce expected results"


class PyClass(Component):
    @classmethod
    def _scope_(cls, scope: Scope, component_args: str) -> None:
        scope['init_args'] = ", ".join((f"{arg}={defval or None}" for arg, defval in scope['args'].items()))
        scope['repr_args'] = ", ".join(arg + '={self.' + arg + '}' for arg in scope['args'].keys())

        parents = scope.get('from', None)
        scope['parents'] = f"({', '.join(parents)})" if parents else ''

    TEMPLATE = """
    class <<name>><<parents>>:
        def __init__(<<init_args>>):
            % for arg in args.keys()
            self.<<arg>> = <<arg>>
            % /for
        
        def __eq__(self, other):
            return (
                isinstance(other, self.__class__)
                % for arg in args.keys()
                and other.<<arg>> == self.<<arg>>
                % /for
            )

        def __ne__(self, other):
            return not self.__eq__(other)
        
        def __repr__(self):
            return f"<<name>>(<<repr_args>>)\""""


def test_pyclass_component():
    actual = component_test('Class', components={
        'Class': PyClass,
        'Outer': Outer
    }, scope={
        'name': 'CtrlToken',
        'args': {
            'prefix': '""',
            'token': 'TokenNone',
        },
        'from': ['Token']
    })
    expected = """\
class CtrlToken(Token):
    def __init__(prefix="", token=TokenNone):
        self.prefix = prefix
        self.token = token
    
    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and other.prefix == self.prefix
            and other.token == self.token
        )

    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return f"CtrlToken(prefix={self.prefix}, token={self.token})"
"""
    if actual != expected:
        print("-----Actual:")
        print(actual)
        print("-----Expected:")
        print(expected)
        print("-----")
    assert actual == expected, "failed to produce expected results"
