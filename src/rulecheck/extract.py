"""Turn an ordinance text into a list of Rule objects, using Claude."""

import json
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from .models import Rule, RuleSet

MODEL = "claude-opus-5"

PROMPT = """You are reading the short-term rental ordinance for {city}.

Extract every requirement that the owner or operator of a short-term rental must
satisfy in order to operate legally.

What counts as a requirement:
- Something the owner or operator must do, must have, or may not do.
- Include deadlines, limits and numeric thresholds when the text states them.

What to leave out:
- Obligations placed on booking platforms rather than on the owner or operator.
- Obligations placed on the city, the director or a hearing officer.
- Definitions, appeal procedure, penalties and severability clauses.

Classify each requirement with one of these kinds:
- license: the owner needs a licence, a permit, a renewal, or must display a
  licence number.
- ownership: who must own the unit, or restrictions on owning it. Owning a
  property and living in it are different facts; do not merge them.
- owner_occupancy: the owner, or a tenant acting with permission, has to live on
  the property or occupy it for part of the year.
- unit_cap: a limit on how many units one person may operate, on one site or in
  total.
- distance: a required separation between one rental and another.
- insurance: a required insurance policy or minimum coverage.
- tax: hotel occupancy tax, remittance or registration with the tax office.
- other: a real requirement that none of the above describes.

How to fill each field:
- requirement: one short sentence in your own words, written the same way you
  would write it for any other city, so that two cities expressing the same rule
  end up with similar text. Start with "Owner must" or "Owner may not".
  Example: "Owner must hold a valid operator license for each unit."
- section: the section number the requirement comes from, for example 4-23-32.
- quote: the sentence from the ordinance that the requirement rests on, copied
  verbatim. The text was extracted from a PDF and a few words are split across
  spaces; copy them exactly as they appear rather than repairing them.
- city: {city}
- value and unit: only when the text states a number that the rule turns on, for
  example 1000 with unit feet, or 25 with unit percent. Leave both empty
  otherwise. Never invent a number.

Never record a requirement that the text does not state. If the ordinance is
silent on something, leave it out.

Ordinance text:

{text}"""


def _schema() -> dict:
    """A flat schema, declared by hand.

    Pydantic emits a $ref to Rule, and the model answered that by putting the
    whole array into a JSON string. Inlining the shape fixed it. Strict mode
    then makes the guarantee explicit rather than hoping, which is why every
    field is listed in `required` and the optional ones are nullable instead.
    """
    rule = Rule.model_json_schema()
    rule["additionalProperties"] = False
    rule["required"] = list(rule["properties"])
    for optional in ("value", "unit"):
        inner = rule["properties"][optional]
        inner.pop("anyOf", None)
        inner["type"] = (
            ["number", "null"] if optional == "value" else ["string", "null"]
        )
    return {
        "type": "object",
        "properties": {"rules": {"type": "array", "items": rule}},
        "required": ["rules"],
        "additionalProperties": False,
    }


def _parse_payload(payload: object) -> object:
    """The model is an untrusted source. Unwrap before validating.

    Strict mode makes this close to dead code, and it stays because it cost one
    debugging session to find the first time: before the schema was inlined the
    model returned the whole array as a JSON string inside the field.
    """
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict) and isinstance(payload.get("rules"), str):
        payload = json.loads(payload["rules"])
    return payload


def extract(city: str, text: str) -> RuleSet:
    client = anthropic.Anthropic()

    tool = {
        "name": "save_rules",
        "description": "Save the requirements found in the ordinance text.",
        "input_schema": _schema(),
        # Without this the model is merely asked to match the schema. With it
        # the API guarantees the arguments validate, which matters here because
        # the extraction is measured and a malformed run would be noise in the
        # numbers rather than a visible failure.
        "strict": True,
    }

    message = client.messages.create(
        model=MODEL,
        # Sampling parameters are not available on current models, so runs
        # cannot be pinned with temperature=0. Repeatability has to come from
        # the schema and the prompt instead: a strict tool, an explicit set of
        # categories, and rules about what not to record.
        max_tokens=16000,
        tools=[tool],
        tool_choice={"type": "tool", "name": "save_rules"},
        messages=[{"role": "user", "content": PROMPT.format(city=city, text=text)}],
    )

    print(
        f"tokens in: {message.usage.input_tokens}, out: {message.usage.output_tokens}"
    )
    return RuleSet.model_validate(_parse_payload(message.content[0].input))


def main() -> None:
    load_dotenv()

    source = Path("data/austin.txt")
    rules = extract("Austin, Texas", source.read_text())

    out = source.with_suffix(".rules.json")
    out.write_text(rules.model_dump_json(indent=2))
    print(f"{len(rules.rules)} rules written to {out}")
