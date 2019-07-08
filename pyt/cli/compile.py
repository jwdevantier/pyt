import logging
import os
import sys

import typing as t
import multiprocessing as mp
import watchgod
from watchgod.watcher import Change

from pyt.parser import Parser, Context, PARSE_OK, parse_result_err
import pyt.parser as pparse
from pyt.utils.decorators import Debounce
from pyt.protocols import IWriter
from pyt.utils.fhash import file_hash
from pyt.utils.watch import Watcher, CompileWatcher, MPScheduler
from pyt.cli.conf import Configuration, ConfParser

log = logging.getLogger(__name__)

CompileFn = t.Callable[[Configuration], None]
Changeset = t.Set[t.Tuple[Change, str]]


class MPCompiler(MPScheduler):
    def __init__(self, parser_conf: ConfParser):
        self.parser_conf = parser_conf
        super().__init__()

    def _num_processes(self):
        return self.parser_conf.processes

    def _target(self, jobs: mp.connection.Connection):
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


def compile_once_mp(config: Configuration) -> None:
    # TODO: move creation of all three objects one level up.
    root_path = config.project.absolute().as_posix()
    walker = CompileWatcher(root_path, config=config)
    sched = MPCompiler(config.parser)
    with sched as s:
        s.submit((entry.path for entry in dirwalker(walker, root_path)))


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
