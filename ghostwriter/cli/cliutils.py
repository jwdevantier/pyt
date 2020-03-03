import click
import colorama as clr
import json


B_BLU = f"{clr.Style.BRIGHT}{clr.Fore.BLUE}"
B_MAG = f"{clr.Style.BRIGHT}{clr.Fore.MAGENTA}"
B_YEL = f"{clr.Style.BRIGHT}{clr.Fore.YELLOW}"
CLR = clr.Style.RESET_ALL


def echo_err(txt: str) -> None:
    click.echo(
        f"{clr.Style.BRIGHT}{clr.Fore.RED}✖{clr.Style.RESET_ALL} {txt}")


def pretty_print(data) -> str:
    return json.dumps(data, indent=2, )


def echo_header(txt) -> None:
    click.echo(f"\n\n{B_YEL}>>{CLR} {B_BLU}{txt}{CLR}")


def echo_prompt(txt, confirm=True, **kwargs):
    prompt_txt = f"{clr.Style.BRIGHT}{clr.Fore.GREEN}?{clr.Style.RESET_ALL} {clr.Style.BRIGHT}{txt}{clr.Style.RESET_ALL}"
    while True:
        result = click.prompt(prompt_txt, **kwargs)
        if not confirm or kwargs.get("default", None) == result:
            break
        confirm_txt = f"Confirm {B_YEL}{result}{CLR}?"
        if click.confirm(confirm_txt, default=False, abort=False, prompt_suffix=': ', show_default=True, err=False):
            break
    return result


def validate_or_retry(validator, prompt_fn, *args, **kwargs):
    result = prompt_fn(*args, **kwargs)
    error = validator(result)
    while error:
        echo_err(error)
        result = prompt_fn(*args, **kwargs)
        error = validator(result)
    return result