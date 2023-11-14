import io
import pathlib

ops = {"inbox", "outbox", "copyfrom", "copyto", "add", "sub",
       "bumpup", "bumpdn", "jump", "jumpz", "jumpn"}


class ParseError(Exception):
    def __init__(self, lineno, message):
        if lineno is None:
            super().__init__(message)
        else:
            super().__init__(f"[{lineno}] {message}")
        self.lineno = lineno
        self.message = message

    @classmethod
    def check(cls, cond, lineno, message):
        if not cond:
            raise cls(lineno, message)


def tokenize(src):
    if isinstance(src, io.TextIOBase):
        stream = src
    elif isinstance(src, str):
        path = pathlib.Path(src)
        if path.exists():
            stream = path.open()
        else:
            stream = io.StringIO(src)
    else:
        raise ParseError(None, "invalid source")
    text = stream.read()
    skip = False
    labels = set()
    for num, (line, raw) in enumerate(((ln.strip(), ln)
                                       for ln in text.splitlines()),
                                      start=1):
        toks = line.split()
        if skip:
            if not line or line.endswith(";"):
                skip = False
        elif not line:
            continue
        elif toks and toks[0].lower() == "define":
            skip = True
        elif line.startswith("--") or (toks and toks[0].lower() == "comment"):
            continue
        elif line.endswith(":"):
            lbl = line[:-1].strip()
            ParseError.check(lbl not in labels,
                             num,
                             f"parse error: duplicate label {raw!r}")
            labels.add(lbl)
            yield num, "lbl", lbl
        else:
            ParseError.check(toks and (toks[0].lower() in ops),
                             num,
                             f"[{num}] parse error: unknown operation {raw!r}")
            toks[0] = toks[0].lower()
            yield num, "op", toks


def parse(src):
    prog = []
    labels = {}
    for num, kind, obj in tokenize(src):
        if kind == "lbl":
            labels[obj] = len(prog)
        elif kind == "op":
            op, *args = obj
            prog.append((num, [op] + args))
    for pos, (num, cmd) in enumerate(prog):
        for i, a in enumerate(cmd[1:], start=1):
            if a in labels:
                pass
            elif a.startswith("[") and a.endswith("]"):
                try:
                    cmd[i] = [int(a[1:-1])]
                except Exception:
                    raise ParseError(num, f"invalid integer {a[1:-1]!r}")
            else:
                try:
                    cmd[i] = int(a)
                except Exception:
                    raise ParseError(num, f"invalid integer {a!r}")
        prog[pos] = cmd
    return prog, labels
