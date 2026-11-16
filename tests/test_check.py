"""The checker is pure logic, so it is cheap to test and worth testing hard."""

import pytest

from rulecheck.check import check_rule
from rulecheck.models import Property, Rule, Status


def rule(kind, requirement="Owner must do the thing.", value=None, unit=None):
    return Rule(
        city="Austin, Texas",
        kind=kind,
        requirement=requirement,
        section="4-23-1",
        quote="...",
        value=value,
        unit=unit,
    )


def prop(**kwargs):
    return Property(city="Austin", **kwargs)


class TestBooleanRules:
    def test_licence_held_is_satisfied(self):
        f = check_rule(rule("license"), prop(has_license=True))
        assert f.status is Status.SATISFIED

    def test_licence_missing_is_a_violation(self):
        f = check_rule(rule("license"), prop(has_license=False))
        assert f.status is Status.VIOLATED

    def test_unanswered_is_not_a_violation(self):
        """The whole point: silence is not a no."""
        f = check_rule(rule("license"), prop())
        assert f.status is Status.UNKNOWN


class TestUnitCap:
    def test_under_the_cap(self):
        f = check_rule(rule("unit_cap", value=2, unit="units"), prop(units_operated=1))
        assert f.status is Status.SATISFIED

    def test_on_the_cap_is_allowed(self):
        f = check_rule(rule("unit_cap", value=2, unit="units"), prop(units_operated=2))
        assert f.status is Status.SATISFIED

    def test_over_the_cap(self):
        f = check_rule(rule("unit_cap", value=2, unit="units"), prop(units_operated=3))
        assert f.status is Status.VIOLATED

    def test_cap_in_percent_is_not_guessed_at(self):
        """Austin caps some sites at a percentage of units owned. We cannot
        answer that from the facts we collect, so we say so."""
        f = check_rule(
            rule("unit_cap", value=25, unit="percent"), prop(units_operated=3)
        )
        assert f.status is Status.UNKNOWN


class TestDistance:
    def test_far_enough(self):
        f = check_rule(
            rule("distance", value=1000, unit="feet"), prop(feet_to_nearest_rental=1200)
        )
        assert f.status is Status.SATISFIED

    def test_too_close(self):
        f = check_rule(
            rule("distance", value=1000, unit="feet"), prop(feet_to_nearest_rental=800)
        )
        assert f.status is Status.VIOLATED

    def test_exactly_the_limit_counts_as_far_enough(self):
        f = check_rule(
            rule("distance", value=1000, unit="feet"), prop(feet_to_nearest_rental=1000)
        )
        assert f.status is Status.SATISFIED

    def test_distance_unknown(self):
        f = check_rule(rule("distance", value=1000, unit="feet"), prop())
        assert f.status is Status.UNKNOWN


class TestOther:
    @pytest.mark.parametrize("kind", ["other", "insurance", "tax"])
    def test_nothing_is_invented(self, kind):
        f = check_rule(rule(kind), prop())
        assert f.status is Status.UNKNOWN
