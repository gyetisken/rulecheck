from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from .canonical import CanonicalId

RuleKind = Literal[
    "license",
    "ownership",
    "owner_occupancy",
    "unit_cap",
    "distance",
    "insurance",
    "tax",
    "other",
]


class Rule(BaseModel):
    """One requirement a short-term rental operator has to satisfy."""

    city: str
    kind: RuleKind
    requirement: str
    section: str
    quote: str
    value: float | None = Field(
        default=None,
        description="The numeric threshold the rule turns on, if it states one.",
    )
    unit: str | None = Field(
        default=None,
        description="What the value is measured in: feet, percent, days, units.",
    )
    canonical_id: CanonicalId | None = Field(
        default=None,
        description="Which shared requirement this is, once mapped across cities.",
    )


class RuleSet(BaseModel):
    rules: list[Rule]


class Property(BaseModel):
    """The facts about one property that the rules are checked against.

    A field left as None means we do not know, which is deliberately different
    from False. A missing answer must never be reported as a violation.
    """

    city: str
    has_license: bool | None = None
    owner_owns: bool | None = None
    owner_occupies: bool | None = None
    units_operated: int | None = None
    feet_to_nearest_rental: float | None = None
    has_insurance: bool | None = None
    registered_for_tax: bool | None = None


class Status(str, Enum):
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    UNKNOWN = "unknown"


class Finding(BaseModel):
    rule: Rule
    status: Status
    reason: str
