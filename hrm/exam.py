import re
import random as R
import itertools as I
import functools as F
import string as S

from pathlib import Path

from pygments.lexer import RegexLexer
from pygments.token import Name, Keyword, Punctuation, Number, Text, Comment
from pygments.formatters import LatexFormatter
from pygments import highlight

from . import words as W
from .parse import parse, LBLDEF, Str
from .hrmx import HRMX
from . import ops


class Func:
    _builtins = {"R": R, "W": W, "I": I, "F": F, "S": S}

    def __init__(self, name, args, expr, env={}):
        self.name = name
        self.args = tuple(args)
        self.expr = expr.strip()
        self.code = compile(self.expr, f"<{name}>", "eval")
        self._env = self._builtins.copy()
        self._env.update(env)

    def __repr__(self):
        return f"({', '.join(self.args)} => {self.expr})"

    def __call__(self, *args):
        env = self._env.copy()
        env.update(zip(self.args, args))
        return self.eval(self.code, env)

    @classmethod
    def env(cls, extra={}):
        env = cls._builtins.copy()
        env.update(extra)
        return env

    @classmethod
    def eval(cls, expr, extra={}):
        return eval(expr, cls.env(extra))

    @classmethod
    def exec(cls, stmt, extra={}, **more):
        exec(stmt, cls.env(more), extra)


class SourceError(Exception):
    pass


class Source:
    _pyrun = re.compile(r"\s*--\s*\>\>\>\s*(.+)$")
    _meta = {"func": re.compile(r"^\s*--\s*(\w+)\s+([\w\s,]+)=>(.+)$"),
             "expr": re.compile(r"^\s*--\s*(\w+)\s*=\s*(.+)$"),
             "text": re.compile(r"^\s*--\s*(\w+)\s*:\s*(.+)$"),
             "pyrun": re.compile(f"^{_pyrun.pattern}")}

    def __init__(self, src, rand={}):
        self.path = Path(src)
        self._rand = rand
        self._inbox = self._outbox = self._hrm = None
        self.meta = {}
        self._regs = set()
        self._labels = set()
        self.src = []
        self.lno = {}
        self.onl = {}
        for lno, line in enumerate(self.path.open(), start=1):
            line = line.rstrip()
            for kind, rexp in self._meta.items():
                if match := rexp.match(line):
                    break
            else:
                onl = len(self.src) + 1
                self.lno[onl] = lno
                self.onl[lno] = onl
                if match := self._pyrun.search(line):
                    Func.exec(match.group(1), self.meta, line=line, lno=lno)
                    line = line.replace(match.group(0), "")
                self.src.append(line)
                self._scan(line)
                continue
            g = match.groups()
            if kind == "expr":
                if g[0] == "inbox":
                    self.meta[g[0]] = Func(g[0], [], g[1], self.meta)
                else:
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

    def _scan(self, line):
        for tok in parse.tokenize_line(line, 1):
            if isinstance(tok, int):
                self._regs.add(tok)
            elif tok.kind == "lbl":
                self._labels.add(str(tok).rstrip(LBLDEF))

    def __getitem__(self, old):
        return self._rand.get(old, old)

    @property
    @F.cache
    def regs(self):
        return tuple(sorted(self._regs))

    @property
    @F.cache
    def labels(self):
        return tuple(sorted(self._labels))

    @property
    def hrm(self):
        if self._hrm is None:
            self._hrm = HRMX.parse(self.source())
        return self._hrm

    @hrm.deleter
    def hrm(self):
        self._hrm = None

    @property
    def inbox(self):
        if self._inbox is None:
            self._inbox = self.meta["inbox"]()
        return self._inbox

    @inbox.deleter
    def inbox(self):
        self._inbox = None

    @property
    def expected(self):
        box = list(self.inbox)
        out = self.meta["outbox"]
        if not len(box) % len(out.args) == 0:
            raise SourceError("wrong inbox size")
        expected = []
        while box:
            args = [box.pop(0) for _ in out.args]
            if isinstance(val := out(*args), tuple):
                expected.extend(val)
            else:
                expected.append(val)
        return expected

    @property
    def outbox(self):
        return self.hrm(self.inbox)

    def check(self):
        exp, out = self.expected, self.outbox
        if exp != out:
            raise SourceError("expected outbox {exp} but got {out}")

    def source(self, hide={}):
        lines = []
        for num, src in enumerate(self.src, start=1):
            lno = self.lno[num]
            indent = " " * (len(src) - len(src.lstrip()))
            if (h := hide.get(lno, None)) is None:
                lines.append(src)
            elif callable(h):
                lines.append(h(lno, src, indent))
            else:
                if not isinstance(h, str):
                    h = "{indent}-- line {lno}"
                env = dict(self.meta, indent=indent, lno=lno)
                lines.append(Func.eval(f"f{h!r}", env))
        return "\n".join(lines)

    def copy(self, **attr):
        cls = self.__class__
        new = cls.__new__(cls)
        new._inbox = new._outbox = new._hrm = None
        for a in ("_regs", "_labels", "_rand", "src"):
            if a in attr:
                setattr(new, a, attr[a])
            else:
                setattr(new, a, getattr(self, a).copy())
        new.meta = self.meta.copy()
        new.lno = self.lno.copy()
        new.onl = self.onl.copy()
        return new

    def randomize(self, names=W.animals, nregs=9):
        nregs = max(nregs, len(self.regs))
        rand, reg, lbl = {}, {}, {}
        reg.update(zip(self.regs, R.sample(range(nregs), len(self.regs))))
        rand.update(reg)
        lbl.update(zip(self.labels, R.sample(names, len(self.labels))))
        rand.update(lbl)
        RAND = {str(k).upper(): str(v) for k, v in rand.items()}
        sub = re.compile(fr"\b({'|'.join(RAND)})\b", re.I)

        def matchsub(match):
            return RAND.get(match[0].upper(), match[0])

        src = [sub.sub(matchsub, ln) for ln in self.src]
        return self.copy(_regs=set(reg.values()),
                         _labels=set(lbl.values()),
                         src=src,
                         _rand=rand)

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
            yield from ((a,) + t for a in alt
                        for t in self._alt(tail, ops, regs, labels))

    def _alt_chose(self, addr, instr, count):
        outbox = self.outbox
        hrm = self.hrm.copy()
        alt = [[pool[0]] for pool in instr]
        instr = [list(pool[1:]) for pool in instr]
        patch = dict(zip(addr, [a[0] for a in alt]))
        for pos, pool in enumerate(instr):
            while pool and len(alt[pos]) < count:
                c = pool.pop(R.randint(0, len(pool)-1))
                for version in I.product(*([c] if pos == i else a
                                         for i, a in enumerate(alt))):
                    patch = dict(zip(addr, version))
                    hrm.patch(patch)
                    try:
                        if outbox == hrm(self.meta["inbox"]):
                            break
                    except Exception:
                        pass
                else:
                    alt[pos].append(c)
        return alt

    def alt(self, lines, ops=True, regs=True, labels=True, count=0):
        if isinstance(lines, str):
            lines = self.meta[lines]
        addr, instr = [], []
        l2a = {l: a for a, l in self.hrm.lineno.items()}
        ref = []
        for lno in lines:
            onl = self.onl[lno]
            toks = tuple(t for t in parse.tokenize_line(self.src[onl - 1], lno)
                         if t.kind != "skip")
            ref.append(toks)
            _ops = [str(t) for t in toks if t in self._atl_op]
            if _ops and ops:
                for op in _ops[:]:  # [:] => don't change list during iteration
                    _ops.extend(self._atl_op[op] - set(_ops))
            _regs = [int(t) for t in toks if isinstance(t, int)]
            if _regs and regs:
                _regs.extend(set(self.regs) - set(_regs))
            _labels = [str(t) for t in toks if t.kind in ("lbl", "str")]
            if _labels and labels:
                _labels.extend(set(self.labels) - set(_labels))
            addr.append(l2a[onl])
            instr.append(tuple(self._alt(toks, _ops, _regs, _labels)))
        assert all(v[0] == r for v, r in zip(instr, ref))
        if count <= 0:
            count = max(len(i) for i in instr)
        return dict(zip(lines, self._alt_chose(addr, instr, count)))


class SourcePool:
    def __init__(self, paths):
        self.src = [Source(p) for p in paths]

    def pick(self, check=True, names=W.animals, nregs=9):
        src = R.choice(self.src).randomize(names, nregs)
        if check:
            src.check()
        return src


class HRMLexer(RegexLexer):
    name = "HRM"
    aliases = ["hrm"]
    filenames = ["*.hrm"]
    flags = re.I
    tokens = {
        "root": [
            (r"\s+", Text),
            (r"--.*\n", Comment.Single),
            (r"\S+:", Name.Label),
            (fr"\b({'|'.join(ops.colors)})\b", Keyword.Reserved),
            (r"[\[\]]+", Punctuation),
            (r"\d+", Number.Integer),
            (r"\S+", Name.Label),
        ]
    }


class Pygmentize:
    def __init__(self, fmt=LatexFormatter):
        self.lexer = HRMLexer()
        self.formatter = fmt()

    @F.cache
    def __call__(self, source, single=False, **opt):
        if isinstance(source, str):
            src = source
        elif isinstance(source, (tuple, list)):
            src = " ".join(str(t) for t in source)
        elif isinstance(source, Source):
            src = source.source(**opt)
        else:
            raise ValueError("invalid HRM source")
        pyg = highlight(src, self.lexer, self.formatter)
        if single:
            lines = pyg.splitlines()
            return " ".join(lines[1:-1])
        else:
            return pyg
