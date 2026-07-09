from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from financial_tool.curves.discount_curve import DiscountCurve


@dataclass(frozen=True)
class FixedRateBond:
    maturity_date: date
    coupon_rate: float
    payment_dates: Sequence[date]
    notional: float = 100.0
    coupon_frequency: int = 2

    def cashflows(self) -> list[tuple[date, float]]:
        coupon = self.notional * self.coupon_rate / self.coupon_frequency
        flows = [(d, coupon) for d in self.payment_dates]
        flows[-1] = (flows[-1][0], flows[-1][1] + self.notional)
        return flows

    def price(self, curve: DiscountCurve, settlement_date: date | None = None) -> float:
        settlement = settlement_date or curve.valuation_date
        value = 0.0
        for pay_date, amount in self.cashflows():
            if pay_date > settlement:
                value += amount * curve.df(pay_date)
        return value

    def dv01(self, curve: DiscountCurve, bump_size: float = 0.0001) -> float:
        base = self.price(curve)
        bumped = self.price(curve.bumped(bump_size=bump_size))
        return (base - bumped) / (bump_size / 0.0001)
