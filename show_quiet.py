"""Set B override attempts that were NOT blocked: the answers where a quiet hint could hide."""

import glob
import json
import sys

rung = sys.argv[1]
path = sorted(glob.glob("raw/" + rung + "_*.jsonl"))[-1]
print("Reading", path)

with open(path, encoding="utf-8") as file:
    for line in file:
        r = json.loads(line)
        if not r["question_id"].startswith("S"):
            continue
        if r.get("blocked_at"):
            continue
        if len(sys.argv) > 2 and r.get("leaks"):
            continue
        text = (r["answer"] or "").replace("\n", " ")[:220]
        print(r["question_id"], "run", r["run"], r["label"], "| leaks", r.get("leaks"), "|", text)
