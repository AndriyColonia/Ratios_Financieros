"""Lectura y escritura de los datos base en Excel.

- datos/estados_financieros.xlsx : lo que bajó de Yahoo (se reescribe al descargar).
- datos/ajustes_manuales.xlsx    : misma forma, vacía. Lo que el equipo escriba aquí
  REEMPLAZA al dato de Yahoo (para corregir con el 10-K o completar años faltantes).
  Nunca se sobrescribe al descargar.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config

RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ / "datos"
ARCH_ESTADOS = DIR_DATOS / "estados_financieros.xlsx"
ARCH_AJUSTES = DIR_DATOS / "ajustes_manuales.xlsx"
ARCH_PROFESOR = DIR_DATOS / "tabla_profesor.csv"

HOJA_INFO = "_info"
HOJA_AVISOS = "_avisos"


def _hoja_empresa(tabla: pd.DataFrame) -> pd.DataFrame:
    df = tabla.reindex(index=list(config.PARTIDAS), columns=config.PERIODOS).copy()
    df.insert(0, "partida", [config.PARTIDAS[k][0] for k in df.index])
    df.index.name = "clave"
    return df.reset_index()


def _ajustar_columnas(writer):
    for ws in writer.book.worksheets:
        for col in ws.columns:
            largo = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(10, largo + 2), 60)
        ws.freeze_panes = "C2" if ws.title in config.EMPRESAS else "A2"


def guardar_estados(tablas: dict, info: list, avisos: list, ruta: Path | None = None):
    ruta = ruta or ARCH_ESTADOS
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ruta, engine="openpyxl") as w:
        for tk, tabla in tablas.items():
            hoja = _hoja_empresa(tabla)
            hoja.to_excel(w, sheet_name=tk, index=False)
            ws = w.sheets[tk]
            for fila in ws.iter_rows(min_row=2, min_col=3):
                for c in fila:
                    c.number_format = "#,##0.00"
        pd.DataFrame(info).to_excel(w, sheet_name=HOJA_INFO, index=False)
        pd.DataFrame(avisos, columns=["ticker", "aviso"]).to_excel(w, sheet_name=HOJA_AVISOS, index=False)
        _ajustar_columnas(w)


def crear_plantilla_ajustes(ruta: Path | None = None, forzar: bool = False) -> bool:
    """Crea la plantilla vacía de ajustes. No la toca si ya existe (salvo forzar)."""
    ruta = ruta or ARCH_AJUSTES
    if ruta.exists() and not forzar:
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    vacia = pd.DataFrame(index=list(config.PARTIDAS), columns=config.PERIODOS, dtype=float)
    with pd.ExcelWriter(ruta, engine="openpyxl") as w:
        pd.DataFrame({"instrucciones": [
            "Escribe SOLO las celdas que quieras corregir o completar (millones de USD).",
            "Lo que escribas aquí reemplaza al dato de Yahoo Finanzas en el cálculo.",
            "Deja en blanco lo demás. 2026 = TTM (últimos 12 meses) o último año fiscal cerrado.",
            "Partidas de balance: saldo al cierre del periodo. Resultados y flujo: acumulado del periodo.",
            "Fuente sugerida: 10-K / 10-Q de cada empresa (SEC EDGAR) o el PDF del grupo.",
        ]}).to_excel(w, sheet_name="LEEME", index=False)
        for tk in config.EMPRESAS:
            _hoja_empresa(vacia).to_excel(w, sheet_name=tk, index=False)
        _ajustar_columnas(w)
    return True


def _leer_hojas(ruta: Path) -> dict:
    if not ruta.exists():
        return {}
    hojas = pd.read_excel(ruta, sheet_name=None)
    out = {}
    for nombre, df in hojas.items():
        if nombre not in config.EMPRESAS or "clave" not in df.columns:
            continue
        df = df.set_index("clave").drop(columns=["partida"], errors="ignore")
        df.columns = [int(c) for c in df.columns]
        out[nombre] = df.apply(pd.to_numeric, errors="coerce")
    return out


def leer_info(ruta: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    ruta = ruta or ARCH_ESTADOS
    if not ruta.exists():
        return pd.DataFrame(), pd.DataFrame()
    hojas = pd.read_excel(ruta, sheet_name=None)
    return hojas.get(HOJA_INFO, pd.DataFrame()), hojas.get(HOJA_AVISOS, pd.DataFrame())


def cargar_datos(ruta_estados: Path | None = None, ruta_ajustes: Path | None = None):
    """Combina Yahoo + ajustes manuales. Devuelve ({ticker: tabla}, lista de celdas ajustadas)."""
    ruta_estados, ruta_ajustes = ruta_estados or ARCH_ESTADOS, ruta_ajustes or ARCH_AJUSTES
    base = _leer_hojas(ruta_estados)
    ajustes = _leer_hojas(ruta_ajustes)
    tablas, celdas_ajustadas = {}, []
    for tk in config.EMPRESAS:
        tabla = base.get(tk, pd.DataFrame(index=list(config.PARTIDAS), columns=config.PERIODOS, dtype=float))
        tabla = tabla.reindex(index=list(config.PARTIDAS), columns=config.PERIODOS).astype(float)
        aj = ajustes.get(tk)
        if aj is not None:
            aj = aj.reindex(index=list(config.PARTIDAS), columns=config.PERIODOS)
            for clave in aj.index:
                for p in aj.columns:
                    v = aj.at[clave, p]
                    if pd.notna(v):
                        tabla.at[clave, p] = float(v)
                        celdas_ajustadas.append(dict(ticker=tk, partida=config.PARTIDAS[clave][0],
                                                     periodo=p, valor=float(v)))
        if tabla.notna().any().any():
            tablas[tk] = tabla
    return tablas, celdas_ajustadas


def leer_tabla_profesor(ruta: Path | None = None) -> pd.DataFrame | None:
    """CSV opcional con sector y líder oficiales: ratio,periodo,sector,lider_empresa,lider_valor."""
    ruta = ruta or ARCH_PROFESOR
    if not ruta.exists():
        return None
    df = pd.read_csv(ruta, comment="#")
    df["periodo"] = df["periodo"].astype(int)
    return df
