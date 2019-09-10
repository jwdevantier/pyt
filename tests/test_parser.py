from ghostwriter.parser import *
from ghostwriter.protocols import IWriter
from ghostwriter.cli.compile import parse_snippet_name

import pytest
import filecmp

# TODO test:
#  test expansion where contents change (ensures we aren't copy-pasting all input)
#  also, if strict on whiteline - write tests showcasing this


# TODO: enhance test information:
#   don't use filecmp.cmp -> bool, load contents into lines and cmp these - pytest will provide more context
#   accompany each 'program' with a text to display if the assert fails

prog_noop_file = """\
def foo():
    print("time goes on.")
"""

prog_noop_utf8_only = """\
def foo():
    '''
    This function is useless \U0001f604
    '''
    print("time goes by")
"""

# Test that a newline is added to ensure snippet tags remain on separate lines
# - would fail if no code ensures there are newlines between the snippet tags
prog_empty_snippet = """\
def foo():
    print("before")
    # <@@empty_snippet@@>
    # <@@/empty_snippet@@>
    print("after")
"""

# Test that a single, single-line snippet can be expanded
# - would fail if encoding of snippet expansion lines is handled wrongly or so
prog_single_snippet = """\
def foo():
    print("before")
    # <@@snippet1@@>
    hello from snippet1
    # <@@/snippet1@@>
    print("after")
"""

prog_single_snippet_noindent = """\
more
smth

<@@snippet1@@>
hello from snippet1
<@@/snippet1@@>
"""

# Test ensuring that multiple snippets can be expanded
prog_multiple_single_line_snippets = """\
def foo():
    print("before snippet1")
    # <@@snippet1@@>
    hello from snippet1
    # <@@/snippet1@@>
    print("before snippet2")
    # <@@snippet2@@>
    hello from snippet2
    # <@@/snippet2@@>
"""

prog_multiple_inline_writes = """\
def foo():
    print("before snippet1")
    # <@@multiple_inline_writes@@>
    1, 2, 3
    # <@@/multiple_inline_writes@@>
    print("after")
"""

prog_multiline_snippet = """\
def foo():
    print("before snippet1")
    # <@@multiline_snippet@@>
    1
    2
    3
    # <@@/multiline_snippet@@>
    print("after")
"""

prog_err_expected_open = """\
def foo():
    #<@@/snippet1@@>
    hello from snippet1
    #<@@snippet1@@>
    something else
    #<@@snippet2@@>
    hello from snippet 2
    #<@@/snippet2@@>"""

prog_err_expected_close = """\
def foo():
    #<@@snippet1@@>
    hello from snippet1
    #<@@snippet1@@>
    something else
    #<@@snippet2@@>
    hello from snippet 2
    #<@@/snippet2@@>"""

prog_err_mismatched_snippets = """\
def foo():
    #<@@snippet1@@>
    hello from snippet1
    #<@@/snippet2@@>
    something else
    #<@@snippet2@@>
    hello from snippet 2
    #<@@/snippet2@@>"""

SNIPPETS = {}


def snippet(fn):
    SNIPPETS[fn.__name__] = fn
    return fn


@snippet
def snippet1(ctx: Context, prefix: str, out: IWriter):
    out.write(f"{prefix}hello from snippet1")


@snippet
def snippet2(ctx: Context, prefix: str, out: IWriter):
    out.write(f"{prefix}hello from snippet2")


@snippet
def empty_snippet(ctx: Context, prefix: str, out: IWriter):
    pass


@snippet
def multiple_inline_writes(ctx: Context, prefix: str, out: IWriter):
    out.write(f"{prefix}1")
    out.write(", 2")
    out.write(", 3")


@snippet
def multiline_snippet(ctx: Context, prefix: str, out: IWriter):
    out.write(f"{prefix}1\n")
    out.write(f"{prefix}2\n")
    out.write(f"{prefix}3\n")


def expand_snippet(ctx: Context, snippet: str, prefix: str, out: IWriter):
    print("EXPAND")
    SNIPPETS[snippet](ctx, prefix, out)


# TODO: instead of filecmp, simply load file contents into strings, pytest should diff them nicely.
@pytest.mark.parametrize("mode, contents", [
    ("ascii", prog_noop_file),
    ("utf8", prog_noop_file),
    #
    ("utf8", prog_noop_utf8_only),
    # ("utf16", prog_noop_file) # TODO: broken, encoding not detected, cannot write / set UTF16 write mode

    ("utf8", prog_empty_snippet),
    ("utf8", prog_single_snippet),
    ("utf8", prog_single_snippet_noindent),
    ("utf8", prog_multiple_single_line_snippets),
    ("utf8", prog_multiple_inline_writes),
    ("utf8", prog_multiline_snippet),
])
def test_write_otherfile_ok(tmpfile, mode, contents):
    """
    Test that the parser can process some input file and, provided it has no
    snippets or those snippets have already been expanded, write out the exact
    same contents.
    """
    with tmpfile("w", encoding=mode) as input_contents:
        input_contents.write(contents)
        input_contents.flush()
        input_fname = input_contents.name
    with tmpfile('w', encoding=mode) as actual:
        output_fname = actual.name

    parser = Parser('<@@', '@@>')
    parse_res = parser.parse(
        expand_snippet,
        input_fname,
        output_fname)
    print(f"'{input_fname}' => '{output_fname}'")
    assert parse_res == PARSE_OK, "expected a successful parse"
    assert filecmp.cmp(input_fname, output_fname, shallow=False)


@pytest.mark.parametrize("contents, errcode", [
    (prog_err_expected_open, PARSE_EXPECTED_SNIPPET_OPEN),
    (prog_err_expected_close, PARSE_EXPECTED_SNIPPET_CLOSE),
    (prog_err_mismatched_snippets, PARSE_SNIPPET_NAMES_MISMATCH),
])
def test_write_otherfile_errs(tmpfile, contents, errcode):
    """
    Test that the parser correctly identifies and flag errors pertaining to the
    wrong use of snippet tags. Such as encountering a close snippet before an
    opening snippet, multiple open snippet tags (e.g. nesting of snippet tags)
    or snippet tags whose names do not match.
    """
    with tmpfile("w", encoding="utf8") as input_contents:
        input_contents.write(contents)
        input_contents.flush()
        input_fname = input_contents.name
    with tmpfile('w', encoding="utf8") as actual:
        output_fname = actual.name

    parser = Parser('<@@', '@@>')
    retval = parser.parse(
        expand_snippet,
        input_fname,
        output_fname)
    assert retval == errcode, "expected different parser return code"


@pytest.mark.parametrize("contents", [
    prog_noop_file,
    prog_noop_utf8_only,
    prog_empty_snippet,
    prog_single_snippet,
    prog_multiple_single_line_snippets,
    prog_multiple_inline_writes,
    prog_multiline_snippet,
])
def test_write_inplace_ok(tmpfile, contents):
    with tmpfile("w", encoding="utf8") as input_contents:
        input_contents.write(contents)
        input_contents.flush()
        input_fname = input_contents.name
    parser = Parser('<@@', '@@>')
    retval = parser.parse(
        expand_snippet,
        input_fname,
        None)
    assert retval == PARSE_OK, "expected parsing to work"

    with open(input_fname) as fh:
        actual_contents = fh.read()
    print(f"out: {input_fname}")
    assert contents == actual_contents, "parsing failed"


@pytest.mark.parametrize("contents", [
    prog_err_expected_open,
    prog_err_expected_close,
    prog_err_mismatched_snippets,
])
def test_write_inplace_errs(tmpfile, contents):
    with tmpfile("w", encoding="utf8") as input_contents:
        input_contents.write(contents)
        input_contents.flush()
        input_fname = input_contents.name
    parser = Parser('<@@', '@@>')
    retval = parser.parse(
        expand_snippet,
        input_fname,
        None)
    assert retval != PARSE_OK, "expected parsing to fail"

    with open(input_fname) as fh:
        actual_contents = fh.read()
    print(f"out: {input_fname}")
    assert contents == actual_contents, "parsing failed"


@pytest.mark.parametrize("snippet_fqn, module, fn", [
    ("snippet", "<none>", "snippet"),
    ("module.snippet", "module", "snippet"),
    ("package.module.snippet", "package.module", "snippet"),
    ("package.module.snippet ", "package.module", "snippet"),
    (" package.module.snippet", "package.module", "snippet")
])
def test_parse_snippet_name(snippet_fqn, module, fn):
    act_module, act_fn = parse_snippet_name(snippet_fqn)
    assert act_module == module and act_fn == fn, "parsing snippet name failed"
