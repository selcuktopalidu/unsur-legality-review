"""Exhaustive check of the Art. 25 encoding against a direct reading of the provision.

Four inputs, each true, false or unknown: whether the document is an internal
regulation, whether the applicant is an employee, and the two assessments
(affected, of public concern).  The direct reading: access unless the document
is internal, of no public concern, and the applicant is not an affected
employee.  With unknown inputs the reading abstains unless every completion
gives the same answer.
"""
import sys
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unsur import evaluate, load   # noqa: E402

rb = load(ROOT / "rules" / "rti.yaml")
VALUES = (True, False, None)


def reading(internal, employee, affected, public):
    def outcome(i, e, a, p):
        return "T" if i and not p and not (e and a) else "F"
    opts = lambda v: (True, False) if v is None else (v,)
    seen = {outcome(i, e, a, p) for i in opts(internal) for e in opts(employee)
            for a in opts(affected) for p in opts(public)}
    return seen.pop() if len(seen) == 1 else "N"


def engine(internal, employee, affected, public):
    facts = {"request(q,x)", "held(x)", "~about(x,k)", "~personnelRecord(x)", "~formerEmployee(k)",
             "~actsForStaff(k)", "~serviceRelated(x,k)", "~posted(k,w)", "~covers(x,w)"}
    for lit, v in (("internal(x)", internal), ("employee(k)", employee)):
        if v is not None:
            facts.add(lit if v else "~" + lit)
    dets = {lit: v for lit, v in (("affected(k,x)", affected), ("publicConcern(x)", public)) if v is not None}
    return evaluate(rb, facts, dets, mode="review", elements=["cause"]).values["cause"]


if __name__ == "__main__":
    mismatches = []
    configs = list(product(VALUES, repeat=4))
    for cfg in configs:
        if reading(*cfg) != engine(*cfg):
            mismatches.append((cfg, reading(*cfg), engine(*cfg)))
    print(f"{len(configs)} configurations, {len(mismatches)} mismatches")
    for m in mismatches:
        print(" ", m)
