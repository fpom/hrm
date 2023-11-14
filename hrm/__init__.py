# coding: utf-8

import functools
import inspect
import json
import pathlib

from colorama import Fore as F
from colorama import Style as S

from .parse import parse as hrmparse

VERSION = "1.3"

colors = {"inbox": F.GREEN,
          "outbox": F.GREEN,
          "copyfrom": F.RED,
          "copyto": F.RED,
          "add": F.YELLOW+S.DIM,
          "sub": F.YELLOW+S.DIM,
          "bumpup": F.YELLOW+S.DIM,
          "bumpdn": F.YELLOW+S.DIM,
          "jump": F.BLUE,
          "jumpz": F.BLUE,
          "jumpn": F.BLUE}
op_width = max(len(v) for v in colors)


class HRMError(Exception):
    @classmethod
    def check(cls, cond, message):
        if not cond:
            raise cls(message)


def log(method):
    name = method.__name__[3:]

    @functools.wraps(method)
    def wrapper(self, *args):
        if self.verbose:
            self.update = {"inbox": len(self.inbox),
                           "outbox": len(self.outbox)}
        err = None
        try:
            ret = method(self, *args)
        except HRMError as exc:
            err = exc
        if self.verbose:
            head = (colors[name]
                    + " ".join([name]
                               + [str(a) for a in args]).ljust(op_width + 3)
                    + S.RESET_ALL)
            if err:
                print(head, f"😡 {err}")
            elif ret is True:
                print(head, "🛑")
            else:
                post = []
                for key, val in self.update.items():
                    if key == "inbox" and len(self.inbox) != val:
                        post.append(f"📤 {self.hands}")
                    elif key == "outbox" and len(self.outbox) != val:
                        post.append(f"📥 {self.outbox[-1]}")
                    elif isinstance(key, int):
                        post.append(f"🔢 {key}←{val}")
                    elif key == "ip":
                        post.append(f"👉 {self.ip}")
                    elif key == "hands":
                        hands = self.hands if self.hands is not None else ''
                        post.append(f"😬 {hands}")
                print(head, " / ".join(post))
        if err is not None:
            raise err
        else:
            return ret

    return wrapper


class HRM (object):
    def __init__(self, prog, labels):
        self.prog = tuple(prog)
        self.labels = dict(labels)
        self.check()
        self.verbose = False

    @classmethod
    def parse(cls, src):
        return cls(*hrmparse(src))

    @classmethod
    def from_level(cls, level):
        strlvl = str(level)
        path = pathlib.Path(__file__).parent / "solutions.json"
        solutions = json.load(path.open())
        if strlvl not in solutions:
            raise ValueError(f"missing level {level!r}")
        sol = solutions[strlvl]
        lvl = cls.level(level)
        if lvl is None:
            raise ValueError(f"missing level {level}")
        if "floor" in lvl and "tiles" in lvl["floor"]:
            floor = lvl["floor"]["tiles"]
        else:
            floor = []
        inbox = lvl["examples"][0]["inbox"]
        return cls.parse(sol["source"]), inbox, floor

    @classmethod
    def level(cls, level):
        path = pathlib.Path(__file__).parent / "levels.json"
        for lvl in json.load(path.open()):
            if lvl["number"] == level:
                return lvl

    def runlevel(self, level, example=0, verbose=False):
        if isinstance(level, int):
            level = self.level(level)
        if "floor" in level and "tiles" in level["floor"]:
            floor = level["floor"]["tiles"]
        else:
            floor = []
        return self(level["examples"][example]["inbox"], floor, verbose)

    def iter(self, inbox, floor=[]):
        self.state = {"ip": 0, "hands": None}
        if isinstance(floor, dict):
            self.state.update((int(k), v) for k, v in floor.items())
        else:
            self.state.update(enumerate(floor))
        self.inbox = list(inbox)
        self.outbox = []
        yield 0
        done = False
        while not done:
            if self.ip >= len(self.prog):
                break
            op, *args = self.prog[self.ip]
            self.ip += 1
            handler = getattr(self, f"op_{op.lower()}")
            done = handler(*args)
            if not done:
                yield self.ip

    def __call__(self, inbox, floor=[], verbose=False):
        self.verbose = verbose
        for _ in self.iter(inbox, floor):
            pass
        return self.outbox

    @property
    def ip(self):
        return self["ip"]

    @ip.setter
    def ip(self, value):
        self["ip"] = value

    @property
    def hands(self):
        return self["hands"]

    @hands.setter
    def hands(self, value):
        self["hands"] = value

    def __getitem__(self, addr):
        if addr == "ip":
            return self.state["ip"]
        elif addr == "hands":
            return self.state["hands"]
        elif isinstance(addr, int):
            HRMError.check(self.state.get(addr, None) is not None,
                           f"tile {addr} is empty")
            return self.state[addr]
        elif isinstance(addr, list) and len(addr) == 1 and isinstance(addr[0], int):
            return self[self[addr[0]]]
        else:
            raise ValueError(f"invalid address {addr!r}")

    def __setitem__(self, addr, value):
        update = getattr(self, "update", {})
        if addr == "ip":
            self.state["ip"] = update["ip"] = value
        elif addr == "hands":
            self.state["hands"] = update["hands"] = value
        elif isinstance(addr, int):
            self.state[addr] = update[addr] = value
        elif isinstance(addr, list) and len(addr) == 1 and isinstance(addr[0], int):
            a = self[addr[0]]
            self[a] = update[a] = value
        else:
            raise ValueError(f"invalid address {addr!r}")

    def check(self):
        for op, *args in self.prog:
            fun = getattr(self, f"op_{op.lower()}", None)
            HRMError.check(fun is not None, f"unknown operation {op}")
            sig = inspect.signature(fun)
            try:
                bound = sig.bind(*args)
            except TypeError:
                raise HRMError(f"invalid arguments for {op}: {args}")
            for name, value in bound.arguments.items():
                annot = sig.parameters[name].annotation
                HRMError.check(isinstance(value, annot),
                               f"invalid argument for {op}: {value}")
                if annot is str:
                    HRMError.check(value in self.labels,
                                   f"undefined label {value}")

    @log
    def op_inbox(self):
        if self.inbox:
            self.hands = self.inbox.pop(0)
        else:
            return True

    @log
    def op_outbox(self):
        HRMError.check(self.hands is not None, f"you don't hold any value")
        self.outbox.append(self.hands)
        self.hands = None

    @log
    def op_copyfrom(self, addr: int):
        self.hands = self[addr]

    @log
    def op_copyto(self, addr: int):
        HRMError.check(self.hands is not None, f"you don't hold any value")
        self[addr] = self.hands

    @log
    def op_add(self, addr: int):
        HRMError.check(self.hands is not None, f"you don't hold any value")
        HRMError.check(isinstance(self.hands, int),
                       f"cannot add to value {self.hands!r}")
        val = self[addr]
        HRMError.check(isinstance(val, int), f"cannot add value {val!r}")
        self.hands += val

    @log
    def op_sub(self, addr: int):
        HRMError.check(self.hands is not None, f"you don't hold any value")
        val = self[addr]
        if isinstance(self.hands, int) and isinstance(val, int):
            self.hands -= val
        elif isinstance(self.hands, str) and isinstance(val, str):
            self.hands = ord(self.hands) - ord(val)
        else:
            raise HRMError(f"cannot sub {val!r} from {self.hands!r}")

    @log
    def op_bumpup(self, addr: int):
        val = self[addr]
        HRMError.check(isinstance(val, int),
                       f"cannot increment value {self.hands!r}")
        self.hands = self[addr] = val + 1

    @log
    def op_bumpdn(self, addr: int):
        val = self[addr]
        HRMError.check(isinstance(val, int),
                       f"cannot decrement value {self.hands!r}")
        self.hands = self[addr] = val - 1

    @log
    def op_jump(self, lbl: str):
        HRMError.check(lbl in self.labels, f"labels {lbl} is not defined")
        pos = self.labels[lbl]
        HRMError.check(0 <= pos <= len(self.prog), f"invalid program position")
        if pos == len(self.prog):
            return True
        self.ip = pos

    @log
    def op_jumpz(self, lbl: str):
        HRMError.check(lbl in self.labels, f"labels {lbl} is not defined")
        pos = self.labels[lbl]
        HRMError.check(self.hands is not None, f"you don't hold any value")
        HRMError.check(0 <= pos <= len(self.prog), f"invalid program position")
        if self.hands == 0:
            if pos == len(self.prog):
                return True
            self.ip = pos

    @log
    def op_jumpn(self, lbl: str):
        HRMError.check(lbl in self.labels, f"labels {lbl} is not defined")
        pos = self.labels[lbl]
        HRMError.check(self.hands is not None, f"you don't hold any value")
        HRMError.check(0 <= pos <= len(self.prog), f"invalid program position")
        if self.hands < 0:
            if pos == len(self.prog):
                return True
            self.ip = pos
