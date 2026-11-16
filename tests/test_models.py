import pytest
from pydantic import ValidationError

from rulecheck.models import Rule, RuleSet


def test_rule_kind_is_constrained():
    """The Literal is not decoration: it is also the enum in the JSON schema we
    hand to the model, so it constrains the extraction as well as the code."""
    with pytest.raises(ValidationError):
        Rule(
            city="Austin", kind="swimming_pool", requirement="x", section="1", quote="y"
        )


def test_missing_quote_is_rejected():
    with pytest.raises(ValidationError):
        Rule(city="Austin", kind="license", requirement="x", section="1")


def test_schema_exposes_the_kinds_to_the_model():
    schema = Rule.model_json_schema()
    assert "license" in str(schema["properties"]["kind"])


def test_ruleset_round_trips():
    r = Rule(city="Austin", kind="license", requirement="x", section="1", quote="y")
    rs = RuleSet(rules=[r])
    assert RuleSet.model_validate_json(rs.model_dump_json()) == rs
