import pytest
from ghostwriter.parser.tags import Tags


@pytest.mark.parametrize(
    "line,prefix,valid",
    [("/* @@begin: poodles", "@@", True),
     ("/* @@begin:poodles", "@@", True),
     ("//@@begin:", "@@", True),
     ("// @@begin:", "@@", True),

     ("// @@begin :", "@@", False),
     ("// @@ begin:", "@@", False),

     # same tests, just using '!--' as prefix

     ("/* !--begin: poodles", "!--", True),
     ("/* !--begin:poodles", "!--", True),
     ("//!--begin:", "!--", True),
     ("// !--begin:", "!--", True),

     ("// !--begin :", "!--", False),
     ("// !-- begin:", "!--", False)
     ]
)
def test_tags_begin(line, prefix, valid):
    t = Tags(prefix=prefix)
    if valid:
        assert t.begin in line, "unexpected failure"
    else:
        assert t.begin not in line, "unexpected match"


@pytest.mark.parametrize(
    "line,prefix,lang",
    [("/* @@begin: poodles", "@@", "poodles"),
     ("/* @@begin:poodles", "@@", "poodles"),
     ("//@@begin: py", "@@", "py"),
     ("// @@begin:py", "@@", "py"),

     # same tests, just using '-*-' as prefix

     ("/* -*-begin: poodles", "-*-", "poodles"),
     ("/* -*-begin:poodles", "-*-", "poodles"),
     ("//-*-begin: py", "-*-", "py"),
     ("// -*-begin:py", "-*-", "py")
     ]
)
def test_tags_begin_lang(line, prefix, lang):
    t = Tags(prefix=prefix)
    assert t.snippet_lang(line) == lang, f"unexpected lang"


@pytest.mark.parametrize(
    "line,prefix,valid",
    [("@@out", "@@", True),
     ("/* @@out", "@@", True),
     ("* @@out */", "@@", True),
     ("* @@out*/", "@@", True),
     ("* @@outt*/", "@@", True),

     ("// @@ out", "@@", False),

     # same tests, just using '!--' as prefix
     ("!--out", "!--", True),
     ("/* !--out", "!--", True),
     ("* !--out */", "!--", True),
     ("* !--out*/", "!--", True),
     ("* !--outt*/", "!--", True),

     ("// !-- out", "!--", False),
    ]
)
def test_tags_out(line, prefix, valid):
    t = Tags(prefix=prefix)
    if valid:
        assert t.out in line, "unexpected failure"
    else:
        assert t.out not in line, "unexpected match"


@pytest.mark.parametrize(
    "line,prefix,valid",
    [("@@end", "@@", True),
     ("/* @@end", "@@", True),
     ("* @@end */", "@@", True),
     ("* @@end*/", "@@", True),
     ("* @@endt*/", "@@", True),

     ("// @@ replace", "@@", False),

     # same tests, just using '!--' as prefix
     ("¤¤end", "¤¤", True),
     ("/* ¤¤end", "¤¤", True),
     ("* ¤¤end */", "¤¤", True),
     ("* ¤¤end*/", "¤¤", True),
     ("* ¤¤endt*/", "¤¤", True),

     ("// ¤¤ replace", "¤¤", False)]
)
def test_tags_end(line, prefix, valid):
    t = Tags(prefix=prefix)
    if valid:
        assert t.end in line, "unexpected failure"
    else:
        assert t.end not in line, "unexpected match"
