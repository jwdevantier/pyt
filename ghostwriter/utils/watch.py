from os import DirEntry
from pathlib import Path
import asyncio
import signal
import logging
import typing as t
import watchgod as wg
import aiostream.stream.combine as stream
from typing_extensions import Protocol

log = logging.getLogger(__name__)


class Watcher(Protocol):

    def should_watch_dir(self, entry: DirEntry) -> bool:
        ...

    def should_watch_file(self, entry: DirEntry) -> bool:
        ...


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


def make_interruptible_loop():
    loop = asyncio.new_event_loop()

    async def loop_exit():
        loop = asyncio.get_event_loop()
        loop.stop()

    def ask_exit():
        log.info("watch-mode cancelled, exiting...")
        for task in asyncio.Task.all_tasks():
            task.cancel()
        asyncio.ensure_future(loop_exit())

    loop.add_signal_handler(signal.SIGINT, ask_exit)
    return loop


def watch_dirs(watchdirs: t.List[WatcherConfig]):
    loop = make_interruptible_loop()

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
    except asyncio.CancelledError:
        log.info("watch-mode exited.")
    finally:
        loop.close()
