# coding: utf-8

VERSION = "1.0"

import functools, pathlib, json
from collections import deque

from colorama import Fore as F, Back as B, Style as S

from .parse import parse

colors = {"inbox" : F.GREEN,
          "outbox" : F.GREEN,
          "copyfrom" : F.RED,
          "copyto" : F.RED,
          "add" : B.YELLOW,
          "sub" : B.YELLOW,
          "bumpup" : B.YELLOW,
          "bumpdn" : B.YELLOW,
          "jump" : F.BLUE,
          "jumpz" : F.BLUE,
          "jumpn" : F.BLUE}
op_width = max(len(v) for v in colors)

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
        err = None
        try :
            ret = method(self, *args)
        except AssertionError as exc :
            err = exc
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
            head = (colors[name]
                    + " ".join([name] + [str(a) for a in args]).ljust(op_width + 3)
                    + S.RESET_ALL)
            if err :
                print(head, f"😡 {err}")
            elif ret is True :
                print(head, "🛑")
            elif post :
                print(head, " / ".join(post))
            else :
                print(head)
        if err is not None :
            raise err
        else :
            return ret
    return wrapper

class HRM (object) :
    def __init__ (self, prog) :
        self.prog = tuple(prog)
    @classmethod
    def parse (cls, src) :
        return cls(parse(src))
    def level (self, level) :
        path = pathlib.Path(__file__).parent / "levels.json"
        for lvl in json.load(path.open()) :
            if lvl["number"] == level :
                return lvl
    def runlevel (self, level, example=0, verbose=False) :
        if isinstance(level, int) :
            level = self.level(level)
        if "floor" in level and "tiles" in level["floor"] :
            floor = level["floor"]["tiles"]
        else :
            floor = []
        return self(level["examples"][example]["inbox"], floor, verbose)
    def __call__ (self, inbox, floor=[], verbose=False) :
        self.verbose = verbose
        self.ip = 0
        if isinstance(floor, dict) :
            self.tiles = {int(k) : v for k, v in floor.items()}
        else :
            self.tiles = dict(enumerate(floor))
        self.inbox = deque(inbox)
        self.outbox = []
        self.hands = None
        while True :
            if self.ip >= len(self.prog) :
                break
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
        assert self.hands is not None, f"you don't hold any value"
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
        assert self.hands is not None, f"you don't hold any value"
        assert isinstance(self.hands, int), f"cannot add to value {self.hands!r}"
        val = self[addr]
        assert isinstance(val, int), f"cannot add value {val!r}"
        self.hands += val
    @log
    def op_sub (self, addr) :
        assert self.hands is not None, f"you don't hold any value"
        val = self[addr]
        if isinstance(self.hands, int) and isinstance(val, int) :
            self.hands -= val
        elif isinstance(self.hands, str) and isinstance(val, str) :
            self.hands = ord(self.hands) - ord(val)
        else :
            assert False, f"cannot sub {val!r} from {self.hands!r}"
    @log
    def op_bumpup (self, addr) :
        val = self[addr]
        assert isinstance(val, int), f"cannot increment value {self.hands!r}"
        self.hands = self[addr] = val + 1
    @log
    def op_bumpdn (self, addr) :
        val = self[addr]
        assert isinstance(val, int), f"cannot decrement value {self.hands!r}"
        self.hands = self[addr] = val - 1
    @log
    def op_jump (self, pos) :
        assert 0 <= pos <= len(self.prog), f"invalid program position"
        if pos == len(self.prog) :
            return True
        self.ip = pos
    @log
    def op_jumpz (self, pos) :
        assert self.hands is not None, f"you don't hold any value"
        assert 0 <= pos <= len(self.prog), f"invalid program position"
        if self.hands == 0 :
            if pos == len(self.prog) :
                return True
            self.ip = pos
    @log
    def op_jumpn (self, pos) :
        assert self.hands is not None, f"you don't hold any value"
        assert 0 <= pos <= len(self.prog), f"invalid program position"
        if self.hands < 0 :
            if pos == len(self.prog) :
                return True
            self.ip = pos
