# Minimalist Human Resource Machine implementation

This is a Python interpreter for [Human Resource Machine](http://tomorrowcorporation.com/humanresourcemachine) from [Tomorrow Corporation](http://tomorrowcorporation.com).
From the game, one may copy/paste the source code that is edited visually.
This library features a parser for this code, an interpreter, and a translator into TikZ pictures to be included in LaTeX.

```pycon
>>> from hrm import HRM, tikz
>>> hrm = HRM.parse('test/level-7.hrm')
>>> hrm([1, 0, -2, 'D', 0, 0, 8, 9])
[1, -2, 'D', 8, 9]
>>> tikz('test/level-7.hrm', open('lvl.tex', 'w'))
```

`hrm` object could also have been called with `verbose=True`, which traces the execution.
TikZ code requires to use package `hrm.sty`.

## Limitations

 * the parser is not very robust
 * generated TikZ code generally requires manual editing

## Tests

The content of directory `test` has been borrowed from:

 * [atesgoral.github.io/hrm-solutions](http://atesgoral.github.io/hrm-solutions)
   for the solutions (`solutions.json` and sub-directory `solutions`)
 * [github.com/atesgoral/hrm-level-data](http://github.com/atesgoral/hrm-level-data)
   for the information about levels (`levels.json`)
