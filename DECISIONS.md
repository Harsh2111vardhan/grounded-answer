## 1st Review

read through the policy manual before starting implementation and found the following inconsistencies:

### Full-time student reference

The manual refers to full-time education in §3.2.3 and §5.2.3, saying that it is addressed separately.

§7.1.3 then specifically points to §5.4 for the exception relating to full-time students.

However, §5.4 is about households including a person receiving a care allowance, not full-time students.

This looks like an apparent gap or broken cross-reference. I don't want to hard-code this specific case. The system should detect when a referenced clause does not actually support what the surrounding text suggests.

### Reporting period

There is also an inconsistency between:

- §4.3.2, which requires changes to be reported within 10 calendar days.
- §9.1.4, which refers to 30 calendar days.

The system should surface this conflict rather than silently choosing one.

## Initial architecture

The current plan is:

Question -> Retrieval -> Evidence -> Verification -> Answer / Refusal

## Planned Stack

- Python
- Gemini 2.5 Flash
- Sentence Transformers
- BM25
- pytest
- CLI

### Retrieval

BM25 + local sentence-transformer embeddings, combined using reciprocal rank fusion.

### Chunking

Use the policy's existing clause numbers as the main chunk boundaries so citations can point directly to clauses such as §4.3.2.

### Refusal

If the policy does not actually support the answer, the system should refuse instead of filling the gap with general knowledge.

More decisions will be added as implementation progresses.
