from pyt.parser import parser
import tempfile

tcode23 = """\
def foo():
    # <@garbage@>
    # <@/garbage@>
    print('all done!')"""

def test_x():
    parser.read_file("/tmp/test-parse.py", "/tmp/test-parse.py.out")
    # try:
    #     parser.read_file("/tmp/test-parse.py", "/tmp/test-parse.py.out")
    # except parser.PytError as e:
    #     print("GOT PytError!!")