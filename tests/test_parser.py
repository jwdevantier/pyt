# from pyt.parser import parser as p
from pyt.parser import *
import tempfile
from pyt.protocols import IWriter

tcode23 = """\
def foo():
    # <@garbage@>
    # <@/garbage@>
    print('all done!')"""


# def test_x():
#     #parser.read_file("/tmp/test-parse.py", "/tmp/test-parse.py.out")
#     parser.read_file(
#         "/tmp/test-parse.py",
#         None, # "/tmp/test-parse.py.out",
#         "<@@",
#         "@@>")
#     # TODO: re-test with out=None => tmp_file_path
#     # try:
#     #     parser.read_file("/tmp/test-parse.py", "/tmp/test-parse.py.out")
#     # except parser.PytError as e:
#     #     print("GOT PytError!!")


def expand_snippet(ctx: Context, out: IWriter):
    print(ctx)
    print(f"expand_snippet(env: {ctx.env}, out: {out}, snippet_name: {ctx.src}")
    out.write("hello, world")

def test_x():
    parser = Parser('<@@', '@@>')
    parser.parse(
        expand_snippet,
        "/tmp/test-parse.py",
        '/tmp/lolcat')
    print("PARSER")
    print(parser)
