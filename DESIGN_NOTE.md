# Design Note — DesignForge

## MVP Scope

DesignForge implements the full practice loop end to end for 3 seeded LLD
problems: Parking Lot, Vending Machine, and Elevator.

The learner can:

* choose a problem
* read the problem description
* start an attempt
* write a design using text/pseudocode
* submit it
* receive structured feedback
* revisit previous submissions
* revise and resubmit within the same attempt

The MVP deliberately excludes a diagram editor, multi-user accounts, and
real code execution/compilation. These are future extensions rather than
requirements for proving the core design-evaluation loop within the 2-day
scope.

## User Flow

```text
Learner opens app
  → sees a list of problems
  → picks a problem and reads the description
  → starts an attempt
  → writes their design as text/pseudocode
  → submits
  → sees feedback: verdict + strengths + gaps
  → optionally revises the same attempt and resubmits
  → sees submission history with verdicts
```

If evaluation fails, for example because the LLM call errors out, the learner
gets a clear error state with a **Retry** button rather than a stuck or
silently failed submission.

## Key Classes and Interfaces

```text
Problem  ──< Attempt  ──< Submission ── Feedback

Evaluator (interface)
├── RuleBasedEvaluator
├── LLMEvaluator
└── CompositeEvaluator
```

### Domain Entities

Defined in `app/models.py`.

* **Problem** — a fixed practice prompt containing the title, description,
  and difficulty.
* **Attempt** — one learner's ongoing effort at a problem. It is deliberately
  separate from `Submission` so a learner can revise and resubmit multiple
  times within a single attempt.
* **Submission** — one specific try within an attempt. It stores the submitted
  content, evaluation status, and an optional error message.
* **Feedback** — the result associated with one submission, containing a
  verdict, strengths, gaps, and information about which evaluator was used.

This separation makes revision history meaningful instead of treating every
submission as an unrelated one-off attempt.

## Evaluation

Defined in `app/evaluators.py`.

### Evaluator

`Evaluator` is an abstract interface with a single method:

```text
evaluate(problem_description, submission_content) -> FeedbackResult
```

This gives the application a common contract for different evaluation
strategies.

### RuleBasedEvaluator

The rule-based evaluator performs cheap, deterministic structural checks, such
as:

* whether classes or interfaces are mentioned
* whether responsibility separation is addressed
* whether extensibility is considered
* whether the submission is long enough to contain a meaningful design

These checks are predictable and do not depend on an external service.

### LLMEvaluator

The LLM evaluator calls Groq's `gpt-oss-120b` model with a system prompt that
asks for structured JSON feedback containing:

* verdict
* strengths
* gaps

Failures such as network errors, rate limits, missing configuration, or
malformed responses are converted into a typed `EvaluationError` rather than
letting raw exceptions propagate through the application.

### CompositeEvaluator

`CompositeEvaluator` runs both evaluators and combines their results.

The LLM provides the holistic judgment, while the rule-based evaluator
provides deterministic structural feedback.

If the LLM call fails, the composite evaluator falls back to the
rule-based result instead of failing the submission immediately.

## Deterministic vs. LLM Evaluation

This split is the central evaluation decision in DesignForge.

| Concern                                              | Deterministic | LLM |
| ---------------------------------------------------- | :-----------: | :-: |
| Are classes/interfaces present?                      |       ✓       |     |
| Is responsibility separation mentioned?              |       ✓       |     |
| Is the submission trivially too short?               |       ✓       |     |
| Is this a good design for this particular problem?   |               |  ✓  |
| Are there subtle design weaknesses?                  |               |  ✓  |
| Are the proposed relationships reasonably decoupled? |               |  ✓  |

The rule-based layer is fast, predictable, and always available. It acts as a
basic quality floor.

The LLM is used where actual design reasoning is useful. LLD problems can
have multiple valid solutions, so evaluating them against one fixed expected
answer would be too restrictive.

## Extensibility

Adding another evaluation approach later — for example, one that parses a
class diagram image or performs static analysis on real code — would involve
creating another class that implements `Evaluator.evaluate()`.

The existing routes and frontend depend on the evaluator contract rather than
a specific implementation, so the new evaluator can be introduced without
changing the overall application structure.

Adding a new submission format, such as an uploaded diagram, would require
additional submission data and format-aware evaluation. This is a somewhat
larger change, but it would still be localized rather than requiring a
complete rearchitecture.

## Handling Slow or Failed Evaluation

The failure-handling approach is intentionally simple because of the
assignment's 2-day scope.

* `Submission.status` tracks the lifecycle:
  `pending → evaluating → completed/failed`.
* If the LLM call fails, `CompositeEvaluator` falls back to rule-based
  feedback.
* If evaluation fails completely, the submission is marked as `failed` with
  an error message.
* A `/retry` endpoint allows the learner to run the evaluation again.
* There is no background job queue, retry-with-backoff system, or polling
  mechanism.

For this prototype, synchronous evaluation is sufficient. Adding distributed
infrastructure would increase complexity without improving the core LLD
practice experience.

## Key Trade-offs

### Text/Pseudocode Instead of a Code Editor or Diagram Tool

Submissions are currently text/pseudocode rather than executable code or
diagrams.

This keeps the submission format simple and allows both evaluators to work
with the same input. The trade-off is that the platform cannot verify whether
code compiles or runs.

This is acceptable for an LLD reasoning tool, but it would not be sufficient
for a code-execution grader.

### Single Learner and No Authentication

The prototype uses a demo learner ID and does not implement authentication.

This keeps the MVP focused while `learner_id` is still part of the
`Attempt` model, making multi-user support easier to add later.

### Trusting the LLM Verdict

When both evaluators succeed, the LLM provides the overall verdict while the
rule-based checks are retained as additional strengths and gaps.

This gives the learner both the deterministic structural signals and the
more holistic AI-based assessment instead of silently discarding the
rule-based result.

### SQLite Instead of a Heavier Database

SQLite is sufficient for the current single-learner prototype and keeps local
setup simple.

Using SQLModel also keeps the database layer relatively easy to migrate to
PostgreSQL later if the application grows.

## Architecture Summary

```text
                 ┌──────────────────┐
                 │     Frontend     │
                 │  HTML/CSS/JS     │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │     FastAPI      │
                 │     Routes       │
                 └────────┬─────────┘
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
      ┌──────────────┐        ┌─────────────────┐
      │   SQLModel   │        │    Evaluator    │
      │    + SQLite  │        │     Layer       │
      └──────────────┘        ├─────────────────┤
                              │ Rule Based      │
                              │ LLM             │
                              │ Composite       │
                              └─────────────────┘
```

The architecture is intentionally a small monolith. The main focus is keeping
the domain model clear, the evaluator replaceable, feedback useful, and AI
failures recoverable without introducing infrastructure that the MVP does not
need.
