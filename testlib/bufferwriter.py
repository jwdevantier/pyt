from ghostwriter.utils.iwriter import IWriter
from io import StringIO


class BufferWriter(IWriter):
    def __init__(self):
        super().__init__()
        self._buffer = StringIO()

    def write(self, contents: str):
        self._buffer.write(contents)

    def getvalue(self) -> str:
        return self._buffer.getvalue()