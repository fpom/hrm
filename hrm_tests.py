import json, collections, operator

from hrm import HRM

fail, crash, win = 0, 0, 0

for sol in sorted(json.load(open("test/solutions.json")),
                  key=operator.itemgetter("levelNumber")):
    if sol["successRatio"] != 1 :
        continue
    num = sol["levelNumber"]
    print(f"level {num} vs {sol['path']}")
    hrm = HRM.parse(f"test/solutions/{sol['path']}")
    lvl = hrm.level(num)
    for ex, example in enumerate(lvl["examples"]) :
        try :
            out = hrm.runlevel(lvl, ex)
        except :
            print("* crashed")
            crash += 1
            break
        if out != example["outbox"] :
            print("! failed")
            break
            fail += 1
        win += 1

print(f"{win} succeeded / {fail} failed / {crash} crashed")
