# coding: utf-8

import collections
import json
import operator
import pathlib
import sys

import tqdm
from colorama import Fore as F
from colorama import Style as S
from IPython.core import ultratb

from hrm import HRM
from hrm.hrmx import HRMX, HRMProgramError

log = tqdm.tqdm(sorted(json.load(open("solutions/solutions.json")),
                       key=operator.itemgetter("levelNumber")))
pdf_base = pathlib.Path("pdf")
errors = collections.defaultdict(int)

for sol in log:
    path = f"solutions/{sol['path']}"
    try:
        hrm = HRM.parse(path)
    except Exception as err:
        log.write(f"{F.RED}parse error:{S.RESET_ALL} {sol['path']}")
        log.write(f"{S.DIM}{str(err).rstrip()}{S.RESET_ALL}")
        errors[f"{F.RED}parse error"] += 1
        continue
    # exec code
    num = sol["levelNumber"]
    lvl = hrm.level(num)
    for ex, example in enumerate(lvl["examples"]):
        try:
            out = hrm.runlevel(lvl, ex)
        except AssertionError as err:
            errors[f"{F.RED}invalid solution"] += 1
            log.write(f"{F.RED}{S.BRIGHT}invalid:{S.RESET_ALL} {sol['path']}")
            log.write(f"  😡 {F.RED}{S.DIM}{err}{S.RESET_ALL}")
            break
        except Exception:
            errors[f"{F.RED}crash"] = 1
            log.write(f"{F.RED}{S.BRIGHT}crashed:{S.RESET_ALL} {sol['path']}")
            vtb = ultratb.VerboseTB(color_scheme="Linux")
            log.write("\n".join(vtb.structured_traceback(*sys.exc_info())))
            break
        if sol["successRatio"] == 1 \
                and sol["worky"] \
                and out != example["outbox"]:
            errors[f"{F.YELLOW}failed"] += 1
            log.write(f"{F.YELLOW}failed:{S.RESET_ALL} {sol['path']}")
        # quick execution
        inbox = lvl["examples"][ex]["inbox"]
        if not all(isinstance(i, int) for i in inbox):
            continue
        if "floor" in lvl and "tiles" in lvl["floor"]:
            floor = lvl["floor"]["tiles"]
        else:
            floor = []
        if not all(isinstance(t, (int, type(None))) for t in floor):
            continue
        try:
            hrmx = HRMX(hrm.prog, hrm.labels)
            out = hrmx(inbox, floor)
        except HRMProgramError as err:
            errors[f"{F.RED}(quick) failed"] += 1
            log.write(f"{F.RED}{S.BRIGHT}(quick) failed:{S.RESET_ALL} {sol['path']}")
            log.write(f"  😡 {F.RED}{S.DIM}{err}{S.RESET_ALL}")
            log.write(f"  {S.DIM}INBOX: {','.join(str(i) for i in inbox)}{S.RESET_ALL}")
            if floor:
                log.write(f"  {S.DIM}TILES: {','.join(str(f) for f in floor)}{S.RESET_ALL}")
            break
        except Exception:
            errors[f"{F.RED}(quick) crashed"] = 1
            log.write(f"{F.RED}{S.BRIGHT}(quick) crashed:{S.RESET_ALL} {sol['path']}")
            vtb = ultratb.VerboseTB(color_scheme="Linux")
            log.write("\n".join(vtb.structured_traceback(*sys.exc_info())))
            break
        if sol["successRatio"] == 1 \
                and sol["worky"] \
                and out != example["outbox"]:
            errors[f"{F.YELLOW}(quick) failed"] += 1
            log.write(f"{F.YELLOW}(quick) failed:{S.RESET_ALL} {sol['path']}")

for err, count in errors.items():
    print(f"=> {err}:{S.RESET_ALL} {count}")
