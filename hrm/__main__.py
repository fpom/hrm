import random
import re
import string

from typing import Annotated, Optional
from pathlib import Path

from typer import Typer, Option, Argument, Exit
from rich import print as rprint

from . import HRM, HRMError
from .parse import ParseError
from .tui import main as tui
from .hrmx import HRMX, HRMXError


app = Typer(context_settings={"help_option_names": ["-h", "--help"]})


def intval(txt):
    try:
        return int(txt)
    except ValueError:
        pass


def parse_tiles(text):
    if isinstance(text, list):
        return text
    items = []
    for val in text.split(","):
        if val == "":
            items.append(None)
        elif (num := intval(val)) is not None:
            items.append(num)
        elif len(val) == 1:
            items.append(val)
        else:
            raise ValueError("invalid value {val!r}")
    return items


def parse_inbox(text):
    return [val for val in parse_tiles(text) if val is not None]


def gen_inbox(length, neg, chars, bound):
    values = []
    values.extend(range(bound+1))
    if neg:
        values.extend([-v for v in values])
    if chars:
        values.extend(string.ascii_uppercase)
    return [random.choice(values) for _ in range(length)]


def build(prog, inbox, tiles, length, negative, chars, maxval):
    try:
        if match := re.match(r"^(lvl|level):(\d+)$", prog, re.I):
            hrm, inbox, tiles = HRM.from_level(int(match.group(2)))
        else:
            hrm = HRM.parse(Path(prog))
            if inbox is None:
                inbox = gen_inbox(length, negative, chars, maxval)
    except ParseError as err:
        if "\n" in (msg := str(err)):
            head, rest = msg.split("\n", 1)
            rprint(f"[bold red]{head}[/]\n{rest.rstrip()}")
        else:
            rprint(f"[bold red]msg.rstrip()")
        raise Exit(1)
    except OSError as err:
        rprint(f"[bold red]{err}")
        raise Exit(1)
    assert isinstance(inbox, list)
    return hrm, inbox, tiles


@app.command(help="fully run a program and print its outbox")
def run(
    prog: Annotated[
        str,
        Argument(
            help="program to run: either a PATH to source or 'lvl:NUM'")],
    verbose: Annotated[
        int,
        Option(
            "-v", "--verbose",
            count=True,
            help="print INBOX/OUTBOX, use '-vv' to print executed operations"
        )] = 0,
    inbox: Annotated[
        Optional[list],
        Option(
            "-i", "--inbox",
            metavar="LIST",
            parser=parse_inbox,
            help="inbox to use instead of generated one (eg, '1,2,1,B,3')"
        )] = None,
    tiles: Annotated[
        list,
        Option(
            "-t", "--tiles",
            metavar="LIST",
            parser=parse_tiles,
            help="tiles to be used (eg, '1,,,0' with empty slots allowed)"
        )] = [],
    delay: Annotated[
        float,
        Option(
            "-d", "--delay",
            metavar="DELAY",
            help="wait DELAY seconds after each operation"
        )] = 0.0,
    negative: Annotated[
        bool,
        Option(
            "-n", "--negative",
            help="allow negative numbers in generated inbox"
        )] = False,
    chars: Annotated[
        bool,
        Option(
            "-c", "--chars",
            help="allow characters in generated inbox"
        )] = False,
    length: Annotated[
        int,
        Option(
            "-l", "--length",
            metavar="INT",
            help="generate inbox with INT items"
        )] = 10,
    maxval: Annotated[
        int,
        Option(
            "-m", "--max",
            metavar="INT",
            help="generate inbox with |values| <= INT"
        )] = 10):
    hrm, inbox, tiles = build(prog, inbox, tiles,
                              length, negative, chars, maxval)
    try:
        outbox = hrm(inbox, tiles, verbose, delay)
        if not verbose:
            print(*outbox)
    except HRMError:
        raise Exit(1)


@app.command(help="quickly run a program and print its outbox")
def xrun(
    prog: Annotated[
        str,
        Argument(
            help="program to run: either a PATH to source or 'lvl:NUM'")],
    verbose: Annotated[
        bool,
        Option(
            "-v", "--verbose",
            help="print executed operations"
        )] = False,
    inbox: Annotated[
        Optional[list],
        Option(
            "-i", "--inbox",
            metavar="LIST",
            parser=parse_inbox,
            help="inbox to use instead of generated one (eg, '1,2,1,B,3')"
        )] = None,
    tiles: Annotated[
        list,
        Option(
            "-t", "--tiles",
            metavar="LIST",
            parser=parse_tiles,
            help="tiles to be used (eg, '1,,,0' with empty slots allowed)"
        )] = [],
    negative: Annotated[
        bool,
        Option(
            "-n", "--negative",
            help="allow negative numbers in generated inbox"
        )] = False,
    length: Annotated[
        int,
        Option(
            "-l", "--length",
            metavar="INT",
            help="generate inbox with INT items"
        )] = 10,
    maxval: Annotated[
        int,
        Option(
            "-m", "--max",
            metavar="INT",
            help="generate inbox with |values| <= INT"
        )] = 10,
    capacity: Annotated[
        int,
        Option(
            "-c", "--capacity",
            metavar="INT",
            help="maximum size of inbox/outbox/tiles"
        )] = 512):
    hrm, inbox, tiles = build(prog, inbox, tiles,
                              length, negative, False, maxval)
    hrmx = HRMX.compile(hrm.prog, hrm.labels, capacity)
    try:
        print(*hrmx(inbox, tiles, 2 if verbose else 1))
    except HRMXError as err:
        rprint(f"[red]error:[/] {err}")
        raise Exit(1)


@app.command(help="run a program interactively")
def play(prog: Annotated[
            str,
            Argument(
                help="program to run: either a PATH to source or 'lvl:NUM'")],
         inbox: Annotated[
             Optional[list],
             Option(
                 "-i", "--inbox",
                 metavar="LIST",
                 parser=parse_inbox,
                 help="inbox to use instead of generated one (eg, '1,2,1,B,3')"
             )] = None,
         tiles: Annotated[
             list,
             Option(
                 "-t", "--tiles",
                 metavar="LIST",
                 parser=parse_tiles,
                 help="tiles to be used (eg, '1,,,0' with empty slots allowed)"
             )] = [],
         delay: Annotated[
             float,
             Option(
                 "-d", "--delay",
                 metavar="DELAY",
                 help="wait DELAY seconds after each operation"
             )] = 0.0,
         negative: Annotated[
             bool,
             Option(
                 "-n", "--negative",
                 help="allow negative numbers in generated inbox"
             )] = False,
         chars: Annotated[
             bool,
             Option(
                 "-c", "--chars",
                 help="allow characters in generated inbox"
             )] = False,
         length: Annotated[
             int,
             Option(
                 "-l", "--length",
                 metavar="INT",
                 help="generate inbox with INT items"
             )] = 10,
         maxval: Annotated[
             int,
             Option(
                 "-m", "--max",
                 metavar="INT",
                 help="generate inbox with |values| <= INT"
             )] = 10):
    hrm, inbox, tiles = build(prog, inbox, tiles,
                              length, negative, chars, maxval)
    tui(hrm, inbox, tiles)


if __name__ == "__main__":
    app()
