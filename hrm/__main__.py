import argparse, sys, string, random

from . import HRM
from .tikz import tikz, draw

epilog = """
Option '-i 1,2,A,B,3' allows to run the program with the specified
inbox, it starts with 1 (first element to be grabbed) and ends with 3.

Option '-t 0,1,B,U,G' allows to run the program with the specified
data onto the floor tiles, it fills tiles starting from 0, no value
between two commas leaves the corresponding tile empty.

Exporting programs to PDF requires pdflatex with TikZ installed.
"""

parser = argparse.ArgumentParser(prog="hrmi",
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
parser.add_argument("-s", dest="size", type=int, default=None, action="store",
                    help="generate INBOX with SIZE values")
parser.add_argument("-t", dest="tiles", type=str, default=None, action="store",
                    help="run with TILES given as comma-separated values")
parser.add_argument("-q", dest="quit", default=False, action="store_true",
                    help="quit interpreter without running the program")
parser.add_argument("prog", type=str, metavar="PROG", action="store",
                    help="program to be run")

def main () :
    args = parser.parse_args()

    try :
        run = HRM.parse(args.prog)
    except AssertionError as err :
        parser.exit(1, str(err))

    if args.pdf is not None :
        draw(args.prog, args.pdf)

    if args.latex is not None :
        tikz(args.prog, args.latex, True)

    if args.quit :
        sys.exit(0)

    random.seed()

    if args.inbox is not None :
        inbox = args.inbox.split(",")
        for i, v in enumerate(inbox) :
            if len(v) == 1 and v in string.ascii_letters :
                inbox[i] = v.upper()
            else :
                try :
                    inbox[i] = int(v)
                except :
                    parser.exit(2, f"invalid inbox value {v!r}")
    else :
        size = args.size or random.randint(10,20)
        if args.numeric :
            inbox = [random.randint(-20,20) for _ in range(size)]
        else :
            inbox = [random.choice(list(range(-20, 21)) + list(string.ascii_uppercase))
                     for _ in range(size)]

    if args.tiles :
        tiles = args.tiles.split(",")
        for i, v in enumerate(tiles) :
            if not v :
                tiles[i] = None
            elif len(v) == 1 and v in string.ascii_letters :
                tiles[i] = v.upper()
            else :
                try :
                    tiles[i] = int(v)
                except :
                    parser.exit(2, f"invalid tile value {v!r}")
    else :
        tiles = []

    try :
        outbox = run(inbox, tiles, args.verbose)
        print(*outbox)
    except AssertionError as err :
        parser.exit(1, str(err))

if __name__ == "__main__" :
    main()
