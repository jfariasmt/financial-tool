from datetime import date

from financial_tool.core.day_count import year_fraction


def test_act_365_one_year():
    assert year_fraction(date(2026, 1, 1), date(2027, 1, 1), "ACT/365") == 1.0
