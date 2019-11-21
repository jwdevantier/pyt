import pytest
from ghostwriter.utils.cogen.tokenizer import *

EOF = EndOfFile()
NL = Newline()


@pytest.mark.parametrize("msg, prog, toks", [
    ("simple literal",
     "hello", [Literal('hello')]),
    ("literal line",
     "hello\n", [Literal('hello'), NL]),
    ("two literal lines",
     "hello\nworld", [Literal("hello"), NL, Literal("world")]),

    # literals + exprs
    ("literal line with trailing expr",
     "hello <<world>>", [Literal('hello '), Expr('world')]),
    ("literal line with expr",
     "hello, <<free>> world", [
        Literal("hello, "),
        Expr("free"),
        Literal("world")
    ]),
    ("leading expr",
     "<<thing>>", [Expr("thing")]),

    # control lines
    ("control keyword",
     "%for", [CtrlKw('for')]),
    ("control keyword - whitespace suffix",
     "%for ", [CtrlKw('for')]),
    ("control keyword - whitespace prefix",
     "  %for ", [CtrlKw('for')]),
    ("control keyword - whitespace between '%' and keyword",
     "% for ", [CtrlKw('for')]),
    ("control keyword, newline",
     "%for\n", [CtrlKw('for'), NL]),

    ("control keyword - with args",
     "%for x in [1,2,3,4]",
     [CtrlKw('for'), CtrlArgs('x in [1,2,3,4]')]),
    ("control keyword - no args",
     '\n'.join([
         "% foo",
         "hello",
         "% /foo"
     ]), [CtrlKw('foo'),
          NL,
          Literal('hello'),
          NL,
          CtrlKw('/foo')]),

    ("escaped control string (=> literal)",
     "%% literal", [Literal('% literal')]),

    ("small program",
     '\n'.join([
        "hello <<thing>>",
        "%for x in [1,2,3]",
        "<<x>>!",
        "%/for"]),
     [Literal("hello "),
      Expr("thing"),
      NL,
      CtrlKw('for'),
      CtrlArgs('x in [1,2,3]'),
      NL,
      Expr('x'),
      Literal('!'),
      NL,
      CtrlKw('/for')])
])
def test_tokenizer(msg, prog, toks):
    p = Tokenizer(prog)
    actual_toks = []
    i = 0
    while True:
        tok = p.next()
        i += 1
        if i > 100:
            raise RuntimeError("infinite loop prevention")
        if tok == EOF:
            break
        actual_toks.append(tok)
    assert actual_toks == toks, msg
