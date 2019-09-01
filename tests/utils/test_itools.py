from ghostwriter.utils import itools


def test_join():
    assert list(itools.join(
        (n for n in range(0, 2)),
        (n for n in range(5, 10))
    )) == [0, 1, 5, 6, 7, 8, 9], "stuff"


def test_cycle():
    it = itools.cycle([0, 1, 2, 3])
    results = []
    for n in range(0, 10):
        results.append(next(it))
    assert results == [0, 1, 2, 3, 0, 1, 2, 3, 0, 1], "unexpected sequence"
