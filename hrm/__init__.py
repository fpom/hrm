# coding: utf-8

import functools, pathlib
from collections import deque

from .parse import parse

ops = {"inbox" : "➡️inbox",
       "outbox" : "outbox➡️" ,
       "copyfrom" : "copyfrom",
       "copyto" : "copyto",
       "add" : "add",
       "sub" : "sub",
       "bumpup" : "bump+",
       "bumpdn" : "bump-",
       "jump" : "jump",
       "jumpz" : "jump=0",
       "jumpn" : "jump<0"}
op_width = max(len(v) for v in ops.values())

def log (method) :
    name = method.__name__[3:]
    @functools.wraps(method)
    def wrapper (self, *args) :
        if self.verbose :
            pre = dict(self.tiles)
            pre["ip"] = self.ip
            pre["hands"] = self.hands
            pre["inbox"] = len(self.inbox)
            pre["outbox"] = len(self.outbox)
        ret = method(self, *args)
        if self.verbose :
            post = []
            hands = False
            for addr in range(max(self.tiles, default=-1) + 1) :
                if (be := pre.get(addr, None)) != (af := self.tiles.get(addr, None)) :
                    post.append(f"🔢 {addr}={af}")
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
    def parse (cls, src) :
        return cls(parse(src))
    def __call__ (self, inbox, verbose=False) :
        self.verbose = verbose
        self.ip = 0
        self.tiles = {}
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
    def __getitem__ (self, addr) :
        if isinstance(addr, int) :
            assert self.tiles.get(addr, None) is not None, f"tile {addr} is empty"
            return self.tiles[addr]
        elif isinstance(addr, list) :
            assert len(addr)==1 and isinstance(addr[0], int), f"invalid address {addr!r}"
            return self[self[addr[0]]]
        else :
            raise ValueError(f"invalid address {addr!r}")
    def __setitem__ (self, addr, value) :
        if isinstance(addr, int) :
            self.tiles[addr] = value
        elif isinstance(addr, list) :
            self[self[addr[0]]] = value
        else :
            raise ValueError(f"invalid address {addr!r}")
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
    def op_copyfrom (self, addr) :
        self.hands = self[addr]
    @log
    def op_copyto (self, addr) :
        self[addr] = self.hands
    @log
    def op_add (self, addr) :
        assert self.hands is not None
        self.hands += self[addr]
    @log
    def op_sub (self, addr) :
        assert self.hands is not None
        self.hands -= self[addr]
    @log
    def op_bumpup (self, addr) :
        self.hands = self[addr] = self[addr] + 1
    @log
    def op_bumpdn (self, addr) :
        self.hands = self[addr] = self[addr] - 1
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
