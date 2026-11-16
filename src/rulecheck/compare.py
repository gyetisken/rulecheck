"""Put the cities side by side, one row per canonical requirement."""

import json
from dataclasses import dataclass
from pathlib import Path

from .canonical import CANONICAL
from .models import Rule, RuleSet


@dataclass(frozen=True)
class Cell:
    rules: list[Rule]

    @property
    def present(self) -> bool:
        return bool(self.rules)

    @property
    def thresholds(self) -> list[str]:
        """Every number the city attaches to this requirement.

        Returning only the first one was wrong and quietly so: where a city
        states several, the table showed whichever rule happened to come out of
        the extraction first. Several numbers under one requirement is usually a
        sign the matching put something in the wrong row, and that is worth
        seeing rather than hiding behind the first value.
        """
        seen: list[str] = []
        for rule in self.rules:
            if rule.value is None:
                continue
            value = f"{rule.value:,.0f}" if rule.value >= 1000 else f"{rule.value:g}"
            text = f"{value} {rule.unit or ''}".strip()
            if text not in seen:
                seen.append(text)
        return seen

    @property
    def threshold(self) -> str:
        return " / ".join(self.thresholds)


def load(data: Path = Path("data")) -> dict[str, list[Rule]]:
    cities: dict[str, list[Rule]] = {}
    for path in sorted(data.glob("*.rules.json")):
        name = path.name.removesuffix(".rules.json")
        cities[name] = RuleSet.model_validate_json(path.read_text()).rules
    return cities


def matrix(cities: dict[str, list[Rule]]) -> dict[str, dict[str, Cell]]:
    out: dict[str, dict[str, Cell]] = {}
    for key in CANONICAL:
        if key == "UNMAPPED":
            continue
        row = {
            city: Cell([r for r in rules if r.canonical_id == key])
            for city, rules in cities.items()
        }
        if any(cell.present for cell in row.values()):
            out[key] = row
    return out


def unmapped(cities: dict[str, list[Rule]]) -> dict[str, list[Rule]]:
    return {
        city: [r for r in rules if r.canonical_id in (None, "UNMAPPED")]
        for city, rules in cities.items()
    }


def to_json(cities: dict[str, list[Rule]]) -> str:
    table = matrix(cities)
    return json.dumps(
        {
            "cities": list(cities),
            "requirements": {
                key: {
                    "description": CANONICAL[key],
                    "cities": {
                        city: {
                            "present": cell.present,
                            "threshold": cell.threshold,
                            "rules": [r.model_dump() for r in cell.rules],
                        }
                        for city, cell in row.items()
                    },
                }
                for key, row in table.items()
            },
        },
        indent=2,
    )
