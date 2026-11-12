"""Element-by-element evaluation of a file, with principled abstention.

Unknown facts that the rule base may ask about (askable atoms) and
open-textured predicates without a reasoned human determination are
treated as open.  A value is reported for an element only if it is the
same under every completion of the open atoms; otherwise the element is
undetermined and the atoms that would decide it are listed.

Completions are built in two stages.  The open askable atoms are
completed first.  An open-textured atom is then open only in those
completions in which the rules do not already decide it (an interpretation
record may derive it from facts, as IR-4 derives affectedness from the
applicant's posting); otherwise a rule deriving it would be overridden
by a completion that simply asserts the opposite.  Presumptions (e.g. the
presumption that an act serves its purpose) close an open-textured atom
in the modes for which they are declared, again only where the rules do
not decide it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations, product

from .logic import Theory, atom, neg
from .rulebase import RuleBase, build_priority

MAX_OPEN = 12


@dataclass
class Result:
    values: dict
    aggregate: str
    decisive: dict = field(default_factory=dict)   # element -> atoms whose determination would decide it
    warnings: list = field(default_factory=list)
    theory: Theory | None = None
    open_atoms: list = field(default_factory=list)
    completions: int = 1
    reasons: dict = field(default_factory=dict)    # priority reasons, (stronger, weaker) -> criterion


def aggregate(values: dict) -> str:
    """Art. 2(1)(a) AJPA: one unlawful element suffices; lawful only if every element is."""
    if any(v == "F" for v in values.values()):
        return "F"
    if all(v == "T" for v in values.values()):
        return "T"
    return "R"


def _body_atoms(rules):
    seen = []
    for r in rules:
        for b in r.body:
            a = atom(b)
            if a not in seen:
                seen.append(a)
    return seen


def _differs_only_in(a1: dict, a2: dict, a: str) -> bool:
    """Two completions that assign a differently and agree on every other atom both assign."""
    if a not in a1 or a not in a2 or a1[a] == a2[a]:
        return False
    return all(a1[x] == a2[x] for x in a1.keys() & a2.keys() if x != a)


def _lits(atoms, values):
    return {a if v else neg(a) for a, v in zip(atoms, values)}


def evaluate(rb: RuleBase, facts, determinations=None, *, mode="review", t="2026-11-06",
             t_known="9999-12-31", elements=None) -> Result:
    rules = rb.select(t, t_known)
    sup, reasons = build_priority(rules)
    base = set(facts)
    for a, v in (determinations or {}).items():
        base.add(a if v else neg(a))
    known = {atom(l) for l in base}
    candidates = [a for a in _body_atoms(rules) if a not in known]

    probe0 = Theory(base, rules, sup)
    askable = [a for a in candidates
               if rb.open_predicate(a) is None and a.split("(")[0] in rb.askable
               and not (probe0.proved(a) or probe0.proved(neg(a)))]
    textured = [a for a in candidates if rb.open_predicate(a) is not None]
    if len(askable) > MAX_OPEN:
        raise ValueError(f"too many open atoms: {askable}")

    names = list(elements or rb.elements)
    rows = []                       # (assignment of open atoms, element values)
    presumed, open_textured = set(), []
    for combo in product((True, False), repeat=len(askable)):
        f1 = base | _lits(askable, combo)
        th1 = Theory(f1, rules, sup)
        pres, still_open = set(), []
        for a in textured:
            if th1.proved(a) or th1.proved(neg(a)):
                continue                                   # decided by the rules in this completion
            ot = rb.open_predicate(a)
            if ot.presume is not None and mode in ot.presume_in:
                pres.add(a if ot.presume else neg(a))
            else:
                still_open.append(a)
        if len(askable) + len(still_open) > MAX_OPEN:
            raise ValueError(f"too many open atoms: {askable + still_open}")
        presumed |= pres
        open_textured += [a for a in still_open if a not in open_textured]
        for combo2 in product((True, False), repeat=len(still_open)):
            th = Theory(f1 | pres | _lits(still_open, combo2), rules, sup)
            assignment = dict(zip(askable, combo))
            assignment.update(zip(still_open, combo2))
            rows.append((assignment, {e: th.value(rb.elements[e]["lawful"], rb.elements[e]["unlawful"])
                                      for e in names}))
    open_atoms = askable + open_textured

    values, decisive = {}, {}
    for e in names:
        seen = {vals[e] for _, vals in rows}
        if len(seen) == 1:
            values[e] = seen.pop()
            continue
        values[e] = "N"
        decisive[e] = [a for a in open_atoms
                       if any(v1[e] != v2[e] and _differs_only_in(a1, a2, a)
                              for (a1, v1), (a2, v2) in combinations(rows, 2))]

    probe = Theory(base | presumed, rules, sup)
    warnings = sorted(l for l in probe.plus_d if atom(l).startswith("warn_") and not l.startswith("~"))
    return Result(values, aggregate(values), decisive, warnings, probe, open_atoms, len(rows), reasons)
