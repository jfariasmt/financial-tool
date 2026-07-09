from datetime import date

from financial_tool.curves.discount_curve import DiscountCurve

curve = DiscountCurve(
    valuation_date=date(2026, 1, 1),
    pillars=[date(2027, 1, 1), date(2028, 1, 1), date(2029, 1, 1)],
    discount_factors=[0.96, 0.92, 0.88],
    interpolation="linear_zc",
)

print("DF 2027-06-30:", curve.df(date(2027, 6, 30)))
print("Zero 2027-06-30:", curve.zero_rate(date(2027, 6, 30)))
