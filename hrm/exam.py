import re
import random as R
import itertools as I
import functools as F
import string as S

from . import words as W
from .parse import parse, LBLDEF
from .hrmx import HRMX, HRMProgramError


class Func:
    _builtins = {"R": R, "W": W, "I": I, "F": F, "S": S}

    def __init__(self, name, args, expr, env={}):
        self.name = name
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
        if name is None:
            super().__init__(message)
        else:
            super().__init__(f"{name}: {message}")


class Source:
    _pyrun = re.compile(r"\s*--\s*\>\>\>\s*(.+)$")
    _meta = {"func": re.compile(r"^\s*--\s*(\w+)\s+([\w\s,]+)=>(.+)$"),
             "expr": re.compile(r"^\s*--\s*(\w+)\s*=\s*(.+)$"),
             "text": re.compile(r"^\s*--\s*(\w+)\s*:\s*(.+)$"),
             "pyrun": re.compile(f"^{_pyrun.pattern}")}

    def __init__(self, src, **check):
        self.meta = {}
        self.tokens = []
        self.lno = {}
        self.onl = {}
        self._hrm = None
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
                self.meta[g[0]] = Func(g[0],
                                       [a for s in g[1].split(",")
                                        if (a := s.strip())],
                                       g[2],
                                       self.meta)
        if check:
            self.check(**check)

    def copy(self):
        cls = self.__class__
        new = cls.__new__(cls)
        new.meta = dict(self.meta)
        new.tokens = [list(toks) for toks in self.tokens]
        new.lno = dict(self.lno)
        new.onl = dict(self.onl)
        new._hrm = None
        return new

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
        new = self.copy()
        for line in new.tokens:
            for i, tok in enumerate(line):
                if tok in remap:
                    line[i] = tok.sub(remap[tok])
        return new

    def randomize(self, names=W.animals, nregs=9):
        regs = self.regs
        lbls = self.labels
        nregs = max(nregs, len(regs))
        remap = {}
        remap.update(zip(regs, R.sample(range(nregs), len(regs))))
        remap.update(zip(lbls, R.sample(names, len(lbls))))
        return remap, self.rename(remap)

    @property
    def hrm(self):
        if self._hrm is None:
            self._hrm = HRMX.parse(self.source())
        return self._hrm

    def expected_outbox(self, inbox, chk):
        if isinstance(inbox, str):
            inbox = self.meta[inbox]
        box = list(inbox)
        if not len(box) % len(chk.args) == 0:
            raise CheckError(chk.name, "wrong inbox size")
        expected = []
        while box:
            args = [box.pop(0) for _ in chk.args]
            if isinstance(out := chk(*args), tuple):
                expected.extend(out)
            else:
                expected.append(out)
        return expected

    def check(self, *funcs, inbox="inbox", floor=[], maxsteps=1024, hrm=None):
        if hrm is None:
            hrm = self.hrm
        if funcs:
            checkers = {f: self.meta[f] for f in funcs}
        else:
            checkers = {k: v for k, v in self.meta.items()
                        if isinstance(v, Func)}
        if isinstance(floor, str):
            floor = self.meta[floor]
        try:
            outbox = hrm(self.meta[inbox], floor, maxsteps=maxsteps)
        except HRMProgramError as err:
            raise CheckError(None, str(err))
        for name, chk in checkers.items():
            expected = self.expected_outbox(inbox, chk)
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
            yield ()
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
            yield from ((head.sub(a),) + t
                        for a in alt
                        for t in self._alt(tail, ops, regs, labels))

    def _alt_check(self, patch, hrm, **check):
        hrm.patch(patch)
        try:
            self.check(hrm=hrm, **check)
            return True
        except CheckError:
            return False

    def _alt_chose(self, addr, instr, count, **check):
        hrm = self.hrm.copy()
        alt = [[pool[0]] for pool in instr]
        instr = [list(pool[1:]) for pool in instr]
        patch = dict(zip(addr, [a[0] for a in alt]))
        assert self._alt_check(patch, hrm, **check)
        for pos, pool in enumerate(instr):
            while pool and len(alt[pos]) < count:
                c = pool.pop(R.randint(0, len(pool)-1))
                for version in I.product(*([c] if pos == i else a
                                         for i, a in enumerate(alt))):
                    patch = dict(zip(addr, version))
                    if self._alt_check(patch, hrm, **check):
                        break
                else:
                    alt[pos].append(c)
        return alt

    def alt(self, lines, ops=True, regs=True, labels=True, count=0, **check):
        addr, instr = [], []
        l2a = {l: a for a, l in self.hrm.lineno.items()}
        ref = []
        for lno in lines:
            onl = self.onl[lno]
            toks = tuple(t for t in self.tokens[onl - 1] if t.kind != "skip")
            ref.append(toks)
            _ops = [t for t in toks if t in self._atl_op]
            if _ops and ops:
                for op in _ops[:]:  # [:] => don't change list during iteration
                    _ops.extend(self._atl_op[op] - set(_ops))
            _regs = [t for t in toks if isinstance(t, int)]
            if _regs and regs:
                _regs.extend(set(self.regs) - set(_regs))
            _labels = [t for t in toks if t.kind in ("lbl", "str")]
            if _labels and labels:
                _labels.extend(set(self.labels) - set(_labels))
            addr.append(l2a[onl])
            instr.append(tuple(self._alt(toks, _ops, _regs, _labels)))
        assert all(v[0] == r for v, r in zip(instr, ref))
        if count <= 0:
            count = max(len(i) for i in instr)
        return dict(zip(lines, self._alt_chose(addr, instr, count, **check)))


class SourcePool:
    def __init__(self, paths, alt, chk={}):
        self.src = [Source(p) for p in paths]
        self.alt = [src.alt(**{k: src.meta.get(v, v) for k, v in alt.items()},
                            **{k: src.meta.get(v, v) for k, v in chk.items()})
                    for src in self.src]

    def pick(self, count=0, rand={}):
        idx = R.randint(0, len(self.src) - 1)
        ren, src = self.src[idx].randomize(**rand)
        alt = {n: [tuple(t.sub(ren[t]) if t in ren else t for t in toks)
                   for toks in a]
               for n, a in self.alt[idx].items()}
        if count > 0:
            for n, a in alt.items():
                if len(a) > count:
                    alt[n] = [a[0]] + R.sample(a[1:], count - 1)
        return ren, src, alt
