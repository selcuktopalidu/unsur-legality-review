"""Ground propositional defeasible logic.

Proof conditions follow Antoniou, Billington, Governatori and Maher (2001):
definite provability (+D/-D) over facts and strict rules, defeasible
provability (+d/-d) with team defeat and ambiguity blocking.  On top of
this the module defines the support relation used for the four-valued
evaluation of the elements of an administrative act.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

STRICT, DEFEASIBLE, DEFEATER = "strict", "defeasible", "defeater"


def neg(lit: str) -> str:
    return lit[1:] if lit.startswith("~") else "~" + lit


def atom(lit: str) -> str:
    return lit.lstrip("~")


@dataclass(frozen=True)
class Rule:
    id: str
    body: tuple[str, ...]
    head: str
    kind: str = DEFEASIBLE
    src: str = ""
    level: int = 4
    element: str = ""
    valid_from: str = "1900-01-01"
    valid_to: str = "9999-12-31"
    beats: tuple[str, ...] = ()
    record: str = ""          # interpretation record the rule depends on, if any

    def __str__(self) -> str:
        arrow = {STRICT: "->", DEFEASIBLE: "=>", DEFEATER: "~>"}[self.kind]
        return f"{self.id}: {' & '.join(self.body) or 'T'} {arrow} {self.head}"


class Theory:
    """A defeasible theory D = (F, R, >) together with its extension."""

    def __init__(self, facts, rules, sup):
        self.facts = frozenset(facts)
        self.rules = tuple(rules)
        self.sup = frozenset(sup)
        self.by_head = defaultdict(list)
        for r in self.rules:
            self.by_head[r.head].append(r)
        lits = set(self.facts)
        for r in self.rules:
            lits.add(r.head)
            lits.update(r.body)
        self.lits = lits | {neg(l) for l in lits}
        self._definite()
        self._defeasible()

    # rules with a given head
    def rules_for(self, lit, defeaters=True):
        return [r for r in self.by_head.get(lit, ()) if defeaters or r.kind != DEFEATER]

    def _definite(self):
        plus = set(self.facts)
        changed = True
        while changed:
            changed = False
            for r in self.rules:
                if r.kind == STRICT and r.head not in plus and all(b in plus for b in r.body):
                    plus.add(r.head)
                    changed = True
        minus = set()
        changed = True
        while changed:
            changed = False
            for l in self.lits:
                if l in minus or l in plus:
                    continue
                strict = [r for r in self.by_head.get(l, ()) if r.kind == STRICT]
                if all(any(b in minus for b in r.body) for r in strict):
                    minus.add(l)
                    changed = True
        self.plus_D, self.minus_D = plus, minus

    def _defeasible(self):
        plus, minus = set(), set()
        changed = True
        while changed:
            changed = False
            for l in self.lits:
                if l not in plus and self._plus_d(l, plus, minus):
                    plus.add(l)
                    changed = True
                if l not in minus and self._minus_d(l, plus, minus):
                    minus.add(l)
                    changed = True
        self.plus_d, self.minus_d = plus, minus

    def _plus_d(self, l, plus, minus):
        if l in self.plus_D:
            return True
        if neg(l) not in self.minus_D:
            return False
        team = [r for r in self.rules_for(l, defeaters=False) if all(b in plus for b in r.body)]
        if not team:
            return False
        for s in self.rules_for(neg(l)):
            if any(b in minus for b in s.body):
                continue
            if any((t.id, s.id) in self.sup for t in team):
                continue
            return False
        return True

    def _minus_d(self, l, plus, minus):
        if l in self.plus_D or l not in self.minus_D:
            return False
        if neg(l) in self.plus_D:
            return True
        if all(any(b in minus for b in r.body) for r in self.rules_for(l, defeaters=False)):
            return True
        for s in self.rules_for(neg(l)):
            if all(b in plus for b in s.body) and all(
                any(b in minus for b in t.body) or (t.id, s.id) not in self.sup
                for t in self.rules_for(l, defeaters=False)
            ):
                return True
        return False

    # ---- queries -------------------------------------------------------
    def proved(self, lit) -> bool:
        return lit in self.plus_d

    def applicable(self, r: Rule) -> bool:
        return all(b in self.plus_d for b in r.body)

    def overriders(self, r: Rule):
        """Applicable rules for the complement of r's head that are stronger than r."""
        return [s for s in self.rules_for(neg(r.head)) if self.applicable(s) and (s.id, r.id) in self.sup]

    def supported(self, lit) -> bool:
        """An applicable strict or defeasible rule for lit that no stronger applicable rule overrides."""
        if lit in self.plus_D:
            return True
        if neg(lit) in self.plus_D:
            return False
        return any(self.applicable(r) and not self.overriders(r)
                   for r in self.rules_for(lit, defeaters=False))

    def value(self, lawful: str, unlawful: str) -> str:
        """Four-valued evaluation of one element.

        T or F when the lawful or the unlawful literal is defeasibly provable;
        B when neither is provable but both are supported (a conflict the
        priority relation leaves open); N otherwise.
        """
        if lawful in self.plus_d:
            return "T"
        if unlawful in self.plus_d:
            return "F"
        if self.supported(lawful) and self.supported(unlawful):
            return "B"
        return "N"

    def why(self, lit, depth=0, seen=None):
        """A proof tree for lit as nested dicts (used by the explanation layer)."""
        seen = set() if seen is None else seen
        node = {"lit": lit, "by": None, "premises": [], "overridden": [], "inapplicable": [], "superseded": []}
        if lit in self.facts:
            node["by"] = "fact"
            return node
        if lit in seen or depth > 12:
            return node
        seen = seen | {lit}
        for r in self.rules_for(lit, defeaters=False):
            if self.applicable(r) and not self.overriders(r):
                if node["by"] is None:
                    node["by"] = r
                    node["premises"] = [self.why(b, depth + 1, seen) for b in r.body]
            elif self.applicable(r):
                node["superseded"].append((r, self.overriders(r)))
        for s in self.rules_for(neg(lit)):
            if self.applicable(s):
                node["overridden"].append((s, [t for t in self.rules_for(lit) if (t.id, s.id) in self.sup and self.applicable(t)]))
            else:
                missing = [b for b in s.body if b not in self.plus_d]
                node["inapplicable"].append((s, missing))
        return node
