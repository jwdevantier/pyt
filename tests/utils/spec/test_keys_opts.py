import pytest
from ghostwriter.utils import spec as s


@pytest.mark.parametrize("value, conformed", [
    ({1: "something"}, {1: "something", 2: "<default>"}),
    ({3: "smth else"}, {1: None, 2: "<default>", 3: "smth else"})
])
def test_keys_handling_opt_specs_properly(value, conformed):
    """
    When a key entry is an opt-value with a default, that default should be used.

    When a key entry is an opt-value without a default, the entry will be None.

    """
    spec = s.keys({
        1: s.opt(s.str),
        2: s.opt(s.str, "<default>")})
    assert conformed == s.conform(spec, value)