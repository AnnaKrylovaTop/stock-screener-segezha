import pytest

from src.scenarios import build_scenarios


def test_build_scenarios_long():
    results = build_scenarios(
        direction="LONG",
        target_amount=1000,
        hedged_amount=1000,
        futures_price=90,
        current_spot=90,
        pct_range=[-10, 0, 10],
    )
    assert len(results) == 3
    assert results[0].spot_rate == 81
    assert results[-1].spot_rate == pytest.approx(99)


def test_build_scenarios_short():
    results = build_scenarios(
        direction="SHORT",
        target_amount=1000,
        hedged_amount=1000,
        futures_price=90,
        current_spot=90,
        pct_range=[-10, 10],
    )
    assert results[0].futures_pnl != results[1].futures_pnl
