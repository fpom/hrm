import inspect
import json
import pathlib
import time

from typing import Union, get_origin, get_args
from rich import print as rprint
from rich.status import Status
from rich.text import Text

from .parse import parse as hrmparse
from .ops import colors


class Logger:
    def __init__(self, status, width):
        self.s = status
        self.c = status.console
        self.w = width

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    _log_hands = {"inbox", "copyfrom", "copyto", "add", "sub",
                  "bumpup", "bumpdn"}

    def __call__(self, op, args, hrm, err=None):
        opargs = Text(" ".join(f"{x}" for x in (op, *args)),  style=colors[op])
        opargs.align("left", self.w)
        text = [opargs]
        if err is not None:
            more = Text.from_markup(f"[bold red]{err}[/]")
        elif op in self._log_hands:
            more = Text(f"{hrm.hands}")
        elif op == "outbox" and hrm.outbox:
            more = Text(f"{hrm.outbox[-1]}")
        else:
            more = None
        if more is not None:
            text.append(Text.from_markup(" [dim]=>[/] "))
            text.append(more)
        self.c.print(Text.assemble(*text))


class HRMError(Exception):
    @classmethod
    def check(cls, cond, message):
        if not cond:
            raise cls(message)


class HRMStepsError(HRMError):
    pass


class HRM (object):
    def __init__(self, prog, labels):
        self.prog = tuple((op.sub(op.lower()), *args) for op, *args in prog)
        self.labels = dict(labels)

    @classmethod
    def parse(cls, src):
        return cls(*hrmparse(src))

    @classmethod
    def level(cls, level):
        path = pathlib.Path(__file__).parent / "levels.json"
        for lvl in json.load(path.open()):
            if lvl["number"] == level:
                return lvl
        raise ValueError(f"level {level} not found")

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

    def runlevel(self, level, example=0, verbose=0):
        if isinstance(level, int):
            level = self.level(level)
        if "floor" in level and "tiles" in level["floor"]:
            floor = level["floor"]["tiles"]
        else:
            floor = []
        return self(level["examples"][example]["inbox"], floor, verbose)

    def _dummy_log(self, *_):
        pass

    def iter(self, inbox, floor=[], log=None, maxsteps=0):
        if log is None:
            log = self._dummy_log
        self.state = {}
        self.state.update(ip=0, hands=None)
        if isinstance(floor, dict):
            self.state.update((int(k), v) for k, v in floor.items())
        else:
            self.state.update(enumerate(floor))
        self.inbox = list(inbox)
        self.outbox = []
        while 0 <= self.ip < len(self.prog):
            yield self.ip
            op, *args = self.prog[self.ip]
            self.ip += 1
            handler = getattr(self, f"op_{op}")
            try:
                if handler(*args):
                    log(op, args, self, "STOP")
                    break
            except HRMError as err:
                log(op, args, self, err)
                raise
            log(op, args, self)
            maxsteps -= 1
            HRMStepsError.check(maxsteps != 0, "too many steps")

    def __call__(self, inbox, floor=[], verbose=0, delay=0.0, maxsteps=0):
        if verbose:
            rprint("[bold green]INBOX:[/] ",
                   *(Text(f"{i}") for i in inbox))
        if verbose > 1:
            width = max(len(op) + sum(len(str(a)) for a in args) + len(args)
                        for op, *args in self.prog)
            with Status("working...") as status, Logger(status, width) as log:
                for _ in self.iter(inbox, floor, log, maxsteps):
                    time.sleep(delay)
        else:
            try:
                list(self.iter(inbox, floor, None, maxsteps))
            except HRMError as error:
                if verbose:
                    rprint(f"[red bold]error:[/] {error}")
                raise
        if verbose:
            rprint("[bold green]OUTBOX:[/]",
                   *(Text(f"{i}") for i in self.outbox))
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
        elif isinstance(addr, list) and len(addr) == 1 \
                and isinstance(addr[0], int):
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
        elif isinstance(addr, list) and len(addr) == 1 \
                and isinstance(addr[0], int):
            a = self[addr[0]]
            self[a] = update[a] = value
        else:
            raise ValueError(f"invalid address {addr!r}")

    def op_inbox(self):
        if self.inbox:
            self.hands = self.inbox.pop(0)
        else:
            return True

    def op_outbox(self):
        HRMError.check(self.hands is not None, f"you don't hold any value")
        self.outbox.append(self.hands)
        self.hands = None

    def op_copyfrom(self, addr: Union[int, list]):
        self.hands = self[addr]

    def op_copyto(self, addr: Union[int, list]):
        HRMError.check(self.hands is not None, f"you don't hold any value")
        self[addr] = self.hands

    def op_add(self, addr: Union[int, list]):
        HRMError.check(self.hands is not None, f"you don't hold any value")
        HRMError.check(isinstance(self.hands, int),
                       f"cannot add to value {self.hands!r}")
        val = self[addr]
        HRMError.check(isinstance(val, int), f"cannot add value {val!r}")
        self.hands += val

    def op_sub(self, addr: Union[int, list]):
        HRMError.check(self.hands is not None, f"you don't hold any value")
        val = self[addr]
        if isinstance(self.hands, int) and isinstance(val, int):
            self.hands -= val
        elif isinstance(self.hands, str) and isinstance(val, str):
            self.hands = ord(self.hands) - ord(val)
        else:
            raise HRMError(f"cannot sub {val!r} from {self.hands!r}")

    def op_bumpup(self, addr: Union[int, list]):
        val = self[addr]
        HRMError.check(isinstance(val, int),
                       f"cannot increment value {self.hands!r}")
        self.hands = self[addr] = val + 1

    def op_bumpdn(self, addr: Union[int, list]):
        val = self[addr]
        HRMError.check(isinstance(val, int),
                       f"cannot decrement value {self.hands!r}")
        self.hands = self[addr] = val - 1

    def op_jump(self, lbl: str):
        HRMError.check(lbl in self.labels, f"labels {lbl} is not defined")
        pos = self.labels[lbl]
        HRMError.check(0 <= pos <= len(self.prog), f"invalid program position")
        if pos == len(self.prog):
            return True
        self.ip = pos

    def op_jumpz(self, lbl: str):
        HRMError.check(lbl in self.labels, f"labels {lbl} is not defined")
        pos = self.labels[lbl]
        HRMError.check(self.hands is not None, f"you don't hold any value")
        HRMError.check(0 <= pos <= len(self.prog), f"invalid program position")
        if self.hands == 0:
            if pos == len(self.prog):
                return True
            self.ip = pos

    def op_jumpn(self, lbl: str):
        HRMError.check(lbl in self.labels, f"labels {lbl} is not defined")
        pos = self.labels[lbl]
        HRMError.check(self.hands is not None, f"you don't hold any value")
        HRMError.check(0 <= pos <= len(self.prog), f"invalid program position")
        if self.hands < 0:
            if pos >= len(self.prog):
                return True
            self.ip = pos
