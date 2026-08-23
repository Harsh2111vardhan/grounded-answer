# Grounded Answer

A policy Q&A system that answers from supplied policy documents, cites source
clauses, detects relevant conflicts, applies dated amendments, and refuses when
the evidence does not establish an answer.

**Evaluation:** [`evaluation/evaluation_results.md`](evaluation/evaluation_results.md)
contains the final test set, observed answers, pass/fail results, and one
intentionally documented failure case.

## Requirements

- Python 3.11.8
- Git
- Gemini API key

## Setup

### 1. Clone

```bash
git clone https://github.com/Harsh2111vardhan/grounded-answer.git
cd grounded-answer
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Gemini

1. Open [Google AI Studio](https://aistudio.google.com/).
2. Sign in and select **Get API key**.
3. Create an API key.
4. Create `.env` in the project root:

```text
GEMINI_API_KEY=your_api_key_here
```

Do not commit `.env` or your API key.

## Run

```bash
python chat.py
```

Ask a question about the policy manual.

Type `exit` or `quit` to stop.

## Tests

```bash
pytest
```

Expected:

```text
47 passed
```

## How it works

```text
Question
   ↓
Hybrid Retrieval (BM25 + semantic)
   ↓
Policy Evidence
   ↓
Answer + Citations
   ↓
Citation + Conflict + Claim + Entailment Checks
   ↓
ANSWER / PARTIAL / CONFLICT / REFUSE
```

## Amendments

Amendments are parsed from the supplied amendment document rather than
hard-coded into the application.

The system supports event-based and determination-based applicability using
amendment effective dates.

## Grounding decisions

- **ANSWER**: the evidence supports the answer.
- **PARTIAL**: only part of the answer is supported.
- **CONFLICT**: relevant policy provisions conflict.
- **REFUSE**: the supplied evidence does not establish the answer.

The system does not use external knowledge to fill policy gaps or silently
resolve conflicting provisions.

## Project structure

```text
data/        Policy and amendment documents
src/         Application code
tests/       Automated tests
evaluation/  Evaluation results
chat.py      CLI entry point
```

See `DECISIONS.md` for design decisions, trade-offs, and limitations.

See `AI-USAGE.md` for AI-assisted development disclosure.
