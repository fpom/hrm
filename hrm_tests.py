# coding: utf-8

import json, collections, operator, sys
import tqdm

from colorama import Fore as F, Style as S
from IPython.core import ultratb

from hrm import HRM

log = tqdm.tqdm(sorted(json.load(open("solutions/solutions.json")),
                       key=operator.itemgetter("levelNumber")))

for sol in log :
    try :
        hrm = HRM.parse(f"solutions/{sol['path']}")
    except :
        log.write(f"{F.RED}parse error:{S.RESET_ALL} {sol['path']}")
    num = sol["levelNumber"]
    lvl = hrm.level(num)
    for ex, example in enumerate(lvl["examples"]) :
        try :
            out = hrm.runlevel(lvl, ex)
        except AssertionError as err :
            log.write(f"{F.RED}{S.BRIGHT}invalid:{S.RESET_ALL} {sol['path']}")
            log.write(f"  😡 {F.RED}{S.DIM}{err}{S.RESET_ALL}")
            break
        except :
            log.write(f"{F.RED}{S.BRIGHT}crashed:{S.RESET_ALL} {sol['path']}")
            vtb = ultratb.VerboseTB(color_scheme="Linux")
            log.write("\n".join(vtb.structured_traceback(*sys.exc_info())))
            break
        if sol["successRatio"] == 1 and sol["worky"] and out != example["outbox"] :
            log.write(f"{F.YELLOW}failed:{S.RESET_ALL} {sol['path']}")
