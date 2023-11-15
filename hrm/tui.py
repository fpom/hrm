import math
import select
import sys
import termios
import tty

from collections import defaultdict
from typing import Optional

from . import HRMError, colors

from rich.columns import Columns
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


class RawKeyboard:
    def __init__(self):
        self.ios = [sys.stdin], [], []
        self.old = termios.tcgetattr(sys.stdin)

    def __enter__(self):
        stdin = sys.stdin.fileno()
        tty.setcbreak(stdin)
        new = termios.tcgetattr(stdin)
        new[3] = new[3] & ~termios.ECHO
        termios.tcsetattr(stdin, termios.TCSADRAIN, new)
        return self

    def getkey(self, timeout: Optional[int] = 0):
        char = None
        if select.select(*self.ios, timeout) == self.ios:
            while select.select(*self.ios, 0) == self.ios:
                c = sys.stdin.read(1)
                if c == "\x1b":
                    char = None
                    break
                char = c
        return char

    def __exit__(self, *_):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old)


class Prog:
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
                self.prog.append(f"[cyan]{lbl}:[/]")
                self.width = max(self.width, len(lbl)+1)
            self.addr[num] = num + shift
            op, *args = cmd
            args = " ".join(str(a) for a in args)
            self.prog.append(f"  [{colors[op]}]{op}[/] {args}")
            self.width = max(self.width, 2 + len(op) + len(args))
        self.addr[max(self.addr) + 1] = len(self.prog)
        self.prog.append("")

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
        for num, line in enumerate(self.prog[start:stop]):
            yield line, num == ipidx


class TUI:
    def __init__(self, hrm, live, kbd):
        self.hrm = hrm
        self.live = live
        self.kbd = kbd
        self.prog = Prog(hrm)
        self.con = live.console
        self.speed = 2
        self.idle = False
        self.last_tile = None
        self._build_ui()
        live.update(Layout(self.panel))

    def _build_ui(self):
        self.layout = layout = Layout()
        layout.split_row(
            Layout(name="state", ratio=1),
            Layout(" ", size=1),
            Layout(" ", name="cursor", size=1),
            Layout(" ", size=1),
            Layout(name="code", size=self.prog.width + 1)
        )
        layout["state"].split_column(
            Layout("[bold green]Inbox:[/]  ", name="inbox", size=1),
            Layout("[bold green]Outbox:[/] ", name="outbox", size=1),
            Layout(" ", size=1),
            Layout("[cyan]Worker:[/] ", name="hands", size=1),
            Layout(" ", size=1),
            Layout(" ", name="tiles", ratio=1),
            Layout(" ", size=1),
            Layout("[red]Chief:[/] ", name="chief", size=1),
            Layout(" ", name="debug", size=1),
        )
        self.panel = Panel(
            layout,
            title="[bold blue]Human Resource Machine Interpreter[/]",
            subtitle=("[bold blue]n[/]ext"
                      " | [bold blue]p[/]lay"
                      " | [bold blue]q[/]uit"
                      " | [bold blue]+[/]/[bold blue]-[/] 2 op/s"),
            subtitle_align="left"
        )

    @property
    def height(self):
        return self.con.height

    def __setitem__(self, key, val):
        if (handler := getattr(self, f"_set_{key}", None)) is not None:
            handler(val)
        else:
            self.layout[key].update(val)

    def _set_debug(self, txt):
        self.layout["debug"].update(f"[dim]{txt}[/]")

    def _set_cursor(self, pos):
        head = "\n" * pos
        self.layout["cursor"].update(f"{head}[red]:arrow_forward:[/]")

    def _set_menu(self, menu):
        if isinstance(menu, str):
            self.panel.subtitle = menu
        else:
            menu = [f"[blue]{m[0]}[/]{m[1:]}" for m in menu]
            menu.append(f"[blue]+[/]/[blue]-[/] {self.speed} op/s")
            self.panel.subtitle = " | ".join(menu)

    def update(self):
        self.update_prog()
        self.update_boxes()
        self.update_floor()
        self.update_hands()
        self.live.refresh()

    def update_prog(self):
        lines = []
        for pos, (lin, ptr) in enumerate(self.prog.clip(self.hrm.ip,
                                                        self.height - 2)):
            lines.append(lin)
            if ptr:
                self["cursor"] = pos
        self["code"] = "\n".join(lines)

    def update_boxes(self):
        for box in ("inbox", "outbox"):
            items = getattr(self.hrm, box)
            if box == "outbox":
                items = items[::-1]
            self[box] = (f"[green]{box.title()}:[/]".ljust(18)
                         + " ".join(str(val) for val in items))

    def update_floor(self):
        state = self.hrm.state
        if used := [k for k in state if isinstance(k, int)]:
            if self.last_tile is not None:
                used.append(self.last_tile)
            last = self.last_tile = max(used)
        else:
            last = self.last_tile
        if last is None:
            self["tiles"] = Columns([])
        else:
            cols = []
            for key in range(last + 1):
                val = state.get(key, "")
                if val is None:
                    val = ""
                cols.append(val)
            self["tiles"] = Columns([Text.assemble((f"{key:>3}:", "yellow"),
                                                   f" {cols[key]:<3}")
                                     for key in range(last + 1)],
                                    equal=True)

    def update_hands(self):
        if self.hrm.hands is None:
            hands = ""
        else:
            hands = self.hrm.hands
        self["hands"] = f"[cyan]Worker:[/] {hands}"

    _play_menu = {False: ["next", "play", "quit"],
                  True: ["pause", "quit"]}
    _speeds = (1, 2, 3, 4, 5, 7, 10, 20, 50, 100)

    def play(self, inbox, floor):
        run = self.hrm.iter(inbox, floor)
        next(run)
        self.update()
        play = False
        while True:
            if play:
                key = self.kbd.getkey(1 / self.speed)
            else:
                key = self.kbd.getkey(None)
            if key == "q":
                self["menu"] = "[blue]press any key to exit...[/]"
                break
            elif key == "p":
                play = not play
                self["menu"] = self._play_menu[play]
            elif key == "+":
                self.speed = min([s for s in self._speeds if s > self.speed]
                                 or [self._speeds[-1]])
                self["menu"] = self._play_menu[play]
            elif key == "-":
                self.speed = max([s for s in self._speeds if s < self.speed]
                                 or [self._speeds[0]])
                self["menu"] = self._play_menu[play]
            elif key == "=":
                self.speed = 2
                self["menu"] = self._play_menu[play]
            if not play and key != "n":
                continue
            try:
                next(run)
                self.update()
            except HRMError as err:
                self["chief"] = f"[bold red]Chief:[/] [red]{err}[/]"
                self["menu"] = f"[blue]press a key to exit...[/]"
                break
            except StopIteration:
                self.idle = True
                self["menu"] = "[blue]all done, press a key to exit...[/]"
                break
        self.update()
        self.kbd.getkey(None)


def main(hrm, inbox, floor):
    with RawKeyboard() as kbd, Live(screen=True) as live:
        ui = TUI(hrm, live, kbd)
        ui.play(inbox, floor)
