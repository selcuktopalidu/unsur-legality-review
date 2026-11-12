import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unsur import Rule, Theory, evaluate, load               # noqa: E402
from unsur.calendar_tr import nth_working_day               # noqa: E402
from unsur.logic import DEFEATER, STRICT                     # noqa: E402
from unsur.rulebase import Change, build_priority           # noqa: E402

RB = load(ROOT / "rules" / "rti.yaml")


def test_specificity_and_explicit_priority():
    bird = Rule("b", ("bird",), "flies")
    peng = Rule("p", ("bird", "penguin"), "~flies")
    sup, why = build_priority([bird, peng])
    assert ("p", "b") in sup and why[("p", "b")] == "lex specialis"
    th = Theory({"bird", "penguin"}, [bird, peng], sup)
    assert th.proved("~flies") and not th.proved("flies")


def test_ambiguity_gives_both_under_support():
    q = Rule("q", ("quaker",), "pacifist")
    r = Rule("r", ("republican",), "~pacifist")
    th = Theory({"quaker", "republican"}, [q, r], set())
    assert not th.proved("pacifist") and not th.proved("~pacifist")
    assert th.value("pacifist", "~pacifist") == "B"


def test_defeater_blocks_without_supporting():
    r = Rule("r", ("a",), "c")
    d = Rule("d", ("b",), "~c", kind=DEFEATER)
    th = Theory({"a", "b"}, [r, d], set())
    assert not th.proved("c") and not th.proved("~c")
    assert th.value("c", "~c") == "N"


def test_lex_superior_before_lex_posterior():
    old_statute = Rule("s", ("x",), "y", level=4, valid_from="2004-01-01")
    new_regulation = Rule("g", ("x",), "~y", level=2, valid_from="2020-01-01")
    sup, why = build_priority([old_statute, new_regulation])
    assert why[("s", "g")] == "lex superior"


def test_cyclic_priority_is_rejected():
    a = Rule("a", ("x",), "y", beats=("b",))
    b = Rule("b", ("x",), "~y", beats=("a",))
    with pytest.raises(ValueError):
        build_priority([a, b])


def test_bitemporal_selection():
    rb = load(ROOT / "rules" / "rti.yaml")
    rb.changes = [Change("r5", known="2010-03-01", effective="2010-03-01", retroactive=True)]
    ids = lambda rules: {r.id for r in rules}
    assert "r5" in ids(rb.select("2009-06-01", t_known="2009-12-31"))    # as known at the time
    assert "r5" not in ids(rb.select("2009-06-01", t_known="2026-01-01"))  # annulled ex tunc
    rb.changes = [Change("r5", known="2010-03-01", effective="2010-03-01", retroactive=False)]
    assert "r5" in ids(rb.select("2009-06-01", t_known="2026-01-01"))      # repeal ex nunc


def test_deadline_readings():
    assert nth_working_day(date(2026, 10, 14), 15, True) == date(2026, 11, 5)
    assert nth_working_day(date(2026, 10, 14), 15, False) == date(2026, 11, 6)


WORKED = {"request(q,x)", "held(x)", "internal(x)", "employee(k)", "posted(k,w)", "covers(x,w)",
          "~about(x,k)", "~personnelRecord(x)", "~formerEmployee(k)", "~actsForStaff(k)",
          "~serviceRelated(x,k)", "refusal(a)", "totalRefusal(a)", "reasons(a)", "~remedies(a)",
          "signs(p,a)", "authorised(p)"}


def test_worked_example():
    res = evaluate(RB, WORKED, {"publicConcern(x)": False}, mode="precheck")
    assert res.values == {"competence": "T", "form": "T", "cause": "F", "subject": "F", "purpose": "T"}
    assert res.aggregate == "F"
    assert "warn_remedies(a)" in res.warnings


def test_abstention_when_affectedness_is_open():
    facts = (WORKED - {"posted(k,w)"}) | {"~posted(k,w)"}
    res = evaluate(RB, facts, {"publicConcern(x)": False}, mode="precheck")
    assert res.values["cause"] == "N" and res.decisive["cause"] == ["affected(k,x)"]
    assert res.aggregate == "R"


def test_presumption_only_in_precheck():
    facts = WORKED - {"employee(k)"} | {"~employee(k)"}
    assert evaluate(RB, facts, {}, mode="precheck").values["cause"] == "F"   # exception not shown
    assert evaluate(RB, facts, {}, mode="review").values["cause"] == "N"     # left to the reviewer


def test_record_regulation_yields_to_statute():
    facts = {"request(q,x)", "held(x)", "internal(x)", "personnelRecord(x)", "about(x,k)", "recordRegulation(x)"}
    res = evaluate(RB, facts, {"publicConcern(x)": False}, mode="review", elements=["cause"])
    assert res.values["cause"] == "F"


def test_rules_deriving_open_textured_atoms_stay_active():
    # affectedness is open, but IR-4 can derive it from the posting: the posting must count as decisive
    facts = {"request(q,x)", "held(x)", "internal(x)", "employee(k)", "~about(x,k)", "~personnelRecord(x)",
             "~formerEmployee(k)", "~actsForStaff(k)", "~serviceRelated(x,k)"}
    res = evaluate(RB, facts, {"publicConcern(x)": False}, mode="review", elements=["cause"])
    assert res.values["cause"] == "N"
    assert {"posted(k,w)", "covers(x,w)", "affected(k,x)"} <= set(res.decisive["cause"])
    # once posting and coverage are established, the completions no longer contradict d1
    res = evaluate(RB, facts | {"posted(k,w)", "covers(x,w)"}, {"publicConcern(x)": False},
                   mode="review", elements=["cause"])
    assert res.values["cause"] == "F"
