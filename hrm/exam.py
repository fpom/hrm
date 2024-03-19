import re
import random
import itertools
import functools
import string

from .parse import parse
from . import HRM, words


class Func:
    _builtins = {"R": random,
                 "W": words,
                 "I": itertools,
                 "F": functools,
                 "S": string}

    def __init__(self, args, expr, env={}):
        self.args = tuple(args)
        self.expr = expr.strip()
        self._env = env

    def __repr__(self):
        return f"({', '.join(self.args)} => {self.expr})"

    def __call__(self, *args):
        env = dict(self._env)
        env.update(zip(self.args, args))
        return self.eval(self.expr, env)

    @classmethod
    def env(cls, extra={}):
        env = dict(cls._builtins)
        env.update(extra)
        return env

    @classmethod
    def eval(cls, expr, extra={}):
        return eval(expr, cls.env(extra))

    @classmethod
    def exec(cls, stmt, extra={}, **more):
        exec(stmt, cls.env(more), extra)


class CheckError(Exception):
    def __init__(self, name, message):
        super().__init__(f"[{name}]: {message}")


class Source:
    _pyrun = re.compile(r"\s*--\s*\>\>\>\s*(.+)$")
    _meta = {"func": re.compile(r"^\s*--\s*(\w+)\s+([\w\s,]+)=>(.+)$"),
             "expr": re.compile(r"^\s*--\s*(\w+)\s*=\s*(.+)$"),
             "text": re.compile(r"^\s*--\s*(\w+)\s*:\s*(.+)$"),
             "pyrun": re.compile(f"^{_pyrun.pattern}")}

    def __init__(self, src):
        self.meta = {}
        self.tokens = []
        self.lno = {}
        self.onl = {}
        for lno, line in enumerate(parse.read(src).splitlines(), start=1):
            for kind, rexp in self._meta.items():
                if match := rexp.match(line):
                    break
            else:
                onl = len(self.tokens) + 1
                self.lno[onl] = lno
                self.onl[lno] = onl
                if match := self._pyrun.search(line):
                    Func.exec(match.group(1), self.meta, line=line, lno=lno)
                    line = line.replace(match.group(0), "")
                self.tokens.append(list(parse.tokenize_line(line, onl)))
                continue
            g = match.groups()
            if kind == "expr":
                self.meta[g[0]] = Func.eval(g[1], self.meta)
            elif kind == "text":
                self.meta[g[0]] = g[1].strip()
            elif kind == "pyrun":
                Func.exec(g[0], self.meta)
            elif kind == "func":
                self.meta[g[0]] = Func([a for s in g[1].split(",")
                                        if (a := s.strip())],
                                       g[2], self.meta)

    def source(self, hide={}):
        lines = []
        for num, toks in enumerate(self.tokens, start=1):
            lno = self.lno[num]
            ind = []
            for t in toks:
                if t.kind == "skip" and not t.strip():
                    ind.append(t)
                else:
                    break
            indent = "".join(ind)
            if (h := hide.get(lno, None)) is None:
                lines.append("".join(str(t) for t in toks))
            elif callable(h):
                lines.append(h(lno, toks[0].line, indent))
            else:
                if not isinstance(h, str):
                    h = "{indent}-- line {lno}"
                env = dict(self.meta, indent=indent, lno=lno)
                lines.append(Func.eval(f"f{h!r}", env))
        return "\n".join(lines)

    def rename(self, remap):
        for line in self.tokens:
            for i, tok in enumerate(line):
                if tok in remap:
                    line[i] = tok.sub(remap[tok])

    def randomize(self, names=words.animals, nregs=9):
        regs = set(tok for line in self.tokens for tok in line
                   if isinstance(tok, int))
        lbls = set(tok for line in self.tokens for tok in line
                   if tok.kind == "str")
        nregs = max(nregs, len(regs))
        remap = {}
        remap.update(zip(regs, random.sample(range(nregs), len(regs))))
        remap.update(zip(lbls, random.sample(names, len(lbls))))
        self.rename(remap)
        return remap

    def check(self, *funcs, inbox="inbox"):
        if not funcs:
            checkers = {k: v for k, v in self.meta.items()
                        if isinstance(v, Func)}
        else:
            checkers = {f: self.meta[f] for f in funcs}
        hrm = HRM.parse(self.source())
        outbox = hrm(self.meta[inbox])
        for name, chk in checkers.items():
            box = list(self.meta[inbox])
            if not len(box) % len(chk.args) == 0:
                raise CheckError(name, "wrong inbox size")
            expected = []
            while box:
                args = [box.pop(0) for _ in chk.args]
                if isinstance(out := chk(*args), tuple):
                    expected.extend(out)
                else:
                    expected.append(out)
            if outbox != expected:
                raise CheckError(name, f"expected {expected} but got {outbox}")
