from re import escape as re_escape
from re import compile as re_compile


class Tags:
    def __init__(self, prefix: str = r"@@"):
        self._lang_rgx = re_compile(r".*{}begin:\s*(?P<lang>[a-zA-Z]+)\s*".format(re_escape(prefix)))
        self.begin = f"{prefix}begin:"
        self.out = f"{prefix}out"
        self.end = f"{prefix}end"

    def snippet_lang(self, line):
        m = self._lang_rgx.match(line)
        if not m and self.begin in line:
            raise RuntimeError(f"regex failed - lang name is unsupported")
        return m.group('lang')
