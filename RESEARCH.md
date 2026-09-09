# Research Note — DesignForge

## 1. The Learner Problem

Low-Level Design (LLD) is different from problems such as LeetCode because there is
usually no single correct implementation. A learner may design a Parking Lot,
Vending Machine, or Elevator system in several reasonable ways, with the quality
depending on responsibilities, abstractions, coupling, extensibility, and the
trade-offs they make.

This makes self-assessment difficult. A learner can complete an LLD problem and
still not know whether the design is actually good or what should be improved.
This is different from an algorithmic problem where a test suite can provide an
immediate pass/fail signal.

Research into current LLD preparation resources supports this problem. A recent
article by the creator of LowLevelDesign Mastery argues that traditional LLD
preparation often focuses on OOP concepts, SOLID principles, design patterns, and
finished solutions, while effective practice needs more emphasis on explaining
and iterating on design decisions. The same source explicitly notes that LLD
usually has no single correct design; instead, there are reasonable trade-offs
and context-dependent decisions.

This suggests that an effective practice product should not only show reference
solutions. It should give learners a way to **attempt a design, receive useful
feedback, and improve it**.

---

## 2. Existing Approaches

### 2.1 Open-source question collections

Open-source repositories provide a large collection of common LLD/OOD problems
and reference implementations. For example, public LLD collections include
problems such as Parking Lot, Vending Machine, and Elevator System.

These resources are useful for discovering problems and studying possible
solutions, but they generally do not provide a structured loop for submitting
one's own design and receiving personalized feedback.

**Strength:** broad and accessible problem exposure.

**Gap:** little or no structured feedback on the learner's own attempt.

---

### 2.2 Structured courses

Educative's **Grokking the Low Level Design Interview Using OOD Principles**
takes a much more structured approach. Its current course listing describes
215 lessons across 28 sections, approximately 70 hours of study, 21 design
case studies, and 19 mock interviews.

This provides much deeper learning material than a simple question bank and
covers many real-world design problems.

However, its primary format is still a structured learning course. DesignForge
takes a narrower approach: instead of trying to teach the complete LLD
curriculum, it focuses on the repeated cycle of **attempt → feedback →
revision**.

**Strength:** comprehensive learning material and worked problems.

**Gap:** not optimized specifically around a lightweight, repeated submission
and revision loop.

---

### 2.3 AI-powered LLD practice platforms

LowLevelDesign Mastery is the closest product found during this research.
It describes itself as an interactive LLD practice platform with AI-powered
feedback. Its playground includes problem selection, class diagrams, a code
editor, code execution, and feedback, with 40+ problems and multiple supported
languages.

Its creator also describes the intended flow as clarifying requirements,
identifying entities and responsibilities, drawing class diagrams, writing
code, and receiving AI-powered structured feedback.

This validates the general product direction: **LLD practice combined with
AI feedback is already a useful product category**.

DesignForge therefore does not attempt to claim that AI-powered LLD practice
is a new idea. Instead, it deliberately explores a smaller version of that
experience within a two-day engineering scope, with particular focus on
evaluation architecture, feedback, and revision history.

**Strength:** closest match to the intended practice experience.

**Gap/opportunity for this prototype:** focus on a smaller, explainable
evaluation pipeline rather than building a full visual playground and
execution environment.

---

### 2.4 Hiring and assessment platforms

Tools such as Testlify approach LLD from the opposite direction. Its LLD
assessment is designed for interviewing and evaluating candidates, measuring
areas such as OOP principles, class/interface design, design patterns, data
structures, and code-level optimization.

This is useful for employers who need to assess candidates, but the primary
user is the **evaluator/recruiter**, not a learner trying to understand how
their design can improve.

**Strength:** structured candidate assessment.

**Gap:** feedback is primarily an assessment mechanism rather than a
revision-oriented learning loop.

---

## 3. Key Gaps Identified

The research suggests four useful gaps for a small learner-focused product:

1. **Problem exposure is easier than feedback.**  
   Question collections make it easy to find LLD problems, but they do not
   necessarily evaluate the learner's own design.

2. **Deep courses are broader than the required practice loop.**  
   Structured courses provide extensive explanations and worked examples,
   while DesignForge focuses specifically on repeated practice and revision.

3. **Existing AI practice products are much broader in scope.**  
   Platforms such as LowLevelDesign Mastery include diagrams, code execution,
   multiple languages, and many problems. DesignForge intentionally reduces
   this scope to make the core evaluation loop easier to build, test, and
   understand within two days.

4. **Evaluation can be treated as a product feature rather than a black box.**  
   DesignForge makes an explicit distinction between deterministic structural
   checks and LLM-based design reasoning. This makes the evaluation approach
   easier to explain and provides a fallback when the AI service is unavailable.

---

## 4. Product Direction for DesignForge

Based on this research, DesignForge focuses on one narrow problem:

> **Help a learner practice LLD repeatedly and understand how their design can
> improve.**

The MVP therefore uses:

- a small set of familiar LLD problems
- text/pseudocode submissions instead of a full code editor
- structured feedback containing a verdict, strengths, and gaps
- deterministic checks for simple structural properties
- LLM-based reasoning for the parts that require judgment
- multiple submissions within the same attempt
- visible submission history so improvement can be tracked

The evaluation architecture is intentionally hybrid.

```text
                 Submission
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   Rule-based checks       LLM evaluation
          │                     │
          └──────────┬──────────┘
                     ▼
             Composite Feedback
```

The rule-based layer provides a predictable baseline, while the LLM handles
questions such as whether responsibilities are separated sensibly or whether
the proposed design has obvious coupling or extensibility problems.

This is important because LLD does not have one fixed correct answer. A useful
evaluator therefore needs to provide reasoning-oriented feedback rather than
simply comparing a submission with one reference implementation.

---

## 5. Conclusion

The research did not reveal a need to build another large LLD course or
question bank. Those already exist.

Instead, it pointed toward a smaller opportunity: make the **practice and
revision loop** the central product experience.

DesignForge is intentionally limited in scope, but it demonstrates this loop
end to end:

**Choose → Design → Submit → Evaluate → Review → Revise → Resubmit**

The prototype also treats evaluation failures as an engineering concern rather
than assuming that an external LLM will always work. This led to the hybrid
evaluator and rule-based fallback used in the implementation.

The result is not intended to compete with full LLD learning platforms. It is a
focused prototype exploring how structured feedback and revision history can
make LLD practice more useful than simply reading reference solutions.

## Sources

1. **LowLevelDesign Mastery — Project / Platform**  
   Interactive LLD practice platform with AI feedback, diagrams, code editor,
   execution, and 40+ problems.

2. **Vishnu Darshan Sanku — “Why Most Engineers Struggle With Low-Level Design
   Interviews (And How to Actually Practice)”**  
   Discussion of LLD practice, trade-offs, and the need to iterate on designs.

3. **Educative — Grokking the Low Level Design Interview Using OOD Principles**  
   Current course information and scope.

4. **Open-source LLD collection**  
   Example of publicly available LLD/OOD problem collections including
   Parking Lot, Vending Machine, and Elevator.

5. **Testlify — Low-Level Design Interview**  
   Example of an assessment-oriented approach to evaluating LLD skills.