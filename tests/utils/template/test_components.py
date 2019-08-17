import pytest
from pyt.utils.template.dsl import *
from pyt.utils.template.dsl import (
    token_stream, TokenIterator,
    LineWriter, EvalContext, dsl_eval_main
)
from io import StringIO
import typing as t


# TODO: need to rewrite helper here - must pass args, so let's refactor to
#       take in a program instead of just a component name.
def component_test(prog: str, blocks=None, components=None, scope=None) -> str:
    buf = StringIO()

    ctx = EvalContext(
        LineWriter(buf),
        blocks=blocks or {},
        components=components or {})
    tokens = TokenIterator(token_stream(prog))

    dsl_eval_main(ctx, tokens, Scope(scope or {}))
    return buf.getvalue()


class Outer(Component):
    def __init__(self, fn_name, fn_args):
        self.fn_name = fn_name
        self.fn_args = fn_args

    @property
    def template(self) -> str:
        return """
    % MyFN self.fn_name, self.fn_args
    print("hello, world")
    print("more...")
    % /MyFN
    print("done")"""


class MyFN(Component):
    def __init__(self, name: str, args: t.List[str]):
        self.name = name
        self.args = ', '.join(args)

    @property
    def template(self) -> str:
        return """
    def <<self.name>>(<<self.args>>):
        print("<<self.name>> invoked")
        % body
        print("<<self.name>> invoked")"""


def test_c1():
    components = {
        'MyFN': MyFN,
        'Outer': Outer
    }
    scope = {
        'name': 'foo',
        'args': ['one', 'two', 'three']
    }
    prog = """\
%Outer name, args
%/Outer"""
    actual = component_test(prog, components=components, scope=scope)
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
    def __init__(self, name: str, args: t.Mapping[str, t.Any], parents=None):
        self.name = name
        self.args = args
        self.init_args = ", ".join((
            f"{arg}={defval or None}" for arg, defval
            in args.items()))
        self.repr_args = ", ".join(arg + '={self.' + arg + '}' for arg
                                   in args.keys())
        self.parents = f"({', '.join(parents)})" if parents else ''

    @property
    def template(self) -> str:
        return """\
    class <<self.name>><<self.parents>>:
        def __init__(<<self.init_args>>):
            % for arg in self.args.keys()
            self.<<arg>> = <<arg>>
            % /for
        
        def __eq__(self, other):
            return (
                isinstance(other, self.__class__)
                % for arg in self.args.keys()
                and other.<<arg>> == self.<<arg>>
                % /for
            )

        def __ne__(self, other):
            return not self.__eq__(other)
        
        def __repr__(self):
            return f"<<self.name>>(<<self.repr_args>>)\""""


def test_pyclass_component():
    components = {
        'Class': PyClass
    }
    scope = {
        'name': 'CtrlToken',
        'args': {
            'prefix': '""',
            'token': 'TokenNone',
        },
        'parents': ['Token']
    }
    prog = """\
%Class name=name, args=args, parents=parents
%/Class"""
    actual = component_test(prog, components=components, scope=scope)
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
