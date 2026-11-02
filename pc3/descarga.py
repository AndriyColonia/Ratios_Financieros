"""Descarga de estados financieros desde Yahoo Finanzas (librería yfinance).

Por cada empresa arma una tabla partidas × periodos (2022-2026) en millones de USD:
- 2022-2025: estados anuales (año fiscal, nombrado por el año en que cierra).
- 2026: si la empresa ya cerró su año fiscal 2026 se usa ese; si no, se arma el
  TTM (últimos 12 meses = suma de los 4 últimos trimestres) y el balance del
  último trimestre publicado. Con --modo-2026 ttm se fuerza siempre el TTM.
"""
from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from . import config


def etiqueta_periodo(fecha) -> int:
    fecha = pd.Timestamp(fecha)
    return fecha.year - 1 if fecha.month <= config.MES_CORTE_ANIO_ANTERIOR else fecha.year


def _valor(frame: pd.DataFrame | None, etiqueta: str, columna) -> float:
    if frame is None or frame.empty or etiqueta not in frame.index or columna not in frame.columns:
        return math.nan
    v = frame.loc[etiqueta, columna]
    if isinstance(v, pd.Series):  # índice duplicado
        v = v.dropna()
        v = v.iloc[0] if len(v) else math.nan
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


def _extraer(frames: dict, columnas: dict) -> dict:
    """frames: estado -> DataFrame; columnas: estado -> columna a leer.
    Devuelve clave -> valor en unidades de la moneda original."""
    out = {}
    for clave, (_, candidatos) in config.PARTIDAS.items():
        valor = math.nan
        for estado, etiqueta in candidatos:
            col = columnas.get(estado)
            if col is None:
                continue
            valor = _valor(frames.get(estado), etiqueta, col)
            if not math.isnan(valor):
                break
        out[clave] = valor
    return out


def _ttm_desde_trimestres(trim: pd.DataFrame | None) -> tuple[pd.DataFrame | None, object]:
    """Suma los 4 últimos trimestres (deben ser consecutivos)."""
    if trim is None or trim.empty:
        return None, None
    cols = sorted(trim.columns, reverse=True)[:4]
    if len(cols) < 4 or (pd.Timestamp(cols[0]) - pd.Timestamp(cols[3])).days > 300:
        return None, None
    suma = trim[cols].sum(axis=1, min_count=4)
    return suma.to_frame(name=cols[0]), cols[0]


def construir_tabla(anual: dict, trimestral: dict, ttm: dict | None = None,
                    modo_2026: str = "auto") -> tuple[dict, list, list]:
    """Arma {periodo: {clave: valor}} a partir de los DataFrames de yfinance.

    anual / trimestral: {"resultados", "balance", "flujo"} -> DataFrame (filas =
    partidas de Yahoo, columnas = fechas de cierre). ttm: {"resultados", "flujo"}
    opcional (si no viene se suma los trimestres).
    Devuelve (datos, info, avisos).
    """
    datos, info, avisos = {}, [], []

    def a_fecha(c):
        try:
            return pd.Timestamp(c)
        except (TypeError, ValueError):
            return c

    def norm(f):
        return None if f is None or f.empty else f.rename(columns=a_fecha)

    anual = {e: norm(anual.get(e)) for e in ("resultados", "balance", "flujo")}
    trimestral = {e: norm(trimestral.get(e)) for e in ("resultados", "balance", "flujo")}

    # --- Anuales -----------------------------------------------------------
    fechas = set()
    for f in anual.values():
        if f is not None:
            fechas.update(f.columns)
    por_periodo = {}
    for fecha in sorted(fechas):  # la más reciente gana si dos caen en el mismo periodo
        por_periodo[etiqueta_periodo(fecha)] = fecha
    ultima_fecha_anual = max(fechas) if fechas else None

    for periodo, fecha in sorted(por_periodo.items()):
        if periodo not in config.PERIODOS:
            continue
        if periodo == config.ANIO_TTM and modo_2026 == "ttm":
            continue
        cols = {e: (fecha if f is not None and fecha in f.columns else None) for e, f in anual.items()}
        datos[periodo] = _extraer(anual, cols)
        info.append(dict(periodo=periodo, fecha_cierre=fecha.date().isoformat(), tipo="Anual"))

    # --- 2026 como TTM -------------------------------------------------------
    if config.ANIO_TTM not in datos:
        ttm = ttm or {}
        frames, cols = {}, {}
        for estado in ("resultados", "flujo"):
            f = norm(ttm.get(estado))
            if f is not None:
                col = max(f.columns)
            else:
                f, col = _ttm_desde_trimestres(trimestral[estado])
            frames[estado], cols[estado] = f, col
        bal = trimestral["balance"]
        if bal is not None:
            frames["balance"], cols["balance"] = bal, max(bal.columns)
        fecha_ttm = next((c for c in (cols.get("resultados"), cols.get("balance"))
                          if isinstance(c, pd.Timestamp)), None)
        if fecha_ttm is None:
            avisos.append(f"{config.ANIO_TTM}: no hay trimestres para armar el TTM.")
        elif ultima_fecha_anual is not None and pd.Timestamp(fecha_ttm) <= ultima_fecha_anual:
            avisos.append(f"{config.ANIO_TTM}: el último trimestre ({pd.Timestamp(fecha_ttm).date()}) "
                          f"coincide con el último año cerrado; no hay datos nuevos para el TTM.")
        else:
            datos[config.ANIO_TTM] = _extraer(frames, cols)
            info.append(dict(periodo=config.ANIO_TTM, fecha_cierre=pd.Timestamp(fecha_ttm).date().isoformat(),
                             tipo="TTM (últimos 12 meses)"))

    for p in config.PERIODOS:
        if p not in datos:
            avisos.append(f"{p}: Yahoo no entregó este periodo; complétalo en datos/ajustes_manuales.xlsx.")
    return datos, info, avisos


def _tipo_cambio(moneda: str, fecha: str, periodo: int) -> tuple[float, str]:
    if moneda == "USD":
        return 1.0, "USD"
    try:
        import yfinance as yf
        f = pd.Timestamp(fecha)
        h = yf.Ticker(f"{moneda}USD=X").history(start=f - dt.timedelta(days=7), end=f + dt.timedelta(days=2))
        if not h.empty:
            return float(h["Close"].iloc[-1]), "Yahoo"
    except Exception:  # noqa: BLE001 - sin red o sin dato: usamos respaldo
        pass
    return config.TIPO_CAMBIO_RESPALDO.get(moneda, {}).get(periodo, math.nan), "respaldo (config.py)"


def descargar_empresa(ticker: str, modo_2026: str = "auto") -> tuple[pd.DataFrame, list, list]:
    """Descarga una empresa. Devuelve (tabla partidas×periodos en M USD, info, avisos)."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    anual = {"resultados": t.income_stmt, "balance": t.balance_sheet, "flujo": t.cashflow}
    trimestral = {"resultados": t.quarterly_income_stmt, "balance": t.quarterly_balance_sheet,
                  "flujo": t.quarterly_cashflow}
    ttm = {}
    for estado, attr in (("resultados", "ttm_income_stmt"), ("flujo", "ttm_cashflow")):
        try:
            ttm[estado] = getattr(t, attr)
        except Exception:  # noqa: BLE001 - versiones antiguas de yfinance
            ttm[estado] = None

    if all(f is None or f.empty for f in anual.values()):
        raise RuntimeError(f"Yahoo no devolvió estados financieros para {ticker} "
                           "(¿sin internet o Yahoo bloqueado?).")

    datos, info, avisos = construir_tabla(anual, trimestral, ttm, modo_2026)

    moneda = config.MONEDA_FINANCIERA.get(ticker, "USD")
    try:
        moneda = t.info.get("financialCurrency") or moneda
    except Exception:  # noqa: BLE001
        pass

    for fila in info:
        fx, fuente_fx = _tipo_cambio(moneda, fila["fecha_cierre"], fila["periodo"])
        fila.update(moneda_original=moneda, tipo_cambio_usd=fx, fuente_tipo_cambio=fuente_fx)
        if moneda != "USD":
            avisos.append(f"{fila['periodo']}: convertido de {moneda} a USD con {fx:.4f} ({fuente_fx}).")
        datos[fila["periodo"]] = {k: v * fx / 1e6 for k, v in datos[fila["periodo"]].items()}

    tabla = pd.DataFrame(datos).reindex(index=list(config.PARTIDAS), columns=config.PERIODOS)
    return tabla, info, avisos


def descargar_todas(tickers=None, modo_2026: str = "auto"):
    tickers = tickers or list(config.EMPRESAS)
    tablas, info, avisos = {}, [], []
    for tk in tickers:
        print(f"  Descargando {tk} ({config.EMPRESAS.get(tk, tk)})...", flush=True)
        try:
            tabla, inf, av = descargar_empresa(tk, modo_2026)
        except Exception as e:  # noqa: BLE001
            print(f"    ERROR: {e}")
            avisos.append(dict(ticker=tk, aviso=f"No se pudo descargar: {e}"))
            continue
        tablas[tk] = tabla
        info += [dict(ticker=tk, **f) for f in inf]
        avisos += [dict(ticker=tk, aviso=a) for a in av]
        for a in av:
            print(f"    aviso: {a}")
    return tablas, info, avisos
