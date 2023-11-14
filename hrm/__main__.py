import argparse
import pathlib
import random
import string
import sys

from . import HRM, HRMError
from .tikz import draw, tikz
from .xui import main as xui

epilog = """
Option '-i 1,2,A,B,3' allows to run the program with the specified
inbox, it starts with 1 (first element to be grabbed) and ends with 3.

Option '-t 0,1,B,U,G' allows to run the program with the specified
data onto the floor tiles, it fills tiles starting from 0, no value
between two commas leaves the corresponding tile empty.

Exporting programs to PDF requires pdflatex with TikZ installed.
"""

parser = argparse.ArgumentParser(
    prog="hrmi",
    description="Human Resource Machine interpreter",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=epilog.strip())
parser.add_argument("-v", dest="verbose", default=False, action="store_true",
                    help="print messages while execution progresses")
parser.add_argument("-p", dest="pdf", type=str, default=None, action="store",
                    help="export program as a PDF image")
parser.add_argument("-l", dest="latex", type=str, default=None, action="store",
                    help="export program as a LaTeX/TikZ file")
parser.add_argument("-i", dest="inbox", type=str, default=None, action="store",
                    help="run with INBOX given as comma-separated values")
parser.add_argument("-n", dest="numeric", default=False, action="store_true",
                    help="generate INBOX with only numeric values")
parser.add_argument("-N", dest="positive", default=False, action="store_true",
                    help="generate INBOX with no negative values")
parser.add_argument("-s", dest="size", type=int, default=None, action="store",
                    help="generate INBOX with SIZE values")
parser.add_argument("-t", dest="tiles", type=str, default=None, action="store",
                    help="run with TILES given as comma-separated values")
parser.add_argument("-q", dest="quit", default=False, action="store_true",
                    help="quit interpreter without running the program")
parser.add_argument("-g", dest="gui", default=False, action="store_true",
                    help="run (semi-)graphical user interface")
parser.add_argument("-G", dest="gui", default=False, action="store_false",
                    help="run (semi-)graphical user interface")
parser.add_argument("-d", dest="delay", default=0, action="store", type=float,
                    help="delay between operations in non-gui + verbose mode")
parser.add_argument("prog", type=str, metavar="PROG", action="store",
                    help="program to be run")


def main():
    args = parser.parse_args()
    inbox = tiles = None

    try:
        if pathlib.Path(args.prog).exists():
            run = HRM.parse(args.prog)
        else:
            try:
                lvl = int(args.prog.split(":", 1)[1])
            except Exception:
                parser.exit(1, f"invalid program {args.prog}")
            run, inbox, tiles = HRM.from_level(lvl)
    except HRMError as err:
        parser.exit(1, str(err))

    if args.pdf is not None:
        draw(args.prog, args.pdf)

    if args.latex is not None:
        tikz(args.prog, args.latex, True)

    if args.quit:
        sys.exit(0)

    random.seed()

    if args.inbox is not None and inbox is None:
        inbox = args.inbox.split(",")
        for i, v in enumerate(inbox):
            if len(v) == 1 and v in string.ascii_letters:
                inbox[i] = v.upper()
            else:
                try:
                    inbox[i] = int(v)
                except Exception:
                    parser.exit(2, f"invalid inbox value {v!r}")
    elif inbox is None:
        size = args.size or random.randint(10, 20)
        if args.positive:
            MIN, MAX = 0, 20
        else:
            MIN, MAX = -20, 20
        if args.numeric:
            inbox = [random.randint(MIN, MAX) for _ in range(size)]
        else:
            inbox = [random.choice(list(range(MIN, MAX+1))
                                   + list(string.ascii_uppercase))
                     for _ in range(size)]

    if args.tiles and tiles is None:
        tiles = args.tiles.split(",")
        for i, v in enumerate(tiles):
            if not v:
                tiles[i] = None
            elif len(v) == 1 and v in string.ascii_letters:
                tiles[i] = v.upper()
            else:
                try:
                    tiles[i] = int(v)
                except Exception:
                    parser.exit(2, f"invalid tile value {v!r}")
    elif tiles is None:
        tiles = []

    if args.gui:
        xui(run, inbox, tiles)
    else:
        try:
            if args.verbose:
                print("<", *inbox)
            outbox = run(inbox, tiles, args.verbose, args.delay)
            if args.verbose:
                print(">", *outbox)
            else:
                print(*outbox)
        except HRMError as err:
            parser.exit(1)


if __name__ == "__main__":
    main()
