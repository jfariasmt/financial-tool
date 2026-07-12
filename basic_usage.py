import pandas as pd
from equity_option_engine import EquityOption, VolatilitySurface

surface_df = pd.DataFrame({30:[0.25,0.23,0.22,0.21],180:[0.24,0.22,0.21,0.20],365:[0.23,0.21,0.20,0.19]},
                          index=[80.0,100.0,110.0,120.0])
surface = VolatilitySurface(surface_df, axis_type="moneyness",
                            smile_method="cubic", time_method="v2t",
                            extrapolation="flat")
option = EquityOption(spot=100, strike=105, rate=0.04, dividend=0.01,
                      maturity_days=180, notional=1_000_000, option_type="call")
sigma = surface.volatility(option.moneyness, option.maturity_days)
print("Sigma:", sigma)
print("Price:", option.price(sigma))
print("Delta:", option.delta(sigma))
print("Gamma:", option.gamma(sigma))
print("Vega +1 vol point:", option.vega(sigma, 0.01, "pl_per_bump"))
print(surface.transform([85,95,100,105,115],[45,90,270]).values)
