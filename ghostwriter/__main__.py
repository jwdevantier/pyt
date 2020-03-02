import os
import logging
import sys
from pathlib import Path
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
@click.option('--project', envvar='PROJECT', default=os.getcwd(), callback=valid_directory)
@click.pass_context
def cli(ctx, project):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s: %(message)s',
        datefmt='%H:%M:%S')
    log = logging.getLogger(CLI_LOGGER_NAME)

    # We make the project directory our actual working directory.
    # This has several benefits, among them that relative paths become
    # relative to the project-root.
    os.chdir(project)

    # load configuration & configure logging accordingly
    # (skipped if "init"(-ialising) a new project
    if ctx.invoked_subcommand != "init":
        log.info(f"Loading configuration from '{project}'")
        ctx.obj = conf.load(Path('.').absolute())
        configure_logging(ctx.obj)


@cli.command(help="create config file and snippets directories")
def init():
    conf_path = Path(".", conf.CONF_NAME)
    if conf_path.exists():
        click.echo(f"cannot initialize directory - {conf.CONF_NAME} already exists")
        sys.exit(1)
    cli_init(conf_path)


@cli.command(help="parse files and expand any snippets")
@click.option('--watch/--no-watch', envvar="GHOSTWRITER_WATCH", default=False, show_default=True,
              help="recompile snippets on file changes")
@click.pass_obj
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
