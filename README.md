# Human Resource Machine interpreter

This is a Python interpreter for programs from the [Human Resource Machine](http://tomorrowcorporation.com/humanresourcemachine) game from [Tomorrow Corporation](http://tomorrowcorporation.com).
Within the game, one may copy/paste the source code that is edited visually.
This library features a parser for this code, an interpreter, and a translator into TikZ pictures to be included in LaTeX.

```pycon
>>> from hrm import HRM
>>> hrm = HRM.parse('level-2.hrm')
>>> hrm([1, 0, -2, 'D', 0, 0, 8, 9])
1 0 -2 D 0 0 8 9
>>> from hrm.tikz import tikz, draw
>>> tikz('level-2.hrm', 'level-2.tex')
>>> draw('level-2.hrm', 'level-2.pdf')
```

## Installation

Just run `pip install hrm-interpreter` or clone the git repository and run `python setup.py install`.

## Language

If not copied from the game, a program may be written from scratch:

 * each command is given on a single line
 * empty line and spacing are non-significant
 * comments start with `--` and extend up to the end of the line
 * code is case insensitive (in the implementation at least)
 * available commands are:
   * `inbox` grab a value from the INBOX
   * `outbox` put the value at hand to the OUTBOX
   * `copyfrom N` put a copy of the value at hand onto floor tile `N`
   * `copyto N` grab a copy of the value stored on floor tile `N`.
   * `add N` add the value stored on tile `N` to that at hand,
     the result goes to hands
   * `sub N` substract the value stored on tile `N` from that at hand,
     the result goes to hands. This operation is valid on letters in which
     case it computes the distance between two letters in the alphabet
   * `bumpup N` increments the value stored on tile `N` and copies to result
     to hands
   * `bumpdn N` decrements the value stored on tile `N` and copies to result
     to hands
   * `jump L` jump to label `L` that should be defined somewhere as
     `L:` alone on its line
   * `jumpz L` jump to label `L` if the value at hand is zero
   * `jumpn L` jump to label `L` if the value at hand is less that zero
 * if a tile number `N` is `[A]`, the tile from which the value is copied
   is that whose number is stored on tile `A`
 * labels are defined using `NAME:`

Copying code from the game may yield other elements (like drawn tiles labels and comments), but they are ignored in this implementation.

## API

### Class `hrm.HRM`

This is the interpreter itself, it is initialised as either:

 * `HRM(prog)`
   creates an instance to run an already parsed program `prog`
 * `HRM.parse(source)`
   creates an instance by parsing source code `source`,
   it can be a file path, an opened file, or source code given as a `str`

Methods for an `HRM` instance `run`:

 * `run(inbox, floor=[], verbose=False)`
   run the program with `inbox` (list `list` of integers or uppercase characters).
   If `floor` is provided, it initialised the tiles on the floor.
   If `verbose` is `True`, program execution is traced.
 * `run.level(number)`
   returns information about a level from the official game
 * `run.runlevel(level, idx=0, verbose=False)`
   load inbox number `idx` from `level` information as returned by `run.level(level)`
   and run the program with it, passing `verbose`

### Drawing programs

 * `hrm.tikz.tikz(source, out=sys.stdout, headers=False)`
   exports a TikZ rendering of `source` to file `out` (an opened file
   or a file name), including LaTeX headers or not
 * `hrm.tikz.draw(source, path)`
   exports a PDF rendering of `source` to file `path`,
   `pdflatex` must be installed with TikZ

## Command-line interface

```
$ python -m hrm --help
usage: hrmi [-h] [-v] [-p PDF] [-l LATEX] [-i INBOX] [-n] [-s SIZE] [-t TILES]
            [-q]
            PROG

Human Resource Machine interpreter

positional arguments:
  PROG        program to be run

optional arguments:
  -h, --help  show this help message and exit
  -v          print messages while execution progresses
  -p PDF      export program as a PDF image
  -l LATEX    export program as a LaTeX/TikZ file
  -i INBOX    run with INBOX given as comma-separated values
  -n          generate INBOX with only numeric values
  -s SIZE     generate INBOX with SIZE values
  -t TILES    run with TILES given as comma-separated values
  -q          quit interpreter without running the program

Option '-i 1,2,A,B,3' allows to run the program with the specified
inbox, it starts with 1 (first element to be grabbed) and ends with 3.

Option '-t 0,1,B,U,G' allows to run the program with the specified
data onto the floor tiles, it fills tiles starting from 0, no value
between two commas leaves the corresponding tile empty.

Exporting programs to PDF requires pdflatex with TikZ installed.
```

## Limitations

 * the parser is not very robust
 * generated TikZ code generally requires manual editing
 
Differences with the game:
 * the number of available tiles is not limited
 * indirection `[A]` is not limited to `copyfrom`
 * a label may be jumped to from several locations in the program,
   which is never the case in code copied from the game
   as each jump is attached to exactly one target

## Borrowed files

 * the content of directory `solutions` is from
   [atesgoral.github.io/hrm-solutions](http://atesgoral.github.io/hrm-solutions)
 * file `hrm/levels.json` is from 
   [github.com/atesgoral/hrm-level-data](http://github.com/atesgoral/hrm-level-data)
