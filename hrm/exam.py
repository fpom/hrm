import re
import random
import itertools
import functools
import string

from .parse import parse, LBLDEF
from . import HRM, words, HRMError


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

    def __getitem__(self, lno):
        toks = self.tokens[self.onl[lno] - 1]
        return "".join(str(t) for t in toks)

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

    @property
    def regs(self):
        return set(tok for line in self.tokens for tok in line
                   if isinstance(tok, int))

    @property
    def labels(self):
        return set(tok.sub(str(tok).rstrip(LBLDEF))
                   for line in self.tokens
                   for tok in line if tok.kind == "lbl")

    def rename(self, remap):
        for line in self.tokens:
            for i, tok in enumerate(line):
                if tok in remap:
                    line[i] = tok.sub(remap[tok])

    def randomize(self, names=words.animals, nregs=9):
        regs = self.regs
        lbls = self.labels
        nregs = max(nregs, len(regs))
        remap = {}
        remap.update(zip(regs, random.sample(range(nregs), len(regs))))
        remap.update(zip(lbls, random.sample(names, len(lbls))))
        self.rename(remap)
        return remap

    def check(self, *funcs, inbox="inbox", floor=[], maxsteps=0):
        if not funcs:
            checkers = {k: v for k, v in self.meta.items()
                        if isinstance(v, Func)}
        else:
            checkers = {f: self.meta[f] for f in funcs}
        hrm = HRM.parse(self.source())
        if isinstance(floor, str):
            floor = self.meta[floor]
        try:
            outbox = hrm(self.meta[inbox], floor, maxsteps=maxsteps)
        except HRMError as err:
            raise CheckError(None, str(err))
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

    _atl_op = {
        "inbox": {"outbox"},
        "outbox": {"inbox"},
        "copyfrom": {"copyto"},
        "copyto": {"copyfrom"},
        "add": {"sub"},
        "sub": {"add"},
        "bumpup": {"bumpdn"},
        "bumpdn": {"bumpup"},
        "jump": {"jumpz", "jumpn"},
        "jumpz": {"jump", "jumpn"},
        "jumpn": {"jump", "jumpz"}}

    def _alt(self, toks, ops, regs, labels):
        if not toks:
            yield []
        else:
            head, *tail = toks
            if head in self._atl_op:
                alt = ops
            elif isinstance(head, int):
                alt = regs
            elif head.kind in ("str", "lbl"):
                alt = labels
            else:
                alt = [head]
            yield from ([a] + t
                        for a in alt
                        for t in self._alt(tail, ops, regs, labels))

    def alt(self, lno, ops=True, regs=True, labels=True, strip=True):
        toks = self.tokens[self.onl[lno] - 1]
        # [] => original line is yielded first
        _ops = [t for t in toks if t in self._atl_op]
        if _ops and ops:
            for op in _ops[:]:  # [:] => avoid changing list during iteration
                _ops.extend(self._atl_op[op] - set(_ops))
        _regs = [t for t in toks if isinstance(t, int)]
        if _regs and regs:
            _regs.extend(set(self.regs) - set(_regs))
        _labels = [t for t in toks if t.kind in ("lbl", "str")]
        if _labels and labels:
            _labels.extend(set(self.labels) - set(_labels))
        yield from ("".join(str(t) for t in alt).strip(None if strip else "\0")
                    for alt in self._alt(toks, _ops, _regs, _labels))
