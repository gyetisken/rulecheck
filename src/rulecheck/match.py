"""Map each city's rules onto the canonical requirements.

This is a second pass, kept separate from extraction on purpose. Extraction
answers "what does this document say"; matching answers "is this the same
obligation the other four cities have". Running them together would mean a
mistake in either one is impossible to attribute, and matching is the step
most likely to be wrong, because it is the step that requires judgement about
two texts rather than one.

The model never invents an identifier. It picks from the fixed list, or says
UNMAPPED, which is why the list lives in canonical.py and not in the prompt.
"""

from pathlib import Path

import anthropic
from pydantic import BaseModel

from .canonical import CANONICAL, CanonicalId
from .extract import MODEL, _parse_payload
from .models import Rule, RuleSet


class _Assignment(BaseModel):
    index: int
    canonical_id: CanonicalId


class _Assignments(BaseModel):
    assignments: list[_Assignment]


PROMPT = """Below are requirements extracted from the short-term rental ordinance of
{city}. Assign each one to the canonical requirement that describes the same
obligation, so that rules from different cities can be compared.

The canonical requirements are:

{catalogue}

Rules for the assignment:
- Match on what the operator has to do, not on wording. "The licence number must
  appear in the listing" and "no advertisement without a valid permit number"
  are the same obligation.
- A rule that states a threshold belongs to the requirement the threshold is
  for. A 1,000 foot separation is MIN_SEPARATION_BETWEEN_RENTALS whether the
  city frames it as a distance or as a cap on nearby units.
- Use UNMAPPED when the requirement is real but none of the entries fits.
  Do not stretch an entry to cover something it does not describe.
- Return exactly one assignment per rule, using the index shown.

The rules:

{rules}"""


def _catalogue() -> str:
    return "\n".join(f"- {key}: {text}" for key, text in CANONICAL.items())


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "canonical_id": {"type": "string", "enum": list(CANONICAL)},
                    },
                    "required": ["index", "canonical_id"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["assignments"],
        "additionalProperties": False,
    }


def match(city: str, rules: list[Rule]) -> list[Rule]:
    listing = "\n".join(
        f"{i}. [{rule.kind}] {rule.requirement}" for i, rule in enumerate(rules)
    )
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        tools=[
            {
                "name": "assign",
                "description": "Assign each rule to a canonical requirement.",
                "input_schema": _schema(),
                "strict": True,
            }
        ],
        tool_choice={"type": "tool", "name": "assign"},
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(
                    city=city, catalogue=_catalogue(), rules=listing
                ),
            }
        ],
    )
    print(
        f"tokens in: {message.usage.input_tokens}, out: {message.usage.output_tokens}"
    )

    assignments = _Assignments.model_validate(_parse_payload(message.content[0].input))
    by_index = {a.index: a.canonical_id for a in assignments.assignments}
    return [
        rule.model_copy(update={"canonical_id": by_index.get(i, "UNMAPPED")})
        for i, rule in enumerate(rules)
    ]


def match_file(path: Path, city: str) -> int:
    rules = RuleSet.model_validate_json(path.read_text())
    mapped = RuleSet(rules=match(city, rules.rules))
    path.write_text(mapped.model_dump_json(indent=2))
    return sum(1 for r in mapped.rules if r.canonical_id != "UNMAPPED")
