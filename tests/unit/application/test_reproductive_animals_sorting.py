from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from src.application.use_cases.reproduction.list_reproductive_animals import (
    VALID_SORTS,
    ReproductiveAnimalRow,
    _sort_rows,
)


def make_row(
    tag: str,
    *,
    name: str | None = None,
    days_postpartum: int | None = None,
    days_pregnant: int | None = None,
    alert_level: str = "none",
    bucket: str = "sin_inseminar",
    last_event_date: date | None = None,
) -> ReproductiveAnimalRow:
    return ReproductiveAnimalRow(
        animal_id=uuid4(),
        tag=tag,
        name=name,
        days_postpartum=days_postpartum,
        last_calving_date=None,
        days_pregnant=days_pregnant,
        expected_calving_date=None,
        alert_level=alert_level,
        bucket=bucket,
        situation_label="",
        last_event_type=None,
        last_event_date=last_event_date,
        last_insemination_id=None,
        last_insemination_status=None,
        method=None,
        technician=None,
        heat_detected=None,
        labels=[],
    )


def tags(rows: list[ReproductiveAnimalRow]) -> list[str]:
    return [r.tag for r in rows]


@pytest.mark.parametrize("sort", sorted(VALID_SORTS))
@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_every_column_sorts_without_error(sort: str, direction: str):
    rows = [
        make_row("002", name="Bety", days_postpartum=40, alert_level="optimal"),
        make_row("013", days_pregnant=100, bucket="prenadas", alert_level="critical"),
        make_row("018", name="Mario", last_event_date=date(2026, 6, 18)),
    ]
    _sort_rows(rows, sort, direction)
    assert sorted(tags(rows)) == ["002", "013", "018"]


def test_days_column_uses_gestation_days_for_pregnant_cows():
    rows = [
        make_row("a", days_postpartum=50),
        make_row("b", days_pregnant=200, bucket="prenadas"),
        make_row("c", days_postpartum=120),
    ]
    _sort_rows(rows, "days", "desc")
    assert tags(rows) == ["b", "c", "a"]


def test_rows_without_a_value_sink_to_the_bottom_in_both_directions():
    rows = [
        make_row("empty"),
        make_row("a", days_postpartum=10),
        make_row("b", days_postpartum=90),
    ]

    _sort_rows(rows, "days", "asc")
    assert tags(rows) == ["a", "b", "empty"]

    _sort_rows(rows, "days", "desc")
    assert tags(rows) == ["b", "a", "empty"]


def test_alert_column_puts_the_most_urgent_first_ascending():
    rows = [
        make_row("ok", alert_level="optimal"),
        make_row("crit", alert_level="critical"),
        make_row("warn", alert_level="warning"),
    ]
    _sort_rows(rows, "alert", "asc")
    assert tags(rows) == ["crit", "warn", "ok"]


def test_situation_column_follows_the_reproductive_cycle():
    rows = [
        make_row("none", bucket="sin_inseminar"),
        make_row("preg", bucket="prenadas"),
        make_row("empty", bucket="vacias"),
        make_row("ins", bucket="inseminadas"),
    ]
    _sort_rows(rows, "situation", "asc")
    assert tags(rows) == ["preg", "ins", "empty", "none"]


def test_last_event_sorts_most_recent_first_descending():
    rows = [
        make_row("old", last_event_date=date(2026, 1, 5)),
        make_row("never"),
        make_row("recent", last_event_date=date(2026, 6, 18)),
    ]
    _sort_rows(rows, "last_event", "desc")
    assert tags(rows) == ["recent", "old", "never"]
