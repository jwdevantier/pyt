from pyt.parser import *
import tempfile
from pyt.protocols import IWriter
from io import open as io_open
import pytest
import os
import filecmp


# TODO test:
#  (err) mismatched snippet tags
#  (err) unclosed snippet
#  (err) initial closing tag
#  in-place writing tests -- should produce non-empty files
#  test expansion where contents change (ensures we aren't copy-pasting all input)


# TODO: enhance test information:
#   don't use filecmp.cmp -> bool, load contents into lines and cmp these - pytest will provide more context
#   accompany each 'program' with a text to display if the assert fails

@pytest.fixture
def tmpfile():
    file_handles = []
    REMOVE_FILES = False  # TODO: true when no longer debugging, this will litter the HDD

    def _tmpfile(*args, **kwargs):
        """
        Generate and open temporary file using ``io.open``

        ```
        with io.open(filename, 'w', encoding='utf8') as f:
            f.write(text)
        ```

        Parameters
        ----------
        args : list
            arguments to ``io.open``
        kwargs : dict
            keyword arguments to ``oi.open``

        Returns
        -------
            The open file  handle
        """
        with tempfile.NamedTemporaryFile(prefix='test_parser', suffix='.tmp', delete=False) as tmp:
            fpath = tmp.name
        fh = io_open(fpath, *args, **kwargs)
        file_handles.append(fh)
        return fh

    try:
        yield _tmpfile
    finally:

        for fh in file_handles:
            file_path = fh.name
            try:
                fh.close()
            except:
                pass
            try:
                os.remove(file_path) if REMOVE_FILES else '<noop>'
            except:
                pass


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
    ("utf8", prog_multiple_single_line_snippets),
    ("utf8", prog_multiple_inline_writes),
    ("utf8", prog_multiline_snippet),
])
def test_file_parsing(tmpfile, mode, contents):
    """
    Test that the parser can process some input file and, provided it has no
    snippets or those snippets have already been expanded, write out the exact
    same contents.
    """
    with tmpfile("w", encoding=mode) as expected:
        expected.write(contents)
        expected.flush()
        expected_name = expected.name
        print(f"expected at '{expected.name}' (encoding={mode})")
    with tmpfile('w', encoding=mode) as actual:
        actual_name = actual.name

    parser = Parser('<@@', '@@>')
    parser.parse(
        expand_snippet,
        expected_name,
        actual_name)
    print(f"'{expected_name}' => '{actual_name}'")
    assert filecmp.cmp(expected_name, actual_name, shallow=False)
