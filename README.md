# Minimalist Human Resource Machine implementation

This is a Python interpreter for [Human Resource Machine](http://tomorrowcorporation.com/humanresourcemachine) from [Tomorrow Corporation](http://tomorrowcorporation.com).
From the game, one may copy/paste the source code that is edited visually.
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

`hrm` object could also have been called with `verbose=True`, which traces the execution.

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

 * missing `setup.py`
 * missing a real cli script
 * the parser is not very robust
 * generated TikZ code generally requires manual editing

## Borrowed files

 * the content of directory `solutions` is from
   [atesgoral.github.io/hrm-solutions](http://atesgoral.github.io/hrm-solutions)
 * file `hrm/levels.json` is from 
   [github.com/atesgoral/hrm-level-data](http://github.com/atesgoral/hrm-level-data)
