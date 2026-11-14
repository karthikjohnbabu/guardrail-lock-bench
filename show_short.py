"""Short view of flagged answers (refused, check, blocked) for one rung."""

import glob
import json
import sys

rung = sys.argv[1]
path = sorted(glob.glob("raw/" + rung + "_*.jsonl"))[-1]
print("Reading", path)

with open(path, encoding="utf-8") as file:
    for line in file:
        r = json.loads(line)
        if r["label"] not in ("refused", "check", "blocked"):
            continue
        where = ""
        if r.get("blocked_at"):
            where = " | at " + r["blocked_at"] + " " + str(r.get("input_category") or r.get("output_category") or "")
        text = (r["answer"] or "").replace("\n", " ")[:160]
        print(r["question_id"], "run", r["run"], r["label"] + where, "|", text)
