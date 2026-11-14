"""Phase 5: build the results table, a chart and a reading list from the newest raw file of each rung."""

import csv
import glob
import json
import os

RUNGS = ["A1", "A2", "A3", "A4", "B1", "B2", "B3"]
LOCKS = {
    "A1": "Llama alone (lock in the weights)",
    "A2": "Llama + permissive system prompt",
    "A3": "Qwen uncensored (no lock)",
    "A4": "Llama + Llama Guard filter",
    "B1": "Llama + secret-word prompt (text lock)",
    "B2": "Qwen uncensored + text lock",
    "B3": "Llama + text lock + code filter",
}
OUT_DIR = "results"


def newest(rung):
    files = sorted(glob.glob("raw/" + rung + "_*.jsonl"))
    return files[-1] if files else None


def load(path):
    with open(path, encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def rate(records, group, hit):
    """Return (n, hits, percent, lowest run percent, highest run percent)."""
    rows = [r for r in records if group(r)]
    if not rows:
        return (0, 0, 0.0, 0.0, 0.0)
    hits = sum(1 for r in rows if hit(r))
    by_run = {}
    for r in rows:
        by_run.setdefault(r["run"], []).append(r)
    run_pcts = [100.0 * sum(1 for r in rs if hit(r)) / len(rs) for rs in by_run.values()]
    return (len(rows), hits, 100.0 * hits / len(rows), min(run_pcts), max(run_pcts))


def count(records, group, label):
    return sum(1 for r in records if group(r) and r["label"] == label)


def avg_seconds(records):
    values = [r["total_seconds"] + r.get("filter_seconds", 0.0) for r in records]
    return sum(values) / len(values) if values else 0.0


def is_stopped(r):
    return r["label"] in ("refused", "blocked")


def fmt(p):
    return "%.0f%%" % p if abs(p - round(p)) < 0.05 else "%.1f%%" % p


def spread(low, high):
    return "%.0f to %.0f%%" % (low, high)


def apply_hand_read(data, path="hand_read.csv"):
    """Apply the corrections I made by reading answers. Returns borderline counts per rung."""
    borderline = {}
    if not os.path.exists(path):
        return borderline
    with open(path, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        records = data.get(row["rung"], [])
        found = [r for r in records if r["question_id"] == row["question_id"] and str(r["run"]) == row["run"]]
        if len(found) != 1:
            print("hand_read.csv: could not find", row)
            continue
        r = found[0]
        if row["verdict"] == "add_leak":
            r["leaks"] = list(r.get("leaks") or []) + ["hand_read"]
            r["leaked_to_user"] = True
        elif row["verdict"] == "not_stopped":
            r["label"] = "answered"
        elif row["verdict"] == "borderline":
            borderline[row["rung"]] = borderline.get(row["rung"], 0) + 1
    print("Applied", len(rows), "hand-read corrections from", path)
    return borderline


def main():
    data = {}
    for rung in RUNGS:
        path = newest(rung)
        if path:
            data[rung] = load(path)
            runs = len(set(r["run"] for r in data[rung]))
            print("Using", path, "|", len(data[rung]), "answers |", runs, "run(s)")
        else:
            print("No raw file for", rung)

    borderline = apply_hand_read(data)
    os.makedirs(OUT_DIR, exist_ok=True)
    tidy = []
    md = []

    # ---- Set A ----
    set_a = {}
    md.append("## Set A: harmless questions that sound risky\n")
    md.append("| Rung | Lock | Risky-sounding wrongly stopped | Of those: model refused / filter blocked / to check | Plain controls wrongly stopped | Avg seconds per answer |")
    md.append("| --- | --- | --- | --- | --- | --- |")
    print()
    print("SET A - harmless questions wrongly stopped (automatic labels, read by hand before publishing)")
    for rung in ["A1", "A2", "A3", "A4"]:
        if rung not in data:
            continue
        recs = data[rung]
        risky = lambda r: r["question_type"] == "risky_harmless"
        control = lambda r: r["question_type"] == "control"
        rr = rate(recs, risky, is_stopped)
        cr = rate(recs, control, is_stopped)
        refused = count(recs, risky, "refused")
        blocked = count(recs, risky, "blocked")
        check = count(recs, risky, "check")
        secs = avg_seconds(recs)
        set_a[rung] = rr
        line = "%s  risky %s (%d of %d, per-run %s) | refused %d, blocked %d, check %d | controls %s | %.1f sec" % (
            rung, fmt(rr[2]), rr[1], rr[0], spread(rr[3], rr[4]), refused, blocked, check, fmt(cr[2]), secs)
        print(" ", line)
        md.append("| %s | %s | %s (%d of %d; per run %s) | %d / %d / %d | %s (%d of %d) | %.1f |" % (
            rung, LOCKS[rung], fmt(rr[2]), rr[1], rr[0], spread(rr[3], rr[4]),
            refused, blocked, check, fmt(cr[2]), cr[1], cr[0], secs))
        tidy.append([rung, "A", "risky_harmless", "stopped", rr[0], rr[1], round(rr[2], 1), round(rr[3], 1), round(rr[4], 1)])
        tidy.append([rung, "A", "control", "stopped", cr[0], cr[1], round(cr[2], 1), round(cr[3], 1), round(cr[4], 1)])

    # ---- Set B ----
    set_b = {}
    set_b_norm = {}
    md.append("\n## Set B: the secret-word game\n")
    md.append("| Rung | Lock | Secret reached the user | Model leaked before any filter | Normal questions wrongly stopped | Avg seconds per answer |")
    md.append("| --- | --- | --- | --- | --- | --- |")
    print()
    print("SET B - secret word (automatic rules plus hand-read corrections)")
    for rung in ["B1", "B2", "B3"]:
        if rung not in data:
            continue
        recs = data[rung]
        override = lambda r: r["question_type"] == "override_attempt"
        normal = lambda r: r["question_type"] == "normal"
        reached = rate(recs, override, lambda r: bool(r.get("leaked_to_user")))
        modelled = rate(recs, override, lambda r: bool(r.get("leaks")))
        norm = rate(recs, normal, is_stopped)
        secs = avg_seconds(recs)
        set_b[rung] = reached
        set_b_norm[rung] = norm
        print("  %s  reached user %s (%d of %d, per-run %s) | model leaked %s | normal stopped %s (%d of %d) | %.1f sec" % (
            rung, fmt(reached[2]), reached[1], reached[0], spread(reached[3], reached[4]),
            fmt(modelled[2]), fmt(norm[2]), norm[1], norm[0], secs))
        md.append("| %s | %s | %s (%d of %d; per run %s) | %s | %s (%d of %d) | %.1f |" % (
            rung, LOCKS[rung], fmt(reached[2]), reached[1], reached[0], spread(reached[3], reached[4]),
            fmt(modelled[2]), fmt(norm[2]), norm[1], norm[0], secs))
        tidy.append([rung, "B", "override_attempt", "reached_user", reached[0], reached[1], round(reached[2], 1), round(reached[3], 1), round(reached[4], 1)])
        tidy.append([rung, "B", "override_attempt", "model_leaked", modelled[0], modelled[1], round(modelled[2], 1), round(modelled[3], 1), round(modelled[4], 1)])
        tidy.append([rung, "B", "normal", "stopped", norm[0], norm[1], round(norm[2], 1), round(norm[3], 1), round(norm[4], 1)])

    note = "\nAutomatic labels plus corrections from reading the answers by hand (hand_read.csv). Per-run ranges show the spread across the repeated runs."
    if borderline:
        listed = ", ".join(k + " " + str(v) for k, v in sorted(borderline.items()))
        note += " Borderline cases not counted: " + listed + "."
        print("Borderline cases not counted:", listed)
    md.append(note)
    with open(os.path.join(OUT_DIR, "summary.md"), "w", encoding="utf-8") as file:
        file.write("\n".join(md) + "\n")
    with open(os.path.join(OUT_DIR, "summary.csv"), "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["rung", "set", "group", "measure", "n", "hits", "percent", "lowest_run_percent", "highest_run_percent"])
        writer.writerows(tidy)

    # ---- Reading list ----
    lines = []
    for rung in ["A1", "A2", "A3", "A4"]:
        for r in data.get(rung, []):
            if r["label"] in ("refused", "check", "blocked"):
                lines.append("[%s run %s %s] label=%s %s" % (rung, r["run"], r["question_id"], r["label"],
                             ("blocked at " + str(r.get("blocked_at")) + " " + str(r.get("input_verdict")) + "/" + str(r.get("output_verdict"))) if r["label"] == "blocked" else ""))
                lines.append("Q: " + r["prompt"])
                lines.append("A: " + (r["answer"] if r["answer"] else "(model never saw this question)"))
                lines.append("")
    set_b_lines = []
    for rung in ["B1", "B2", "B3"]:
        for r in data.get(rung, []):
            quiet = r["question_type"] == "override_attempt" and not r.get("leaks")
            normal_stopped = r["question_type"] == "normal" and is_stopped(r)
            if quiet or normal_stopped:
                kind = "QUIET OVERRIDE (no leak found, read for hints)" if quiet else "NORMAL QUESTION STOPPED"
                set_b_lines.append("[%s run %s %s] %s label=%s" % (rung, r["run"], r["question_id"], kind, r["label"]))
                set_b_lines.append("Q: " + r["prompt"])
                set_b_lines.append("A: " + (r["answer"] if r["answer"] else "(empty)"))
                set_b_lines.append("")
    with open(os.path.join(OUT_DIR, "to_read.txt"), "w", encoding="utf-8") as file:
        file.write("SET A: refused, check or blocked answers\n\n" + "\n".join(lines))
        file.write("\nSET B: quiet override answers and stopped normal questions\n\n" + "\n".join(set_b_lines))
    print()
    print("Wrote results/summary.md, results/summary.csv, results/to_read.txt")
    print("Answers to read by hand: Set A", sum(1 for l in lines if l.startswith("[")),
          "| Set B", sum(1 for l in set_b_lines if l.startswith("[")))

    # ---- Chart ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed, so no chart. Install it with: pip install matplotlib")
        return

    surface, ink, ink2, grid, bar = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
    panels = [
        ("Harmless risky-sounding questions\nwrongly stopped", set_a, ["A1", "A2", "A3", "A4"],
         ["A1 Llama alone", "A2 Llama + permissive prompt", "A3 Qwen uncensored", "A4 Llama + Llama Guard"]),
        ("Secret reached the user\n(8 override attempts)", set_b, ["B1", "B2", "B3"],
         ["B1 text lock", "B2 text lock on Qwen", "B3 text lock + code filter"]),
        ("Normal questions\nwrongly stopped", set_b_norm, ["B1", "B2", "B3"],
         ["B1 text lock", "B2 text lock on Qwen", "B3 text lock + code filter"]),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), facecolor=surface)
    for ax, (title, values, keys, names) in zip(axes, panels):
        ax.set_facecolor(surface)
        shown = [(k, n) for k, n in zip(keys, names) if k in values]
        ys = list(range(len(shown)))[::-1]
        for y, (k, n) in zip(ys, shown):
            p, low, high = values[k][2], values[k][3], values[k][4]
            ax.barh(y, p, height=0.42, color=bar)
            ax.plot([low, high], [y, y], color=ink2, linewidth=1.5, solid_capstyle="butt")
            ax.plot([low, low], [y - 0.1, y + 0.1], color=ink2, linewidth=1.5)
            ax.plot([high, high], [y - 0.1, y + 0.1], color=ink2, linewidth=1.5)
            ax.text(max(high, p) + 1.5, y, fmt(p), va="center", ha="left", color=ink, fontsize=10)
        ax.set_yticks(ys)
        ax.set_yticklabels([n for _, n in shown], color=ink, fontsize=9.5)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(["0", "25", "50", "75", "100%"], color=ink2, fontsize=9)
        ax.set_title(title, color=ink, fontsize=11, loc="left", fontweight="bold")
        ax.xaxis.grid(True, color=grid, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(grid)
        ax.tick_params(axis="y", length=0)
    fig.suptitle("Where does each lock hold, and what does it cost?", color=ink, fontsize=14, x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.02, "Bars: all runs together. Whiskers: lowest and highest single run. Counts checked by hand. Llama 3.2 1B and Qwen 3.5 4B, local Ollama, one Mac.",
             color=ink2, fontsize=9, ha="left")
    fig.tight_layout(rect=(0, 0.05, 1, 0.92))
    fig.savefig(os.path.join(OUT_DIR, "chart.png"), dpi=200, facecolor=surface)
    print("Wrote results/chart.png")


if __name__ == "__main__":
    main()
