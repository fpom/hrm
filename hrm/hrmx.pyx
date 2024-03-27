from libc.stdlib cimport malloc, free
from libc.string cimport memcpy
from cython.operator cimport postincrement as _pp, preincrement as pp_

from rich import print as rprint
from rich.text import Text

from .parse import parse as hrmparse, Tok
from .ops import colors

#
#
#

cdef class frozendict:
    "immutable dict"
    cdef dict d

    def __cinit__(self, *args, **kargs):
        self.d = dict(*args, **kargs)

    def __iter__(self):
        yield from self.d

    def __len__(self):
        return len(self.d)

    def __getitem__(self, object key):
        return self.d[key]

    def __eq__(self, other):
        if isinstance(other, frozendict):
            return self.d == other.d
        else:
            return self.d == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"frozendict({self.d!r})"

    cpdef object get(self, object key, object defaut=None):
        return self.d.get(key, defaut)

    cpdef object items(self):
        return self.d.items()

    cpdef object keys(self):
        return self.d.keys()

    cpdef object values(self):
        return self.d.values()

#
# HRM operations
#

cdef enum Op:
    INBOX
    OUTBOX
    COPYFROMIDX
    COPYFROMPTR
    COPYTOIDX
    COPYTOPTR
    ADDIDX
    ADDPTR
    SUBIDX
    SUBPTR
    BUMPUPIDX
    BUMPUPPTR
    BUMPDNIDX
    BUMPDNPTR
    JUMP
    JUMPN
    JUMPZ

# result of executing one operation
cdef enum Stop:
    DONE = 0
    EMPTY = 1
    CAPACITY = 2
    OUTBOUND = 3
    BADOP = 4
    STEPS = 5

# execute one operation
#  - return Stop.STEPS if program may continue
#  - Stop.DONE if program has fully executed
#  - Stop.* if an error occurred
cdef inline Stop step(HRMX hrm) noexcept nogil:
    cdef int op, arg
    cdef Stop s
    cdef unsigned int idx
    if hrm.ip == hrm.prog_len:
        return Stop.DONE
    elif hrm.ip > hrm.prog_len:
        return Stop.OUTBOUND
    op = hrm.prog[_pp(hrm.ip)]
    if op == Op.INBOX:
        if hrm.inbox_pos == hrm.inbox_len:
            return Stop.DONE
        hrm.hands = hrm.inbox[_pp(hrm.inbox_pos)]
        hrm.hands_used = True
    elif op == Op.OUTBOX:
        if not hrm.hands_used:
            return Stop.EMPTY
        if hrm.outbox_pos == hrm.capacity:
            return Stop.CAPACITY
        hrm.outbox[_pp(hrm.outbox_pos)] = hrm.hands
        hrm.hands_used = False
    elif op == Op.COPYFROMIDX:
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        hrm.hands = hrm.tiles[idx]
        hrm.hands_used = True
    elif op == Op.COPYFROMPTR:
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        idx = <unsigned int> hrm.tiles[idx]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        hrm.hands = hrm.tiles[idx]
        hrm.hands_used = True
    elif op == Op.COPYTOIDX:
        if not hrm.hands_used:
            return Stop.EMPTY
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        hrm.tiles[idx] = hrm.hands
        hrm.tiles_used[idx] = True
    elif op == Op.COPYTOPTR:
        if not hrm.hands_used:
            return Stop.EMPTY
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        idx = <unsigned int> hrm.tiles[idx]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        hrm.tiles[idx] = hrm.hands
        hrm.tiles_used[idx] = True
    elif op == Op.ADDIDX:
        if not hrm.hands_used:
            return Stop.EMPTY
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        hrm.hands += hrm.tiles[idx]
    elif op == Op.ADDPTR:
        if not hrm.hands_used:
            return Stop.EMPTY
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        idx = hrm.tiles[idx]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        hrm.hands += hrm.tiles[idx]
    elif op == Op.SUBIDX:
        if not hrm.hands_used:
            return Stop.EMPTY
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        hrm.hands -= hrm.tiles[idx]
    elif op == Op.SUBPTR:
        if not hrm.hands_used:
            return Stop.EMPTY
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        idx = hrm.tiles[idx]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if not hrm.tiles_used[idx]:
            return Stop.EMPTY
        hrm.hands -= hrm.tiles[idx]
    elif op == Op.BUMPUPIDX:
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        arg = hrm.tiles[idx]
        hrm.hands = hrm.tiles[idx] = arg + 1
        hrm.hands_used = True
    elif op == Op.BUMPUPPTR:
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        idx = hrm.tiles[idx]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        arg = hrm.tiles[idx]
        hrm.hands = hrm.tiles[idx] = arg + 1
        hrm.hands_used = True
    elif op == Op.BUMPDNIDX:
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        arg = hrm.tiles[idx]
        hrm.hands = hrm.tiles[idx] = arg - 1
        hrm.hands_used = True
    elif op == Op.BUMPDNPTR:
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        idx = hrm.tiles[idx]
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        if idx >= hrm.capacity:
            return Stop.OUTBOUND
        arg = hrm.tiles[idx]
        hrm.hands = hrm.tiles[idx] = arg - 1
        hrm.hands_used = True
    elif op == Op.JUMP:
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[hrm.ip]
        hrm.ip = idx
    elif op == Op.JUMPZ:
        if not hrm.hands_used:
            return Stop.EMPTY
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if hrm.hands == 0:
            hrm.ip = idx
    elif op == Op.JUMPN:
        if not hrm.hands_used:
            return Stop.EMPTY
        if hrm.ip >= hrm.prog_len:
            return Stop.OUTBOUND
        idx = <unsigned int> hrm.prog[_pp(hrm.ip)]
        if hrm.hands < 0:
            hrm.ip = idx
    else:
        return Stop.BADOP
    return Stop.STEPS

#
# errors during program execution
#

class HRMProgramError(Exception):
    """Error during a program execution

    Attributes:
     - `errno`: error number
     - `strerror`: map error numbers to strings
    """
    strerror = {Stop.DONE: "no error",
                Stop.EMPTY: "empty register",
                Stop.CAPACITY: "capacity exceeded",
                Stop.OUTBOUND: "out of boundary access",
                Stop.BADOP: "invalid operation",
                Stop.STEPS: "maximum number of steps exceeded"}

    def __init__(self, errno, tok=None):
        msg = self.strerror.get(errno, "unknown error")
        if tok is None:
            super().__init__(msg)
        else:
            super().__init__(tok.err(msg, False))
        self.errno = errno

#
# static info to encode/decode operations
#

# op name to Op translation
cdef dict opop = {"inbox": Op.INBOX,
                  "outbox": Op.OUTBOX,
                  "copyfrom": (Op.COPYFROMIDX, Op.COPYFROMPTR),
                  "copyto": (Op.COPYTOIDX, Op.COPYTOPTR),
                  "add": (Op.ADDIDX, Op.ADDPTR),
                  "sub": (Op.SUBIDX, Op.SUBPTR),
                  "bumpup": (Op.BUMPUPIDX, Op.BUMPUPPTR),
                  "bumpdn": (Op.BUMPDNIDX, Op.BUMPDNPTR),
                  "jump": Op.JUMP,
                  "jumpz": Op.JUMPZ,
                  "jumpn": Op.JUMPN}

cdef enum ArgSpec:
    NONE
    IDX
    PTR
    LABEL

cdef dict opspec = {Op.INBOX: ("inbox", ArgSpec.NONE),
                    Op.OUTBOX: ("outbox", ArgSpec.NONE),
                    Op.COPYFROMIDX: ("copyfrom", ArgSpec.IDX),
                    Op.COPYFROMPTR: ("copyfrom", ArgSpec.PTR),
                    Op.COPYTOIDX: ("copyto", ArgSpec.IDX),
                    Op.COPYTOPTR: ("copyto", ArgSpec.PTR),
                    Op.ADDIDX: ("add", ArgSpec.IDX),
                    Op.ADDPTR: ("add", ArgSpec.PTR),
                    Op.SUBIDX: ("sub", ArgSpec.IDX),
                    Op.SUBPTR: ("sub", ArgSpec.PTR),
                    Op.BUMPUPIDX: ("bumpup", ArgSpec.IDX),
                    Op.BUMPUPPTR: ("bumpup", ArgSpec.PTR),
                    Op.BUMPDNIDX: ("bumpdn", ArgSpec.IDX),
                    Op.BUMPDNPTR: ("bumpdn", ArgSpec.PTR),
                    Op.JUMP: ("jump", ArgSpec.LABEL),
                    Op.JUMPZ: ("jumpz", ArgSpec.LABEL),
                    Op.JUMPN: ("jumpn", ArgSpec.LABEL)}
#
# main class
#

cdef class HRMX:
    # arrays length
    cdef unsigned int capacity
    # encoded program
    cdef int* prog
    cdef unsigned int prog_len
    # instruction pointer
    cdef unsigned int ip
    # inbox
    cdef int* inbox
    cdef unsigned int inbox_pos
    cdef unsigned int inbox_len
    # outbox
    cdef int* outbox
    cdef unsigned int outbox_pos
    # registers
    cdef int* tiles
    cdef bint* tiles_used
    # hands
    cdef int hands
    cdef bint hands_used
    # info about programm (labels => addr, addr => original op, addr => source line number)
    cdef readonly frozendict labels, source, lineno
    # inverse of labels
    cdef dict labels_inv

    def __cinit__(self, prog=None, labels=None, unsigned int capacity=512):
        self.capacity = capacity
        self.prog = <int*> malloc(capacity * sizeof(int))
        self.inbox = <int*> malloc(capacity * sizeof(int))
        self.outbox = <int*> malloc(capacity * sizeof(int))
        self.tiles = <int*> malloc(capacity * sizeof(int))
        self.tiles_used = <bint*> malloc(capacity * sizeof(bint))
        self.labels = frozendict()
        self.labels_inv = {}
        self.source = frozendict()
        self.lineno = frozendict()
        self.prog_len = self.ip = 0
        self.inbox_len = self.inbox_pos = self.outbox_pos = 0

    cpdef HRMX copy(self):
        "Copy an HRMX instance."
        copy = HRMX(capacity=self.capacity)
        memcpy(copy.prog, self.prog, self.prog_len * sizeof(int))
        copy.prog_len = self.prog_len
        copy.ip = self.ip
        memcpy(copy.inbox, self.inbox, self.inbox_len * sizeof(int))
        copy.inbox_pos = self.inbox_pos
        copy.inbox_len = self.inbox_len
        memcpy(copy.outbox, self.outbox, self.outbox_pos * sizeof(int))
        copy.outbox_pos = self.outbox_pos
        memcpy(copy.tiles, self.tiles, self.capacity * sizeof(int))
        memcpy(copy.tiles_used, self.tiles_used, self.capacity * sizeof(bint))
        copy.hands = self.hands
        copy.hands_used = self.hands_used
        copy.labels.d.update(self.labels.d)
        copy.source.d.update(self.source.d)
        copy.lineno.d.update(self.lineno.d)
        copy.labels_inv.update(self.labels_inv)
        return copy

    def __dealloc__(self):
        free(self.prog)
        free(self.inbox)
        free(self.outbox)
        free(self.tiles)
        free(self.tiles_used)

    @classmethod
    def parse(cls, src, unsigned int capacity=512):
        """Create an HRMX instance from parsed source.

        Arguments:
         - `src`: program source as expected by parser
         - `capacity: int = 512`: like for `__init__`

        Return: a new HRMX instance
        """
        return cls(*hrmparse(src), capacity)

    def __init__(self, prog=None, labels=None, unsigned int capacity=512):
        """Create a new HRM executor

        If `prog` and `labels` are passed, the program is directly loaded,
        otherwise method `load` has to be used to do so.

        Arguments:
         - `prog: list = None`: program as returned by the parser
         - `labels: dict = None`: labels positions in the program, as returned by the parser
         - `capacity: int = 512`: memories sizes (inbox, outbox, program, registers)
        """
        if prog is not None:
            self.load(prog, labels)
        elif labels is not None:
            raise ValueError("unexpected argument 'labels' when 'prog' is None")

    cpdef unsigned int load(self, prog, labels):
        """Load a program into the executor

        Arguments:
         - `prog: list = None`: program as returned by the parser
         - `labels: dict = None`: labels positions in the program, as returned by the parser

        Return: the length of the loaded program, after encoding
        """
        cdef unsigned int n
        cdef unsigned int p = 0
        cdef dict lbls = {}
        cdef dict addr = {}
        cdef dict n2l = {}
        cdef object op, k
        cdef list args
        if 2 * len(prog) > self.capacity:
            # this is an over approximation but should be DONE in general
            raise ValueError("program too long")
        for k, n in labels.items():
            if n not in n2l:
                n2l[n] = [k]
            else:
                n2l.append(k)
        self.ip = 0
        self.inbox_pos = self.inbox_len = 0
        self.outbox_pos = 0
        self.labels.d.clear()
        self.labels_inv.clear()
        self.source.d.clear()
        self.lineno.d.clear()
        for n, (op, *args) in enumerate(prog):
            addr[n] = p
            self.lineno.d[p] = op.lineno
            if n in n2l:
                for k in n2l[n]:
                    self.labels.d[k] = p
                    self.labels_inv[p] = k
            if not args:
                self.source.d[p] = (op, None)
                self.prog[_pp(p)] = opop[op]
            elif isinstance(args[0], str):
                self.source.d[p] = (op, args[0])
                self.prog[_pp(p)] = opop[op]
                lbls[_pp(p)] = args[0]
            elif isinstance(args[0], int):
                self.source.d[p] = (op, args[0])
                self.prog[_pp(p)] = opop[op][0]
                self.prog[_pp(p)] = args[0]
            elif isinstance(args[0], list):
                self.source.d[p] = (op, args[0])
                self.prog[_pp(p)] = opop[op][1]
                self.prog[_pp(p)] = args[0][0]
            else:
                raise ValueError("invalid program")
        self.prog_len = addr[len(prog)] = p
        for p, k in lbls.items():
            self.prog[p] = self.labels.d[k]
        return self.prog_len

    cpdef void boot(self, inbox, tiles=[]):
        """Start the executor with a given context

        Arguments:
         - `inbox: list`: inbox to be processed
         - `tiles: list = []`: initial content of the registers,
           with `None` where a tile has to be left empty
        """
        cdef unsigned int i
        cdef int v
        cdef object t
        if self.prog_len == 0:
            raise ValueError("no program loaded")
        if len(inbox) > self.capacity:
            raise ValueError("inbox too large")
        if len(tiles) > self.capacity:
            raise ValueError("too many tiles")
        for i in range(self.capacity):
            self.tiles_used[i] = False
        self.hands_used = False
        for i, v in enumerate(inbox):
            self.inbox[i] = v
        self.inbox_len = len(inbox)
        for i, t in enumerate(tiles):
            if t is not None:
                self.tiles[i] = t
                self.tiles_used[i] = True
        self.ip = self.inbox_pos = self.outbox_pos = 0

    def __call__(self, inbox=None, tiles=[], unsigned int maxsteps=1024):
        """Execute a program

        If not `inbox` is provided, method `boot` has to be called.
        The program is executed until its end, or `maxsteps` operations have been
        executed.
        
        Arguments:
         - `inbox: list[int] | None = None`: if not `None`, `inbox` is passed to `boot`
         - `tiles: list[int | None] = []`: is `inbox` is not `None`, `tiles` is also passed to `boot`
         - `maxsteps: int = 1024`: maximum number of operations that can be executed

        Return: produced outbox if program executes to its end, or raise `HRMProgramError`
        if `maxsteps` is reached (or another error occurred).
        """
        cdef unsigned int i, ip
        cdef Stop stop
        if self.prog_len == 0:
            raise ValueError("no program loaded")
        if inbox is not None:
            self.boot(inbox, tiles)
        if self.inbox_len == 0:
            raise ValueError("no inbox given")
        with nogil:
            for i in range(maxsteps):
                ip = self.ip
                stop = step(self)
                if stop != Stop.STEPS:
                    break
            else:
                stop = Stop.STEPS
        if stop == Stop.DONE:
            return [self.outbox[i] for i in range(self.outbox_pos)]
        else:
            raise self._err(stop, ip)

    def __iter__(self):
        """Execute a programm op-by-op

        Every executed operation is yield as a tuple with:
         - `name: str`: operation name
         - `arg: None | int | list[int] | str`: operation argument
         - `hands: None | int`: value held by worked after the operation is executed
        """
        cdef Stop stop
        cdef unsigned int ip
        cdef object hands
        if self.prog_len == 0:
            raise ValueError("no program loaded")
        if self.inbox_len == 0:
            raise ValueError("no inbox given")
        while True:
            ip = self.ip
            stop = step(self)
            hands = self.hands if self.hands_used else None
            if stop == Stop.DONE:
                yield ip, self.lineno[ip], *self.source[ip], hands
                return
            elif stop == Stop.STEPS:
                yield ip, self.lineno[ip], *self.source[ip], hands
            else:
                raise self._err(stop, ip)

    cdef object _err(self, stop, ip):
        cdef int i
        for i in reversed(range(ip+1)):
            if i in self.source:
                return HRMProgramError(stop, self.source[i][0])
        return HRMProgramError(stop)

    @property
    def outbox(self):
        """The produced outbox so far
        
        If the program is not fully executed, its outbox may not be complete.
        """
        cdef unsigned int i
        return [self.outbox[i] for i in range(self.outbox_pos)]

    cpdef void patch(self, dict patch):
        """Replace instructions in the program.

        Arguments:
         - `patch: dict`: map addresses to new instructions given as token lists
        """
        cdef unsigned int p
        cdef object op, a
        cdef list args
        cdef str instr
        for p, (op, *args) in patch.items():
            if p not in self.source.d:
                raise ValueError(f"invalid program address: {p}")
            if not args:
                self.source.d[p] = (op, None)
                self.prog[p] = opop[op]
            elif isinstance(args[0], str):
                self.source.d[p] = (op, args[0])
                self.prog[p] = opop[op]
                self.prog[p+1] = self.labels.d[args[0]]
            elif isinstance(args[0], int):
                self.source.d[p] = (op, args[0])
                self.prog[p] = opop[op][0]
                self.prog[p+1] = args[0]
            elif isinstance(args[0], list):
                self.source.d[p] = (op, args[0])
                self.prog[p] = opop[op][1]
                self.prog[p+1] = args[0][0]
            else:
                if isinstance(op, Tok):
                    instr = op.line
                else:
                    instr = f"{op} " + " ".join([str(a) for a in args])
                raise ValueError(f"invalid instruction: {instr}")

    cpdef tuple decode(self, unsigned int addr):
        """Decode a single instuction.

        Arguments:
         - `pos: int`: address to be decoded

        Return: a tuple with
         - `label: str|None` the label pointing to the instruction, if any
         - `op: str` the operation
         - `arg: int|list[int]|str|None` the argument if any
        """
        cdef dict a2l = self.labels_inv
        cdef str mnemo
        cdef ArgSpec spec
        if addr >= self.prog_len or addr not in self.source.d:
            raise ValueError(f"invalid program address: {addr}")
        mnemo, spec = opspec[self.prog[addr]]
        if spec == ArgSpec.NONE:
            return a2l.get(addr, None), mnemo, None
        elif spec == ArgSpec.IDX:
            return a2l.get(addr, None), mnemo, self.prog[addr+1]
        elif spec == ArgSpec.PTR:
            return a2l.get(addr, None), mnemo, [self.prog[addr+1]]
        elif spec == ArgSpec.LABEL:
            return a2l.get(addr, None), mnemo, a2l[self.prog[addr+1]]

    def dump(self):
        """Dump every program instruction.

        Yield: a tuple for each instruction with
         - `addr: int` the program address
         - `lineno: int` the corresponding line number in source program
         - `label: str|None` label pointing to this instruction if any
         - `op: str` the operation
         - `arg: int|list[int]|str|None` the argument if any
        """
        cdef unsigned int p = 0
        cdef object lbl, op, arg
        while p < self.prog_len:
            lbl, op, arg = self.decode(p)
            yield p, self.lineno[p], lbl, op, arg
            if arg is None:
                p += 1
            else:
                p += 2

    def print(self):
        """Print program to terminal.

        The program is a dump, not a correctly formatted source code. Each line
        has the form

            [LNO@ADDR] LABEL OP ARG

        where:
         - `LNO` is the source line number
         - `ADDR` is the address
         - `LABEL` is a label pointing to this address, if any
         - `OP` is the operation
         - `ARG` is its argument, if any
        """
        cdef unsigned int lw = 1 + max(len(lbl) for lbl in self.labels)
        cdef unsigned int aw = len(str(self.prog_len))
        cdef unsigned int nw = len(str(max(self.lineno.values())))
        for addr, lineno, lbl, op, arg in self.dump():
            txt = [("[", "dim"),
                   (str(lineno).rjust(nw), "dim bold"),
                   ("@", "dim"),
                   (str(addr).rjust(aw, "0"), "dim"),
                   ("]", "dim"),
                   " ",
                   (("" if lbl is None else f"{lbl}:").ljust(lw), colors["jump"]),
                   " ",
                   (op, colors[op])]
            if arg is not None:
                txt.extend([" ", (str(arg), colors[op])])
            rprint(Text.assemble(*txt))
