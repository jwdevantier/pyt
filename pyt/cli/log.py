import logging
from pyt.cli.conf import Configuration


def configure_logging(conf: Configuration) -> None:
    """Reconfigure root logger to use formats and log level in `conf`."""
    root_logger = logging.getLogger()
    formatter = logging.Formatter(
        fmt=conf.logging.format,
        datefmt=conf.logging.datefmt)
    root_logger.setLevel(conf.logging.level.upper())
    if not root_logger.handlers:
        handler: logging.Handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.handlers.append(handler)
    else:
        handler = root_logger.handlers[0]
        handler.setFormatter(formatter)
