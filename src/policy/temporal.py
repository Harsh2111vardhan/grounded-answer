from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from calendar import monthrange


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass(frozen=True)
class TemporalContext:
    event_date: date | None = None
    determination_date: date | None = None
    claim_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None


def _parse_date(value: str) -> date | None:
    value = value.strip()

    formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                value,
                fmt,
            ).date()
        except ValueError:
            continue

    month_match = re.fullmatch(
        r"([A-Za-z]+)\s+(\d{4})",
        value,
    )

    if month_match:
        month = MONTHS.get(
            month_match.group(1).lower()
        )

        if month:
            return date(
                int(month_match.group(2)),
                month,
                1,
            )

    return None


def extract_dates(text: str) -> list[date]:
    """
    Extract dates from text.

    The return type is deliberately just list[date].
    Consumers should not expect DateMatch.value or other
    wrapper attributes.
    """

    matches: list[tuple[int, int, date]] = []

    patterns = [
        (
            r"\b\d{4}-\d{2}-\d{2}\b",
            "day",
        ),
        (
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
            "day",
        ),
        (
            r"\b\d{1,2}-\d{1,2}-\d{4}\b",
            "day",
        ),
        (
            r"\b\d{1,2}\s+"
            r"(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)"
            r"\s+\d{4}\b",
            "day",
        ),
        (
            r"\b(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)"
            r"\s+\d{1,2},\s+\d{4}\b",
            "day",
        ),
        (
            r"\b(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)"
            r"\s+\d{4}\b",
            "month",
        ),
    ]

    for pattern, _granularity in patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            parsed = _parse_date(
                match.group(0)
            )

            if parsed is not None:
                matches.append(
                    (
                        match.start(),
                        match.end(),
                        parsed,
                    )
                )

    matches.sort(
        key=lambda item: item[0]
    )

    result: list[date] = []

    for start, end, parsed in matches:
        if matches and result:
            previous_start = next(
                (
                    item[0]
                    for item in matches
                    if item[2] == result[-1]
                ),
                -1,
            )

            if start < previous_start:
                continue

        if parsed not in result:
            result.append(parsed)

    return result


def _month_end(value: date) -> date:
    return date(
        value.year,
        value.month,
        monthrange(
            value.year,
            value.month,
        )[1],
    )


def extract_temporal_context(
    question: str,
) -> TemporalContext:
    dates = extract_dates(question)

    if not dates:
        return TemporalContext()

    lowered = question.lower()

    if re.search(
        r"\b(change|changed|change of circumstances|"
        r"occurred|happened)\b",
        lowered,
    ):
        return TemporalContext(
            event_date=dates[0],
            claim_date=dates[0],
        )

    if re.search(
        r"\b(determination|determined|decision|"
        r"award was determined)\b",
        lowered,
    ):
        return TemporalContext(
            determination_date=dates[0],
            claim_date=dates[0],
        )

    if len(dates) >= 2:
        first = dates[0]
        second = dates[1]

        if first <= second:
            return TemporalContext(
                claim_date=first,
                period_start=first,
                period_end=second,
            )

    return TemporalContext(
        claim_date=dates[0],
        determination_date=dates[0],
    )


def select_date(
    context: TemporalContext,
    basis: str,
    fallback: date | None = None,
) -> date | None:
    """
    Select the date relevant to an amendment's applicability rule.

    'event' uses the event/change date.
    'determination' uses the determination date.
    """

    if basis == "event":
        return (
            context.event_date
            or context.claim_date
            or fallback
        )

    if basis == "determination":
        return (
            context.determination_date
            or context.claim_date
            or fallback
        )

    return (
        context.claim_date
        or fallback
    )