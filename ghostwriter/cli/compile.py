import logging
from ghostwriter.cli.conf import Configuration
from ghostwriter.utils.compile import cli_compile


log = logging.getLogger(__name__)


def compile(config: Configuration, watch: bool) -> None:
    cli_compile(config, watch)
