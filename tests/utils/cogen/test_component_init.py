from testlib.components.scope_init.comp2 import Comp2
from testlib.components.scope_init.comp1 import Comp1
from testlib.components.scope_init.comp0 import Comp0
from testlib.components.scope_init import sharedbuf
import typing as t


def test_init_order_and_arg_passing():
    # this test is ugly, but serves to ensure that all __init__ functions are called
    # and are called in order.
    #
    # Component Comp2 inherits from Comp1 which inherits from Comp0
    # Each component writes an entry into a shared buffer containing its name and the arguments received
    # by its __init__ function.
    #
    # Furthermore, not all arguments are passed along to the ancestor component.
    # This way, we are trying to test whether the RIGHT arguments are passed to each init function
    # as opposed to getting the same arguments at each level.
    sharedbuf.reset()

    def component_scope_keys(comp) -> t.Optional[t.Set[str]]:
        scope = getattr(comp, "__ghostwriter_component_scope__", None)
        if scope is None:
            return None
        return set(scope.keys())

    assert component_scope_keys(Comp2) == set(), "expected empty/uninitialized component scope"
    assert component_scope_keys(Comp1) == set(), "expected empty/uninitialized component scope"
    assert component_scope_keys(Comp0) == set(), "expected empty/uninitialized component scope"

    c2 = Comp2("c2arg")
    entries = sharedbuf.values()
    expected = [
        {"component": "comp2", "msg": "pre", "args": ["c2arg"]},
        {"component": "comp1", "msg": "pre", "args": ["comp2:fixed_arg"]},
        {"component": "comp0", "msg": "pre", "args": ["comp2:fixed_arg", "comp1:arg2"]},
        {"component": "comp0", "msg": "post"},
        {"component": "comp1", "msg": "post"},
        {"component": "comp2", "msg": "post"},
    ]
    assert entries == expected, \
        "call/init order or arg-passing issue. Either the order of messages or the args passed differ"

    # TODO: beware, only modules and components (including self) is in scope.
    assert component_scope_keys(Comp2) == {"Comp1", "Comp2", "sharedbuf"}, "Comp2 component scope"
    assert component_scope_keys(Comp1) == set(), "Comp1 should not be resolved yet (not yet initialized a component)"
    assert component_scope_keys(Comp0) == set(), "Comp0 should not be resolved yet (not yet initialized a component)"

    Comp1("smth")
    assert component_scope_keys(Comp1) == {"Comp1", "Comp0", "sharedbuf"}, "Comp1 scope not as expected"

    Comp0("", "")
    assert component_scope_keys(Comp0) == {"Comp0", "sharedbuf", "Component"}, "Comp0 scope not as expected"
