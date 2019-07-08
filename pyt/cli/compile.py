import logging
import os
import sys
from re import compile as re_compile
import typing as t
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
import multiprocessing as mp

import watchgod
from watchgod.watcher import Change, AllWatcher
from typing_extensions import Protocol

from mypy_extensions import KwArg
from threading import Timer
from time import time
from math import ceil

from pyt.parser import Parser, Context, PARSE_OK, parse_result_err
import pyt.parser as pparse
from pyt.protocols import IWriter
from pyt.utils.fhash import file_hash
from pyt.utils import itools
from pyt.cli.conf import Configuration, ConfParser

log = logging.getLogger(__name__)

WatchChangesFn = t.Callable[[str, KwArg(t.Any)], t.Iterator[t.Set[t.Tuple[watchgod.Change, str]]]]
CompileFn = t.Callable[[Configuration], None]
Changeset = t.Set[t.Tuple[Change, str]]
Matcher = t.Callable[[t.Any], t.Optional[t.Match[t.AnyStr]]]


def or_pattern(patterns: t.List[str]) -> Matcher:
    """Compile pattern matching any of the regex strings in `patterns`."""
    return re_compile('|'.join(f'(?:{entry})' for entry in patterns)).match


class CompileWatcher(AllWatcher):
    def __init__(self, path: str, *, config: Configuration):
        self.ignore_file = or_pattern(config.parser.ignore_patterns)
        self.include_file = or_pattern(config.parser.include_patterns)
        self.temp_file_suffix = config.parser.temp_file_suffix
        super().__init__(path)

    def should_watch_dir(self, entry: os.DirEntry):
        return False

    def should_watch_file(self, entry: os.DirEntry):
        fpath: str = entry.path
        if fpath.endswith(self.temp_file_suffix) or self.ignore_file(entry.path):
            return False
        return self.include_file(entry.path) is not None


class Watcher(Protocol):

    def should_watch_dir(self, entry: os.DirEntry) -> bool:
        ...

    def should_watch_file(self, entry: os.DirEntry) -> bool:
        ...


def dirwalker(w: Watcher, path: str) -> t.Iterator[os.DirEntry]:
    for entry in os.scandir(path):
        if entry.is_dir():
            if w.should_watch_dir(entry):
                yield from dirwalker(w, entry.path)
        elif w.should_watch_file(entry):
            yield entry


def expand_snippet(ctx: Context, snippet: str, prefix: str, out: IWriter):
    out.write(f"{prefix}look out!\n")
    out.write(f"{prefix}something more")


# TODO: revamp compile fns into small objects (resource allocation)

def compile_once_singlecore(config: Configuration, ) -> None:
    # TODO: make walker outside this fn
    root_path: str = config.project.absolute().as_posix()
    walker = CompileWatcher(root_path, config=config)
    parser = Parser(
        config.parser.open, config.parser.close,
        temp_file_suffix=config.parser.temp_file_suffix)
    for entry in dirwalker(walker, root_path):
        out = parser.parse(expand_snippet, entry.path)
        if out != 0:
            log.error(f"parse() => {out} ({pparse.parse_result_err(out)})")
            log.error(f"in: {entry.path}")


class MPScheduler:
    def __init__(self, parser_conf: ConfParser):
        self._pipe_snd: t.List[Connection] = []
        self._pipe_rcv: t.List[Connection] = []
        self.parser_conf = parser_conf
        self._procs: t.List[Process] = []

        for n in range(parser_conf.processes):
            snd, rcv = Pipe()
            self._pipe_snd.append(snd)
            self._pipe_rcv.append(rcv)

    def _target(self, jobs: Connection):
        parser = Parser(
            self.parser_conf.open, self.parser_conf.close,
            temp_file_suffix=self.parser_conf.temp_file_suffix)
        fpath: str = jobs.recv()
        while fpath != "<stop>":
            log.info(f"received fpath '{fpath}' (type: {type(fpath)})")
            out = parser.parse(expand_snippet, fpath)  # TODO: ERROR COMES HERE - NONE
            fpath = jobs.recv()
            if out:
                log.error(f"parse() => {out} ({pparse.parse_result_err(out)})")
                log.error(f"in: {fpath}")

    def _spawn_procs(self):
        assert self._procs == [], "cannot spawn before cleaning up old processes"
        for n in range(self.parser_conf.processes):
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


def compile_once_mp(config: Configuration) -> None:
    # TODO: move creation of all three objects one level up.
    root_path = config.project.absolute().as_posix()
    walker = CompileWatcher(root_path, config=config)
    sched = MPScheduler(config.parser)
    with sched as s:
        s.submit((entry.path for entry in dirwalker(walker, root_path)))


class Debounce:
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


def compile_watch(config: Configuration, compile_fn: CompileFn) -> None:
    compile: Debounce = Debounce(compile_fn)
    # TODO: write FHASH functionality - filter changed list through fhash - schedule iff len(filter(fhash)) != 0

    compile(config)
    # should be fpath => hash (because there may be identical files)
    fmap: t.Dict[str, str] = {}

    log.info(f"Watching: {config.project.absolute().as_posix()}")

    def filer_changeset(changeset: Changeset) -> t.Iterator[t.Tuple[Change, str]]:
        nonlocal fmap
        for typ, fpath in changeset:
            if typ == Change.modified:
                new_hash = file_hash(fpath)
                old_hash = fmap.get(fpath, None)
                if new_hash != old_hash:
                    fmap[fpath] = new_hash
                    yield typ, fpath
            elif typ == Change.added:
                fmap[fpath] = file_hash(fpath)
                yield typ, fpath
            elif typ == Change.deleted:
                fmap.pop(fpath, None)

    for changes in watchgod.watch(
            config.project.absolute().as_posix(),
            watcher_cls=CompileWatcher,
            watcher_kwargs={'config': config}):
        real_changes = list(filer_changeset(changes))
        if real_changes:
            print("REAL CHANGES")
            print(real_changes)
            compile.schedule(config)


def compile(config: Configuration, watch: bool) -> None:
    log.info(f"compile mode: '{'watch' if watch else 'once'}' with {config.parser.processes} processes")
    log.info(f"compile path '{config.project.absolute().as_posix()}'")
    log.info("Config:")
    log.info(config)

    compile_fn: CompileFn
    if config.parser.processes == 1:
        compile_fn = compile_once_singlecore
    else:
        # TODO - move start_method choice to config
        mp.set_start_method('forkserver')
        compile_fn = compile_once_mp

    # single pass then exit
    if not watch:
        compile_fn(config)
        sys.exit(0)

    compile_watch(config, compile_fn)
