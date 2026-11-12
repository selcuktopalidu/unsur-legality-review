"""The worked example of the paper: a draft refusal under Art. 25 RTIA, checked before signature."""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unsur import evaluate, load                      # noqa: E402
from unsur.calendar_tr import add_days, nth_working_day, working_days_late   # noqa: E402
from unsur.counterfactual import minimal_changes        # noqa: E402

rb = load(ROOT / "rules" / "rti.yaml")

received = date(2026, 10, 14)
signed = date(2026, 11, 6)
deadline = {"I": nth_working_day(received, 15, half_day_counts=True),
            "II": nth_working_day(received, 15, half_day_counts=False)}
late = {k: working_days_late(d, signed, k == "I") for k, d in deadline.items()}

facts = {
    "request(q,x)", "held(x)", "internal(x)",
    "employee(k)", "posted(k,w)", "covers(x,w)",
    "~about(x,k)", "~personnelRecord(x)", "~formerEmployee(k)", "~actsForStaff(k)", "~serviceRelated(x,k)",
    "refusal(a)", "totalRefusal(a)", "reasons(a)", "~remedies(a)",
    "signs(p,a)", "authorised(p)",
}
if any(late.values()):
    facts.add("lateUnderSomeReading(a)")
determinations = {"publicConcern(x)": False}     # reasoned finding of the RTI unit

res = evaluate(rb, facts, determinations, mode="precheck", t=signed.isoformat())
rules = {r.id: r for r in rb.rules}


def show(node, indent="  ", depth=0):
    by = node["by"]
    label = "fact" if by == "fact" else (f"{by.id}: {by.src}" if by else "not proved")
    print(f"{indent}{node['lit']:<18}[{label}]")
    for r, over in node["superseded"]:
        names = ", ".join(f"{o.id}, {res.reasons[(o.id, r.id)]}" for o in over)
        print(f"{indent}  - {r.id} ({r.src}) applies but is overridden by {names}")
    for s, stronger in node["overridden"]:
        names = ", ".join(f"{t.id}, {res.reasons[(t.id, s.id)]}" for t in stronger)
        print(f"{indent}  - {s.id} ({s.src}) applies but is overridden by {names}")
    if depth < 2:
        for p in node["premises"]:
            show(p, indent + "    ", depth + 1)


print(f"UNSUR pre-check    rule base {rb.version}    reference date {signed}")
print("draft: refusal of request q (internal directive x) made by applicant k\n")
print(f"{'element':<15}{'value':<7}rules")
used = {"competence": "k1", "form": "f1 w1 w2", "cause": "r1 r2 r3 c1 d1", "subject": "m1", "purpose": "p0"}
for e, v in res.values.items():
    print(f"{e:<15}{v:<7}{used[e]}")
print(f"{'aggregate':<15}{res.aggregate}")
print("warnings:", ", ".join(w + f" ({rules['w1' if 'remedies' in w else 'w2'].record})" for w in res.warnings))

print("\nwhy cause = F")
show(res.theory.why("access(q)"))

print("\ntime limit, RTIA Art. 11(1) with IR-1 and IR-2")
print(f"  request received          {received} ({received:%a})")
for k, d in deadline.items():
    print(f"  reading {k:<3} 15th working day {d} ({d:%a})   signed {signed}: "
          + (f"{late[k]} working day(s) late" if late[k] else "in time"))

base, changes = minimal_changes(
    rb, facts, determinations,
    ["employee(k)", "posted(k,w)", "covers(x,w)", "internal(x)", "held(x)", "reasons(a)", "publicConcern(x)"],
    mode="precheck", t=signed.isoformat())
print(f"\nminimal changes that alter the aggregate ({base})")
for c in changes:
    f, d = set(facts), dict(determinations)
    from unsur.counterfactual import flip   # noqa: E402
    for lit in c:
        f, d = flip(f, d, lit)
    r = evaluate(rb, f, d, mode="precheck", t=signed.isoformat())
    extra = f"   open: {', '.join(r.decisive.get('cause', []))}" if r.aggregate == "R" else ""
    print(f"  flip {', '.join(c):<16} -> {r.aggregate}{extra}")

notified = date(2026, 11, 9)
print(f"\nremedies if the refusal is maintained: objection to the Board within 15 days of notification "
      f"(notified {notified} -> {add_days(notified, 15)}); action for annulment within 60 days (AJPA Art. 7)")
