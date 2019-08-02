import pytest
from pyt.utils.template.dsl import *
from io import StringIO


# def test_smth():
#     out = gen_loop_iterator("lbl, val in smth['entry']", {
#         'smth': {'entry': [('one', 11), ('two', 22)]},
#         'nodetypes': [('one', 1), ('two', 2)]})
#     for env in out:
#         print(f"iter env: {env}")

# TODO: chars should be keys from 'prop.tokens'
# TODO: should define proptypes somewhere, including required
# TODO: establish convention for calling

# TODO: fix - how to ensure blocks are rendered with the right component lookup env
# Component render should get Scope(?) and props and should return 'str'
# which is the template to be rendered
#
# prop-renderer fns should be on the component class
# static initialization can be done w. statements inside the class definition
# ALL functions should be @staticmethod
#
# prop-renderer: _prop_<>(props: Props) -> t.Any
#
# schemas:
#   props_spec(input: Props) -> <<SPEC OUTPUT>>
#   scope_spec(input: Scope) -> <<SPEC OUTPUT>>


class Outer(Component):
    TEMPLATE = """
    % MyFN
    print("hello, world")
    print("more...")
    % /MyFN
    end of world"""


class MyFN(Component):
    @classmethod
    def _scope_(cls, scope: Scope, component_args: str) -> None:
        scope['args'] = ", ".join(scope['args'])

    TEMPLATE = """
    def <<name>>(<<args>>):
        print("<<name>> invoked")

        % body
        print("<<name>> invoked")"""


def test_xms():
    buf = StringIO()
    # TODO: some form of type coercion here ?
    ctx = EvalContext(LineWriter(buf), blocks={}, components={
        'MyFN': MyFN,
        'Outer': Outer
    })
    tokens = TokenIterator(token_stream((
        "%Outer"
        "%/Outer"
    )))
    scope = Scope({
        'name': 'foo',
        'args': ['one', 'two', 'three']
    })
    dsl_eval_main(ctx, tokens, scope)
    actual = buf.getvalue()
    print(actual)
    assert actual == "<some-res>", f"failed to produce expected result"
