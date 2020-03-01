import os
import logging
import sys
from pathlib import Path
import click
from ghostwriter.cli import conf
from ghostwriter.cli.log import configure_logging, CLI_LOGGER_NAME
import ghostwriter.cli.compile as cli_compile
import ghostwriter.cli.init as cli_init
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


@cli.command()
@click.pass_obj
def init(config):
    log = logging.getLogger(CLI_LOGGER_NAME)
    conf_path = Path(".", conf.CONF_NAME)
    if conf_path.exists():
        log.error(f"cannot initialize directory - {conf.CONF_NAME} already exists")
        sys.exit(1)

    search_paths = ["snippets"]
    for search_path in search_paths:
        abs_search_path = Path(".", search_path)
        try:
            os.mkdir(abs_search_path.name)
        except FileExistsError as e:
            if not abs_search_path.is_dir():
                raise e  # something exists and its not a directory
    cli_init.write_configuration(cli_init.ConfDefault(
        search_paths=search_paths
    ), {}, conf_path.absolute())
    sys.exit(0)


@cli.command()
@click.option('--watch/--no-watch', envvar="GHOSTWRITER_WATCH", default=False)
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
