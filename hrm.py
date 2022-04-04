# coding: utf-8

import sys, functools, pathlib
from collections import deque

ops = {"inbox" : "➡️inbox",
       "outbox" : "outbox➡️" ,
       "copyfrom" : "copyfrom",
       "copyto" : "copyto",
       "add" : "add",
       "bumpup" : "bump+",
       "bumpdn" : "bump-",
       "jump" : "jump",
       "jumpz" : "jump=0",
       "jumpn" : "jump<0"}
op_width = max(len(v) for v in ops.values())

def parse (text) :
    try :
        text = pathlib.Path(text).open()
    except :
        pass
    try :
        text = text.read()
    except :
        pass
    skip = False
    for num, line in enumerate(l.strip() for l in text.splitlines()) :
        if skip :
            if not line :
                skip = False
        elif not line :
            continue
        elif line.split()[0].lower() == "define" :
            skip = True
        elif line == "-- HUMAN RESOURCE MACHINE PROGRAM --" :
            continue
        elif line.endswith(":") :
            yield num, "lbl", line[:-1]
        else :
            yield num, "op", line.split()

def log (method) :
    name = method.__name__[3:]
    @functools.wraps(method)
    def wrapper (self, *args) :
        if self.verbose :
            pre = dict(self.regs)
            pre["ip"] = self.ip
            pre["hands"] = self.hands
            pre["inbox"] = len(self.inbox)
            pre["outbox"] = len(self.outbox)
        ret = method(self, *args)
        if self.verbose :
            post = []
            hands = False
            for reg in range(max(self.regs, default=-1) + 1) :
                if (be := pre.get(reg, None)) != (af := self.regs.get(reg, None)) :
                    post.append(f"🔢 {reg}={af}")
            if len(self.inbox) != pre["inbox"] :
                post.append(f"📤 {self.hands}")
                hands = True
            if len(self.outbox) != pre["outbox"] :
                post.append(f"📥 {self.outbox[-1]}")
            if hands or self.hands != pre["hands"] :
                post.append(f"😬 {self.hands if self.hands is not None else ''}")
            if pre["ip"] != self.ip :
                post.append(f"👉 {self.ip}")
            head = " ".join([name] + [str(a) for a in args]).ljust(op_width + 3)
            if ret :
                print(head, "🛑")
            elif post :
                print(head, " / ".join(post))
            else :
                print(head)
        return ret
    return wrapper

class HRM (object) :
    def __init__ (self, prog) :
        self.prog = tuple(prog)
    @classmethod
    def parse (cls, text) :
        prog = []
        labels = {}
        for num, kind, obj in parse(text) :
            if kind == "lbl" :
                labels[obj] = len(prog)
            elif kind == "op" :
                op, *args = obj
                assert hasattr(cls, f"op_{op.lower()}"), line
                prog.append([op] + args)
        for cmd in prog :
            for i, a in enumerate(cmd[1:], start=1) :
                if a in labels :
                    cmd[i] = labels[a]
                else :
                    cmd[i] = int(a)
        return cls(prog)
    def __call__ (self, inbox, verbose=False) :
        self.verbose = verbose
        self.ip = 0
        self.regs = {}
        self.inbox = deque(inbox)
        self.outbox = []
        self.hands = None
        while True :
            op, *args = self.prog[self.ip]
            self.ip += 1
            handler = getattr(self, f"op_{op.lower()}")
            if handler(*args) :
                break
        return self.outbox
    def op_comment (self, *args) :
        pass
    @log
    def op_inbox (self) :
        if self.inbox :
            self.hands = self.inbox.popleft()
        else :
            return True
    @log
    def op_outbox (self) :
        assert self.hands is not None
        self.outbox.append(self.hands)
        self.hands = None
    @log
    def op_copyfrom (self, reg) :
        assert self.regs.get(reg, None) is not None
        self.hands = self.regs[reg]
    @log
    def op_copyto (self, reg) :
        assert self.hands is not None
        self.regs[reg] = self.hands
    @log
    def op_add (self, reg) :
        assert self.hands is not None
        assert self.regs.get(reg, None) is not None
        self.hands += self.regs[reg]
    @log
    def op_sub (self, reg) :
        assert self.hands is not None
        assert self.regs.get(reg, None) is not None
        self.hands -= self.regs[reg]
    @log
    def op_bumpup (self, reg) :
        assert self.regs.get(reg, None) is not None
        self.regs[reg] += 1
        self.hands = self.regs[reg]
    @log
    def op_bumpdn (self, reg) :
        assert self.regs.get(reg, None) is not None
        self.regs[reg] -= 1
        self.hands = self.regs[reg]
    @log
    def op_jump (self, pos) :
        assert 0 <= pos < len(self.prog)
        self.ip = pos
    @log
    def op_jumpz (self, pos) :
        assert self.hands is not None
        assert 0 <= pos < len(self.prog)
        if self.hands == 0 :
            self.ip = pos
    @log
    def op_jumpn (self, pos) :
        assert self.hands is not None
        assert 0 <= pos < len(self.prog)
        if self.hands < 0 :
            self.ip = pos

def tikz (text, out=None) :
    if out is None :
        out = sys.stdout
    elif isinstance(out, str) :
        out = open(out, "w")
    out.write("\\documentclass{standalone}\n"
              "\\usepackage{hrm}\n"
              "\\begin{document}\n"
              "\\begin{tikzpicture}[yscale=.9]\n")
    color = {"inbox" : "green",
             "outbox" : "green",
             "copyfrom" : "red",
             "copyto" : "red",
             "add" : "orange",
             "sub" : "orange",
             "bumpup" : "orange",
             "bumpdn" : "orange",
             "jump" : "blue",
             "jumpz" : "blue",
             "jumpn" : "blue"}
    label = {"inbox" : "\\raisebox{-.2ex}{\\ding{231}}\\texttt{inbox}",
             "outbox" : "\\texttt{outbox}\,\\raisebox{-.2ex}{\\ding{231}}",
             "copyfrom" : "\\texttt{copyfrom}",
             "copyto" : "\\texttt{copyto}",
             "add" : "\\texttt{add}",
             "sub" : "\\texttt{sub}",
             "bumpup" : "\\texttt{bump+}",
             "bumpdn" : "\\texttt{bump-}",
             "jump" : "\\texttt{jump}",
             "jumpz" : "\\texttt{jump}${}^{\\texttt{\\relsize{-1}if}}_{\\texttt{\\relsize{-1}zero}}$",
             "jumpn" : "\\texttt{jump}${}^{\\texttt{\\relsize{-1}if}}_{\\texttt{\\relsize{-1}negative}}$"}
    skip = False
    y = 0
    for num, kind, obj in parse(text) :
        if kind == "lbl" :
            out.write(f"% {obj}:\n"
                      f"\\node[lbl] ({obj}) at (0,{y}) {{}};\n")
            y -= 1;
        elif kind == "op" :
            op, *args = obj
            op = op.lower()
            if op == "comment" :
                continue
            elif op in ("jumpz", "jumpn", "jump") :
                out.write(f"% {' '.join(obj)}\n"
                          f"\\node[hrm={color[op]}] (n{-y}) at (0,{y})"
                          f" {{{label[op]}}};\n"
                          f"\\begin{{scope}}[on background layer]\n"
                          f"\\draw (n{-y}.east) edge[jmp=40] ({args[0]}.east);\n"
                          f"\\end{{scope}}\n")
            else :
                out.write(f"% {' '.join(obj)}\n"
                          f"\\node[hrm={color[op]}] at (0,{y}) {{{label[op]}"
                          f" \\texttt{{{' '.join(args)}}}}};\n")
            y -= 1
    out.write("\\end{tikzpicture}\n"
              "\\end{document}")
