import sys
import traceback
from re import compile as re_compile, S as re_S
from io import StringIO


rgx = re_compile(r"""\s*File "(?P<filename>.*?)", line (?P<lineno>\d+), in (?P<name>\S*)\n(?:(?P<line>.*))\n*""", re_S)


cdef class Error(Exception):
    cpdef str error_message(self):
        raise NotImplementedError("error_message not implemented")

    cpdef str error_details(self):
        raise NotImplementedError("error_details not implemented")


cpdef str error_details(e, str indentation = "  "):
    return f"\n{indentation}".join(
        (e.error_details()
         if isinstance(e, Error) or hasattr(e, "error_details")
         else traceback.format_exc()).split("\n"))


cpdef str error_message(e):
    if isinstance(e, Error) or hasattr(e, "error_message"):
        return e.error_message()
    return f"{str(e)} (Type: {type(e).__qualname__})"


cdef class FrameInfo:
    def __init__(self, str filename, int lineno, str name, str line = None):
        self.filename = filename
        self.lineno = lineno
        self.name = name
        self.line = line

    def __str__(self):
        if self.line:
            return f"""File "{self.filename}", line {self.lineno}, in {self.name}\n    {self.line}\n"""
        return f"""File "{self.filename}", line {self.lineno}, in {self.name}\n"""

    def __repr__(self):
        return f"<FrameInfo filename: {self.filename}, lineno: {self.lineno}, name: {self.name}, line: {self.line}>"


cdef list parse_traceback(object tb):
    cdef list stack = []
    cdef str line
    for line in traceback.format_tb(tb):
        m = rgx.match(line)
        if not m:
            raise RuntimeError("failed to match line")
        stack.append(FrameInfo(m["filename"], int(m["lineno"]), m["name"], m["line"][:-1]))
    return stack


cdef class ExceptionInfo:
    def __cinit__(self, Exception exc, list stacktrace):
        self.exc = exc
        self.stacktrace = stacktrace
        self._error_message = f"{type(exc).__qualname__}: {str(exc)}"

    cpdef str error_message(self):
        return self._error_message

    cpdef str error_details(self):
        cdef FrameInfo f
        # in some cases the stacktrace is empty.
        # typically happens when an error happens at top-level (e.g. evaluating a string value)
        if not self.stacktrace:
            return ""

        with StringIO() as buf:
            # buf.write("Traceback (most recent call last):\n")
            for f in self.stacktrace:
                buf.write(str(f))
            return buf.getvalue()

    def __repr__(self):
        return f"<{repr(self.exc)}, stack: {repr(self.stacktrace)}>"


cpdef ExceptionInfo catch_exception_info():
    _, exc, tb = sys.exc_info()
    return ExceptionInfo(exc, parse_traceback(tb))

cdef class WrappedException(Error):
    """Wrap raised exception and format it for subsequent display.

    Wraps exception and implement methods used elsewhere to pretty-print exceptions."""

    def __init__(self, ExceptionInfo ei):
        super().__init__(ei.error_message())
        self.ei = ei

    cpdef str error_details(self):
        return self.ei.error_details()

    cpdef str error_message(self):
        return self.ei.error_message()
