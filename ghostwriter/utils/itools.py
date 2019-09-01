import typing as t


def join(*iters):
    """Join multiple iteratables into one"""
    for it in iters:
        yield from it


def cycle(iterable: t.Iterable):
    """Create an endless iterable.

    Note: unlike itertools.cycle, this does NOT buffer the elements"""
    while True:
        for elem in iterable:
            yield elem

