import json, collections, operator

from hrm import HRM

levels = {}
for lvl in json.load(open("test/levels.json")) :
    assert lvl["number"] not in levels, "duplicate level"
    levels[lvl["number"]] = lvl

fail, crash, win = 0, 0, 0

for sol in sorted(json.load(open("test/solutions.json")),
                  key=operator.itemgetter("levelNumber")):
    if sol["successRatio"] != 1 :
        continue
    lvl = levels[sol["levelNumber"]]
    print(f"level {lvl['number']} with solution {sol['path']}")
    floor = lvl["floor"]["tiles"] if "floor" in lvl and "tiles" in lvl["floor"] else []
    hrm = HRM.parse(f"test/solutions/{sol['path']}")
    for example in lvl["examples"] :
        try :
            out = hrm(example["inbox"], floor)
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
