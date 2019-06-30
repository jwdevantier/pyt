from watchdog.observers import Observer
from watchdog.events import RegexMatchingEventHandler
from time import sleep
import logging

from pyt.cli.conf import Configuration

log = logging.getLogger(__name__)


# TODO: should move more of this to the Configuration
class Watcher:
    IGNORE_PATTERNS = ""
    IGNORE_DIRECTORIES = True
    CASE_SENSITIVE = True

    # will be functions taking a single 'event' argument
    on_created = on_modified = on_moved = on_deleted = None

    def __init__(self, conf: Configuration):
        ev_handler = RegexMatchingEventHandler(
            regexes=conf.parser.include_patterns,
            ignore_regexes=conf.parser.ignore_patterns,
            # Ignore directories, just noise to us.
            ignore_directories=True,
            # Always enforce case sensitivity.
            case_sensitive=True
        )

        self.conf = conf

        if hasattr(self, 'on_created') and callable(self.on_created):
            log.debug("watcher: found 'on_created' handler")
            ev_handler.on_created = self.on_created
        if hasattr(self, 'on_modified') and callable(self.on_modified):
            log.debug("watcher: found 'on_modified' handler")
            ev_handler.on_modified = self.on_modified
        if hasattr(self, 'on_moved') and callable(self.on_moved):
            log.debug("watcher: found 'on_moved' handler")
            ev_handler.on_moved = self.on_moved
        if hasattr(self, 'on_deleted') and callable(self.on_deleted):
            log.debug("watcher: found 'on_deleted' handler")
            ev_handler.on_deleted = self.on_deleted

        self._observer = Observer()
        log.info(f"listening to project dir '{conf.project}'")
        log.info(f"watching for {', '.join(conf.parser.include_patterns)}")
        self._observer.schedule(ev_handler, path=str(conf.project), recursive=True)

    def __call__(self):
        self._observer.start()
        log.info(f"watching '{self.conf.project}'...")
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            self._observer.stop()
        self._observer.join()