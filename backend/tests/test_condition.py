import pytest

from app.execution.condition import ConditionNode


@pytest.fixture
def node():
    return ConditionNode()


def test_equal_values_match(node):
    result = node.execute(None, {"operator": "eq"}, {"left": "high", "right": "high"})
    assert result["matched"] is True


def test_unequal_values_do_not_match(node):
    result = node.execute(None, {"operator": "eq"}, {"left": "low", "right": "high"})
    assert result["matched"] is False


def test_contains_operator(node):
    result = node.execute(None, {"operator": "contains"}, {"left": "database timeout", "right": "timeout"})
    assert result["matched"] is True


def test_numeric_comparison(node):
    result = node.execute(None, {"operator": "gte"}, {"left": 0.95, "right": 0.9})
    assert result["matched"] is True


def test_missing_input_is_rejected(node):
    with pytest.raises(ValueError, match="requires 'left' and 'right'"):
        node.execute(None, {"operator": "eq"}, {"left": "high"})


def test_unknown_operator_is_rejected(node):
    with pytest.raises(ValueError, match="Unsupported condition operator"):
        node.execute(None, {"operator": "between"}, {"left": 5, "right": 3})
