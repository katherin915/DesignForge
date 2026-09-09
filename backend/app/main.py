from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from sqlmodel import Session, select
from pydantic import BaseModel

from pathlib import Path
from app.db import init_db, get_session
from app.models import Problem, Attempt, Submission, Feedback, SubmissionStatus
from app.evaluators import CompositeEvaluator, EvaluationError
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="LLD Practice Platform")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)
@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

evaluator = CompositeEvaluator()


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- Request/response schemas ----------

class AttemptCreate(BaseModel):
    problem_id: int
    learner_id: str = "demo-learner"


class SubmissionCreate(BaseModel):
    content: str


class FeedbackOut(BaseModel):
    verdict: str
    strengths: List[str]
    gaps: List[str]
    evaluator_used: str


class SubmissionOut(BaseModel):
    id: int
    content: str
    status: str
    error_message: Optional[str] = None
    feedback: Optional[FeedbackOut] = None


# ---------- Routes: Problems ----------

@app.get("/problems", response_model=List[Problem])
def list_problems(session: Session = Depends(get_session)):
    return session.exec(select(Problem)).all()


@app.get("/problems/{problem_id}", response_model=Problem)
def get_problem(problem_id: int, session: Session = Depends(get_session)):
    problem = session.get(Problem, problem_id)
    if not problem:
        raise HTTPException(404, "Problem not found")
    return problem


# ---------- Routes: Attempts ----------

@app.post("/attempts", response_model=Attempt)
def start_attempt(data: AttemptCreate, session: Session = Depends(get_session)):
    problem = session.get(Problem, data.problem_id)
    if not problem:
        raise HTTPException(404, "Problem not found")
    attempt = Attempt(problem_id=data.problem_id, learner_id=data.learner_id)
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return attempt


@app.get("/attempts", response_model=List[Attempt])
def list_attempts(learner_id: str = "demo-learner", session: Session = Depends(get_session)):
    """History: all past attempts for a learner, most recent first."""
    statement = select(Attempt).where(Attempt.learner_id == learner_id).order_by(Attempt.created_at.desc())
    return session.exec(statement).all()


@app.get("/attempts/{attempt_id}/submissions", response_model=List[SubmissionOut])
def get_attempt_history(attempt_id: int, session: Session = Depends(get_session)):
    """All submissions within one attempt, so a learner can see how their
    design evolved across revisions."""
    attempt = session.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    results = []
    for s in attempt.submissions:
        fb_out = None
        if s.feedback:
            fb_out = FeedbackOut(
                verdict=s.feedback.verdict,
                strengths=s.feedback.strengths_list(),
                gaps=s.feedback.gaps_list(),
                evaluator_used=s.feedback.evaluator_used,
            )
        results.append(SubmissionOut(
            id=s.id, content=s.content, status=s.status,
            error_message=s.error_message, feedback=fb_out,
        ))
    return results


# ---------- Routes: Submissions (the core loop) ----------

@app.post("/attempts/{attempt_id}/submissions", response_model=SubmissionOut)
def submit_solution(attempt_id: int, data: SubmissionCreate, session: Session = Depends(get_session)):
    attempt = session.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(404, "Attempt not found")

    submission = Submission(attempt_id=attempt_id, content=data.content, status=SubmissionStatus.EVALUATING)
    session.add(submission)
    session.commit()
    session.refresh(submission)

    try:
        result = evaluator.evaluate(attempt.problem.description, data.content)
        feedback = Feedback(
            submission_id=submission.id,
            verdict=result.verdict,
            strengths="\n".join(result.strengths),
            gaps="\n".join(result.gaps),
            evaluator_used=result.evaluator_used,
        )
        submission.status = SubmissionStatus.COMPLETED
        session.add(feedback)
        session.add(submission)
        session.commit()
        session.refresh(submission)

        fb_out = FeedbackOut(
            verdict=feedback.verdict, strengths=result.strengths,
            gaps=result.gaps, evaluator_used=feedback.evaluator_used,
        )
        return SubmissionOut(id=submission.id, content=submission.content,
                              status=submission.status, feedback=fb_out)

    except EvaluationError as e:
        submission.status = SubmissionStatus.FAILED
        submission.error_message = str(e)
        session.add(submission)
        session.commit()
        return SubmissionOut(id=submission.id, content=submission.content,
                              status=submission.status, error_message=submission.error_message)


@app.post("/submissions/{submission_id}/retry", response_model=SubmissionOut)
def retry_submission(submission_id: int, session: Session = Depends(get_session)):
    """Practical answer to 'what if evaluation fails': just let the learner
    retry the same submission instead of building a retry queue."""
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(404, "Submission not found")

    attempt = session.get(Attempt, submission.attempt_id)
    try:
        result = evaluator.evaluate(attempt.problem.description, submission.content)
        feedback = Feedback(
            submission_id=submission.id,
            verdict=result.verdict,
            strengths="\n".join(result.strengths),
            gaps="\n".join(result.gaps),
            evaluator_used=result.evaluator_used,
        )
        submission.status = SubmissionStatus.COMPLETED
        submission.error_message = None
        session.add(feedback)
        session.add(submission)
        session.commit()
        session.refresh(submission)
        fb_out = FeedbackOut(verdict=feedback.verdict, strengths=result.strengths,
                              gaps=result.gaps, evaluator_used=feedback.evaluator_used)
        return SubmissionOut(id=submission.id, content=submission.content,
                              status=submission.status, feedback=fb_out)
    except EvaluationError as e:
        submission.status = SubmissionStatus.FAILED
        submission.error_message = str(e)
        session.add(submission)
        session.commit()
        return SubmissionOut(id=submission.id, content=submission.content,
                              status=submission.status, error_message=submission.error_message)