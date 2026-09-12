"""What the lactation card shows: litres, money and how many records built them.

`production_count` used to be a hardcoded 0, so a card could read "1141,7 L"
and "0 registros de producción" at the same time.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.application.use_cases.animals.list_lactations import compute_metrics

START = date(2025, 9, 2)


def make_lactation(end_date: date | None = None):
    return SimpleNamespace(id="lac-1", start_date=START, end_date=end_date, status="closed")


def test_totals_and_count_come_from_the_productions():
    metrics = compute_metrics(
        make_lactation(date(2026, 6, 6)),
        {
            "total_volume_l": Decimal("1141.7"),
            "total_amount": Decimal("571.85"),
            "production_count": 277,
            "currency": "USD",
        },
    )

    assert metrics.total_volume_l == Decimal("1141.7")
    assert metrics.total_amount == Decimal("571.85")
    assert metrics.production_count == 277
    assert metrics.currency == "USD"
    assert metrics.days_in_milk == 277
    assert round(metrics.average_daily_l, 1) == Decimal("4.1")


def test_a_lactation_with_no_productions_reads_zero_rather_than_blank():
    metrics = compute_metrics(make_lactation(date(2026, 6, 6)), None)

    assert metrics.total_volume_l == Decimal("0")
    assert metrics.total_amount == Decimal("0")
    assert metrics.production_count == 0
    assert metrics.average_daily_l == Decimal("0.0")


def test_currency_falls_back_to_the_farm_default_when_no_production_carries_one():
    metrics = compute_metrics(make_lactation(), {"total_amount": Decimal("0")}, "EUR")

    assert metrics.currency == "EUR"


def test_an_open_lactation_counts_days_up_to_today():
    metrics = compute_metrics(make_lactation(end_date=None), {"total_volume_l": Decimal("100")})

    assert metrics.days_in_milk == (date.today() - START).days
    assert metrics.average_daily_l > 0


def test_a_lactation_that_starts_today_does_not_divide_by_zero():
    lactation = SimpleNamespace(id="lac-2", start_date=date.today(), end_date=None)

    metrics = compute_metrics(lactation, {"total_volume_l": Decimal("12")})

    assert metrics.days_in_milk == 0
    assert metrics.average_daily_l == Decimal("0.0")
