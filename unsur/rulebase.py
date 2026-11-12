"""Loading a rule base, building the priority relation, temporal selection."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .logic import DEFEASIBLE, Rule, atom, neg

CRITERIA = ("explicit priority", "lex superior", "lex specialis", "lex posterior")


@dataclass
class OpenTexture:
    name: str                  # predicate name, e.g. publicConcern
    burden: str = ""           # who must establish it, for the record
    presume: bool | None = None
    presume_in: tuple = ()     # modes in which the presumption applies


@dataclass
class Change:
    """A recorded change to a rule: known from `known`, effective from `effective`."""
    rule: str
    known: str
    effective: str
    retroactive: bool


@dataclass
class RuleBase:
    version: str
    rules: list
    elements: dict
    open_texture: dict
    askable: list
    records: dict
    changes: list = field(default_factory=list)

    def select(self, t: str, t_known: str = "9999-12-31"):
        """R(t, t'): the rules valid at t according to what was recorded by t'."""
        out = []
        for r in self.rules:
            start, end = r.valid_from, r.valid_to
            for c in self.changes:
                if c.rule == r.id and c.known <= t_known:
                    if c.retroactive:
                        start, end = "9999-12-31", "0000-01-01"   # empty interval
                    else:
                        end = min(end, c.effective)
            if start <= t < end:
                out.append(r)
        return out

    def priority(self, rules=None):
        rules = self.rules if rules is None else rules
        return build_priority(rules)

    def open_predicate(self, lit: str):
        name = atom(lit).split("(")[0]
        return self.open_texture.get(name)


def _specific(a: Rule, b: Rule) -> bool:
    # for conjunctions of literals, phi(a) |= phi(b) iff body(b) is a subset of body(a)
    return set(b.body) < set(a.body)


def build_priority(rules):
    """Lexicographic combination of the four criteria for every pair of conflicting rules."""
    ids = {r.id for r in rules}
    explicit = {(r.id, w) for r in rules for w in r.beats if w in ids}
    tests = (
        lambda a, b: (a.id, b.id) in explicit,
        lambda a, b: a.level > b.level,
        _specific,
        lambda a, b: a.valid_from > b.valid_from,
    )
    sup, reason = set(), {}
    for a in rules:
        for b in rules:
            if a.head != neg(b.head):
                continue
            for name, test in zip(CRITERIA, tests):
                if test(a, b):
                    sup.add((a.id, b.id))
                    reason[(a.id, b.id)] = name
                    break
                if test(b, a):
                    break
    if _has_cycle(sup):
        raise ValueError("priority relation is cyclic")
    return sup, reason


def _has_cycle(pairs) -> bool:
    graph = {}
    for a, b in pairs:
        graph.setdefault(a, set()).add(b)
    state = {}

    def visit(n):
        state[n] = 1
        for m in graph.get(n, ()):
            if state.get(m) == 1 or (m not in state and visit(m)):
                return True
        state[n] = 2
        return False

    return any(n not in state and visit(n) for n in list(graph))


def load(path) -> RuleBase:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    rules = []
    for d in data["rules"]:
        rules.append(Rule(
            id=d["id"], body=tuple(d.get("if", [])), head=d["then"],
            kind=d.get("kind", DEFEASIBLE), src=d.get("src", ""), level=d.get("level", 4),
            element=d.get("element", ""), valid_from=str(d.get("valid_from", "1900-01-01")),
            valid_to=str(d.get("valid_to", "9999-12-31")), beats=tuple(d.get("beats", [])),
            record=d.get("record", ""),
        ))
    ot = {}
    for name, spec in (data.get("open_textured") or {}).items():
        spec = spec or {}
        ot[name] = OpenTexture(name, spec.get("burden", ""), spec.get("presume"),
                               tuple(spec.get("presume_in", [])))
    changes = [Change(c["rule"], str(c["known"]), str(c["effective"]), bool(c.get("retroactive")))
               for c in data.get("changes", [])]
    return RuleBase(data.get("version", ""), rules, data.get("elements", {}), ot,
                    data.get("askable", []), data.get("records", {}), changes)
