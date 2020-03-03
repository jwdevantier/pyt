import click
import colorama as clr
import json


def echo_err(txt):
    click.echo(
        f"{clr.Style.BRIGHT}{clr.Fore.RED}✖{clr.Style.RESET_ALL} {txt}")


def fmt_datastructure(data) -> str:
    return json.dumps(data, indent=2, )