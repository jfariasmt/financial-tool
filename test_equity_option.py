import numpy as np
from equity_option_engine import EquityOption

def option():
    return EquityOption(100,100,0.03,0.01,365,1.0,"call")

def test_price_positive():
    assert option().price(0.20) > 0

def test_delta_reasonable():
    assert 0 < option().delta(0.20) < 1

def test_vega_positive():
    assert option().vega(0.20, 0.01, "derivative") > 0

def test_full_revaluation_changes_pv():
    r = option().full_revaluation(0.20, 0.21, spot_shock=0.05, shock_type="relative")
    assert r["pv_shocked"] != r["pv_base"]
