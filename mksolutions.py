import collections
import json
import pathlib

sols = {}
root = pathlib.Path("solutions")

bylvl = collections.defaultdict(list)

for sol in json.load((root / "solutions.json").open()):
    if "type" not in sol and sol["legal"] and sol["worky"]:
        bylvl[sol["levelNumber"]].append(sol)

missing = set(lvl["number"]
              for lvl in json.load(open("hrm/levels.json"))
              if not lvl.get("cutscene", False)) - set(bylvl)
assert not missing, missing


def solrank(sol):
    return sol["size"], sol["steps"], -sol["successRatio"]


for lvl, group in bylvl.items():
    if any(sol["author"] == "atesgoral" for sol in group):
        bylvl[lvl] = group = [sol for sol in group
                              if sol["author"] == "atesgoral"]
    group.sort(key=solrank)
    sols[lvl] = group[0] | {"source": (root / group[0]["path"]).read_text()}

with open("hrm/solutions.json", "w") as out:
    json.dump(sols, out, indent=2)
