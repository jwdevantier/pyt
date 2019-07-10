from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from os import DirEntry
import logging
import typing as t
from abc import ABC, abstractmethod

from re import compile as re_compile
from typing_extensions import Protocol
from watchgod.watcher import AllWatcher

from pyt.utils import itools
from pyt.cli.conf import Configuration, ConfParser

log = logging.getLogger(__name__)

Matcher = t.Callable[[t.Any], t.Optional[t.Match[t.AnyStr]]]


def or_pattern(patterns: t.List[str]) -> Matcher:
    """Compile pattern matching any of the regex strings in `patterns`."""
    return re_compile('|'.join(f'(?:{entry})' for entry in patterns)).match


class CompileWatcher(AllWatcher):
    def __init__(self, path: str, *, config: Configuration):
        self.ignore_file = or_pattern(config.parser.ignore_patterns)
        self.include_file = or_pattern(config.parser.include_patterns)
        self.ignore_dir = or_pattern(config.parser.ignore_dir_patterns)
        self.temp_file_suffix = config.parser.temp_file_suffix
        super().__init__(path)

    def should_watch_dir(self, entry: DirEntry):
        return self.ignore_dir(entry.path) is None

    def should_watch_file(self, entry: DirEntry):
        fpath: str = entry.path
        if fpath.endswith(self.temp_file_suffix) or self.ignore_file(entry.path):
            return False
        return self.include_file(entry.path) is not None


class Watcher(Protocol):

    def should_watch_dir(self, entry: DirEntry) -> bool:
        ...

    def should_watch_file(self, entry: DirEntry) -> bool:
        ...


class MPScheduler(ABC):
    def __init__(self):
        self._pipe_snd: t.List[Connection] = []
        self._pipe_rcv: t.List[Connection] = []
        self._procs: t.List[Process] = []

        for n in range(self.num_processes):
            snd, rcv = Pipe()
            self._pipe_snd.append(snd)
            self._pipe_rcv.append(rcv)

    @abstractmethod
    def _target(self, jobs: Connection):
        """the starting point of the worker process"""
        ...

    @property
    def num_processes(self):
        """return number of processes to have in pool"""
        return self._num_processes()

    @abstractmethod
    def _num_processes(self) -> int:
        """return number of processes to have in pool"""
        ...

    def _spawn_procs(self):
        assert self._procs == [], "cannot spawn before cleaning up old processes"
        for n in range(self.num_processes):
            proc = Process(target=self._target, args=(self._pipe_rcv[n],), daemon=True)
            self._procs.append(proc)
            proc.start()

    def _kill_procs(self):
        for fn in itools.join(
                (lambda: p.send("<stop>") for p in self._pipe_snd),
                (p.join for p in self._procs)):
            try:
                fn()
            except:
                pass
        self._procs = []

    def close(self):
        self._kill_procs()
        for fn in itools.join((p.close for p in self._pipe_rcv), (p.close for p in self._pipe_snd)):
            try:
                fn()
            except:
                pass

    def __enter__(self):
        log.info("--mp enter--")
        self._spawn_procs()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("--mp exit--")
        self._kill_procs()

    def submit(self, work: t.Iterable[t.Any]):
        pipes = itools.cycle(self._pipe_snd)
        for item in work:
            next(pipes).send(item)
