from io import StringIO
import attr
import typing as t
from typing_extensions import Protocol
from ghostwriter.utils.iwriter import IWriter


# Minimal writer inspired by PicoCog
# https://github.com/ainslec/picocog/blob/master/src/main/java/org/ainslec/picocog/PicoWriter.java


@attr.s(frozen=True)
class Newline:
    indents = attr.ib(type=int)


_indent_cache: t.Dict[int, Newline] = {}


class Section(Protocol):
    def render(self, out: IWriter) -> None:
        ...


WriterElement = t.Union[Section, str, Newline]


def natint(_, attribute, value):
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{attribute.name} has to be a natural integer")


@attr.s
class Writer:
    _prefix = attr.ib(default='', type=str)
    # base indentation level for the whole block
    _indents = attr.ib(init=False, default=0, type=int, validator=natint)
    # add this as prefix when indenting lines
    _indent_by = attr.ib(default=' ', type=str)
    # all the written content
    _content = attr.ib(init=False, type=t.List[WriterElement], factory=list)
    # temporary buffer - holds at most a single line
    _buf = attr.ib(init=False, repr=False, factory=StringIO)

    def indent(self):
        self._indents += 1

    def dedent(self):
        if self._indents > 0:
            self._indents -= 1
        else:
            raise RuntimeError("cannot dedent past initial indentation level")

    def __newline(self):
        indents = self._indents
        if indents not in _indent_cache:
            nl = Newline(indents)
            _indent_cache[indents] = nl
            return nl
        return _indent_cache[indents]

    def __flush(self):
        self._content.extend([self.__newline(), self._buf.getvalue()])
        self._buf = StringIO()

    def write(self, s):
        self._buf.write(s)

    def writeln(self, s):
        self._buf.write(s)
        self.__flush()

    def writeln_r(self, s):
        self._buf.write(s)
        self.__flush()
        self._indents += 1

    def writeln_l(self, s):
        self._indents -= 1
        if self._indents < 0:
            raise RuntimeError("cannot dedent past initial indentation level")
        self._buf.write(s)
        self.__flush()

    def writeln_lr(self, s):
        self._indents -= 1
        if self._indents < 0:
            raise RuntimeError("cannot dedent past initial indentation level")
        self._buf.write(s)
        self.__flush()
        self._indents += 1

    def section(self) -> "Writer":
        self.__flush()
        w = Writer(
            prefix=self._prefix + self._indent_by * self._indents,
            indent_by=self._indent_by)
        self._content.append(w)
        return w

    # Union to avoid spurious type warnings
    def render(self, buf: t.Union[IWriter, StringIO]) -> None:
        if self._buf.tell() != 0:
            self.__flush()
        content = self._content
        # Skip leading newline created when writing a line first
        if content and isinstance(content[0], Newline):
            content = content[1:]
        for elem in content:
            if isinstance(elem, str):
                buf.write(elem)
            elif isinstance(elem, Newline):
                buf.write(f"\n{self._prefix}{self._indent_by * elem.indents}")
            else:
                elem.render(buf)

# Cannot reuse sections with this writer
# (Because indentation is absolute)
