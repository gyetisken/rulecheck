"""Score the extraction against a hand-written answer key.

Someone reads the ordinance, writes down the obligations it places on an owner,
and that list is the truth. The extraction is then judged against it: every
requirement the key holds that the model found, every one it missed, and
everything it produced that the key does not contain.

Pairing the two lists is itself a reading problem, because the same obligation
is rarely phrased the same way twice. A model does the pairing, which puts a
model inside the measurement of a model, and that is a real weakness rather
than a detail. It is mitigated by printing every pairing so a person can check
it, and by scoring per section so an error cannot travel far. It is not solved.
"""

import json
from pathlib import Path

import anthropic
from pydantic import BaseModel

from .extract import MODEL, _parse_payload
from .models import Rule, RuleSet


class Pairing(BaseModel):
    key_index: int
    extracted_index: int | None


class Pairings(BaseModel):
    pairings: list[Pairing]


class SectionScore(BaseModel):
    section: str
    expected: int
    found: int
    missed: list[str]
    unsupported: list[str]

    @property
    def recall(self) -> float:
        return self.found / self.expected if self.expected else 1.0

    @property
    def precision(self) -> float:
        produced = self.found + len(self.unsupported)
        return self.found / produced if produced else 1.0


PROMPT = """Two people read the same section of a short-term rental ordinance and
wrote down the obligations it places on an owner.

List A was written by hand and is the reference.
List B was produced by a program.

Pair each entry in A with the entry in B that states the same obligation, even
when the wording differs. An entry in A with nothing equivalent in B is a miss:
return null for it. Do not pair two entries that merely sound similar; they have
to be the same duty.

List A:
{key}

List B:
{found}"""


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "pairings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key_index": {"type": "integer"},
                        "extracted_index": {"type": ["integer", "null"]},
                    },
                    "required": ["key_index", "extracted_index"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["pairings"],
        "additionalProperties": False,
    }


def _pair(key: list[str], found: list[Rule]) -> Pairings:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        tools=[
            {
                "name": "pair",
                "description": "Pair reference requirements with extracted ones.",
                "input_schema": _schema(),
                "strict": True,
            }
        ],
        tool_choice={"type": "tool", "name": "pair"},
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(
                    key="\n".join(f"{i}. {text}" for i, text in enumerate(key)),
                    found="\n".join(
                        f"{i}. {rule.requirement}" for i, rule in enumerate(found)
                    ),
                ),
            }
        ],
    )
    return Pairings.model_validate(_parse_payload(message.content[0].input))


def score(key_path: Path, rules_path: Path, verbose: bool = True) -> list[SectionScore]:
    key = json.loads(key_path.read_text())
    rules = RuleSet.model_validate_json(rules_path.read_text()).rules

    scores: list[SectionScore] = []
    for section, expected in key["sections"].items():
        found = [r for r in rules if r.section.strip() == section]
        pairings = _pair(expected, found).pairings

        matched = {p.extracted_index for p in pairings if p.extracted_index is not None}
        missed = [expected[p.key_index] for p in pairings if p.extracted_index is None]
        unsupported = [r.requirement for i, r in enumerate(found) if i not in matched]

        if verbose:
            print(f"\n{section}")
            for p in pairings:
                mark = "  ok " if p.extracted_index is not None else " MISS"
                print(f"{mark}  {expected[p.key_index]}")
            for text in unsupported:
                print(f"  EXTRA {text}")

        scores.append(
            SectionScore(
                section=section,
                expected=len(expected),
                found=len(expected) - len(missed),
                missed=missed,
                unsupported=unsupported,
            )
        )
    return scores


def report(scores: list[SectionScore]) -> str:
    expected = sum(s.expected for s in scores)
    found = sum(s.found for s in scores)
    missed = sum(len(s.missed) for s in scores)
    extra = sum(len(s.unsupported) for s in scores)
    produced = found + extra

    lines = [
        "",
        f"{'section':<12}{'expected':>9}{'found':>7}{'missed':>8}{'unsupported':>13}",
    ]
    for s in scores:
        lines.append(
            f"{s.section:<12}{s.expected:>9}{s.found:>7}{len(s.missed):>8}"
            f"{len(s.unsupported):>13}"
        )
    lines += [
        "",
        f"recall    {found}/{expected} = {found / expected:.0%}"
        "   of the obligations in the key, this many were found",
        f"precision {found}/{produced} = {found / produced:.0%}"
        "   of what the model produced, this much is in the key",
    ]
    if missed:
        lines += ["", "Missed:"] + [f"  - {m}" for s in scores for m in s.missed]
    if extra:
        lines += ["", "Not in the key:"] + [
            f"  - {u}" for s in scores for u in s.unsupported
        ]
    return "\n".join(lines)
