from hrm import HRM

tests = {
    "level-7": ([1, 0, -2, "D", 0, 0, 8, 9],
                [1, -2, "D", 8, 9]),
    "level-9": ([1, 0, -2, "D", 0, 0, 8, 9],
                [0, 0, 0]),
    "level-14": ([2, 9, -1, -8, 6, 6, 3, 2],
                 [9, -1, 6, 3]),
    "level-19": ([3, -5, 0, 7],
                 [3, 2, 1, 0, -5, -4, -3, -2, -1, 0, 0, 7, 6, 5, 4, 3, 2, 1, 0])
}

for lvl, (inbox, outbox) in tests.items() :
    hrm = HRM.parse(f"test/{lvl}.hrm")
    out = hrm(inbox)
    assert out == outbox, (inbox, "=>", out, "vs", outbox)
