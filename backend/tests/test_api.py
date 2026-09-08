"""Integration tests for the API flow: problem -> attempt -> submission -> feedback.
Uses an isolated in-memory SQLite DB and mocks the LLM call so tests run offline."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from app import main as main_module
from app.db import get_session
from app.models import Problem
from app.evaluators import FeedbackResult, EvaluationError
from app.models import Verdict, EvaluatorType


@pytest.fixture(name="client")
def client_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def get_session_override():
        with Session(engine) as session:
            yield session

    main_module.app.dependency_overrides[get_session] = get_session_override

    with Session(engine) as session:
        session.add(Problem(title="Parking Lot", description="Design a parking lot.", difficulty="medium"))
        session.commit()

    with TestClient(main_module.app) as c:
        yield c

    main_module.app.dependency_overrides.clear()

#test 1 list problems
def test_list_problems(client):
    resp = client.get("/problems")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Parking Lot"

# Test2 create attempt and submission, mock evaluator to return solid verdict   
def test_full_practice_loop_success(client, monkeypatch):
    monkeypatch.setattr(
        main_module.evaluator, "evaluate",
        lambda problem_description, submission_content: FeedbackResult(
            verdict=Verdict.SOLID, strengths=["Clear classes"], gaps=[], evaluator_used=EvaluatorType.COMPOSITE
        )
    )

    attempt_resp = client.post("/attempts", json={"problem_id": 1})
    assert attempt_resp.status_code == 200
    attempt_id = attempt_resp.json()["id"]

    sub_resp = client.post(f"/attempts/{attempt_id}/submissions", json={"content": "class ParkingLot {}"})
    assert sub_resp.status_code == 200
    body = sub_resp.json()
    assert body["status"] == "completed"
    assert body["feedback"]["verdict"] == "solid"

    history = client.get(f"/attempts/{attempt_id}/submissions")
    assert len(history.json()) == 1

#Test 3-Evaluator Failure Handling: Simulate an evaluator failure and check that the submission is marked as failed, then retry and ensure it succeeds.
def test_submission_marked_failed_when_evaluator_errors(client, monkeypatch):
    def raise_error(problem_description, submission_content):
        raise EvaluationError("Groq API unreachable")

    monkeypatch.setattr(main_module.evaluator, "evaluate", raise_error)

    attempt_resp = client.post("/attempts", json={"problem_id": 1})
    attempt_id = attempt_resp.json()["id"]

    sub_resp = client.post(f"/attempts/{attempt_id}/submissions", json={"content": "class ParkingLot {}"})
    body = sub_resp.json()
    assert body["status"] == "failed"
    assert "unreachable" in body["error_message"].lower()

#test 4 test retry after failure succeeds
def test_retry_after_failure_succeeds(client, monkeypatch):
    attempt_resp = client.post("/attempts", json={"problem_id": 1})
    attempt_id = attempt_resp.json()["id"]

    def raise_error(problem_description, submission_content):
        raise EvaluationError("temporary outage")
    monkeypatch.setattr(main_module.evaluator, "evaluate", raise_error)

    sub_resp = client.post(f"/attempts/{attempt_id}/submissions", json={"content": "class X {}"})
    submission_id = sub_resp.json()["id"]
    assert sub_resp.json()["status"] == "failed"

    def succeed(problem_description, submission_content):
        return FeedbackResult(verdict=Verdict.DECENT, strengths=["ok"], gaps=["minor"], evaluator_used=EvaluatorType.COMPOSITE)
    monkeypatch.setattr(main_module.evaluator, "evaluate", succeed)

    retry_resp = client.post(f"/submissions/{submission_id}/retry")
    assert retry_resp.json()["status"] == "completed"


def test_attempt_for_nonexistent_problem_returns_404(client):
    resp = client.post("/attempts", json={"problem_id": 999})
    assert resp.status_code == 404