import pytest
from ghostwriter.utils.cogen.tokenizer import (
    Tokenizer,
    PyTokenFactory as TokenFactory
)

NL = TokenFactory.newline()
EOF = TokenFactory.eof()


@pytest.mark.parametrize("msg, prog, toks", [
    ("simple literal",
     "hello", [
         TokenFactory.literal('hello')
     ]),

    ("literal line",
     "hello\n", [
         TokenFactory.literal('hello'),
         NL
     ]),

    ("two literal lines",
     "hello\nworld", [
         TokenFactory.literal("hello"),
         NL,
         TokenFactory.literal("world")
     ]),

    # literals + exprs
    ("literal line with trailing expr",
     "hello <<world>>", [
         TokenFactory.literal('hello '),
         TokenFactory.expr('world')
     ]),

    ("literal line with expr",
     "hello, <<free>> world", [
         TokenFactory.literal("hello, "),
         TokenFactory.expr("free"),
         TokenFactory.literal("world")
     ]),

    ("leading expr",
     "<<thing>>", [
         TokenFactory.expr("thing")
     ]),

    # control lines
    ("control keyword",
     "%for", [TokenFactory.ctrl_kw('for')]),

    ("control keyword - whitespace suffix",
     "%for ", [TokenFactory.ctrl_kw('for')]),

    ("control keyword - whitespace prefix",
     "  %for ", [TokenFactory.ctrl_kw('for')]),

    ("control keyword - whitespace between '%' and keyword",
     "% for ", [TokenFactory.ctrl_kw('for')]),

    ("control keyword, newline",
     "%for\n", [TokenFactory.ctrl_kw('for'), NL]),

    ("control keyword - with args",
     "%for x in [1,2,3,4]",
     [TokenFactory.ctrl_kw('for'), TokenFactory.ctrl_args('x in [1,2,3,4]')]),

    ("control keyword - no args",
     '\n'.join([
         "% foo",
         "hello",
         "% /foo"
     ]), [TokenFactory.ctrl_kw('foo'),
          NL,
          TokenFactory.literal('hello'),
          NL,
          TokenFactory.ctrl_kw('/foo')]),

    ("escaped control string (=> literal)",
     "%% literal", [TokenFactory.literal('% literal')]),

    ("small program",
     '\n'.join([
         "hello <<thing>>",
         "%for x in [1,2,3]",
         "<<x>>!",
         "%/for"]),
     [TokenFactory.literal("hello "),
      TokenFactory.expr("thing"),
      NL,
      TokenFactory.ctrl_kw('for'),
      TokenFactory.ctrl_args('x in [1,2,3]'),
      NL,
      TokenFactory.expr('x'),
      TokenFactory.literal('!'),
      NL,
      TokenFactory.ctrl_kw('/for')])
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
