# Evaluation Results

The evaluation set tests grounded answers, refusals, policy conflicts, amendments,
and an explicit edge case. All results were produced by running the submitted
application.

## Evaluation Summary

```text
01  GROUNDED ANSWER
    Question: What is a full-time student under the policy?
    Expected: ANSWER
    Actual:   ANSWER
    Result:   PASS
    Answer:   A full-time student is a person enrolled in a course of study at
              an accredited institution of higher education, where the
              institution classifies the enrolment as full-time. 【§1.4.6】
    Why:      Directly supported by §1.4.6 with a valid citation.


02  UNSUPPORTED SCENARIO
    Question: A person is enrolled in a course at an accredited institution,
              but the institution does not classify the enrolment as full-time.
              Should the person be treated as a full-time student?
    Expected: REFUSE
    Actual:   REFUSE
    Result:   PASS
    Answer:   The supplied policy evidence does not establish the answer.
    Why:      The evidence does not establish the requested determination, so
              the system refuses instead of making an unsupported inference.


03  PROCEDURE
    Question: How can a recipient report a change of circumstances?
    Expected: ANSWER
    Actual:   ANSWER
    Result:   PASS
    Answer:   A recipient may report a change of circumstances in person at a
              district office, by telephone to the Program line, in writing,
              or through the online account. 【§4.3.3】
    Why:      The reporting methods are directly stated in §4.3.3.


04  CONFLICTING PROVISIONS
    Question: A recipient's change of circumstances occurred on 15 February
              2026. What is the reporting deadline?
    Expected: CONFLICT
    Actual:   CONFLICT
    Result:   PASS
    Answer:   The manual contains conflicting provisions. §4.3.2 gives 10
              calendar days while §9.1.4 refers to 30 calendar days. The manual
              does not establish which requirement takes precedence.
    Why:      The system detected the relevant contradiction and surfaced both
              provisions instead of silently selecting one.


05  POST-AMENDMENT EVENT
    Question: A recipient's change of circumstances occurred on 15 April 2026.
              What is the reporting deadline?
    Expected: ANSWER
    Actual:   ANSWER
    Result:   PASS
    Answer:   The recipient must report the change within 14 calendar days of
              the change occurring, or within 14 calendar days of becoming
              aware of the change, whichever is later. 【§4.3.2】
    Why:      The amendment applicable to the event date was selected instead
              of applying the older rule.


06  POLICY LIMIT
    Question: What is the deduction limit from ongoing assistance?
    Expected: ANSWER
    Actual:   ANSWER
    Result:   PASS
    Answer:   Deduction from ongoing assistance must not exceed 10 per cent of
              the monthly award, or 20 per cent where §9.6 applies. 【§9.3.2】
    Why:      The limit is directly stated and supported by §9.3.2.


07  DETERMINATION-BASED AMENDMENT
    Question: A sanction determination was made on 15 April 2026. What is the
              sanction period for a first sanction?
    Expected: ANSWER
    Actual:   ANSWER
    Result:   PASS
    Answer:   The sanction period for a first sanction is 4 weeks. 【§10.5.2】
    Why:      The applicable policy is selected using the determination date.


08  UNSUPPORTED TOPIC
    Question: What is the Department's policy on housing loans?
    Expected: REFUSE
    Actual:   REFUSE
    Result:   PASS
    Answer:   The supplied policy evidence does not establish the answer.
    Why:      No supplied evidence establishes a housing-loan policy, so the
              system refuses rather than using outside knowledge.


09  DEFINITION
    Question: What is the definition of a dependent child?
    Expected: ANSWER
    Actual:   ANSWER
    Result:   PASS
    Answer:   A dependent child is a person under the age of 18 who is a
              household member, or a person aged 18 to 20 who is a household
              member and is enrolled in secondary education. 【§1.4.5】
    Why:      The definition is directly supported by §1.4.5.


10  TIME PERIOD
    Question: How long is residential care treated as temporary?
    Expected: ANSWER
    Actual:   ANSWER
    Result:   PASS
    Answer:   Residence in a residential care facility is treated as temporary
              for the first 56 days. 【§4.2.2】
    Why:      The 56-day period is directly stated in §4.2.2.


11  DATE CALCULATION EDGE CASE
    Question: A recipient's change of circumstances occurred on 15 April 2026.
              What is the exact calendar date by which they must report it?
    Expected: ANSWER
    Actual:   ANSWER
    Result:   FAIL
    Answer:   A recipient must report any change of circumstances within 14
              calendar days of the change occurring, or within 14 calendar days
              of becoming aware of the change, whichever is later. 【§4.3.2】
    Why:      The policy rule was correctly retrieved and grounded, but the
              system did not calculate the requested exact date.
              Expected date: 29 April 2026.
```

## Final Result

**10/11 passed. One test was intentionally allowed to fail.**

The failed case exposes a real limitation: the system grounds policy rules
correctly but does not currently guarantee calendar-date arithmetic when the
user asks for an exact date.

The evaluation therefore tests both what the system can do and where its
current boundary is.
