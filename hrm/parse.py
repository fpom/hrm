import io, pathlib

ops = {"inbox", "outbox", "copyfrom", "copyto", "add", "sub",
       "bumpup", "bumpdn", "jump", "jumpz", "jumpn"}

def tokenize (src) :
    if isinstance(src, io.TextIOBase) :
        stream = src
    elif isinstance(src, str) :
        path = pathlib.Path(src)
        if path.exists() :
            stream = path.open()
        else :
            stream = io.StringIO(src)
    else :
        assert False, "invalid source"
    text = stream.read()
    skip = False
    labels = set()
    for num, (line, raw) in enumerate(((l.strip(), l) for l in text.splitlines()),
                                      start=1) :
        toks = line.split()
        if skip :
            if not line or line.endswith(";") :
                skip = False
        elif not line :
            continue
        elif toks and toks[0].lower() == "define" :
            skip = True
        elif line.startswith("--") or (toks and toks[0].lower() == "comment") :
            continue
        elif line.endswith(":") :
            lbl = line[:-1]
            assert lbl not in labels, (f"[{num}] parse error:"
                                       f" duplicate label {raw!r}")
            labels.add(lbl)
            yield num, "lbl", lbl
        else :
            assert toks and (toks[0].lower() in ops), (f"[{num}] parse error:"
                                                       f" unknown operation {raw!r}")
            toks[0] = toks[0].lower()
            yield num, "op", toks

def parse (src) :
    prog = []
    labels = {}
    for num, kind, obj in tokenize(src) :
        if kind == "lbl" :
            labels[obj] = len(prog)
        elif kind == "op" :
            op, *args = obj
            prog.append((num, [op] + args))
    for pos, (num, cmd) in enumerate(prog) :
        for i, a in enumerate(cmd[1:], start=1) :
            if a in labels :
                cmd[i] = labels[a]
            elif a.startswith("[") and a.endswith("]") :
                try :
                    cmd[i] = [int(a[1:-1])]
                except :
                    assert False, f"[{num}] parse error: invalid integer {a[1:-1]!r}"
            else :
                try :
                    cmd[i] = int(a)
                except :
                    assert False, f"[{num}] parse error: invalid integer {a!r}"
        prog[pos] = cmd
    return prog
