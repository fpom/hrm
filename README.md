# Human Resource Machine interpreter

This is a Python interpreter for programs from the [Human Resource Machine](http://tomorrowcorporation.com/humanresourcemachine) game from [Tomorrow Corporation](http://tomorrowcorporation.com).
Within the game, one may copy/paste the source code that is edited visually.
This library features a parser for this code, and CLI/TUI interpreters.

```pycon
>>> from hrm import HRM
>>> hrm = HRM.parse('level-2.hrm')
>>> hrm([1, 0, -2, 'D', 0, 0, 8, 9])
1 0 -2 D 0 0 8 9
```

## Installation

Just run `pip install hrm-interpreter` or clone the git repository and run `pip install`.

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

Class `hrm.HRM` is the interpreter itself, it is initialised as either:

 * `HRM(prog)`
   creates an instance to run an already parsed program `prog`
 * `HRM.parse(source)`
   creates an instance by parsing source code `source`, it can be a file path, an opened file, or source code given as a `str`
 * `HRM.from_level(number)`
   load a level from the game and returns the corresponding instance, together with a valid inbox and tiles initial state to run it

An `HRM` instance `hrm` can execute the program for various inputs using method `hrm(inbox, floor=[], verbose=False)` which runs the program with `inbox` (`list` of integers or uppercase characters).
If `floor` is provided, it initialised the tiles on the floor.
If `verbose` is `True`, program execution is traced.

## Limitations

 * the parser is not very robust
 
Differences with the game:
 * the number of available tiles is not limited
 * indirection `[A]` is not limited to `copyfrom`
 * a label may be jumped to from several locations in the program, which is never the case in code copied from the game as each jump is attached to exactly one target

## Borrowed files

 * the content of directory `solutions` is from
   [atesgoral.github.io/hrm-solutions](http://atesgoral.github.io/hrm-solutions)
 * file `hrm/levels.json` is from 
   [github.com/atesgoral/hrm-level-data](http://github.com/atesgoral/hrm-level-data)

## Licence

Appart from the borrowed files above, this package is (C) 2023 Franck Pommereau <franck.pommereau@univ-evry.fr> and released under the MIT Licence, see `LICENCE` for details.
