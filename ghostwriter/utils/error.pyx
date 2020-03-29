import traceback
import sys

cdef class EvalError(Exception):
    cpdef str error_message(self):
        return ""
    cpdef str error_details(self):
        return ""


cdef class WrappedException(EvalError):
    """Wrap raised exception and format it for subsequent display.

    Wraps exception and implement methods used elsewhere to pretty-print exceptions."""

    def __init__(self):
        # NOTE: this exception expects to be created INSIDE an exception block
        cls, inst, tb = sys.exc_info()
        self._error = f"{cls.__qualname__}: {str(inst)}"
        super().__init__(self._error)
        self.stacktrace_lines = traceback.format_tb(tb)
        # Python exceptions are rendered with this line at the start of the stack trace
        self.stacktrace_lines.insert(0, "Traceback (most recent call last):\n")

    cpdef str error_details(self):
        return "".join(self.stacktrace_lines)

    cpdef str error_message(self):
        return self._error
