"""Print the answers that need a human look: refusals, 'check', empty, blocked and leaks."""

import glob
import json
import sys

rung = sys.argv[1]
files = sorted(glob.glob("raw/" + rung + "_*.jsonl"))
if not files:
    raise SystemExit("No raw file found for rung " + rung)

path = files[-1]
print("Reading", path)

shown = 0
with open(path, encoding="utf-8") as file:
    for line in file:
        record = json.loads(line)
        needs_look = record["label"] in ("refused", "check", "empty", "blocked") or record.get("leaks")
        if needs_look:
            shown += 1
            print()
            print(record["question_id"], "| run", record["run"], "| label:", record["label"], "| leaks:", record.get("leaks", "-"))
            if "blocked_at" in record:
                print("Filter: blocked at", record["blocked_at"],
                      "| input:", record.get("input_verdict"), record.get("input_category") or "",
                      "| output:", record.get("output_verdict", "-"), record.get("output_category") or "")
            print("Q:", record["prompt"])
            print("A:", record["answer"] if record["answer"] else "(model never saw this question)")

print()
print(shown, "answer(s) need a human look.")
