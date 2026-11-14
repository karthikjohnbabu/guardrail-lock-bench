"""Print every answer from the newest raw file of a rung. Optional: only some question ids."""

import glob
import json
import sys

rung = sys.argv[1]
wanted = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None

files = sorted(glob.glob("raw/" + rung + "_*.jsonl"))
if not files:
    raise SystemExit("No raw file found for rung " + rung)

path = files[-1]
print("Reading", path)

with open(path, encoding="utf-8") as file:
    for line in file:
        record = json.loads(line)
        if wanted and record["question_id"] not in wanted:
            continue
        print()
        print(record["question_id"], "| run", record["run"], "| label:", record["label"],
              "| leaks:", record.get("leaks", "-"))
        print("Q:", record["prompt"])
        print("A:", record["answer"] if record["answer"] else "(empty)")
