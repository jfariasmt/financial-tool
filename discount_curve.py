from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

import numpy as np
from scipy.interpolate import CubicSpline

from financial_tool.core.day_count import year_fraction


@dataclass(frozen=True)
class DiscountCurve:
    """Discount curve with interpolation over discount factors or zero rates."""

    valuation_date: date
    pillars: Sequence[date]
    discount_factors: Sequence[float]
    day_count: str = "ACT/365"
    interpolation: str = "linear_df"  # linear_df, linear_zc, cubic_df, cubic_zc

    def __post_init__(self) -> None:
        if len(self.pillars) != len(self.discount_factors):
            raise ValueError("pillars and discount_factors must have the same length")
        if len(self.pillars) < 2:
            raise ValueError("at least two pillars are required")
        if any(df <= 0 for df in self.discount_factors):
            raise ValueError("discount factors must be positive")

    @property
    def times(self) -> np.ndarray:
        return np.array([year_fraction(self.valuation_date, p, self.day_count) for p in self.pillars], dtype=float)

    @property
    def dfs(self) -> np.ndarray:
        return np.array(self.discount_factors, dtype=float)

    @property
    def zero_rates(self) -> np.ndarray:
        t = self.times
        return -np.log(self.dfs) / t

    def df(self, target_date: date) -> float:
        """Interpolated discount factor for target date."""
        t = year_fraction(self.valuation_date, target_date, self.day_count)
        if t < 0:
            raise ValueError("target_date cannot be before valuation_date")
        if t == 0:
            return 1.0

        method = self.interpolation.lower()
        x = self.times

        if method == "linear_df":
            return float(np.interp(t, x, self.dfs))

        if method == "linear_zc":
            z = float(np.interp(t, x, self.zero_rates))
            return float(np.exp(-z * t))

        if method == "cubic_df":
            cs = CubicSpline(x, self.dfs, extrapolate=True)
            return float(cs(t))

        if method == "cubic_zc":
            cs = CubicSpline(x, self.zero_rates, extrapolate=True)
            z = float(cs(t))
            return float(np.exp(-z * t))

        raise ValueError(f"Unsupported interpolation method: {self.interpolation}")

    def zero_rate(self, target_date: date) -> float:
        """Continuously compounded zero rate implied by the curve."""
        t = year_fraction(self.valuation_date, target_date, self.day_count)
        if t <= 0:
            return 0.0
        return -np.log(self.df(target_date)) / t

    def bumped(self, bump_size: float = 0.0001, mode: str = "parallel_zc") -> "DiscountCurve":
        """Return a bumped copy of the curve.

        bump_size is expressed in decimal rates. 1 bp = 0.0001.
        """
        mode = mode.lower()
        if mode != "parallel_zc":
            raise ValueError("Only parallel_zc bump is implemented in the initial version")

        bumped_zeros = self.zero_rates + bump_size
        bumped_dfs = np.exp(-bumped_zeros * self.times)
        return DiscountCurve(
            valuation_date=self.valuation_date,
            pillars=list(self.pillars),
            discount_factors=list(bumped_dfs),
            day_count=self.day_count,
            interpolation=self.interpolation,
        )
