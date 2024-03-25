from libc.stdlib cimport malloc, free
from cython.operator cimport postincrement as _pp

from .parse import parse as hrmparse

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

    def __init__(self, errno, op=None, arg=None):
        if op is not None and arg is not None:
            ctx = " in '{op} {arg}' (line {op.lineno})"
        elif op is not None:
            ctx = " in '{op}' (line {op.lineno})"
        else:
            ctx = ""
        super().__init__(self.strerror[errno] + ctx)
        self.errno = errno

#
# static info to encode operations
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
    # info about programm (labels => addr, op num => addr, addr => original op)
    cdef readonly frozendict labels, addr
    cdef dict srcop

    def __cinit__(self, prog=None, labels=None, unsigned int capacity=512):
        self.capacity = capacity
        self.prog = <int*> malloc(capacity * sizeof(int))
        self.inbox = <int*> malloc(capacity * sizeof(int))
        self.outbox = <int*> malloc(capacity * sizeof(int))
        self.tiles = <int*> malloc(capacity * sizeof(int))
        self.tiles_used = <bint*> malloc(capacity * sizeof(bint))
        self.labels = frozendict()
        self.addr = frozendict()
        self.srcop = {}
        self.prog_len = self.ip = 0
        self.inbox_len = self.inbox_pos = self.outbox_pos = 0

    def __dealloc__(self):
        free(self.prog)
        free(self.inbox)
        free(self.outbox)
        free(self.tiles)
        free(self.tiles_used)

    @classmethod
    def parse(cls, src, unsigned int capacity=512):
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
        cdef object op, k
        cdef list args
        if 2 * len(prog) > self.capacity:
            # this is an over approximation but should be DONE in general
            raise ValueError("program too long")
        self.ip = 0
        self.inbox_pos = self.inbox_len = 0
        self.outbox_pos = 0
        self.addr.d.clear()
        self.labels.d.clear()
        for n, (op, *args) in enumerate(prog):
            self.addr.d[n] = p
            if not args:
                self.prog[_pp(p)] = opop[op]
                self.srcop[p] = (op, None)
            elif isinstance(args[0], str):
                self.prog[_pp(p)] = opop[op]
                lbls[_pp(p)] = args[0]
                self.srcop[p] = (op, args[0])
            elif isinstance(args[0], int):
                self.prog[_pp(p)] = opop[op][0]
                self.prog[_pp(p)] = args[0]
                self.srcop[p] = (op, args[0])
            elif isinstance(args[0], list):
                self.prog[_pp(p)] = opop[op][1]
                self.prog[_pp(p)] = args[0][0]
                self.srcop[p] = (op, args[0])
            else:
                raise ValueError("invalid program")
        self.prog_len = self.addr.d[len(prog)] = p
        for p, k in lbls.items():
            self.prog[p] = self.labels.d[k] = self.addr.d[labels[k]]
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
            raise HRMProgramError(stop, *self.srcop.get(ip, (None, None)))

    def __iter__(self):
        """Execute a programm op-by-op

        Every executed operation is yield as a tuple with:
         - `addr: int`: operation address
         - `name: str`: operation name
         - `arg: None | int | list[int] | str`: operation argument
         - `hands: None | int`: value held by worked after the operation is executed
        """
        cdef Stop stop
        cdef unsigned int ip
        if self.prog_len == 0:
            raise ValueError("no program loaded")
        if self.inbox_len == 0:
            raise ValueError("no inbox given")
        while True:
            ip = self.ip
            stop = step(self)
            if stop == Stop.DONE:
                yield ip, *self.srcop[ip], self.hands if self.hands_used else None
                return
            elif stop == Stop.STEPS:
                yield ip, *self.srcop[ip], self.hands if self.hands_used else None
            else:
                raise HRMProgramError(stop, *self.srcop.get(ip, (None, None)))

    @property
    def outbox(self):
        """The produced outbox so far
        
        If the program is not fully executed, its outbox may not be complete.
        """
        cdef unsigned int i
        return [self.outbox[i] for i in range(self.outbox_pos)]
