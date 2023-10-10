import curses
import math
import re

from collections import defaultdict

from . import HRMError


class Text:
    def __init__(self, win):
        self.win = win
        self.pairs = {}
        for num, color in enumerate(["white", "red", "green", "blue",
                                     "yellow", "cyan", "magenta"],
                                    start=1):
            abbr = color[0].upper()
            fg = getattr(curses, f"COLOR_{color.upper()}")
            curses.init_pair(num, fg, curses.COLOR_BLACK)
            self.pairs[abbr] = curses.color_pair(num)

    _txt = re.compile(r"(\\\[|[^\[])|\[([WRGBYCM]):([^\]]+)\]")

    def __call__(self, y, x, text):
        c = 0
        for match in self._txt.finditer(text):
            raw, col, txt = match.groups()
            txt = raw or txt
            if col is None:
                self.win.addstr(y, x+c, txt)
            else:
                self.win.addstr(y, x+c, txt, self.pairs[col])
            c += len(txt)
        return c


class Prog:
    hl = {"inbox": "G",
          "outbox": "G",
          "copyfrom": "R",
          "copyto": "R",
          "add": "Y",
          "sub": "Y",
          "bumpup": "Y",
          "bumpdn": "Y",
          "jump": "B",
          "jumpz": "B",
          "jumpn": "B"}

    def __init__(self, hrm):
        self.prog = []
        self.addr = {}
        self.width = 0
        labels = defaultdict(list)
        for n, a in hrm.labels.items():
            labels[a].append(n)
        shift = 0
        for num, cmd in enumerate(hrm.prog):
            for lbl in labels[num]:
                shift += 1
                self.prog.append(f"[C:{lbl}:]")
                self.width = max(self.width, len(lbl)+1)
            self.addr[num] = num + shift
            op, *args = cmd
            args = " ".join(str(a) for a in args)
            self.prog.append(f"  [{self.hl[op]}:{op}] {args}")
            self.width = max(self.width, 2 + len(op) + len(args))

    def clip(self, ip, count):
        size = len(self.prog)
        if size <= count:
            start = 0
            stop = len(self.prog)
            ipidx = self.addr[ip]
        else:
            mid = self.addr[ip]
            start = mid - math.ceil(count / 2)
            stop = mid + math.floor(count / 2)
            if start < 0:
                start, stop = 0, count
            elif stop > size:
                start, stop = size - count, size
            ipidx = mid - start
            assert stop - start == count, f"{start=}, {mid=}, {stop=}, {size=}"
        for num, line in enumerate(self.prog[start:stop]):
            yield line, num == ipidx


class Interface:
    def __init__(self, hrm, inbox, floor=[]):
        self.hrm = hrm
        self.run = hrm.iter(inbox, floor)
        next(self.run)
        self.prog = Prog(hrm)
        self.menu = ["next", "play", "quit"]
        self.error = None
        self.idle = False
        self.speed = 2

    def __enter__(self):
        self.win = curses.initscr()
        curses.start_color()
        self.t = Text(self.win)
        curses.noecho()
        curses.curs_set(False)
        curses.cbreak()
        self.win.keypad(True)
        self.win.clear()
        self._h, self._w = self.win.getmaxyx()
        self._wr = self.prog.width + 2
        self._wl = self._w - self._wr - 4
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        curses.endwin()
        if exc_type == KeyboardInterrupt:
            return True

    def display(self):
        self.win.clear()
        # frame
        self.win.border()
        for y in range(1, self._h-1):
            self.win.addch(y, self._wl+1, curses.ACS_VLINE)
        self.win.addch(0, self._wl+1, curses.ACS_TTEE)
        self.win.addch(self._h-1, self._wl+1, curses.ACS_BTEE)
        title = " Human Resource Machine interpreter "
        pos = int(self._w / 2 - len(title) / 2)
        self.t(0, pos, f"[B:{title}]")
        self.win.addch(0, pos-1, curses.ACS_RTEE)
        self.win.addch(0, pos + len(title), curses.ACS_LTEE)
        # program
        for num, (cmd, isip) in enumerate(self.prog.clip(self.hrm.ip,
                                                         self._h-4)):
            self.t(num+2, self._wl+3, cmd)
            if isip:
                self.win.addch(num + 2,
                               self._wl + 1,
                               curses.ACS_DIAMOND,
                               self.t.pairs["C"])
        # inbox and outbox
        y = 2
        for box in ("inbox", "outbox"):
            self.t(y, 2, f"[G:{box.title()}:]")
            pos = 9
            items = getattr(self.hrm, box)
            if box == "outbox":
                items = items[::-1]
            for val in items:
                txt = f" {val}"
                if pos + len(txt) + 3 > self._wl:
                    self.t(y, pos, "...")
                    break
                self.t(y, pos, txt)
                pos += len(txt)
            y += 1
        # tiles
        x, y = 2, 7
        for num in range(100):
            val = self.hrm.state.get(num, "    ")
            inc = len(f"{num:>2} {val:<4}")
            if x + inc >= self._wl - 1:
                x = 2
                y += 2
                if y > self._h - 4:
                    break
            x += self.t(y, x, f"[M:{num:>2}:] {val:<4}")
        # characters
        if self.idle:
            player = "\U0001f62c"
        else:
            player = "\U0001f610"
        if self.hrm.hands is None:
            self.t(5, 2, player)
        else:
            self.t(5, 2, f"{player} {self.hrm.hands}")
        if self.error is None:
            self.t(self._h-3, 2, "\U0001f621")
        else:
            self.t(self._h-3, 2, f"\U0001f92c [R:{self.error}]")
        # menu and rate
        rate = str(self.speed)
        pos = self._wl - len(rate) - 11
        self.t(self._h-1, pos, f" [B:+]/[B:-] {rate} op/s ")
        if isinstance(self.menu, list):
            menu = " | ".join(f"[B:{m[0]}]{m[1:]}" for m in self.menu)
        else:
            menu = self.menu
        self.t(self._h-1, 2, f" {menu} ")
        #
        self.win.refresh()

    _speeds = (1, 2, 3, 4, 5, 7, 10, 20, 50, 100)
    _play_menu = {False: ["next", "play", "quit"],
                  True: ["pause", "quit"]}

    def __call__(self):
        play = False
        self.speed = 2
        while True:
            self.display()
            self.win.timeout(int(1000 / self.speed) if play else -1)
            key = self.win.getch()
            if 32 <= key <= 254:
                key = chr(key)
            if key == "q":
                self.menu = "press a key to exit..."
                break
            elif key == "p":
                play = not play
                self.menu = self._play_menu[play]
            elif key == "+" or key == curses.KEY_UP:
                self.speed = min([s for s in self._speeds if s > self.speed]
                                 or [self._speeds[-1]])
            elif key == "-" or key == curses.KEY_DOWN:
                self.speed = max([s for s in self._speeds if s < self.speed]
                                 or [self._speeds[0]])
            elif key == "=":
                self.speed = 2
            if not play and key != "n":
                continue
            try:
                next(self.run)
            except HRMError as err:
                self.error = str(err)
                self.menu = "press a key to exit..."
                break
            except StopIteration:
                self.idle = True
                self.menu = "all done, press a key to exit..."
                break
        self.display()
        self.win.timeout(-1)
        self.win.getch()
