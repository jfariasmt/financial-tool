# Equity Option Engine

Modular Python package for equity-option pricing, finite-difference Greeks, volatility-surface interpolation, surface transformation, and full-revaluation scenarios.

## Main classes

### `VolatilitySurface`

Internal grid:

- rows: strike or moneyness;
- columns: maturity day counts;
- values: volatility in decimal form (`0.18 = 18%`).

Methods:

- smile interpolation: `linear`, `cubic`, `pchip`;
- time interpolation: `linear_vol`, `linear_variance`, `v2t`;
- extrapolation: `flat`, `linear`;
- `transform()` to a new strike/moneyness and maturity grid;
- `to_strike_surface()` and `to_moneyness_surface()`;
- `apply_shocks()` for additive or multiplicative shocks.

### `EquityOption`

European option priced with the Black forward formula. Volatility is passed explicitly to `price()` and Greek methods, making direct sigma shocks and shocked-surface revaluation straightforward.

## Install and test

```bash
python -m pip install -e ".[dev]"
pytest
```

## Example

```python
import pandas as pd
from equity_option_engine import EquityOption, VolatilitySurface

surface_df = pd.DataFrame(
    {
        30: [0.24, 0.22, 0.21],
        180: [0.23, 0.21, 0.20],
        365: [0.22, 0.20, 0.19],
    },
    index=[80.0, 100.0, 120.0],
)

surface = VolatilitySurface(
    values=surface_df,
    axis_type="moneyness",
    smile_method="cubic",
    time_method="v2t",
    extrapolation="flat",
)

option = EquityOption(
    spot=100.0,
    strike=105.0,
    rate=0.04,
    dividend=0.01,
    maturity_days=180,
    notional=1_000_000,
    option_type="call",
)

sigma = surface.volatility(option.moneyness, option.maturity_days)
print(option.price(sigma))
print(option.delta(sigma))
print(option.vega(sigma, bump=0.01, quote="pl_per_bump"))
```
