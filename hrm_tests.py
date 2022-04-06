# coding: utf-8

import json, collections, operator, sys, pathlib
import tqdm

from colorama import Fore as F, Style as S
from IPython.core import ultratb

from hrm import HRM
from hrm.tikz import draw

log = tqdm.tqdm(sorted(json.load(open("solutions/solutions.json")),
                       key=operator.itemgetter("levelNumber")))
pdf_base = pathlib.Path("pdf")

for sol in log :
    path = f"solutions/{sol['path']}"
    try :
        hrm = HRM.parse(path)
    except :
        log.write(f"{F.RED}parse error:{S.RESET_ALL} {sol['path']}")
    # draw code
    pdf = (pdf_base / sol["path"]).with_suffix(".pdf")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    try :
        draw(path, pdf)
    except :
        log.write(f"{F.YELLOW}draw failed:{S.RESET_ALL} {sol['path']}")
    # exec code
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
