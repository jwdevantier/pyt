import typing as t

_buffer = []


def write(entry: t.Any):
    _buffer.append(entry)


def reset():
    global _buffer
    _buffer = []


def values() -> t.List[str]:
    return [entry for entry in _buffer]
