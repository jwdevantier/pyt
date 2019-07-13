import os
import logging
import sys
from pathlib import Path
import click
from pyt.cli import conf
from pyt.cli.log import configure_logging
import pyt.cli.compile as cli_compile
import colorama

colorama.init()


def valid_directory(ctx, param, val):
    if not os.path.isdir(val):
        raise click.BadParameter("should be a directory")
    return val


@click.group()
@click.option('--project', envvar='PROJECT', default=os.getcwd(), callback=valid_directory)
@click.pass_context
def cli(ctx, project):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s: %(message)s',
        datefmt='%H:%M:%S')
    log = logging.getLogger("pyt.start")
    log.info(f"Loading configuration from '{project}'")

    # We make the project directory our actual working directory.
    # This has several benefits, among them that relative paths become
    # relative to the project-root.
    os.chdir(project)
    ctx.obj = conf.load(Path('.').absolute())

    configure_logging(ctx.obj)


@cli.command()
@click.option('--watch/--no-watch', envvar="PYT_WATCH", default=False)
@click.pass_obj
def compile(config, watch):
    cli_compile.compile(config, watch)
    sys.exit(0)
