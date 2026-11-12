"""Replay Right to Information Review Board decisions on Art. 25 RTIA.

Each row of bedk_art25.csv codes one decision at the level of the
Article 25 question: the facts as stated in the decision, the Board's
assessments of the two open-textured predicates, and whether the Board
held that Article 25 barred access.  Parts of a request decided on other
provisions are outside the rule base and were not coded.
"""
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unsur import evaluate, load   # noqa: E402

rb = load(ROOT / "rules" / "rti.yaml")

FACTS = {"employee": "employee(k)", "former": "formerEmployee(k)", "service_related": "serviceRelated(x,k)",
         "acts_for_staff": "actsForStaff(k)", "about": "about(x,k)", "personnel_record": "personnelRecord(x)",
         "internal": "internal(x)"}
DETERMINATIONS = {"public_concern": "publicConcern(x)", "affected": "affected(k,x)"}


def encode(row, determinations=True):
    facts = {"request(q,x)", "held(x)"}
    for col, lit in FACTS.items():
        if row[col] == "1":
            facts.add(lit)
        elif row[col] == "0":
            facts.add("~" + lit)
    if row["record_regulation"] == "1":
        facts.add("recordRegulation(x)")
    dets = {}
    if determinations:
        for col, lit in DETERMINATIONS.items():
            if row[col] in ("0", "1"):
                dets[lit] = row[col] == "1"
    return facts, dets


def replay(rows, determinations, mode):
    out = []
    for row in rows:
        facts, dets = encode(row, determinations)
        res = evaluate(rb, facts, dets, mode=mode, t=row["date"], elements=["cause"])
        value = res.values["cause"]
        expected = "T" if row["board_art25"] == "bar" else "F"
        status = "agree" if value == expected else ("refer" if value in ("N", "B") else "disagree")
        out.append({"id": row["id"], "split": row["split"], "pattern": row["pattern"], "board": expected,
                    "unsur": value, "status": status, "open": " ".join(res.decisive.get("cause", [])),
                    "completions": res.completions, "n_open": len(res.open_atoms)})
    return out


def summary(results, split):
    c = Counter(r["status"] for r in results if r["split"] == split)
    n = sum(c.values())
    decided = c["agree"] + c["disagree"]
    return {"n": n, "agree": c["agree"], "disagree": c["disagree"], "refer": c["refer"],
            "accuracy_on_decided": round(c["agree"] / decided, 3) if decided else None,
            "referral_rate": round(c["refer"] / n, 3) if n else None}


def main():
    rows = list(csv.DictReader(open(ROOT / "eval" / "bedk_art25.csv", encoding="utf-8")))
    runs = {
        "board": (True, "review"),          # facts and assessments as stated by the Board
        "withheld": (False, "review"),      # the two assessments removed
        "withheld_precheck": (False, "precheck"),
    }
    report, all_results = {}, {}
    for name, (dets, mode) in runs.items():
        t0 = time.perf_counter()
        res = replay(rows, dets, mode)
        elapsed = time.perf_counter() - t0
        all_results[name] = res
        report[name] = {s: summary(res, s) for s in ("dev", "test", "compendium")}
        report[name]["ms_per_file"] = round(1000 * elapsed / len(rows), 2)
        report[name]["max_open_atoms"] = max(r["n_open"] for r in res)

    by_pattern = defaultdict(Counter)
    for name in ("board", "withheld"):
        for r in all_results[name]:
            if r["split"] == "test":
                by_pattern[(name, r["pattern"])][r["status"]] += 1
    report["test_by_pattern"] = {f"{k[0]}:{k[1]}": dict(v) for k, v in sorted(by_pattern.items())}

    with open(ROOT / "eval" / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "split", "pattern", "board", "unsur_board", "status_board",
                    "unsur_withheld", "status_withheld", "open_withheld"])
        for a, b in zip(all_results["board"], all_results["withheld"]):
            w.writerow([a["id"], a["split"], a["pattern"], a["board"], a["unsur"], a["status"],
                        b["unsur"], b["status"], b["open"]])
    (ROOT / "eval" / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in report.items() if k != "test_by_pattern"}, indent=2))
    print("\nheld-out decisions by pattern (status counts):")
    for k, v in report["test_by_pattern"].items():
        print(f"  {k:<38} {v}")
    for name in ("board", "withheld"):
        print(f"\nnot in agreement ({name} run):")
        for r in all_results[name]:
            if r["status"] != "agree" and (name == "board" or r["status"] == "disagree" or r["split"] == "compendium"):
                print(f"  {r['id']:<10} {r['split']:<10} {r['pattern']:<20} board={r['board']} unsur={r['unsur']} open={r['open']}")


if __name__ == "__main__":
    main()
