"""Noticias que respaldan la lectura de cada ratio (ventana del 2026 TTM).

Dos fuentes:
- Automática: noticias de la empresa foco en Yahoo Finanzas (yfinance). Se asignan a cada ratio por
  palabras clave; es una coincidencia automática, no una validación: léanlas antes de usarlas.
- Manual: datos/noticias_manuales.csv. Lo que el equipo escribe ahí tiene prioridad y, si trae la
  columna ratio, se muestra siempre en ese ratio.

Columnas de ambos CSV: ticker, ratio, fecha (AAAA-MM-DD), titular, fuente, extracto, url
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd

from . import config, datos

COLUMNAS = ["ticker", "ratio", "fecha", "titular", "fuente", "extracto", "url"]
MAX_EXTRACTO = 300
MAX_POR_RATIO = 2


def ruta_auto() -> Path:
    return datos.DIR_DATOS / "noticias_yahoo.csv"


def ruta_manual() -> Path:
    return datos.DIR_DATOS / "noticias_manuales.csv"


# Palabras clave por ratio (las noticias de Yahoo están en inglés; se incluyen ambos idiomas)
CLAVES = {
    "liquidez_corriente": ["liquidity", "cash", "working capital", "credit facility", "funding", "raise",
                           "investment", "stake", "equity", "liquidez", "caja", "inversión"],
    "prueba_acida": ["liquidity", "cash", "working capital", "credit facility", "funding", "liquidez", "caja"],
    "capital_trabajo": ["working capital", "cash", "liquidity", "funding", "capital de trabajo", "caja"],
    "endeudamiento": ["debt", "bond", "notes", "loan", "borrow", "credit rating", "downgrade", "leverage",
                      "deuda", "bonos", "préstamo", "calificación"],
    "cobertura_deuda": ["debt", "bond", "notes", "loan", "borrow", "credit rating", "downgrade", "leverage",
                        "ebitda", "deuda", "bonos", "préstamo"],
    "dias_inventario": ["inventory", "write-down", "writedown", "stockpile", "oversupply", "excess supply",
                        "supply", "inventario", "existencias"],
    "dias_cobro": ["receivable", "collections", "customers", "payment terms", "cobranza", "clientes"],
    "dias_pago": ["supplier", "suppliers", "payable", "vendor", "payment terms", "proveedores"],
    "ciclo_efectivo": ["inventory", "receivable", "supplier", "supply chain", "payment terms", "inventario"],
    "margen_bruto": ["gross margin", "margin", "pricing", "yield", "wafer", "foundry", "cost of", "18a",
                     "margen bruto"],
    "margen_operativo": ["operating loss", "operating income", "restructuring", "layoff", "job cuts",
                         "headcount", "opex", "operating expenses", "impairment", "r&d", "margen operativo"],
    "margen_neto": ["net loss", "net income", "profit", "earnings", "loss", "impairment", "tax",
                    "pérdida", "utilidad"],
    "margen_ebitda": ["ebitda", "operating", "depreciation", "capex", "capital expenditure"],
    "roa": ["net loss", "net income", "assets", "impairment", "profit", "return on assets", "capex"],
    "roe": ["net loss", "net income", "shareholder", "equity", "return on equity", "buyback", "dividend"],
}


# ---------------------------------------------------------------------------
# Descarga (Yahoo)
# ---------------------------------------------------------------------------
def _texto(x) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(x or ""))).strip()


def normalizar_yahoo(item: dict, ticker: str) -> dict | None:
    """Acepta el formato nuevo de yfinance ({'content': {...}}) y el antiguo (plano)."""
    c = item.get("content") if isinstance(item.get("content"), dict) else item
    titular = _texto(c.get("title"))
    if not titular:
        return None
    fecha = c.get("pubDate") or c.get("displayTime")
    if not fecha and c.get("providerPublishTime"):
        fecha = dt.datetime.fromtimestamp(int(c["providerPublishTime"]), dt.timezone.utc).isoformat()
    fecha = str(pd.Timestamp(fecha).date()) if fecha else ""
    prov = c.get("provider") if isinstance(c.get("provider"), dict) else {}
    fuente = prov.get("displayName") or c.get("publisher") or "Yahoo Finanzas"
    url = ""
    for clave in ("canonicalUrl", "clickThroughUrl"):
        if isinstance(c.get(clave), dict) and c[clave].get("url"):
            url = c[clave]["url"]
            break
    url = url or c.get("link") or ""
    extracto = _texto(c.get("summary") or c.get("description"))
    return dict(ticker=ticker, ratio="", fecha=fecha, titular=titular, fuente=fuente,
                extracto=extracto, url=url)


def descargar(ticker: str, n: int = 50) -> int:
    """Baja las noticias recientes de Yahoo y las suma a datos/noticias_yahoo.csv. Devuelve cuántas bajó."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    try:
        crudas = t.get_news(count=n, tab="news")
    except Exception:  # noqa: BLE001 - versiones antiguas
        crudas = t.news or []
    nuevas = [x for x in (normalizar_yahoo(i, ticker) for i in crudas or []) if x]
    if not nuevas:
        return 0
    ruta = ruta_auto()
    previas = pd.read_csv(ruta).fillna("") if ruta.exists() else pd.DataFrame(columns=COLUMNAS)
    todo = pd.concat([pd.DataFrame(nuevas), previas], ignore_index=True)
    todo = todo.drop_duplicates(subset=["ticker", "url", "titular"]).sort_values("fecha", ascending=False)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    todo[COLUMNAS].to_csv(ruta, index=False)
    return len(nuevas)


def crear_plantilla_manual() -> bool:
    ruta = ruta_manual()
    if ruta.exists():
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=COLUMNAS).to_csv(ruta, index=False)
    return True


# ---------------------------------------------------------------------------
# Lectura y asignación a ratios
# ---------------------------------------------------------------------------
def _leer(ruta: Path, origen: str) -> pd.DataFrame:
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS + ["origen"])
    df = pd.read_csv(ruta, dtype=str).fillna("")
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = ""
    df["origen"] = origen
    return df[COLUMNAS + ["origen"]]


def _puntaje(fila, ratio: str) -> int:
    texto = f"{fila['titular']} {fila['extracto']}".lower()
    return sum(1 for k in CLAVES.get(ratio, []) if re.search(rf"(?<![a-z]){re.escape(k)}", texto))


def asignar(ticker: str, desde: dt.date | None = None) -> tuple[dict, pd.DataFrame]:
    """Devuelve ({ratio: [noticia, ...]}, DataFrame con todas las noticias usadas)."""
    manual = _leer(ruta_manual(), "equipo")
    auto = _leer(ruta_auto(), "yahoo")
    todas = pd.concat([manual, auto], ignore_index=True)
    todas = todas[(todas.ticker.str.upper() == ticker.upper()) | (todas.ticker == "")]
    todas = todas[todas.titular.str.strip() != ""].copy()
    todas["_f"] = pd.to_datetime(todas.fecha, errors="coerce")
    if desde is not None:  # solo la ventana del TTM (lo manual con ratio se respeta siempre)
        fuera = todas._f.notna() & (todas._f < pd.Timestamp(desde)) & ~((todas.origen == "equipo") & (todas.ratio != ""))
        todas = todas[~fuera]
    todas = todas.sort_values("_f", ascending=False, na_position="last")

    out, usadas = {}, set()
    # 1) lo que el equipo asignó a un ratio
    for ratio in config.RATIOS:
        sel = todas[(todas.origen == "equipo") & (todas.ratio == ratio)]
        out[ratio] = [r.to_dict() for _, r in sel.iterrows()]
        usadas.update(sel.index)
    # 2) el resto por palabras clave (equipo sin ratio + Yahoo)
    libres = todas[(todas.ratio == "") & ~todas.index.isin(usadas)]
    for ratio in config.RATIOS:
        if len(out[ratio]) >= MAX_POR_RATIO:
            continue
        cand = libres[~libres.index.isin(usadas)].copy()
        cand["_p"] = cand.apply(lambda r: _puntaje(r, ratio), axis=1)
        cand = cand[cand._p > 0].sort_values(["_p", "_f"], ascending=[False, False])
        for idx, r in cand.head(MAX_POR_RATIO - len(out[ratio])).iterrows():
            d = r.to_dict()
            d["ratio"] = ratio
            out[ratio].append(d)
            usadas.add(idx)
    filas = [dict(n, ratio=ratio) for ratio, lista in out.items() for n in lista]
    return out, pd.DataFrame(filas, columns=COLUMNAS + ["origen"])


def recortar(texto: str, n: int = MAX_EXTRACTO) -> str:
    texto = _texto(texto)
    return texto if len(texto) <= n else texto[:n].rsplit(" ", 1)[0] + "…"
