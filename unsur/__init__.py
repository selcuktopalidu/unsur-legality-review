"""UNSUR: element-wise legality review of administrative acts in defeasible logic."""
from .logic import Rule, Theory, neg
from .rulebase import RuleBase, load
from .evaluate import Result, evaluate, aggregate

__all__ = ["Rule", "Theory", "neg", "RuleBase", "load", "Result", "evaluate", "aggregate"]
__version__ = "0.3"
