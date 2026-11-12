"""Minimal changes to the facts that alter the aggregate result."""
from itertools import combinations

from .evaluate import evaluate
from .logic import neg


def flip(facts, determinations, lit):
    facts = set(facts)
    determinations = dict(determinations)
    a = lit.lstrip("~")
    if a in determinations:
        determinations[a] = not determinations[a]
    elif lit in facts:
        facts.discard(lit)
        facts.add(neg(lit))
    else:
        facts.discard(neg(lit))
        facts.add(lit)
    return facts, determinations


def minimal_changes(rb, facts, determinations, candidates, *, mode="precheck", max_size=2, **kw):
    """All subset-minimal sets of flipped literals (up to max_size) that change the aggregate."""
    base = evaluate(rb, facts, determinations, mode=mode, **kw).aggregate
    found = []
    for k in range(1, max_size + 1):
        for combo in combinations(candidates, k):
            if any(set(f) <= set(combo) for f in found):
                continue
            f, d = set(facts), dict(determinations)
            for lit in combo:
                f, d = flip(f, d, lit)
            new = evaluate(rb, f, d, mode=mode, **kw).aggregate
            if new != base:
                found.append(combo)
    return base, found
