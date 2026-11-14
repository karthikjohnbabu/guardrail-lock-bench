"""Set B: leak types per rung, and per question how many of the 5 runs leaked (automatic rules)."""

import glob
import json
from collections import Counter, defaultdict

for rung in ("B1", "B2", "B3"):
    path = sorted(glob.glob("raw/" + rung + "_*.jsonl"))[-1]
    types = Counter()
    per_question = defaultdict(int)
    with open(path, encoding="utf-8") as file:
        for line in file:
            r = json.loads(line)
            leaks = r.get("leaks") or []
            for leak in leaks:
                types[leak] += 1
            if leaks:
                per_question[r["question_id"]] += 1
    print(rung, "leak types:", dict(types))
    print("   answers with a leak, per question (out of 5 runs):", dict(sorted(per_question.items())))
