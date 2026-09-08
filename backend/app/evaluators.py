"""
Evaluator hierarchy.

Design intent (this is the core LLD decision of the whole project):

    Evaluator (abstract interface)
        - evaluate(problem, submission_content) -> FeedbackResult
        |
        +-- RuleBasedEvaluator   -> cheap, deterministic, instant
        +-- LLMEvaluator         -> nuanced, judges design quality, slower
        +-- CompositeEvaluator   -> runs both, merges results

Adding a NEW evaluation approach later (e.g. a diagram-parsing evaluator,
or a static-analysis-based one for actual code submissions) means writing
one new class that implements `evaluate()`. Nothing else in the app changes
-- main.py just needs to know which Evaluator instance to call.

This directly answers the assignment's questions:
  - "which parts should be deterministic vs LLM?"
      -> RuleBasedEvaluator handles structural/keyword checks that don't
         need judgment; LLMEvaluator handles the actually-hard question of
         "is this a good design", which has no single right answer.
  - "how would this accommodate another evaluation approach later?"
      -> subclass Evaluator. That's it.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from groq import Groq

from app.models import Verdict, EvaluatorType


@dataclass
class FeedbackResult:
    """Plain data object returned by every evaluator, independent of the
    DB layer -- keeps evaluators testable without a database."""
    verdict: Verdict
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    evaluator_used: EvaluatorType = EvaluatorType.RULE_BASED


class Evaluator(ABC):
    """The interface every evaluation strategy must implement."""

    @abstractmethod
    def evaluate(self, problem_description: str, submission_content: str) -> FeedbackResult:
        raise NotImplementedError


class EvaluationError(Exception):
    """Raised when an evaluator cannot produce a result (e.g. API failure).
    Caught by the calling route, which marks the Submission as FAILED."""
    pass


# ---------- Rule-based ----------

_STRUCTURE_KEYWORDS = ["class", "interface", "abstract", "extends", "implements"]
_RESPONSIBILITY_KEYWORDS = ["responsibility", "encapsulat", "single responsibility"]
_EXTENSIBILITY_KEYWORDS = ["extend", "future", "plug", "strategy", "factory", "polymorph"]


class RuleBasedEvaluator(Evaluator):
    """Fast, deterministic structural checks. Does not judge whether the
    design is *good* -- only whether basic LLD hygiene is present."""

    def evaluate(self, problem_description: str, submission_content: str) -> FeedbackResult:
        text = submission_content.lower()
        strengths, gaps = [], []

        if any(k in text for k in _STRUCTURE_KEYWORDS):
            strengths.append("Defines explicit classes/interfaces.")
        else:
            gaps.append("No clear class or interface structure found — define concrete entities.")

        if any(k in text for k in _RESPONSIBILITY_KEYWORDS):
            strengths.append("Mentions responsibility separation.")
        else:
            gaps.append("Consider calling out single-responsibility boundaries explicitly.")

        if any(k in text for k in _EXTENSIBILITY_KEYWORDS):
            strengths.append("Shows awareness of extensibility (e.g. a pattern or interface for future change).")
        else:
            gaps.append("No mention of how this design would extend to new requirements.")

        if len(submission_content.strip()) < 40:
            gaps.append("Submission is very short — add more detail on classes and their relationships.")

        verdict = Verdict.SOLID if len(gaps) == 0 else (Verdict.DECENT if len(gaps) <= 2 else Verdict.NEEDS_WORK)

        return FeedbackResult(
            verdict=verdict,
            strengths=strengths or ["Submission received."],
            gaps=gaps,
            evaluator_used=EvaluatorType.RULE_BASED,
        )


# ---------- LLM-based (Groq) ----------

_SYSTEM_PROMPT = """You are an expert software design reviewer evaluating a learner's \
Low-Level Design (LLD) solution. You will be given a problem description and the \
learner's submission (text and/or pseudocode). Judge the design on: class/interface \
choices, responsibility separation, relationships, and extensibility.

Respond with ONLY valid JSON, no markdown fences, no extra text, in this exact shape:
{
  "verdict": "needs_work" | "decent" | "solid",
  "strengths": ["short point", "short point"],
  "gaps": ["short point", "short point"]
}
Keep each point under 20 words. 2-4 strengths and 2-4 gaps."""


class LLMEvaluator(Evaluator):
    """Calls Groq's OpenAI-compatible chat completions API to judge design
    quality -- the part that genuinely needs reasoning, not just pattern
    matching."""

    def __init__(self, model: str = "openai/gpt-oss-120b", api_key: str | None = None):
        self.model = model
        self._api_key = api_key or os.environ.get("GROQ_API_KEY")
        self._client: Groq | None = None

    @property
    def client(self) -> Groq:
        # Lazy init: don't blow up app startup just because the key isn't
        # configured yet. Fail only when an evaluation is actually attempted,
        # so it surfaces as a normal EvaluationError the caller already handles.
        if self._client is None:
            if not self._api_key:
                raise EvaluationError("GROQ_API_KEY is not configured.")
            self._client = Groq(api_key=self._api_key)
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    def evaluate(self, problem_description: str, submission_content: str) -> FeedbackResult:
        user_prompt = (
            f"PROBLEM:\n{problem_description}\n\n"
            f"LEARNER SUBMISSION:\n{submission_content}\n\n"
            "Evaluate this design now."
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(raw)

            return FeedbackResult(
                verdict=Verdict(data["verdict"]),
                strengths=list(data.get("strengths", [])),
                gaps=list(data.get("gaps", [])),
                evaluator_used=EvaluatorType.LLM,
            )
        except Exception as e:
            # Network error, malformed JSON, rate limit, etc.
            # Caller decides what to do (e.g. mark submission FAILED, allow retry).
            raise EvaluationError(f"LLM evaluation failed: {e}") from e


# ---------- Composite ----------

class CompositeEvaluator(Evaluator):
    """Runs the rule-based check first (cheap, always available), then the
    LLM check. If the LLM call fails, falls back to rule-based results
    alone rather than failing the whole submission -- keeps the practical
    'what if evaluation fails' answer simple, per the assignment's ask."""

    def __init__(self, llm_evaluator: LLMEvaluator | None = None):
        self.rule_based = RuleBasedEvaluator()
        self.llm = llm_evaluator or LLMEvaluator()

    def evaluate(self, problem_description: str, submission_content: str) -> FeedbackResult:
        rule_result = self.rule_based.evaluate(problem_description, submission_content)

        try:
            llm_result = self.llm.evaluate(problem_description, submission_content)
        except EvaluationError:
            # Degrade gracefully: still return useful feedback instead of failing outright.
            rule_result.gaps.append("(AI-based review unavailable right now — showing structural check only.)")
            return rule_result

        merged_strengths = list(dict.fromkeys(rule_result.strengths + llm_result.strengths))
        merged_gaps = list(dict.fromkeys(rule_result.gaps + llm_result.gaps))

        return FeedbackResult(
            verdict=llm_result.verdict,  # trust the LLM's holistic judgment for final verdict
            strengths=merged_strengths,
            gaps=merged_gaps,
            evaluator_used=EvaluatorType.COMPOSITE,
        )