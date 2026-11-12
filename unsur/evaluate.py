"""Element-by-element evaluation of a file, with principled abstention.

Unknown facts that the rule base may ask about (askable atoms) and
open-textured predicates without a reasoned human determination are
treated as open.  A value is reported for an element only if it is the
same under every completion of the open atoms; otherwise the element is
undetermined and the atoms that would decide it are listed.
Presumptions (e.g. the presumption that an act serves its purpose) close
an open predicate in the modes for which they are declared.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

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


def evaluate(rb: RuleBase, facts, determinations=None, *, mode="review", t="2026-11-06",
             t_known="9999-12-31", elements=None) -> Result:
    rules = rb.select(t, t_known)
    sup, reasons = build_priority(rules)
    base = set(facts)
    for a, v in (determinations or {}).items():
        base.add(a if v else neg(a))
    known = {atom(l) for l in base}

    open_atoms = []
    for a in _body_atoms(rules):
        if a in known:
            continue
        ot = rb.open_predicate(a)
        if ot is not None:
            if ot.presume is not None and mode in ot.presume_in:
                base.add(a if ot.presume else neg(a))
            else:
                open_atoms.append(a)
        elif a.split("(")[0] in rb.askable:
            open_atoms.append(a)

    probe = Theory(base, rules, sup)
    open_atoms = [a for a in open_atoms if not (probe.proved(a) or probe.proved(neg(a)))]
    if len(open_atoms) > MAX_OPEN:
        raise ValueError(f"too many open atoms: {open_atoms}")

    names = list(elements or rb.elements)
    table = {}
    for combo in product((True, False), repeat=len(open_atoms)):
        f = base | {a if v else neg(a) for a, v in zip(open_atoms, combo)}
        th = Theory(f, rules, sup)
        table[combo] = {e: th.value(rb.elements[e]["lawful"], rb.elements[e]["unlawful"]) for e in names}

    values, decisive = {}, {}
    for e in names:
        seen = {row[e] for row in table.values()}
        if len(seen) == 1:
            values[e] = seen.pop()
            continue
        values[e] = "N"
        matters = []
        for i, a in enumerate(open_atoms):
            for combo, row in table.items():
                flipped = combo[:i] + (not combo[i],) + combo[i + 1:]
                if table[flipped][e] != row[e]:
                    matters.append(a)
                    break
        decisive[e] = matters

    warnings = sorted(l for l in probe.plus_d if atom(l).startswith("warn_") and not l.startswith("~"))
    return Result(values, aggregate(values), decisive, warnings, probe, open_atoms, len(table), reasons)
