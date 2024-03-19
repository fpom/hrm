import io
import re
import pathlib

ops = {"inbox": None,
       "outbox": None,
       "copyfrom": int,
       "copyto": int,
       "add": int,
       "sub": int,
       "bumpup": int,
       "bumpdn": int,
       "jump": str,
       "jumpz": str,
       "jumpn": str}


class ParseError(Exception):
    def __init__(self, message, token=None):
        if token is None:
            super().__init__(self, message)
            self.lineno = self.token = None
        else:
            super().__init__(f"[{token.lineno}] {message}\n"
                             f"  {token.line}\n"
                             f"  {' ' * token.start}"
                             f"{'^' * (token.end - token.start)}\n")
            self.lineno = token.lineno
            self.token = token
        self.message = message

    @classmethod
    def check(cls, cond, token, message):
        if not cond:
            raise cls(f"parse error: {message}", token)


class Tok(object):
    kind = None
    lineno = None
    line = None
    start = None
    end = None

    def __new__(cls, base, value, kind, lineno, line, start, end):
        obj = base.__new__(cls, value)
        obj.kind = kind
        obj.lineno = lineno
        obj.line = line
        obj.start = start
        obj.end = end
        return obj

    def sub(self, new):
        return self.__class__(new, self.kind, self.lineno, self.line, self.start, self.end)


class Str(str, Tok):
    def __new__(cls, value, kind, lineno, line, start, end):
        return Tok.__new__(cls, str, str(value), kind, lineno, line, start, end)


class Int(int, Tok):
    def __new__(cls, value, kind, lineno, line, start, end):
        return Tok.__new__(cls, int, int(value), kind, lineno, line, start, end)


class Parser:
    tokens = {
        "int": r"\b[0-9]+\b",
        "str": r"\b[a-z]\w*",
        "lsb": r"\[",
        "rsb": r"\]",
        "col": r":",
        "cmt": r"--.*"}

    def __init__(self):
        self.tok = re.compile("|".join(f"(?P<{k}>{v})"
                                       for k, v in self.tokens.items()),
                              re.I)

    def strip(self, line):
        return line.split("--", 1)[0].strip()

    def read(self, src):
        if isinstance(src, io.TextIOBase):
            stream = src
        elif isinstance(src, pathlib.Path):
            stream = src.open()
        elif isinstance(src, str):
            try:
                path = pathlib.Path(src)
                if path.exists():
                    stream = path.open()
                else:
                    stream = io.StringIO(src)
            except OSError:
                stream = io.StringIO(src)
        else:
            raise ParseError("invalid source")
        return stream.read()

    def tokenize_line(self, line, lno):
        pos = 0
        for match in self.tok.finditer(line):
            (k, v), *_ = ((k, v) for k, v in match.groupdict().items()
                          if v is not None)
            start, end = match.span()
            if start > pos:
                yield Str(line[pos:start], "skip", lno, line, pos, start)
            if v.isdecimal():
                yield Int(v, k, lno, line, start, end)
            elif (hd := v.lower()) in ops:
                yield Str(hd, "cmd", lno, line, start, end)
            else:
                yield Str(hd, k, lno, line, start, end)
            pos = end
        if pos < len(line):
            yield Str(line[pos:], "skip", lno, line, pos, len(line))

    def tokenize(self, src, clean=True):
        skip = False
        src = self.read(src)
        for lno, line in enumerate(src.splitlines(), start=1):
            stripped = self.strip(line)
            if skip:
                if not stripped or stripped.endswith(";"):
                    skip = False
                if clean:
                    continue
                yield "skip", [Str(line, "skip", lno, line, 0, len(line))]
            elif not stripped:
                if clean:
                    continue
                yield "skip", [Str(line, "skip", lno, line, 0, len(line))]
            else:
                toks = list(self.tokenize_line(line, lno))
                keep = [t for t in toks if t.kind not in ("skip", "cmt")]
                if not keep or keep[0] == "comment":
                    if clean:
                        continue
                    yield "skip", toks
                elif keep[0] == "define":
                    skip = True
                    if clean:
                        continue
                    yield "skip", toks
                elif keep[-1].kind == "col":
                    if clean:
                        yield "lbl", keep
                    else:
                        yield "lbl", toks
                else:
                    if clean:
                        yield "op", keep
                    else:
                        yield "op", toks

    def __call__(self, src):
        prog = []
        labels = {}
        for kind, toks in self.tokenize(src, True):
            head, *tail = toks
            if kind == "lbl":
                ParseError.check(tail == [":"], head, "invalid label definition")
                ParseError.check(head not in labels, head, "duplicate label")
                labels[head] = len(prog)
            elif kind == "op":
                ParseError.check(head in ops, head, "unknown operation")
                if tail and tail[0].kind == "lsb":
                    ParseError.check(len(tail) == 3
                                     and tail[2].kind == "rsb",
                                     tail[0],
                                     f"invalid arguments")
                    tail = [[tail[1]]]
                spec = ops[head]
                if spec is None:
                    ParseError.check(not tail, head, "unexpected argument")
                    prog.append([head])
                elif len(tail) == 0:
                    raise ParseError("missing argument", head)
                elif len(tail) > 1:
                    raise ParseError("too many arguments", tail[1])
                else:
                    arg = tail[0]
                    if spec is str:
                        ParseError.check(isinstance(arg, str), arg, "invalid argument")
                    elif spec is int:
                        ParseError.check(isinstance(arg, int)
                                         or (isinstance(arg, list)
                                             and len(arg) == 1
                                             and isinstance(arg[0], int)),
                                         arg, "invalid argument")
                    else:
                        assert False
                    prog.append([head, arg])
        return prog, labels


parse = Parser()
