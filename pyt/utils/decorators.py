import typing as t
from threading import Timer
from time import time
from math import ceil


class Debounce:
    """Wrap function providing (optional) self-adjusting debounce logic.

    Regular call invokes the function immediately. `schedule` will invoke the
    function after a while provided no further calls to `schedule` are made before
    the wait time has elapsed.

    The wait time is self-adjusting and based on the last call to the function.
    It is thus best suitable to functions with relatively predictable execution
    speeds."""
    def __init__(self, fn: t.Callable):
        self.fn: t.Callable = fn
        self.timer: t.Optional[Timer] = None
        self.elapsed: int = 0

        self.time_start: float = time()  # TODO: remove

    def __call__(self, *args, **kwargs):
        start: float = time()
        print(f"COMPILING '{ceil(time() - self.time_start)}'")  # TODO: remove
        result = self.fn(*args, **kwargs)
        self.elapsed = ceil(time() - start)
        return result

    def schedule(self, *args, **kwargs):
        if self.timer is not None:
            self.timer.cancel()
        self.timer = Timer(self.elapsed, lambda: self(*args, **kwargs))
        self.timer.start()
