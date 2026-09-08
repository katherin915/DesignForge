from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class Verdict(str, Enum):
    NEEDS_WORK = "needs_work"
    DECENT = "decent"
    SOLID = "solid"


class EvaluatorType(str, Enum):
    RULE_BASED = "rule_based"
    LLM = "llm"
    COMPOSITE = "composite"


class Problem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    difficulty: str = "medium"
    attempts: List["Attempt"] = Relationship(back_populates="problem")


class Attempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="problem.id")
    learner_id: str = "demo-learner"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    problem: Optional[Problem] = Relationship(back_populates="attempts")
    submissions: List["Submission"] = Relationship(back_populates="attempt")


class Submission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    attempt_id: int = Field(foreign_key="attempt.id")
    content: str
    status: SubmissionStatus = SubmissionStatus.PENDING
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None

    attempt: Optional[Attempt] = Relationship(back_populates="submissions")
    feedback: Optional["Feedback"] = Relationship(back_populates="submission")


class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submission.id", unique=True)
    verdict: Verdict
    strengths: str
    gaps: str
    evaluator_used: EvaluatorType
    created_at: datetime = Field(default_factory=datetime.utcnow)

    submission: Optional[Submission] = Relationship(back_populates="feedback")

    def strengths_list(self) -> List[str]:
        return [s for s in self.strengths.split("\n") if s.strip()]

    def gaps_list(self) -> List[str]:
        return [g for g in self.gaps.split("\n") if g.strip()]