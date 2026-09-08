"""Unit tests for the Evaluator hierarchy — no DB, no network."""
import pytest
from unittest.mock import MagicMock
from app.evaluators import (
    RuleBasedEvaluator,
    LLMEvaluator,
    CompositeEvaluator,
    EvaluationError,
    FeedbackResult,
)
from app.models import Verdict, EvaluatorType


def test_rule_based_flags_missing_structure():
    result = RuleBasedEvaluator().evaluate(
        problem_description="Design a parking lot.",
        submission_content="I will just use a big if-else to handle everything.",
    )
    assert result.evaluator_used == EvaluatorType.RULE_BASED
    assert any("class" in g.lower() for g in result.gaps)
    assert result.verdict in (Verdict.NEEDS_WORK, Verdict.DECENT)


def test_rule_based_rewards_good_structure():
    submission = (
        "I define a ParkingSpot abstract class with subclasses for each vehicle type. "
        "Each class has a single responsibility. A SpotAssignmentStrategy interface "
        "allows this to extend to new vehicle types in future."
    )
    result = RuleBasedEvaluator().evaluate("Design a parking lot.", submission)
    assert result.verdict == Verdict.SOLID
    assert len(result.gaps) == 0


def test_rule_based_flags_very_short_submission():
    result = RuleBasedEvaluator().evaluate("Design a parking lot.", "idk classes")
    assert any("short" in g.lower() for g in result.gaps)


def test_llm_evaluator_parses_valid_json_response():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content='{"verdict": "solid", "strengths": ["Good separation"], "gaps": []}'))
    ]
    evaluator = LLMEvaluator(api_key="fake")
    evaluator.client = mock_client

    result = evaluator.evaluate("Design a vending machine.", "Some design text.")
    assert result.verdict == Verdict.SOLID
    assert result.strengths == ["Good separation"]
    assert result.evaluator_used == EvaluatorType.LLM


def test_llm_evaluator_raises_evaluation_error_on_api_failure():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("network down")
    evaluator = LLMEvaluator(api_key="fake")
    evaluator.client = mock_client

    with pytest.raises(EvaluationError):
        evaluator.evaluate("Design a vending machine.", "Some design text.")


def test_llm_evaluator_raises_on_malformed_json():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="this is not json"))
    ]
    evaluator = LLMEvaluator(api_key="fake")
    evaluator.client = mock_client

    with pytest.raises(EvaluationError):
        evaluator.evaluate("Design a vending machine.", "Some design text.")


def test_composite_falls_back_to_rule_based_when_llm_fails():
    """Core resilience behaviour: LLM outage should never fail the whole
    submission — it should degrade to rule-based feedback."""
    failing_llm = MagicMock()
    failing_llm.evaluate.side_effect = EvaluationError("boom")

    composite = CompositeEvaluator(llm_evaluator=failing_llm)
    result = composite.evaluate("Design a parking lot.", "A design mentioning a class and an interface.")

    assert result is not None
    assert any("unavailable" in g.lower() for g in result.gaps)


def test_composite_merges_llm_and_rule_based_when_both_succeed():
    working_llm = MagicMock()
    working_llm.evaluate.return_value = FeedbackResult(
        verdict=Verdict.SOLID,
        strengths=["LLM strength"],
        gaps=["LLM gap"],
        evaluator_used=EvaluatorType.LLM,
    )
    composite = CompositeEvaluator(llm_evaluator=working_llm)
    result = composite.evaluate("Design a parking lot.", "A design mentioning a class.")

    assert "LLM strength" in result.strengths
    assert "LLM gap" in result.gaps
    assert result.evaluator_used == EvaluatorType.COMPOSITE