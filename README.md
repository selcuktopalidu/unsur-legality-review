# UNSUR

UNSUR checks a draft administrative act element by element (competence, form,
cause, subject matter and purpose, the five grounds of Article 2(1)(a) of the
Turkish Administrative Judicial Procedure Act) and reports, for each element,
whether the act is lawful, unlawful, or has to be referred to a person. The
legal knowledge is written as rules in defeasible logic; conflicts between
norms are resolved by *lex superior*, *lex specialis* and *lex posterior*, and
every conclusion comes with the provisions and facts it rests on. Where the
answer depends on an open-textured predicate such as "of concern to the
public", the system does not guess: it reports which determination is missing
and leaves the file to the official.

The rule base covers refusals under Article 25 (internal regulations) of the
Turkish Right to Information Act, Law No. 4982. The `eval` folder replays 107
decisions of the Right to Information Review Board (Bilgi Edinme Değerlendirme
Kurulu) on that article.

This repository accompanies the paper

> Öztoprak S, Topal S. Element-wise legality review of administrative acts in
> defeasible logic, with an evaluation on Turkish right-to-information
> decisions. Manuscript in preparation.

## Running it

Python 3.10 or later.

```
pip install -r requirements.txt
python examples/worked_example.py     # worked example of Section 5.3 of the paper
python eval/run_bedk.py               # replay of the Board's decisions -> eval/results.csv, eval/summary.json
python eval/consistency.py            # Art. 25 encoding against a direct reading, 81 input configurations
python eval/make_figure.py            # Figure 3 of the paper
python -m pytest tests                # unit tests
```

## Layout

| path | contents |
|---|---|
| `unsur/logic.py` | defeasible logic (+Δ, −Δ, +∂, −∂), support, four-valued element values, proof trees |
| `unsur/rulebase.py` | YAML loader, priority relation (explicit > lex superior > lex specialis > lex posterior), bitemporal selection |
| `unsur/evaluate.py` | evaluation of a file: open atoms, completions, presumptions by mode, aggregation |
| `unsur/calendar_tr.py` | working-day arithmetic, including the 28 October half day |
| `unsur/counterfactual.py` | subset-minimal changes that alter the aggregate result |
| `rules/rti.yaml` | the rule base (version rti-0.3) and interpretation records IR-1 to IR-8 |
| `eval/bedk_art25.csv` | the 107 coded decisions |
| `eval/results.csv`, `eval/summary.json` | output of the replay |
| `eval/coding_notes.md` | notes taken while reading the decisions, including the decisions left out and why |

## The decision data

The decisions from June 2004 to November 2005 were read from the Board's
record of its meetings and decisions as reproduced by a civil-society
organisation at <https://www.bilgiedinmehakki.org/doc/BEDK_kararlar.pdf>. The
three later decisions were read from the Board's website:
[2020/1796](https://bedk.adalet.gov.tr/Resimler/SayfaDokuman/610202114570116.12.2020%20Tarih%20ve%202020.1796%20say%C4%B1l%C4%B1%20Karar.pdf),
[2021/1027](https://bedk.adalet.gov.tr/Resimler/SayfaDokuman/61020211500352021-1027%20Nolu%20Karar.pdf) and
[2022/964](https://bedk.adalet.gov.tr/Resimler/SayfaDokuman/120920220920002022-964.pdf).

Each row codes the Article 25 question only. Parts of a request that the Board
decided on other provisions (Arts. 3, 7, 19, 21, 27) are mentioned in `note`
and are not part of the comparison. The 2004 decisions (`split = dev`) were
used to write interpretation records IR-6 to IR-8; the rule base was then left
unchanged for the decisions from 2005 onwards (`split = test`).

Columns of `eval/bedk_art25.csv` (1 = yes, 0 = no, empty = not stated in the decision):

| column | meaning |
|---|---|
| `id`, `date` | decision number and date |
| `split` | `dev` (2004) or `test` (2005 onwards) |
| `institution`, `request` | the institution and a summary of what was requested |
| `pattern` | kind of case, used to group the results |
| `employee` | the applicant works for the institution |
| `former` | the applicant used to work for the institution |
| `service_related` | the documents relate to the applicant's period of service |
| `acts_for_staff` | the applicant is a union or a lawyer acting for staff |
| `about` | the documents concern the applicant personally |
| `personnel_record` | the documents are personnel or evaluation records |
| `record_regulation` | the institution relied on the record regulation |
| `internal` | the documents are internal regulations or practices in the sense of Art. 25 |
| `public_concern` | the Board found the information to be of concern to the public |
| `affected` | the Board found the applicant to be affected |
| `board_art25` | whether the Board held that Art. 25 barred access (`bar`, `no_bar`) |
| `board_outcome` | `accept`, `partial` or `reject` |
| `note` | remarks |

The coding was done from text extracts of the decisions and is being checked
against the original decisions; check the latest version of this file before
citing the results.

## Licence

The code is released under the GNU General Public License v3.0 (`LICENSE`).
The coded data in `eval/` are released under the Creative Commons Attribution
4.0 International licence (`eval/LICENSE`).

## Citation

See `CITATION.cff`.
