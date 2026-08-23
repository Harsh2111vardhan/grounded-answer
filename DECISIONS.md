# DECISIONS.md

## 1. Goal

The priority was to build a working grounded policy assistant before adding
extra features.

Core flow:

`Question → Retrieval → Evidence → Answer → Grounding Gate → Decision`

The system can return `ANSWER`, `PARTIAL`, `CONFLICT`, or `REFUSE`.

---

## 2. Considered, Chosen, Rejected

### Technology

**Considered:** Python + local retrieval, LangChain/vector DB, external web
search.

**Chosen:** Python 3.11 with BM25 + semantic retrieval, Gemini, and pytest.

**Rejected:** LangChain and a vector database because the supplied corpus is
small and did not justify the added infrastructure. Web search was rejected
because the supplied policy documents are the source of truth.

### Retrieval

**Considered:** keyword-only, semantic-only, hybrid retrieval.

**Chosen:** hybrid BM25 + semantic retrieval to cover both exact policy terms
and semantically similar questions.

**Rejected:** relying on either method alone.

### Grounding

**Considered:** trusting the generated answer, citation-only validation,
post-generation claim verification.

**Chosen:** post-generation grounding with citation, conflict, claim, and
entailment checks.

**Rejected:** trusting the LLM alone because a plausible answer is not proof
that the policy supports it.

### Policy conflicts

**Considered:** choose the most recent/relevant provision automatically or
surface the conflict.

**Chosen:** surface relevant conflicts and return `CONFLICT`.

**Rejected:** silently selecting one provision because the manual may not
establish precedence.

### Amendments

**Considered:** hard-code amended values into existing clauses or add a separate
policy applicability layer.

**Chosen:** a separate amendment layer with effective dates and applicability
basis.

**Rejected:** hard-coding amendments into retrieval/answering logic because it
would make future amendments harder to extend.

Retrieval, policy applicability, answer generation, and grounding remain
separate so changes to one part do not require rewriting the system.

---

## 3. Grounding and Refusal

A generated answer is not accepted just because it sounds correct.

The grounding gate checks:

1. Evidence exists.
2. Citations refer to retrieved clauses.
3. Relevant conflicts are detected.
4. Claims can be extracted.
5. Claims are supported by the retrieved evidence.

If the evidence does not establish the answer, the system refuses rather than
guessing.

I deliberately chose a conservative refusal threshold because an unsupported
policy answer is worse than asking a user to seek clarification.

---

## 4. Conflict Handling

The policy contains provisions that can conflict.

The system does not silently choose one. When a relevant conflict is detected,
it shows the conflicting clauses and returns `CONFLICT`.

The conflict detector also considers the question so unrelated different
numbers in retrieved clauses are not automatically treated as contradictions.

For example, a reporting-method question can still be answered from the
reporting-method clause even when a separate retrieved clause contains a
conflicting deadline.

---

## 5. Day-Two Amendment

The amendment requirement was handled by adding a policy layer rather than
rewriting the retrieval and grounding pipeline.

Amendments are represented with:

- amendment ID;
- effective date;
- target clause;
- operation;
- applicability basis.

The system distinguishes event-based applicability from
determination-based applicability.

This matters because a change-of-circumstances rule may depend on when the
change occurred, while a sanction rule may depend on when the determination
was made.

This allows the same question to produce different valid results for different
dates without manually replacing the original policy.

---

## 6. What I Cut

To keep the submission focused, I did not build:

- a web UI;
- authentication;
- conversation memory;
- external policy/web search;
- automatic contact with government departments;
- production-scale infrastructure.

These would add complexity without improving the required grounded-answer
workflow for the supplied corpus.

---

## 7. What the Solution Does Not Do

The system does not:

- invent missing policy;
- use general knowledge to fill policy gaps;
- silently resolve conflicting provisions;
- claim an ambiguous policy has a unique answer;
- perform external actions;
- provide legal advice;
- guarantee correctness beyond the supplied evidence;
- support every possible amendment format.

When the evidence is insufficient, the intended behavior is to say so.

---

## 8. Testing

The project includes automated tests for retrieval, parsing, amendments,
citations, claims, conflicts, grounding, entailment, and rendering.

The final evaluation includes:

- normal grounded answers;
- unsupported questions;
- conflicting provisions;
- amended rules;
- event-based applicability;
- determination-based applicability;
- an explicit date-calculation edge case.

The final evaluation contains 11 cases: **10 passed and 1 intentionally
failed**.

The failed case is documented in `evaluation/evaluation_results.md` and exposes
a known limitation in exact calendar-date calculation.

---

## 9. Innovation

Innovation was kept secondary to the required functionality.

The main design choice beyond basic retrieval and generation is the explicit
grounding pipeline:

`Evidence → Citation → Conflict → Claims → Entailment → Decision`

This makes the system distinguish between:

- a supported answer;
- insufficient evidence;
- partial support;
- an unresolved policy conflict.

The goal was reliability rather than adding a feature that could make the
submission harder to run or explain.

---

## 10. Trade-offs

### Conservative refusal

A stricter grounding threshold can produce more refusals, but reduces the risk
of confident unsupported policy answers.

### Local architecture

The current design is simple and reproducible for the supplied corpus, but is
not intended for very large policy collections.

### Deterministic checks

Citation and conflict checks are handled outside the LLM where possible, making
important failure paths easier to test and inspect.

---

## 11. What I Would Improve First

If more time were available, I would first:

1. Expand the labelled evaluation set with more edge cases.
2. Improve semantic conflict detection for less obvious contradictions.
3. Add broader temporal tests for multiple and overlapping amendments.
4. Improve claim extraction and citation verification.
5. Add direct navigation from citations to source text.

---

## Final Principle

**Answer when the policy evidence supports the answer. Stop when it does not.**

The floor was prioritized over extra complexity.
