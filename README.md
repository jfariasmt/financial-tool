# financial-tool

Librería Python para ingeniería financiera, valorización y riesgo de mercado.

## Objetivo

Construir un motor modular para:

- Curvas de tasas y factores de descuento
- Bonos y derivados de renta fija
- FX forwards y FX swaps
- Opciones
- Crédito
- Sensibilidades y VaR
- RTPL / Market Risk analytics

## Estructura inicial

```text
financial_tool/
├── core/          # Fechas, day count, calendarios, convenciones
├── curves/        # Curvas de descuento, zero rates, interpolación
├── instruments/   # Bonos, FX forwards, swaps, opciones
├── marketdata/    # Contenedores de datos de mercado
├── risk/          # Sensibilidades, VaR, stress, RTPL
└── utils/         # Funciones auxiliares

tests/             # Pruebas unitarias
examples/          # Ejemplos de uso
```

## Instalación local

```bash
pip install -e .
```

## Primer ejemplo

```python
from datetime import date
from financial_tool.curves.discount_curve import DiscountCurve

curve = DiscountCurve(
    valuation_date=date(2026, 1, 1),
    pillars=[date(2027, 1, 1), date(2028, 1, 1)],
    discount_factors=[0.95, 0.90],
)

print(curve.df(date(2027, 6, 30)))
```
