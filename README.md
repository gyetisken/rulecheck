# rulecheck

Five US cities regulate short-term rentals. All five require a licence, three
require the owner to live there, two require insurance, and every one of them
writes it differently. This reads all five ordinances and puts them in one table.

![The five cities side by side](docs/compare.png)

A model reads each ordinance once. Everything after that is ordinary code.

## The idea

The hard part of this problem is not the language. It is that the same
obligation shows up as *operator's license* in Austin, *permit* in New Orleans,
and *short-term residential occupancy licence* in San Diego, and no amount of
string matching will tell you those are the same thing.

So there are two passes, and they are kept apart on purpose:

**Extraction** reads one ordinance and returns a list of requirements, each one
carrying the sentence it came from. The model is handed a schema it is required
to fill, so the category field cannot take a value outside the enumerated list
and no requirement can be recorded without its source text.

**Matching** takes those requirements and assigns each to one of seventeen
shared identifiers. This is the canonical model, and it is deliberately fixed.
A requirement that genuinely does not fit is marked unmapped and shown
separately rather than forced into the nearest box — thirty of the hundred and
thirty-three currently sit there, which is information, not a gap.

Keeping the passes separate matters because they fail differently. Extraction
gets the ordinance wrong; matching gets the comparison wrong. Run them as one
step and a bad row in the table could be either.

![The schema handed to the model](docs/schema.png)

## Where the model is, and where it is not

| Step | Model | Why |
|---|---|---|
| Download and clean the ordinance | no | Stripping page headers is not a judgement call |
| Extract requirements | **yes** | Reading law requires reading |
| Assign a shared identifier | **yes** | Deciding two sentences mean the same thing requires judgement |
| Build the comparison | no | Grouping labelled records is a `for` loop |
| Check a property | no | "Does this licence exist" is a comparison, not an inference |

Putting a model in the last row would make the tool slower, more expensive, and
impossible to test.

## Silence is not a no

![Checking one property](docs/check.png)

Each rule resolves to satisfied, violated or unknown, and the third one is the
reason the project exists. Submitting the form with nothing filled in returns
zero violations, not thirty, because nobody has said anything yet.

Unknown is also split in two, which matters more than it sounds. One kind you
can clear by answering a question. The other no answer will ever settle: whether
noise carries past the property line, whether the place is habitable, whether a
local contact really turns up within two hours. Those are judgements, so they
are handed to a person rather than guessed at.

Austin states the licence requirement in twelve separate places, so a property
without one fails twelve rules. The page says *you do not have a licence* once,
and keeps the twelve behind a toggle for anyone who wants them.

## Running it

```bash
docker compose up          # http://localhost:8000
```

Or without Docker:

```bash
uv sync
uv run rulecheck serve
```

Rebuilding the data needs an Anthropic API key in `.env`:

```bash
uv run rulecheck fetch              # download all five ordinances
uv run rulecheck extract            # ordinance text  -> rules
uv run rulecheck match              # rules -> shared identifiers
uv run rulecheck compare            # print the table
uv run rulecheck check --rules data/austin.rules.json \
                       --property examples/austin-house.json
```

`fetch` is reproducible: the source URL for each city lives in `sources.py`, so
the corpus can be rebuilt from nothing rather than trusting whatever text file
happens to be checked in.

## What is wrong with it

The table has visible errors and they are left visible. `LICENSE_REQUIRED` shows
*12 months* for Austin and *90 days* for Nashville; those are periods belonging
to other requirements that the matching pass filed in the wrong row. New Orleans
shows *18 years* under `OWNER_MUST_OWN_UNIT`, which is the minimum age of the
operator, not a fact about ownership.

All three are the same failure: a rule carries a number, and the number gets
treated as the threshold for whichever requirement the rule landed under.

The next piece of work is measuring that rather than patching it by hand. A
hand-written answer key for one city, compared against what the model produced,
turns "it looks mostly right" into a number that moves when the prompt changes.

## Stack

Python 3.13, uv, Pydantic for the schemas, FastAPI for the interface, pytest and
ruff. The Anthropic API with strict tool use.

Ordinances are public documents, downloaded unedited and quoted in place.
Nothing here is legal advice.
