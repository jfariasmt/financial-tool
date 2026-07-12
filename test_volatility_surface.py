import numpy as np
import pandas as pd
from equity_option_engine import VolatilitySurface

def surface():
    return VolatilitySurface(pd.DataFrame({30:[0.24,0.20,0.18],180:[0.23,0.19,0.17],365:[0.22,0.18,0.16]},
                                          index=[80.0,100.0,120.0]),
                             axis_type="moneyness", smile_method="linear",
                             time_method="linear_vol", extrapolation="flat")

def test_exact_node():
    assert np.isclose(surface().volatility(100,180), 0.19)

def test_flat_extrapolation():
    s=surface()
    assert np.isclose(s.volatility(50,180),0.23)
    assert np.isclose(s.volatility(150,180),0.17)

def test_transform_shape():
    assert surface().transform([90,100,110],[45,90]).values.shape == (3,2)
