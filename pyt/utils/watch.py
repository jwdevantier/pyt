from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from os import DirEntry
from pathlib import Path
import asyncio
import logging
import typing as t
from abc import ABC, abstractmethod

import watchgod as wg
import aiostream.stream.combine as stream
from re import compile as re_compile
from typing_extensions import Protocol
from watchgod.watcher import AllWatcher

from pyt.utils import itools
from pyt.cli.conf import Configuration

log = logging.getLogger(__name__)

Matcher = t.Callable[[t.Any], t.Optional[t.Match[t.AnyStr]]]


def or_pattern(patterns: t.Iterable[str]) -> Matcher:
    """Compile pattern matching any of the regex strings in `patterns`."""
    return re_compile('|'.join(f'(?:{entry})' for entry in patterns)).match


class Watcher(Protocol):

    def should_watch_dir(self, entry: DirEntry) -> bool:
        ...

    def should_watch_file(self, entry: DirEntry) -> bool:
        ...


class CompileWatcher(AllWatcher):
    def __init__(self, path: str, *, config: Configuration):
        self.ignore_file = or_pattern(config.parser.ignore_patterns)
        self.include_file = or_pattern(config.parser.include_patterns)
        self.ignore_dir = or_pattern(config.parser.ignore_dir_patterns)
        self.temp_file_suffix = config.parser.temp_file_suffix
        super().__init__(path)

    def should_watch_dir(self, entry: DirEntry) -> bool:
        if entry.path.startswith('/tmp'):
            print(f"TMP DIR: {self.ignore_dir(entry.path)}")
        return self.ignore_dir(entry.path) is None  # Should add dirs and subdirs here, too

    def should_watch_file(self, entry: DirEntry) -> bool:
        fpath: str = entry.path
        if fpath.endswith(self.temp_file_suffix) or self.ignore_file(entry.path):
            return False
        return self.include_file(entry.path) is not None


class SearchPathsWatcher(AllWatcher):
    IGNORED_DIRS = {'.git', '__pycache__', 'site-packages', 'env', 'venv', '.env', '.venv'}

    def __init__(self, path: str):
        super().__init__(path)

    def should_watch_dir(self, entry: DirEntry) -> bool:
        return entry.name not in self.IGNORED_DIRS

    def should_watch_file(self, entry: DirEntry) -> bool:
        return entry.name.endswith('.py')


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
        self._spawn_procs()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._kill_procs()

    def submit(self, work: t.Iterable[t.Any]):
        pipes = itools.cycle(self._pipe_snd)
        for item in work:
            next(pipes).send(item)


async def iter_all(*aiters: t.AsyncIterator):
    async with stream.merge(*aiters).stream() as allstream:
        ait = allstream.__aiter__()
        async for x in ait:
            yield x


class WatcherConfig:
    def __init__(self, tag: str, path: t.Union[Path, str], cls: t.Type[Watcher], kwargs: t.Dict[str, t.Any] = None):
        if kwargs is None:
            kwargs = {}
        self.tag = tag
        self.path = path
        self.cls = cls
        self._kwargs = {**kwargs}

    def awatch(self, loop) -> wg.awatch:
        return wg.awatch(self.path, loop=loop, **{'watcher_kwargs': self._kwargs, 'watcher_cls': self.cls})


def watch_dirs(watchdirs: t.List[WatcherConfig]):
    loop = asyncio.new_event_loop()

    async def tagged(tag: str, agen):
        async for elem in agen:
            yield tag, elem

    try:
        # works, but raw, no tag
        # ait = iter_all(*[wd.awatch(loop) for wd in watchdirs])

        ait = iter_all(*[tagged(wd.tag, wd.awatch(loop).__aiter__()) for wd in watchdirs])
        while True:
            try:
                yield loop.run_until_complete(ait.__anext__())
            except StopAsyncIteration:
                break
    except KeyboardInterrupt:
        log.debug('KeyboardInterrupt, exiting')
    finally:
        loop.close()
