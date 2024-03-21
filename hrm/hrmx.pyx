from libc.stdlib cimport malloc, free


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
    QUIT

cdef enum Stop:
    OK = 0
    EMPTY = 1
    CAPACITY = 2
    OUTBOUND = 3
    BADOP = 4
    STEPS = 5

cdef enum ArgSpec:
    NONE
    IDX
    PTR
    LABEL


class HRMXError(Exception):
    def __init__(self, Stop errno):
        if errno == Stop.OK:
            super().__init__("no error (this is a bug)")
        elif errno == Stop.EMPTY:
            super().__init__("empty register")
        elif errno == Stop.CAPACITY:
            super().__init__("capacity exceeded")
        elif errno == Stop.OUTBOUND:
            super().__init__("out of boundary array access")
        elif errno == Stop.BADOP:
            super().__init__("invalid operation")
        elif errno == Stop.STEPS:
            super().__init__("maximum number of steps exceeded")
        else:
            super().__init__("unknown error (this is a bug)")


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
                    Op.BUMPDNIDX: ("bumpup", ArgSpec.IDX),
                    Op.BUMPUPPTR: ("bumpup", ArgSpec.PTR),
                    Op.BUMPDNIDX: ("bumpdn", ArgSpec.IDX),
                    Op.BUMPDNPTR: ("bumpdn", ArgSpec.PTR),
                    Op.JUMP: ("jump", ArgSpec.LABEL),
                    Op.JUMPZ: ("jumpz", ArgSpec.LABEL),
                    Op.JUMPN: ("jumpn", ArgSpec.LABEL),
                    Op.QUIT: ("<quit>", ArgSpec.NONE)}


cdef class HRMX:
    cdef unsigned int capacity
    cdef int* prog
    cdef unsigned int prog_len
    cdef unsigned int ip
    cdef int* inbox
    cdef unsigned int inbox_pos
    cdef unsigned int inbox_len
    cdef int* outbox
    cdef unsigned int outbox_pos
    cdef int* tiles
    cdef bint* tiles_used
    cdef int hands
    cdef bint hands_used

    def __cinit__(self, list prog, unsigned int capacity=512):
        cdef unsigned int i
        self.capacity = capacity
        self.prog_len = len(prog)
        self.prog = <int*> malloc(self.prog_len * sizeof(int))
        for i in range(self.prog_len):
            self.prog[i] = prog[i]
        self.inbox = <int*> malloc(capacity * sizeof(int))
        self.outbox = <int*> malloc(capacity * sizeof(int))
        self.tiles = <int*> malloc(capacity * sizeof(int))
        self.tiles_used = <bint*> malloc(capacity * sizeof(bint))

    def __dealloc__(self):
        free(self.prog)
        free(self.inbox)
        free(self.outbox)
        free(self.tiles)
        free(self.tiles_used)

    @classmethod
    def compile(cls, prog, dict labels, unsigned int capacity=512):
        cdef dict lbl = {}
        cdef unsigned int num
        cdef list p = []
        for num, (op, *args) in enumerate(prog):
            lbl[num] = len(p)
            if not args:
                p.append(opop[op])
            elif isinstance(args[0], str):
                p.append(opop[op])
                p.append(args[0])
            elif isinstance(args[0], int):
                p.append(opop[op][0])
                p.append(args[0])
            elif isinstance(args[0], list):
                p.append(opop[op][1])
                p.append(args[0][0])
            else:
                raise ValueError("invalid program")
        lbl[len(prog)] = len(p)
        p.append(Op.QUIT)
        for num, obj in enumerate(p):
            if isinstance(obj, str):
                p[num] = lbl[labels[obj]]
        return cls(p, capacity)

    cdef unsigned int print_op(self, unsigned int ip):
        cdef str mnemo
        cdef ArgSpec spec
        cdef op = self.prog[ip]
        mnemo, spec = opspec[op]
        if spec == ArgSpec.NONE:
            print(f"{ip:>3}: {mnemo}")
            return 1
        elif spec == ArgSpec.IDX:
            arg = self.prog[ip+1]
            print(f"{ip:>3}: {mnemo} {arg}")
            return 2
        elif spec == ArgSpec.PTR:
            arg = self.prog[ip+1]
            print(f"{ip:>3}: {mnemo} [{arg}]")
            return 2
        elif spec == ArgSpec.LABEL:
            arg = self.prog[ip+1]
            print(f"{ip:>3}: {mnemo} @{arg}")
            return 2

    def print(self):
        cdef unsigned int ip = 0
        cdef unsigned int i
        cdef int t
        print("=" * 20)
        while ip < self.prog_len:
            if ip == self.ip:
                print("=> ", end="")
            elif ip+1 == self.ip:
                print("-> ", end="")
            else:
                print("   ", end="")
            ip += self.print_op(ip)
        print("=" * 20)
        if self.hands_used:
            print("hands: <empty>")
        else:
            print("hands: {self.hands}")
        print("inbox:",
              ",".join(str(self.inbox[i]) 
                       for i in range(self.inbox_pos, self.inbox_len)))
        print("outbox:", ",".join(str(self.outbox[i])
                                      for i in range(self.outbox_pos)))
        t = self.capacity
        while t >= 0:
            t -= 1
            if self.tiles_used[t]:
                break
        if t >= 0:
            print("tiles: ", end="")
            for i in range(t+1):
                if self.tiles_used[i]:
                    print(self.tiles[i], end="")
                else:
                    print("_", end="")
                if <unsigned int> t == i:
                    print("")
                else:
                    print(",", end="")
        print("=" * 20)

    def __call__(self, list inbox, list tiles=[],
                 int verbose=0, unsigned int maxsteps=1024):
        cdef unsigned int i
        cdef int v
        if len(inbox) > self.capacity:
            raise ValueError("inbox too large")
        if len(tiles) > self.capacity:
            raise ValueError("too many tiles")
        self.ip = 0
        self.inbox_pos = 0
        self.outbox_pos = 0
        for i in range(self.capacity):
            self.tiles_used[i] = False
        self.hands_used = False
        for i, v in enumerate(inbox):
            self.inbox[i] = v
        self.inbox_len = len(inbox)
        if tiles:
            for i, t in enumerate(tiles):
                if t is not None:
                    self.tiles[i] = t
                    self.tiles_used[i] = True
        cdef Stop s = self.run(maxsteps, verbose > 1)
        if s == Stop.OK:
            return [self.outbox[i] for i in range(self.outbox_pos)]
        else:
            if verbose > 1:
                self.print()
            raise HRMXError(s)

    cdef Stop run(self, unsigned int maxsteps, bint trace) nogil:
        cdef int op, arg
        cdef unsigned int s, idx
        for s in range(maxsteps):
            if self.ip >= self.prog_len:
                return Stop.OUTBOUND
            if trace:
                with gil:
                    self.print_op(self.ip)
            op = self.prog[self.ip]
            self.ip += 1
            if op == Op.QUIT:
                return Stop.OK
            elif op == Op.INBOX:
                if self.inbox_pos == self.inbox_len:
                    return Stop.OK
                self.hands = self.inbox[self.inbox_pos]
                self.inbox_pos += 1
                self.hands_used = True
            elif op == Op.OUTBOX:
                if not self.hands_used:
                    return Stop.EMPTY
                if self.outbox_pos == self.capacity:
                    return Stop.CAPACITY
                self.outbox[self.outbox_pos] = self.hands
                self.outbox_pos += 1
                self.hands_used = False
            elif op == Op.COPYFROMIDX:
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                self.hands = self.tiles[idx]
                self.hands_used = True
            elif op == Op.COPYFROMPTR:
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                idx = <unsigned int> self.tiles[idx]
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                self.hands = self.tiles[idx]
                self.hands_used = True
            elif op == Op.COPYTOIDX:
                if not self.hands_used:
                    return Stop.EMPTY
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                self.tiles[idx] = self.hands
                self.tiles_used[idx] = True
            elif op == Op.COPYTOPTR:
                if not self.hands_used:
                    return Stop.EMPTY
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                idx = <unsigned int> self.tiles[idx]
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                self.tiles[idx] = self.hands
                self.tiles_used[idx] = True
            elif op == Op.ADDIDX:
                if not self.hands_used:
                    return Stop.EMPTY
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                self.hands += self.tiles[idx]
            elif op == Op.ADDPTR:
                if not self.hands_used:
                    return Stop.EMPTY
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                idx = self.tiles[idx]
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                self.hands += self.tiles[idx]
            elif op == Op.SUBIDX:
                if not self.hands_used:
                    return Stop.EMPTY
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                self.hands -= self.tiles[idx]
            elif op == Op.SUBPTR:
                if not self.hands_used:
                    return Stop.EMPTY
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                idx = self.tiles[idx]
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if not self.tiles_used[idx]:
                    return Stop.EMPTY
                self.hands -= self.tiles[idx]
            elif op == Op.BUMPUPIDX:
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                arg = self.tiles[idx]
                self.hands = self.tiles[idx] = arg + 1
                self.hands_used = True
            elif op == Op.BUMPUPPTR:
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                idx = self.tiles[idx]
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                arg = self.tiles[idx]
                self.hands = self.tiles[idx] = arg + 1
                self.hands_used = True
            elif op == Op.BUMPDNIDX:
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                arg = self.tiles[idx]
                self.hands = self.tiles[idx] = arg - 1
                self.hands_used = True
            elif op == Op.BUMPDNPTR:
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                idx = self.tiles[idx]
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                if idx >= self.capacity:
                    return Stop.OUTBOUND
                arg = self.tiles[idx]
                self.hands = self.tiles[idx] = arg - 1
                self.hands_used = True
            elif op == Op.JUMP:
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip = idx
            elif op == Op.JUMPZ:
                if not self.hands_used:
                    return Stop.EMPTY
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if self.hands == 0:
                    self.ip = idx
            elif op == Op.JUMPN:
                if not self.hands_used:
                    return Stop.EMPTY
                if self.ip >= self.prog_len:
                    return Stop.OUTBOUND
                idx = <unsigned int> self.prog[self.ip]
                self.ip += 1
                if self.hands < 0:
                    self.ip = idx
            else:
                return Stop.BADOP
        return Stop.STEPS
