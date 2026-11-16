"""Check a property against a set of rules.

No model is called here. Reading the ordinance needs judgement, so an LLM does
that once, up front. Deciding whether a licence exists is a comparison, and a
comparison belongs in code: it is faster, it costs nothing, and it gives the
same answer every time.
"""

from .models import Finding, Property, Rule, RuleSet, Status

# A rule phrased as a prohibition sets a ceiling. One phrased as an obligation
# sets a floor. The extraction prompt asks for "Owner must" or "Owner may not",
# so the distinction survives into the data.
_PROHIBITION = "may not"


def _is_prohibition(rule: Rule) -> bool:
    return _PROHIBITION in rule.requirement.lower()


def _boolean(rule: Rule, held: bool | None, name: str) -> Finding:
    if held is None:
        return Finding(rule=rule, status=Status.UNKNOWN, reason=f"{name} not answered")
    if held:
        return Finding(rule=rule, status=Status.SATISFIED, reason=f"{name} is true")
    return Finding(rule=rule, status=Status.VIOLATED, reason=f"{name} is false")


def _unit_cap(rule: Rule, prop: Property) -> Finding:
    if rule.unit not in {"units", None} or rule.value is None:
        return Finding(
            rule=rule,
            status=Status.UNKNOWN,
            reason=f"cap is expressed in {rule.unit!r}, which this checker cannot apply",
        )
    if prop.units_operated is None:
        return Finding(
            rule=rule, status=Status.UNKNOWN, reason="units operated not answered"
        )
    if prop.units_operated <= rule.value:
        return Finding(
            rule=rule,
            status=Status.SATISFIED,
            reason=f"{prop.units_operated} units operated, cap is {rule.value:g}",
        )
    return Finding(
        rule=rule,
        status=Status.VIOLATED,
        reason=f"{prop.units_operated} units operated, cap is {rule.value:g}",
    )


def _distance(rule: Rule, prop: Property) -> Finding:
    if rule.value is None or rule.unit != "feet":
        return Finding(
            rule=rule, status=Status.UNKNOWN, reason="no distance in feet stated"
        )
    if prop.feet_to_nearest_rental is None:
        return Finding(
            rule=rule,
            status=Status.UNKNOWN,
            reason="distance to nearest rental not answered",
        )
    if prop.feet_to_nearest_rental >= rule.value:
        return Finding(
            rule=rule,
            status=Status.SATISFIED,
            reason=f"{prop.feet_to_nearest_rental:g} ft away, {rule.value:g} ft required",
        )
    return Finding(
        rule=rule,
        status=Status.VIOLATED,
        reason=f"{prop.feet_to_nearest_rental:g} ft away, {rule.value:g} ft required",
    )


def check_rule(rule: Rule, prop: Property) -> Finding:
    if rule.kind == "license":
        return _boolean(rule, prop.has_license, "licence held")
    if rule.kind == "ownership":
        return _boolean(rule, prop.owner_owns, "owner owns the property")
    if rule.kind == "owner_occupancy":
        return _boolean(rule, prop.owner_occupies, "owner occupies the property")
    if rule.kind == "insurance":
        return _boolean(rule, prop.has_insurance, "insurance held")
    if rule.kind == "tax":
        return _boolean(rule, prop.registered_for_tax, "registered for tax")
    if rule.kind == "unit_cap":
        return _unit_cap(rule, prop)
    if rule.kind == "distance":
        return _distance(rule, prop)
    return Finding(
        rule=rule,
        status=Status.UNKNOWN,
        reason="no automatic check for this kind of rule, needs a human",
    )


def check(rules: RuleSet, prop: Property) -> list[Finding]:
    """Check every rule for the property's city. Order is preserved."""
    city = prop.city.strip().lower()
    return [
        check_rule(rule, prop)
        for rule in rules.rules
        if city in rule.city.strip().lower() or rule.city.strip().lower() in city
    ]
