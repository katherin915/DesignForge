/**
 * All calls are relative (e.g. "/problems") because the frontend is served
 * by the same FastAPI app (see app/main.py StaticFiles mount). No separate
 * frontend server, no CORS complexity — one process to run.
 */
const API = "";

let currentProblem = null;
let currentAttemptId = null;

// ---------- Init ----------

async function init() {
  const problems = await fetchJSON(`${API}/problems`);
  renderProblemList(problems);
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`Request to ${url} failed with ${res.status}`);
  }
  return res.json();
}

// ---------- Problem list (sidebar) ----------

function renderProblemList(problems) {
  const container = document.getElementById("problem-list");
  container.innerHTML = "";
  problems.forEach((problem) => {
    const btn = document.createElement("button");
    btn.className = "problem-item";
    btn.id = `problem-btn-${problem.id}`;
    btn.innerHTML = `${escapeHtml(problem.title)}<span class="difficulty">${escapeHtml(problem.difficulty)}</span>`;
    btn.addEventListener("click", () => selectProblem(problem));
    container.appendChild(btn);
  });
}

function selectProblem(problem) {
  currentProblem = problem;
  currentAttemptId = null;

  document.querySelectorAll(".problem-item").forEach((el) => el.classList.remove("active"));
  document.getElementById(`problem-btn-${problem.id}`).classList.add("active");

  document.getElementById("empty-state").classList.add("hidden");
  document.getElementById("problem-view").classList.remove("hidden");
  document.getElementById("problem-title").textContent = problem.title;
  document.getElementById("problem-description").textContent = problem.description;

  document.getElementById("work-panel").classList.add("hidden");
  document.getElementById("start-attempt-row").classList.remove("hidden");
  document.getElementById("submission-content").value = "";
  document.getElementById("feedback-container").innerHTML = "";
  document.getElementById("history-list").innerHTML = "";
}

// ---------- Attempts ----------

document.getElementById("start-attempt-btn").addEventListener("click", async () => {
  const attempt = await fetchJSON(`${API}/attempts`, {
    method: "POST",
    body: JSON.stringify({ problem_id: currentProblem.id }),
  });
  currentAttemptId = attempt.id;

  document.getElementById("start-attempt-row").classList.add("hidden");
  document.getElementById("work-panel").classList.remove("hidden");
  await refreshHistory();
});

// ---------- Submissions ----------

document.getElementById("submit-btn").addEventListener("click", async () => {
  const content = document.getElementById("submission-content").value.trim();
  if (!content) return;

  const statusLabel = document.getElementById("submit-status");
  const submitBtn = document.getElementById("submit-btn");
  submitBtn.disabled = true;
  statusLabel.textContent = "evaluating...";

  try {
    const result = await fetchJSON(`${API}/attempts/${currentAttemptId}/submissions`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    renderFeedback(result);
    statusLabel.textContent = "";
    await refreshHistory();
  } catch (e) {
    statusLabel.textContent = "request failed — try again";
  } finally {
    submitBtn.disabled = false;
  }
});

function renderFeedback(submission) {
  const container = document.getElementById("feedback-container");

  if (submission.status === "failed") {
    container.innerHTML = `
      <div class="error-box">
        Evaluation couldn't complete: ${escapeHtml(submission.error_message || "unknown error")}.
        <button class="secondary" style="margin-left: 10px;" onclick="retrySubmission(${submission.id})">Retry</button>
      </div>`;
    return;
  }

  const fb = submission.feedback;
  if (!fb) { container.innerHTML = ""; return; }

  container.innerHTML = `
    <div class="feedback">
      <span class="verdict-badge verdict-${fb.verdict}">${escapeHtml(fb.verdict.replace("_", " "))}</span>
      <span class="evaluator-tag">via ${escapeHtml(fb.evaluator_used.replace("_", " "))}</span>
      <div class="feedback-cols">
        <div class="feedback-col">
          <h4>strengths</h4>
          <ul>${fb.strengths.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>
        </div>
        <div class="feedback-col">
          <h4>gaps to address</h4>
          <ul>${fb.gaps.length ? fb.gaps.map((g) => `<li>${escapeHtml(g)}</li>`).join("") : "<li>none noted</li>"}</ul>
        </div>
      </div>
    </div>`;
}

async function retrySubmission(submissionId) {
  const container = document.getElementById("feedback-container");
  container.innerHTML = `<div class="error-box">Retrying...</div>`;
  try {
    const result = await fetchJSON(`${API}/submissions/${submissionId}/retry`, { method: "POST" });
    renderFeedback(result);
    await refreshHistory();
  } catch (e) {
    container.innerHTML = `<div class="error-box">Retry failed. Try again shortly.</div>`;
  }
}
window.retrySubmission = retrySubmission; // exposed for inline onclick

// ---------- History ----------

async function refreshHistory() {
  if (!currentAttemptId) return;
  const submissions = await fetchJSON(`${API}/attempts/${currentAttemptId}/submissions`);
  const list = document.getElementById("history-list");

  if (submissions.length === 0) {
    list.innerHTML = `<p class="history-meta">No submissions yet for this attempt.</p>`;
    return;
  }

  list.innerHTML = submissions
    .map((s, i) => {
      const verdict = s.feedback ? s.feedback.verdict : null;
      const statusClass = verdict ? `verdict-${verdict}` : (s.status === "failed" ? "verdict-needs_work" : "");
      const label = verdict ? verdict.replace("_", " ") : s.status;
      return `
        <div class="history-item">
          <span>Revision ${i + 1}</span>
          <span class="history-status verdict-badge ${statusClass}">${escapeHtml(label)}</span>
        </div>`;
    })
    .join("");
}

// ---------- Utils ----------

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

init();