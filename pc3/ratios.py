"""Cálculo de los 14 ratios del curso (+ prueba ácida y componentes DuPont).

Convenciones (igual que en clase):
- Saldos de balance en días, ROA, ROE y DuPont: PROMEDIO entre el cierre del
  periodo y el del periodo anterior. Si falta el anterior se usa el saldo de
  cierre y queda anotado.
- EBITDA = Utilidad operativa + Depreciación y amortización.
- "n.s." (no significativo): Deuda/EBITDA con EBITDA <= 0, o ROE / endeudamiento
  con patrimonio <= 0.
- Márgenes, ROA y ROE en %.
"""
from __future__ import annotations

import math

import pandas as pd

from . import config


def _v(tabla: pd.DataFrame, clave: str, periodo: int) -> float:
    if periodo not in tabla.columns:
        return math.nan
    v = tabla.at[clave, periodo]
    return float(v) if pd.notna(v) else math.nan


def _div(a: float, b: float) -> float:
    if math.isnan(a) or math.isnan(b) or b == 0:
        return math.nan
    return a / b


def calcular_empresa(tabla: pd.DataFrame, periodos=None):
    """Devuelve (valores: DataFrame periodo×ratio, ns: set de (periodo, ratio), notas: list)."""
    periodos = periodos or config.PERIODOS
    filas, ns, notas = {}, set(), []

    for p in periodos:
        v = lambda k: _v(tabla, k, p)  # noqa: E731

        def prom(k):
            actual, previo = _v(tabla, k, p), _v(tabla, k, p - 1)
            if math.isnan(actual):
                return math.nan
            if math.isnan(previo):
                notas.append(f"{p}: {config.PARTIDAS[k][0]} promedio no disponible "
                             f"(falta {p - 1}); se usó el saldo de cierre.")
                return actual
            return (actual + previo) / 2

        ventas, costo = v("ventas"), v("costo_ventas")
        ac, pc, inv = v("activo_corriente"), v("pasivo_corriente"), v("inventario")
        u_op, u_neta, da = v("utilidad_operativa"), v("utilidad_neta"), v("dep_amort")
        if math.isnan(costo) and not math.isnan(ventas) and not math.isnan(v("utilidad_bruta")):
            costo = ventas - v("utilidad_bruta")
        ebitda = u_op + (0.0 if math.isnan(da) else da)
        if math.isnan(da) and not math.isnan(u_op):
            notas.append(f"{p}: sin depreciación y amortización; EBITDA = utilidad operativa.")

        r = {}
        r["liquidez_corriente"] = _div(ac, pc)
        r["prueba_acida"] = _div(ac - (0.0 if math.isnan(inv) else inv), pc)
        r["capital_trabajo"] = ac - pc

        pat_total = v("patrimonio_total")
        if math.isnan(pat_total):
            pat_total = v("patrimonio")
        if not math.isnan(pat_total) and pat_total <= 0:
            r["endeudamiento"] = math.nan
            ns.add((p, "endeudamiento"))
        else:
            r["endeudamiento"] = _div(v("pasivo_total"), pat_total)

        deuda = v("deuda_financiera")
        if not math.isnan(ebitda) and ebitda <= 0:
            r["cobertura_deuda"] = math.nan
            ns.add((p, "cobertura_deuda"))
        else:
            r["cobertura_deuda"] = _div(deuda, ebitda)

        costo_dia, venta_dia = _div(costo, 365), _div(ventas, 365)
        r["dias_inventario"] = _div(prom("inventario"), costo_dia)
        r["dias_cobro"] = _div(prom("cuentas_por_cobrar"), venta_dia)
        r["dias_pago"] = _div(prom("cuentas_por_pagar"), costo_dia)
        r["ciclo_efectivo"] = r["dias_inventario"] + r["dias_cobro"] - r["dias_pago"]

        r["margen_bruto"] = _div(ventas - costo, ventas) * 100
        r["margen_operativo"] = _div(u_op, ventas) * 100
        r["margen_neto"] = _div(u_neta, ventas) * 100
        r["margen_ebitda"] = _div(ebitda, ventas) * 100

        activo_prom, pat_prom = prom("activo_total"), prom("patrimonio")
        r["roa"] = _div(u_neta, activo_prom) * 100
        if not math.isnan(pat_prom) and pat_prom <= 0:
            r["roe"] = math.nan
            ns.add((p, "roe"))
        else:
            r["roe"] = _div(u_neta, pat_prom) * 100

        # DuPont
        r["rotacion_activos"] = _div(ventas, activo_prom)
        r["apalancamiento"] = _div(activo_prom, pat_prom) if (math.isnan(pat_prom) or pat_prom > 0) else math.nan
        r["roe_dupont"] = r["margen_neto"] / 100 * r["rotacion_activos"] * r["apalancamiento"] * 100

        filas[p] = r

    # sin duplicar notas
    notas = list(dict.fromkeys(notas))
    return pd.DataFrame(filas).T.rename_axis("periodo"), ns, notas


def calcular_todas(tablas: dict, periodos=None):
    """Devuelve (DataFrame largo con columnas ticker, periodo, ratio, valor, ns), notas por ticker."""
    registros, notas = [], {}
    for tk, tabla in tablas.items():
        valores, ns, nt = calcular_empresa(tabla, periodos)
        notas[tk] = nt
        for p, fila in valores.iterrows():
            for ratio, valor in fila.items():
                registros.append(dict(ticker=tk, periodo=int(p), ratio=ratio,
                                      valor=valor, ns=(p, ratio) in ns))
    return pd.DataFrame(registros), notas
