# DesignForge

An AI-assisted practice platform for Low-Level Design (LLD).

DesignForge lets learners pick a classic design problem, write out their class design, submit it, and receive structured feedback on responsibility separation, class/interface choices, and extensibility. Learners can then revise and resubmit their design to track improvement over multiple revisions.

Built as a focused 2-day prototype with a simple monolithic architecture. The project intentionally avoids unnecessary distributed-system complexity. The main engineering decisions are centered around the evaluator architecture and graceful handling of AI evaluation failures.

## Practice Loop

```text
Choose problem → Write design → Submit → Get feedback → Review history → Revise → Resubmit
```

## Tech Stack

* **Backend:** FastAPI + SQLModel
* **Database:** SQLite
* **LLM Feedback:** Groq (`openai/gpt-oss-120b`)
* **Frontend:** Vanilla HTML/CSS/JavaScript, served directly by the FastAPI application
* **Environment Management:** `python-dotenv`
* **Testing:** pytest
* **Package Management:** uv

The frontend does not require a separate development server or build step. FastAPI serves the frontend and exposes the backend APIs from the same application.

## Project Structure

```text
DesignForge/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI routes + frontend serving
│   │   ├── models.py        # Problem, Attempt, Submission, Feedback
│   │   ├── evaluators.py    # Evaluator interface + implementations
│   │   ├── db.py            # SQLite engine and session setup
│   │   └── seed.py           # Seeds starter problems
│   │
│   ├── tests/
│   │   ├── test_evaluator.py # Evaluator unit tests
│   │   └── test_api.py       # API integration tests
│   │
│   ├── .env                 # Local API key (not committed)
│   ├── pyproject.toml       # Project dependencies and configuration
│   └── uv.lock              # Locked dependency versions
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
└── .gitignore
```

## Domain Model

```text
Problem
   │
   └──< Attempt
          │
          └──< Submission
                    │
                    └── Feedback
```

* A **Problem** is a fixed LLD practice prompt.
* An **Attempt** represents a learner's ongoing effort at one problem.
* An Attempt can contain **multiple Submissions**.
* Each Submission represents one revision of the learner's design.
* Each Submission receives one Feedback result.

Multiple submissions within the same attempt make the history meaningful: learners can submit, review feedback, revise their design, and resubmit instead of creating unrelated one-shot attempts.

## Evaluation Approach

The core design decision in DesignForge is the `Evaluator` interface.

```text
Evaluator (abstract)
│
├── RuleBasedEvaluator
│     └── Deterministic structural checks
│
├── LLMEvaluator
│     └── AI-based design reasoning
│
└── CompositeEvaluator
      ├── Runs rule-based evaluation
      ├── Runs LLM evaluation
      ├── Merges successful results
      └── Falls back to rule-based feedback if LLM fails
```

### Why combine rules and an LLM?

LLD problems can have multiple valid solutions, so evaluating design quality cannot be reduced to a single rigid expected answer.

The **RuleBasedEvaluator** handles objective, inexpensive checks such as:

* Whether the submission contains meaningful design structure
* Whether classes or interfaces are mentioned
* Whether extensibility is addressed
* Whether the submission is sufficiently detailed

The **LLMEvaluator** handles reasoning-oriented feedback such as:

* Responsibility separation
* Quality of class/interface choices
* Design trade-offs
* Extensibility
* Potential design weaknesses

This gives the system a practical combination of **deterministic checks + reasoning-based evaluation**.

### Extensibility

The evaluator architecture is designed around a common interface:

```python
Evaluator.evaluate(problem_description, submission_content)
```

Adding another evaluation strategy does not require changing the existing evaluator implementations.

For example, future evaluators could include:

* A diagram evaluator
* Static analysis for actual code submissions
* A rubric-based evaluator
* A test-case or design-pattern evaluator

Each new strategy can implement the same `Evaluator` interface.

### Evaluation Failure Handling

Submissions maintain an explicit status:

```text
pending
   ↓
evaluating
   ↓
completed
   or
failed
```

The LLM is an external dependency and can fail because of API errors, missing configuration, network problems, or malformed responses.

DesignForge therefore does not make the LLM a single point of failure.

If the LLM evaluation fails:

```text
Submission
    ↓
Rule-based evaluation ✅
    ↓
LLM evaluation ❌
    ↓
Rule-based feedback returned
```

The learner can also retry a failed submission through the **Retry** action.

No background queue or distributed retry infrastructure is used because this is intentionally a small 2-day prototype.

## Running Locally

### Requirements

* Python 3.11
* uv
* pip
* A Groq API key

Create a Groq API key from the [Groq Console](https://console.groq.com?utm_source=chatgpt.com).

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd DesignForge
```

### 2. Install dependencies

```bash
Using pip:

cd backend
pip install -r requirements.txt

Alternatively, using uv:

uv sync
```

### 3. Configure the API key

Create:

```text
backend/.env
```

Add:

```text
GROQ_API_KEY=your_actual_groq_api_key
```

Do not commit the `.env` file. It is excluded through `.gitignore`.

### 4. Start the application

From the `backend` directory:

```bash
uv run uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

The FastAPI application serves both the API and the frontend.

The SQLite database is created automatically when the application starts. Starter LLD problems are seeded through the project's seed setup.

### Running Without an API Key

The platform can still operate without a configured Groq API key.

In that case:

```text
Submission
    ↓
RuleBasedEvaluator
    ↓
Feedback
```

The system gracefully falls back to deterministic rule-based feedback instead of making the entire submission fail.

## Running Tests

From the `backend` directory:

```bash
uv run pytest tests/ -v
```

The test suite covers:

* Rule-based evaluation logic
* Good and weak submissions
* LLM response parsing
* LLM API failure handling
* Malformed LLM responses
* Composite evaluator fallback behavior
* Composite evaluator result merging
* Full API flow
* Evaluation failure handling
* Submission retry flow
* Invalid problem handling

The LLM itself is mocked during tests so that the test suite remains deterministic and does not depend on an external API.

## API Overview

| Method | Route                        | Purpose                                     |
| ------ | ---------------------------- | ------------------------------------------- |
| `GET`  | `/problems`                  | List available problems                     |
| `GET`  | `/problems/{id}`             | Get one problem                             |
| `POST` | `/attempts`                  | Start a new attempt                         |
| `GET`  | `/attempts?learner_id=`      | List a learner's attempts                   |
| `GET`  | `/attempts/{id}/submissions` | Get submissions and feedback for an attempt |
| `POST` | `/attempts/{id}/submissions` | Submit a design for evaluation              |
| `POST` | `/submissions/{id}/retry`    | Retry a failed evaluation                   |

## Key Product Decisions

### 1. Multiple revisions per attempt

A learner should be able to improve the same design instead of creating a new attempt every time.

This makes the product loop:

```text
Design → Feedback → Revision → Feedback → Improvement
```

more meaningful.

### 2. Feedback instead of a single score

A single numerical score can hide why a design is weak.

DesignForge therefore focuses on:

* Verdict
* Strengths
* Gaps to address
* Evaluation method used

This makes feedback more actionable for learners.

### 3. Hybrid evaluation

Rules provide deterministic structural checks while the LLM provides reasoning-oriented design feedback.

This balances reliability, flexibility, and implementation simplicity.

### 4. Graceful AI degradation

The product should remain usable even when the external AI service is unavailable.

The rule-based evaluator provides a deterministic fallback, while failed evaluations can also be retried.

## Known Limitations

* Single hardcoded/demo `learner_id`; no authentication.
* Submissions are currently plain text/pseudocode rather than compiled or executed code.
* Only three starter problems are seeded.
* LLM evaluation is synchronous.
* No background job queue is used.
* No persistent multi-user identity or authorization model.
* Evaluation quality depends partly on the LLM's reasoning and response consistency.

These limitations are intentional scope boundaries for the 2-day prototype rather than attempts to model a production-scale distributed system.

## Future Extensions

Potential future improvements include:

* User authentication and learner profiles
* More LLD problems and difficulty levels
* Diagram submission and diagram-aware evaluation
* Code submission with static analysis
* Rubric-based scoring
* Background evaluation jobs
* Evaluation history and progress analytics
* More specialized evaluators implementing the existing `Evaluator` interface

## AI-Assisted Development

AI assistance was used during development for architecture exploration, implementation support, debugging, testing ideas, and documentation.

The major AI-assisted decisions and what was ultimately accepted or changed are documented separately in:

```text
AI_USAGE.md
```

The goal was to use AI as an engineering assistant while retaining ownership of the architecture, implementation choices, testing strategy, and final product decisions.
