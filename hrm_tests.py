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
            errors["{F.YELLOW}failed"] += 1
            log.write(f"{F.YELLOW}failed:{S.RESET_ALL} {sol['path']}")

for err, count in errors.items():
    print(f"=> {err}:{S.RESET_ALL} {count}")
