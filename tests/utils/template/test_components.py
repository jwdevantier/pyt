import pytest
from ghostwriter.utils.template.dsl import *
from ghostwriter.utils.template.dsl import (
    token_stream, TokenIterator,
    LineWriter, EvalContext, dsl_eval_main
)

from io import StringIO
import typing as t


# TODO: need to rewrite helper here - must pass args, so let's refactor to
#       take in a program instead of just a component name.
def component_test(prog: str, blocks=None, scope=None) -> str:
    buf = StringIO()

    ctx = EvalContext(
        LineWriter(buf),
        blocks=blocks or {})
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
    % r MyFN(self.fn_name, self.fn_args)
    print("hello, world")
    print("more...")
    % /r
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
    scope = {
        'name': 'foo',
        'args': ['one', 'two', 'three'],
        # 'MyFN': MyFN, # -- will be in scope when calling 'Outer'
        'Outer': Outer
    }
    prog = """\
%r Outer(name, args)
%/r"""
    print("Component: '", getattr(MyFN, '__ghostwriter_component__', 'NOPE'),  "'")
    print("Component Scope: '", getattr(MyFN, '__ghostwriter_component_scope__', 'NOPE'), "'")
    actual = component_test(prog, scope=scope)
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
    scope = {
        'Class': PyClass,
        'name': 'CtrlToken',
        'args': {
            'prefix': '""',
            'token': 'TokenNone',
        },
        'parents': ['Token']
    }
    prog = """\
%r Class(name=name, args=args, parents=parents)
%/r"""
    actual = component_test(prog, scope=scope)
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
