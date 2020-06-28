# works, suspect it's a Cython-related issue
from .fileparser import (
    Parser, Context, GhostwriterError, ParseError, SnippetError, SnippetCallbackFn)

# Must match actual definitions in fileparser
PARSE_OK = 0
PARSE_READ_ERR = 1
PARSE_WRITE_ERR = 2
PARSE_EXPECTED_SNIPPET_OPEN = 3
PARSE_EXPECTED_SNIPPET_CLOSE = 4
PARSE_SNIPPET_NAMES_MISMATCH = 5
