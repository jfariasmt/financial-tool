from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline, PchipInterpolator, interp1d

SmileMethod = Literal["linear", "cubic", "pchip"]
TimeMethod = Literal["linear_vol", "linear_variance", "v2t"]
Extrapolation = Literal["flat", "linear"]
AxisType = Literal["strike", "moneyness"]


@dataclass(frozen=True)
class VolatilitySurface:
    values: pd.DataFrame
    axis_type: AxisType = "strike"
    smile_method: SmileMethod = "linear"
    time_method: TimeMethod = "linear_vol"
    extrapolation: Extrapolation = "flat"

    def __post_init__(self) -> None:
        cleaned = self._validate_and_clean(self.values)
        object.__setattr__(self, "values", cleaned)
        if self.axis_type not in {"strike", "moneyness"}:
            raise ValueError("axis_type must be 'strike' or 'moneyness'.")
        if self.smile_method not in {"linear", "cubic", "pchip"}:
            raise ValueError("Unsupported smile_method.")
        if self.time_method not in {"linear_vol", "linear_variance", "v2t"}:
            raise ValueError("Unsupported time_method.")
        if self.extrapolation not in {"flat", "linear"}:
            raise ValueError("Unsupported extrapolation.")

    @staticmethod
    def _validate_and_clean(values: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(values, pd.DataFrame) or values.empty:
            raise ValueError("values must be a non-empty DataFrame.")
        surface = values.copy()
        surface.index = pd.to_numeric(surface.index, errors="raise")
        surface.columns = pd.to_numeric(surface.columns, errors="raise")
        surface = surface.astype(float).sort_index()
        surface = surface.reindex(sorted(surface.columns), axis=1)
        if surface.isna().any().any():
            raise ValueError("Surface contains NaN values.")
        if (surface <= 0).any().any():
            raise ValueError("Volatilities must be positive.")
        if surface.index.duplicated().any() or surface.columns.duplicated().any():
            raise ValueError("Duplicate grid nodes found.")
        if len(surface.index) < 2:
            raise ValueError("At least two smile nodes are required.")
        return surface

    @property
    def x_nodes(self) -> np.ndarray:
        return self.values.index.to_numpy(dtype=float)

    @property
    def maturity_nodes(self) -> np.ndarray:
        return self.values.columns.to_numpy(dtype=float)

    def _smile_interpolator(self, x_nodes: np.ndarray, vols: np.ndarray):
        if self.smile_method == "linear":
            fill = (vols[0], vols[-1]) if self.extrapolation == "flat" else "extrapolate"
            return interp1d(x_nodes, vols, kind="linear", bounds_error=False,
                            fill_value=fill, assume_sorted=True)
        if self.smile_method == "cubic":
            spline = CubicSpline(x_nodes, vols, bc_type="natural", extrapolate=True)
        else:
            spline = PchipInterpolator(x_nodes, vols, extrapolate=True)
        if self.extrapolation == "linear":
            return spline
        def flat_wrapper(x):
            arr = np.asarray(x, dtype=float)
            result = spline(np.clip(arr, x_nodes[0], x_nodes[-1]))
            return float(result) if np.ndim(x) == 0 else np.asarray(result, dtype=float)
        return flat_wrapper

    def smile_values(self, x: float | Iterable[float]) -> np.ndarray:
        x_array = np.atleast_1d(np.asarray(x, dtype=float))
        output = np.empty((len(x_array), len(self.maturity_nodes)))
        for j, maturity in enumerate(self.values.columns):
            vols = self.values[maturity].to_numpy(dtype=float)
            output[:, j] = self._smile_interpolator(self.x_nodes, vols)(x_array)
        return output

    def _time_interpolate_row(self, vols: np.ndarray, targets: np.ndarray) -> np.ndarray:
        source_t = self.maturity_nodes
        targets = np.asarray(targets, dtype=float)
        if np.any(targets <= 0):
            raise ValueError("Maturities must be positive.")
        if len(source_t) == 1:
            return np.full_like(targets, vols[0], dtype=float)
        if self.time_method == "linear_vol":
            return np.interp(targets, source_t, vols, left=vols[0], right=vols[-1])
        if self.time_method == "linear_variance":
            var = vols**2
            out = np.interp(targets, source_t, var, left=var[0], right=var[-1])
            return np.sqrt(np.maximum(out, 0.0))
        vt = vols**2 * source_t
        out = np.interp(targets, source_t, vt, left=vt[0], right=vt[-1])
        return np.sqrt(np.maximum(out / targets, 0.0))

    def volatility(self, x: float, maturity_days: float) -> float:
        smile = self.smile_values([x])[0]
        return float(self._time_interpolate_row(smile, np.array([maturity_days]))[0])

    def transform(self, target_x: Iterable[float], target_maturities: Iterable[float]) -> "VolatilitySurface":
        x_target = np.sort(np.asarray(list(target_x), dtype=float))
        t_target = np.sort(np.asarray(list(target_maturities), dtype=float))
        if len(x_target) == 0 or len(t_target) == 0:
            raise ValueError("Target grids cannot be empty.")
        smiles = self.smile_values(x_target)
        transformed = np.vstack([self._time_interpolate_row(row, t_target) for row in smiles])
        df = pd.DataFrame(transformed, index=x_target, columns=t_target)
        return VolatilitySurface(df, self.axis_type, self.smile_method,
                                 self.time_method, self.extrapolation)

    def to_strike_surface(self, spot: float, target_maturities: Iterable[float] | None = None) -> "VolatilitySurface":
        if self.axis_type != "moneyness":
            raise ValueError("Requires a moneyness surface.")
        if spot <= 0:
            raise ValueError("spot must be positive.")
        maturities = self.maturity_nodes if target_maturities is None else list(target_maturities)
        transformed = self.transform(self.x_nodes, maturities)
        df = transformed.values.copy()
        df.index = transformed.x_nodes / 100.0 * spot
        return VolatilitySurface(df, "strike", self.smile_method,
                                 self.time_method, self.extrapolation)

    def to_moneyness_surface(self, spot: float, target_maturities: Iterable[float] | None = None) -> "VolatilitySurface":
        if self.axis_type != "strike":
            raise ValueError("Requires a strike surface.")
        if spot <= 0:
            raise ValueError("spot must be positive.")
        maturities = self.maturity_nodes if target_maturities is None else list(target_maturities)
        transformed = self.transform(self.x_nodes, maturities)
        df = transformed.values.copy()
        df.index = transformed.x_nodes / spot * 100.0
        return VolatilitySurface(df, "moneyness", self.smile_method,
                                 self.time_method, self.extrapolation)

    def apply_shocks(self, shocks: pd.DataFrame,
                     mode: Literal["additive", "multiplicative"] = "additive") -> "VolatilitySurface":
        aligned = shocks.reindex(index=self.values.index, columns=self.values.columns)
        if aligned.isna().any().any():
            raise ValueError("Transform shocks to the surface grid first.")
        shifted = self.values + aligned if mode == "additive" else self.values * (1.0 + aligned)
        if mode not in {"additive", "multiplicative"}:
            raise ValueError("Unsupported shock mode.")
        return VolatilitySurface(shifted, self.axis_type, self.smile_method,
                                 self.time_method, self.extrapolation)
