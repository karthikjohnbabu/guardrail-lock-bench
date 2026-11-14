"""Ask every question of one rung, several times, and save the answers."""

import argparse
import json
import os
from datetime import datetime

from detect import refusal_label, secret_leaks
from guard import check_input, check_output
from ollama_client import chat
from rungs import RUNGS

QUESTION_FILES = {"A": "questions.json", "B": "secret_game.json"}
TEMPERATURE = 0.7
RAW_FOLDER = "raw"


def load_questions(set_name):
    with open(QUESTION_FILES[set_name], encoding="utf-8") as file:
        return json.load(file)


def main():
    parser = argparse.ArgumentParser(description="Run one rung of the benchmark.")
    parser.add_argument("--rung", required=True, help="Rung id, for example A1")
    parser.add_argument("--runs", type=int, default=1, help="How many times to repeat")
    parser.add_argument("--ids", default="", help="Only these question ids, comma separated")
    args = parser.parse_args()

    if args.rung not in RUNGS:
        raise SystemExit("Unknown rung: " + args.rung + ". Known rungs: " + ", ".join(RUNGS))

    rung = RUNGS[args.rung]
    question_data = load_questions(rung["set"])
    questions = question_data["questions"]

    if args.ids:
        wanted = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in wanted]
        if not questions:
            raise SystemExit("None of those question ids exist in set " + rung["set"])

    system_prompt = rung["system_prompt"]
    if rung.get("use_secret_prompt"):
        system_prompt = question_data["system_prompt"]

    has_filter = bool(rung.get("guard") or rung.get("code_filter"))

    os.makedirs(RAW_FOLDER, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(RAW_FOLDER, args.rung + "_" + stamp + ".jsonl")

    print("Rung", args.rung, "-", rung["description"])
    print("Questions:", len(questions), "| runs:", args.runs, "| saving to", out_path)

    summary = {}
    with open(out_path, "w", encoding="utf-8") as out:
        for run in range(1, args.runs + 1):
            for q in questions:
                guard_info = {}
                filter_seconds = 0.0
                blocked_at = None

                if rung.get("guard"):
                    in_verdict, in_cat, in_sec = check_input(q["prompt"])
                    guard_info["input_verdict"] = in_verdict
                    guard_info["input_category"] = in_cat
                    filter_seconds += in_sec
                    if in_verdict == "unsafe":
                        blocked_at = "input"

                if blocked_at == "input":
                    result = {
                        "content": "", "output_tokens": 0, "tokens_per_sec": None,
                        "total_seconds": 0.0, "load_seconds": 0.0,
                    }
                else:
                    result = chat(
                        rung["model"],
                        q["prompt"],
                        system_prompt=system_prompt,
                        temperature=TEMPERATURE,
                        think=rung["think"],
                    )
                    if rung.get("guard"):
                        out_verdict, out_cat, out_sec = check_output(q["prompt"], result["content"])
                        guard_info["output_verdict"] = out_verdict
                        guard_info["output_category"] = out_cat
                        filter_seconds += out_sec
                        if out_verdict == "unsafe":
                            blocked_at = "output"

                raw_leaks = []
                if rung["set"] == "B":
                    raw_leaks = secret_leaks(result["content"], secret=question_data["secret_word"])

                if rung.get("code_filter") and "plain" in raw_leaks and blocked_at is None:
                    blocked_at = "output"

                label = "blocked" if blocked_at else refusal_label(result["content"])

                record = {
                    "rung": args.rung,
                    "set": rung["set"],
                    "model": rung["model"],
                    "run": run,
                    "question_id": q["id"],
                    "question_type": q["type"],
                    "prompt": q["prompt"],
                    "answer": result["content"],
                    "label": label,
                    "output_tokens": result["output_tokens"],
                    "tokens_per_sec": result["tokens_per_sec"],
                    "total_seconds": result["total_seconds"],
                    "load_seconds": result["load_seconds"],
                    "temperature": TEMPERATURE,
                }
                if has_filter:
                    record.update(guard_info)
                    record["blocked_at"] = blocked_at
                    record["filter_seconds"] = filter_seconds
                if rung["set"] == "B":
                    record["leaks"] = raw_leaks
                    record["leaked_to_user"] = bool(raw_leaks) and blocked_at is None
                out.write(json.dumps(record) + "\n")

                bucket = summary.setdefault(
                    q["type"],
                    {"total": 0, "refused": 0, "check": 0, "answered": 0,
                     "empty": 0, "blocked": 0, "leaked": 0, "raw_leaks": 0},
                )
                bucket["total"] += 1
                bucket[label] += 1
                if raw_leaks:
                    bucket["raw_leaks"] += 1
                if record.get("leaked_to_user"):
                    bucket["leaked"] += 1

                note = ""
                if blocked_at:
                    note = " (blocked at " + blocked_at + ")"
                leak_note = " | leaks: " + ",".join(raw_leaks) if raw_leaks else ""
                print("  run", run, q["id"], "->", label + note, "|",
                      round(result["total_seconds"] + filter_seconds, 1), "sec" + leak_note)

    print()
    print("Summary for", args.rung)
    for question_type, b in summary.items():
        line = (
            question_type + ": " + str(b["total"]) + " answers | refused " + str(b["refused"])
            + " | check " + str(b["check"]) + " | answered " + str(b["answered"])
            + " | empty " + str(b["empty"])
        )
        if has_filter:
            line += " | blocked " + str(b["blocked"])
        if rung["set"] == "B":
            line += " | model leaked " + str(b["raw_leaks"]) + " | reached user " + str(b["leaked"])
        print(line)
    print("Remember: 'refused', 'check' and 'blocked' answers must be read by hand before they are counted.")


if __name__ == "__main__":
    main()
