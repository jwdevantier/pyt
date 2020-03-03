import os
import logging
import sys
from pathlib import Path
from functools import wraps
import click
from ghostwriter.cli import conf
from ghostwriter.cli.log import configure_logging, CLI_LOGGER_NAME
import ghostwriter.cli.compile as cli_compile
from ghostwriter.cli.init import cli_init
from ghostwriter.utils.constants import  *
import colorama as clr


clr.init()


def valid_directory(ctx, param, val):
    if not os.path.isdir(val):
        raise click.BadParameter("should be a directory")
    return val


@click.group()
@click.version_option(GW_VERSION, prog_name=GW_NAME)
@click.pass_context
def cli(ctx):
    # Basic initialization needed for any command goes here
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s: %(message)s',
        datefmt='%H:%M:%S')


def command(load_config=False, **click_options):
    def decorator(fn):
        @cli.command(**click_options)
        @click.option('--project', envvar='PROJECT', default=os.getcwd(), callback=valid_directory, show_default=True,
                      help="the directory containing the configuration, snippets and source code")
        @wraps(fn)
        def wrapper(project, *args, **kwargs):
            # We make the project directory our actual working directory.
            # This has several benefits, among them that relative paths become
            # relative to the project-root.
            os.chdir(project)

            log = logging.getLogger(CLI_LOGGER_NAME)

            if load_config:
                print("LOAD CONFIG")
                log.info(f"Loading configuration from '{project}'")
                config = conf.load(Path('.').absolute())
                configure_logging(config)
                return fn(config, *args, **kwargs)
            else:
                print("NOT loading command")
                return fn(*args, **kwargs)
        return wrapper
    return decorator


@command(load_config=False, help="create config file and snippets directories")
def init():
    conf_path = Path(".", conf.CONF_NAME)
    if conf_path.exists():
        click.echo(f"cannot initialize directory - {conf.CONF_NAME} already exists")
        sys.exit(1)
    cli_init(conf_path)


@command(load_config=True, help="parse files and expand any snippets")
@click.option('--watch/--no-watch', envvar="GHOSTWRITER_WATCH", default=False, show_default=True,
              help="recompile snippets on file changes")
def compile(config, watch):
    cli_compile.compile(config, watch)
    sys.exit(0)


# If packaged with pyinstaller, the 'frozen' attribute is True
# pass on control to click, passing all arguments along.
if getattr(sys, 'frozen', False):
    cli(sys.argv[1:])


# This allows running the program as a script by handing over control (and argument parsing) to click.
if __name__ == '__main__':
    cli()
