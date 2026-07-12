from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import numpy as np
from scipy.stats import norm

OptionType = Literal["call", "put"]
GreekQuote = Literal["derivative", "pl_per_bump"]
ShockType = Literal["absolute", "relative"]


@dataclass
class EquityOption:
    spot: float
    strike: float
    rate: float
    dividend: float
    maturity_days: float
    notional: float = 1.0
    option_type: OptionType = "call"
    day_basis: float = 365.0

    def __post_init__(self) -> None:
        if self.spot <= 0 or self.strike <= 0 or self.maturity_days <= 0:
            raise ValueError("spot, strike and maturity_days must be positive.")
        if self.option_type not in {"call", "put"}:
            raise ValueError("option_type must be 'call' or 'put'.")

    @property
    def maturity_years(self) -> float:
        return self.maturity_days / self.day_basis

    @property
    def discount_factor(self) -> float:
        return float(np.exp(-self.rate * self.maturity_years))

    @property
    def forward(self) -> float:
        return float(self.spot * np.exp((self.rate - self.dividend) * self.maturity_years))

    @property
    def moneyness(self) -> float:
        return self.strike / self.spot * 100.0

    def d1_d2(self, sigma: float) -> tuple[float, float]:
        if sigma <= 0:
            raise ValueError("sigma must be positive.")
        t = self.maturity_years
        d1 = (np.log(self.forward / self.strike) + 0.5 * sigma**2 * t) / (sigma * np.sqrt(t))
        return float(d1), float(d1 - sigma * np.sqrt(t))

    def price(self, sigma: float) -> float:
        d1, d2 = self.d1_d2(sigma)
        if self.option_type == "call":
            unit = self.discount_factor * (self.forward * norm.cdf(d1) - self.strike * norm.cdf(d2))
        else:
            unit = self.discount_factor * (self.strike * norm.cdf(-d2) - self.forward * norm.cdf(-d1))
        return float(unit * self.notional)

    @staticmethod
    def _quote(pv_up: float, pv_down: float, bump: float, quote: GreekQuote) -> float:
        if quote == "derivative":
            return float((pv_up - pv_down) / (2.0 * bump))
        if quote == "pl_per_bump":
            return float((pv_up - pv_down) / 2.0)
        raise ValueError("Unsupported Greek quote.")

    def _fd_attribute(self, sigma: float, attribute: str, bump: float,
                      quote: GreekQuote = "derivative") -> float:
        base = float(getattr(self, attribute))
        up = replace(self, **{attribute: base + bump})
        down = replace(self, **{attribute: base - bump})
        return self._quote(up.price(sigma), down.price(sigma), bump, quote)

    def delta(self, sigma: float, bump: float | None = None,
              quote: GreekQuote = "derivative") -> float:
        bump = max(self.spot * 1e-4, 1e-8) if bump is None else bump
        return self._fd_attribute(sigma, "spot", bump, quote)

    def gamma(self, sigma: float, bump: float | None = None) -> float:
        bump = max(self.spot * 1e-3, 1e-8) if bump is None else bump
        up = replace(self, spot=self.spot + bump)
        down = replace(self, spot=self.spot - bump)
        return float((up.price(sigma) - 2*self.price(sigma) + down.price(sigma)) / bump**2)

    def vega(self, sigma: float, bump: float = 0.01,
             quote: GreekQuote = "pl_per_bump") -> float:
        if sigma - bump <= 0:
            raise ValueError("sigma - bump must be positive.")
        return self._quote(self.price(sigma + bump), self.price(sigma - bump), bump, quote)

    def rho(self, sigma: float, bump: float = 1e-4,
            quote: GreekQuote = "pl_per_bump") -> float:
        return self._fd_attribute(sigma, "rate", bump, quote)

    def dividend_sensitivity(self, sigma: float, bump: float = 1e-4,
                             quote: GreekQuote = "pl_per_bump") -> float:
        return self._fd_attribute(sigma, "dividend", bump, quote)

    def theta_one_day(self, sigma: float) -> float:
        if self.maturity_days <= 1:
            raise ValueError("maturity_days must be greater than one.")
        tomorrow = replace(self, maturity_days=self.maturity_days - 1)
        return float(tomorrow.price(sigma) - self.price(sigma))

    def shocked_copy(self, spot_shock: float = 0.0, rate_shock: float = 0.0,
                     dividend_shock: float = 0.0, maturity_day_shock: float = 0.0,
                     shock_type: ShockType = "absolute") -> "EquityOption":
        if shock_type == "absolute":
            spot = self.spot + spot_shock
            rate = self.rate + rate_shock
            dividend = self.dividend + dividend_shock
        elif shock_type == "relative":
            spot = self.spot * (1 + spot_shock)
            rate = self.rate * (1 + rate_shock)
            dividend = self.dividend * (1 + dividend_shock)
        else:
            raise ValueError("Unsupported shock_type.")
        return replace(self, spot=spot, rate=rate, dividend=dividend,
                       maturity_days=self.maturity_days + maturity_day_shock)

    def full_revaluation(self, sigma_base: float, sigma_shocked: float | None = None,
                         spot_shock: float = 0.0, rate_shock: float = 0.0,
                         dividend_shock: float = 0.0, maturity_day_shock: float = 0.0,
                         shock_type: ShockType = "absolute") -> dict[str, float]:
        shocked = self.shocked_copy(spot_shock, rate_shock, dividend_shock,
                                    maturity_day_shock, shock_type)
        sigma_new = sigma_base if sigma_shocked is None else sigma_shocked
        pv0, pv1 = self.price(sigma_base), shocked.price(sigma_new)
        return {"pv_base": pv0, "pv_shocked": pv1, "pl": pv1-pv0,
                "spot_shocked": shocked.spot, "moneyness_shocked": shocked.moneyness,
                "sigma_base": sigma_base, "sigma_shocked": sigma_new}
