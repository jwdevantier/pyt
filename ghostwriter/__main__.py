import os
import logging
import sys
from pathlib import Path
from functools import wraps
import click
from ghostwriter.cli import conf
from ghostwriter.cli.log import configure_logging, CLI_LOGGER_NAME
from ghostwriter.cli.cliutils import *
import ghostwriter.cli.compile as cli_compile
from ghostwriter.cli.init import cli_init
from ghostwriter.utils.constants import *
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
    # NOTE: is run before eager commands like'--help'.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s: %(message)s',
        datefmt='%H:%M:%S')


def command(load_config=False, **click_options):
    """Create a new top-level CLI command.

    Note: initialization which should not run ahead of an eager command
    (such as --version or --help) should go here.

    Parameters
    ----------
    load_config: bool
        whether to load the Ghostwriter configuration file or not
    click_options
        options passed to @click.command

    Returns
    -------
        A decorated command function
    """
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
                log.info(f"Loading configuration from '{project}'")
                try:
                    config = conf.load(Path('.').absolute())
                    configure_logging(config)
                    return fn(config, *args, **kwargs)
                except conf.ConfigurationNotFoundError as e:
                    click.echo(f"{clr.Style.BRIGHT}{clr.Fore.RED}✖{clr.Style.RESET_ALL} Could not find '{conf.CONF_NAME}' in '{e.project_dir}'")
                    sys.exit(1)
                except conf.ConfigurationFileInvalidError as e:
                    click.echo(fmt_datastructure(e.errors))
                    echo_err("Errors detected in configuration file. Please correct these and try again")
                    sys.exit(1)
            else:
                return fn(*args, **kwargs)
        return wrapper
    return decorator


@command(load_config=False, help="create config file and snippets directories")
def init():
    conf_path = Path(".", conf.CONF_NAME)
    if conf_path.exists():
        echo_err(f"cannot initialize directory - '{conf.CONF_NAME}' already exists")
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
