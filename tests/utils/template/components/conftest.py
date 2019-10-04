from ghostwriter.utils.template import Component
from ghostwriter.parser import Context
import sys
import pathlib as pl
from io import StringIO

sys.path.append(pl.Path(pl.Path(__file__).parent, 'shared').as_posix())


def snippet_eval(snippet) -> str:
    buf = StringIO()
    # snippet(ctx:Context, prefix:str, writer: IWriter)
    ctx = Context(None, "<no-src>", "<no-dest>")
    snippet(ctx, "", buf)
    return buf.getvalue()
