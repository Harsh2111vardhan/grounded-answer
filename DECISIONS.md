# Decisions

## 1st Review

I read through the policy manual before starting implementation and found the
following inconsistencies.

### Full-time student reference

The manual refers to full-time education in §3.2.3 and §5.2.3, saying that it
is addressed separately.

§7.1.3 then specifically points to §5.4 for the exception relating to
full-time students.

However, §5.4 is about households including a person receiving a care
allowance, not full-time students.

This looks like an apparent gap or broken cross-reference. I don't want to
hard-code this specific case. The system should detect when a referenced
clause does not actually support what the surrounding text suggests.

### Reporting period

There is also an inconsistency between:

- §4.3.2, which requires changes to be reported within 10 calendar days.
- §9.1.4, which refers to 30 calendar days.

The system should surface this conflict rather than silently choosing one.

## Initial architecture

The initial plan was:

Question -> Retrieval -> Evidence -> Verification -> Answer / Refusal

I kept this structure because I wanted the grounding checks to happen after
retrieval and generation rather than treating the LLM's response as
automatically trustworthy.

## Planned Stack

- Python
- Gemini
- Sentence Transformers
- BM25
- pytest
- CLI

### Retrieval

I chose BM25 + local sentence-transformer embeddings, combined using reciprocal
rank fusion.

The idea was to combine keyword matching with semantic similarity rather than
depending entirely on either method.

### Chunking

I decided to use the policy's existing clause numbers as the main chunk
boundaries so citations can point directly to clauses such as §4.3.2.

This also makes the retrieved evidence easier to inspect and verify.

### Refusal

If the policy does not actually support the answer, the system should refuse
instead of filling the gap with general knowledge.

I also added an escalation step so that an unsupported answer does not simply
end with "I don't know". If the evidence does not identify a more specific
contact, the response directs the user to the local Department district
office.

## Parser format

While inspecting the manual, I found that clause headings are not completely
consistent.

Most clauses use a format like:

**1.1.1** Clause text

but some include the clause title inside the heading:

**1.4.1 Applicant** — Clause text

The parser initially handled only the first format. This was caught by checking
the parsed output against the source manual, so the parser was updated to
handle both formats.

## Citation validation

I decided that having a citation in an answer is not enough.

The citation must also refer to a clause that was actually present in the
retrieved evidence.

This prevents the model from citing a clause that it was not given.

## Claim-level verification

I added claim extraction and entailment checking because a valid citation does
not necessarily mean that the claim is supported by that clause.

Each generated claim is checked against its cited policy clause before the
grounding decision is made.

## Conflict detection

I added a separate conflict checker so the system can identify cases where
retrieved provisions appear to contradict each other.

The first version was too broad. It could treat unrelated clauses as
conflicting simply because they contained different numbers.

I changed it so that clauses must have meaningful term overlap before a
potential deadline conflict is considered.

This fixed the case where an unrelated deadline could cause an otherwise
correct answer to be marked as CONFLICT.

## Keep conflict detection local

I chose not to use an LLM for the basic conflict detection.

Clear cases such as two overlapping provisions containing different deadlines
can be detected directly from the text.

This reduces API usage and also makes the behaviour deterministic and easier
to test.

## Grounding gate

I added a final grounding gate which turns the verification results into one
of four decisions:

- ANSWER
- PARTIAL
- REFUSE
- CONFLICT

The purpose is to keep answer generation separate from the decision about
whether the answer is actually safe to return.

## User-facing rendering

I added a separate renderer rather than putting formatting logic inside the
grounding gate.

This keeps the grounding logic focused on making the decision while the
renderer handles how that decision is shown to the user.

The output now shows the answer, sources, and a next step when the system
cannot safely answer.

## CLI instead of UI

I decided to keep the project CLI-based.

The handbook does not require a UI, and the CLI is enough to demonstrate the
complete pipeline. I would rather keep the implementation focused on
grounding than spend the remaining time building a frontend.

## Evaluation

I added a separate evaluation runner with predefined questions and expected
grounding decisions.

I used it to test normal answers, conflicts, unsupported questions and
questions requiring multiple policy provisions.

The evaluation exposed the false-conflict problem, which led to the relevance
filtering change.

## Entailment caching

I found that the same claim and citation could be checked more than once.

I added caching inside the entailment checker so identical claim/citation pairs
do not trigger repeated Gemini calls.

Apart from reducing API usage, this also avoids getting inconsistent results
from repeated LLM checks of exactly the same claim.

## Answer formatting

The generated answers initially contained too much repetition and sometimes
put multiple citations around the same claim.

I tightened the answer-generation instructions so that each factual claim has
one clear grounding citation and simple questions are answered directly
without unnecessary repetition.

## What I would have done differently

The first conflict detector was too aggressive. I should have considered
whether retrieved clauses were actually about the same subject before
comparing their numbers.

I also could have designed the claim/citation relationship more carefully from
the beginning. Multiple citations attached to the same generated sentence
created unnecessary ambiguity during entailment checking.

## Current direction

The original implementation assumed that the consolidated manual represented
the policy to apply.

The new amendment breaks that assumption because the correct answer can depend
on the date of the relevant claim or change of circumstances.

I am keeping the original manual intact rather than replacing old clauses with
new values. The next change will add date-aware policy resolution so the system
can determine which provision applies to the relevant date.