import pytest
from pyt.utils.template.scope import Scope


def test_scope_init():
    e = Scope()
    with pytest.raises(KeyError):
        e['hello']
    assert len(e) == 0, "env should have no entries it"
    assert list(iter(e)) == [], "env should be empty"


def test_scope_get_simple():
    """
    Test getting values in the scope itself, no outer scopes
    """
    e = Scope()
    with pytest.raises(KeyError):
        e['foo']

    e._data['foo'] = 'hello'
    assert e['foo'] == 'hello'

    e._data['foo'] = 'world'
    assert e['foo'] == 'world'


def test_scope_set_simple():
    """
    Test setting values in the scope itself, no outer scopes
    """
    e = Scope()
    with pytest.raises(KeyError):
        e['foo']

    e['foo'] = 'hello'
    assert e._data['foo'] == 'hello'

    e['foo'] = 'world'
    assert e._data['foo'] == 'world'


def test_scope_get_set_simple():
    """
    Test getting and setting values in the scope itself, no outer scopes
    """
    e = Scope()
    with pytest.raises(KeyError):
        e['foo']

    e['foo'] = 'hello'
    assert e['foo'] == 'hello'

    e['foo'] = 'world'
    assert e['foo'] == 'world'


def test_scope_len_simple():
    """
    Test ability to count number of entries in scope
    """
    s = Scope()
    assert len(s) == 0, "should be empty initially"
    for i in range(1, 4):
        s[f"key{i}"] = i
        assert len(s) == i, f"should have exactly {i} elements now"


def test_scope_nested_init():
    """
    Ensure new scope correctly refers to their outer scopes
    """
    s1 = Scope()

    s2 = Scope(outer=s1)
    assert s2._outer == s1, "s1 should be the parent of s2 (__init__ method)"


def test_scope_get_outer():
    """Ensure a child scope can resolve values contained in the parent."""
    s1 = Scope()
    s1['foo'] = 'val1'

    assert s1['foo'] == 'val1', "sanity test failed"

    s2 = Scope(outer=s1)
    assert s2['foo'] == 'val1', "(constructor) s2 should resolve 'foo' by passing request to parent (s1)"


def test_scope_set_define_outer():
    """Ensure values first set (i.e. defined) in an inner scope aren't available to the outer scope"""
    s1 = Scope()
    s1['foo'] = 'fooval'
    assert s1['foo'] == 'fooval', 'sanity test - get is broken'

    s2 = Scope(outer=s1)
    s2['bar'] = 'barval'

    assert s2['bar'] == 'barval', '(init) sanity test, s2 is broken!?'
    with pytest.raises(KeyError):
        s1['bar']
        pytest.fail(f"(init) s1 should be unable to resolve entry defined in s2")


def test_scope_set_update_outer():
    """Ensure values defined in an outer scope can be updated from an inner scope

    (i.e. - we are NOT practicing lexical binding)"""
    s1 = Scope()
    s2 = Scope(outer=s1)

    s1['foo'] = 'fooval'
    assert s1['foo'] == 'fooval', f'sanity test, get is broken'
    s2['foo'] = 'fooval_s2'
    assert s2['foo'] == 'fooval_s2', f'sanity test, setting in inner env broken'
    assert s1['foo'] == 'fooval_s2', f'e1 entry not updated - error!'


def test_in_simple():
    s = Scope()
    vals = {
        'foo': 'foo-val',
        'bar': 'bar-val',
        'baz': 'baz-val'
    }
    for ident, val in vals.items():
        s._data[ident] = val
        print(f"'{ident}' in scope?: '{ident in s}'")
        assert ident in s, f"expected '{ident}' to be found in scope"

    for ident in ['not1', 'BAR']:
        assert ident not in s, f"identifier '{ident}' should not be found in scope"


def test_in_nested():
    s1 = Scope()
    s1_vals = {
        'foo': 'foo-val',
        'bar': 'bar-val',
        'baz': 'baz-val'
    }
    for ident, val in s1_vals.items():
        s1[ident] = val

    s2 = Scope(outer=s1)
    s2_vals = {
        'foobar': 'foobar-val'
    }
    for ident, val in s2_vals.items():
        s2[ident] = val

    keys = set()
    keys.update(s1_vals.keys())
    keys.update(s2_vals.keys())
    for ident in keys:
        assert ident in s2, f"expected '{ident}' to be defined in s2, indirectly or otherwise"


# TODO: test  len
# TODO: test iter()

def test_scope_define():
    s1 = Scope()
    vals = {
        'one': 'a',
        'two': 'b',
        'three': 'c'
    }
    for ident, val in vals.items():
        s1[ident] = val

    s2 = Scope(outer=s1)
    for ident, val in vals.items():
        s2.define({k: v + "!" for k, v in vals.items()})

    for ident in vals.keys():
        assert s1[ident] + "!" == s2[ident]


def test_scope_del_simple():
    s1 = Scope()
    s1['one'] = 'a'
    assert s1['one'] == 'a', "sanity test failed"

    del s1['one']
    with pytest.raises(KeyError):
        s1['one']
        pytest.fail("accessing 'one' did not raise KeyError ?")


def test_scope_del_nested():
    s1 = Scope()
    s1['one'] = 'a'
    assert s1['one'] == 'a', "sanity test failed"

    s2 = Scope(outer=s1)
    print(repr(s2))
    del s2['one']
    with pytest.raises(KeyError):
        s1['one']
        pytest.fail(f"accessing 'one' did not raise a KeyError - entry should've been deleted")