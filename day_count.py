from __future__ import annotations

from datetime import date


def year_fraction(start: date, end: date, convention: str = "ACT/365") -> float:
    """Return year fraction between two dates.

    Supported conventions:
    - ACT/365
    - ACT/360
    - 30/360
    """
    convention = convention.upper()

    if end < start:
        raise ValueError("end date must be greater than or equal to start date")

    if convention == "ACT/365":
        return (end - start).days / 365.0

    if convention == "ACT/360":
        return (end - start).days / 360.0

    if convention == "30/360":
        d1 = min(start.day, 30)
        d2 = min(end.day, 30)
        return ((end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)) / 360.0

    raise ValueError(f"Unsupported day count convention: {convention}")
