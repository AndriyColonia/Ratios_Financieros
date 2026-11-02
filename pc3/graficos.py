"""Gráficos PNG listos para pegar en las láminas (16:9)."""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import analisis, config  # noqa: E402

# Paleta: 3 series categóricas en orden fijo (validadas para daltonismo) + neutros
COLOR = {"foco": "#2a78d6", "sector": "#eb6834", "lider": "#1baf7a",
         "resto": "#c3c2b7", "texto": "#0b0b0b", "texto2": "#52514e", "grilla": "#e5e4df",
         "fondo": "#ffffff"}

plt.rcParams.update({
    "font.size": 12, "axes.edgecolor": COLOR["grilla"], "axes.labelcolor": COLOR["texto2"],
    "xtick.color": COLOR["texto2"], "ytick.color": COLOR["texto2"], "axes.titleweight": "bold",
    "axes.titlesize": 16, "axes.titlecolor": COLOR["texto"], "figure.facecolor": COLOR["fondo"],
    "axes.facecolor": COLOR["fondo"], "legend.frameon": False,
})


def _estilo(ax):
    ax.grid(axis="y", color=COLOR["grilla"], linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.axhline(0, color=COLOR["texto2"], linewidth=0.8)
    ax.tick_params(axis="both", length=0)


def _num(v, unidad):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if unidad == "M USD":
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def grafico_ratio(tsl: pd.DataFrame, ratio: str, foco: str, periodos, ruta: Path):
    """Barras agrupadas por año: empresa foco, sector y líder, con el número sobre cada barra."""
    m = analisis.meta(ratio)
    factor, unidad = (100 if analisis.pct(ratio) else 1), analisis.unidad_vis(ratio)
    sub = tsl[tsl.ratio == ratio].set_index("periodo").reindex(periodos)
    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=130)
    ancho = 0.27
    x = range(len(periodos))
    series = [("foco", analisis.nombre(foco), sub.foco), ("sector", "Sector (promedio)", sub.sector),
              ("lider", "Líder", sub.lider_valor)]
    for i, (clave, etiqueta, vals) in enumerate(series):
        vals = vals * factor
        pos = [xi + (i - 1) * ancho for xi in x]
        ax.bar(pos, vals.fillna(0), width=ancho, color=COLOR[clave], label=etiqueta,
               edgecolor=COLOR["fondo"], linewidth=2)
        ns = list(sub.foco_ns) if clave == "foco" else [False] * len(pos)
        es_est = [bool(x) if pd.notna(x) else False for x in sub.foco_est] if clave == "foco" else [False] * len(pos)
        for xp, v, nsv, esv in zip(pos, vals, ns, es_est):
            txt = "n.s." if nsv else _num(v, unidad)
            if not txt:
                continue
            if esv:
                txt += "\n(est.)"
            y = 0 if (isinstance(v, float) and math.isnan(v)) else v
            ax.annotate(txt, (xp, y), xytext=(0, 4 if y >= 0 else -13), textcoords="offset points",
                        ha="center", fontsize=10, fontweight="bold" if clave == "foco" else "normal",
                        color=COLOR["texto"])
    etiquetas = []
    for p in periodos:
        lid = sub.at[p, "lider_nombre"] if p in sub.index else None
        etiquetas.append(f"{p}\nLíder: {lid}" if isinstance(lid, str) and lid != "s/d" else str(p))
    ax.set_xticks(list(x), etiquetas)
    ax.set_ylabel(unidad)
    ax.margins(y=0.12)
    ax.set_title(f"{m['nombre']}: {analisis.nombre(foco)} vs sector y líder", loc="left", pad=28)
    ax.text(0, 1.02, m.get("formula", ""), transform=ax.transAxes, color=COLOR["texto2"], fontsize=11)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.14), ncol=3)
    _estilo(ax)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def grafico_ranking(df: pd.DataFrame, tsl: pd.DataFrame, ratio: str, foco: str, periodo: int, ruta: Path):
    """Las 9 empresas ordenadas de mejor a peor en el último periodo; foco resaltado."""
    m = analisis.meta(ratio)
    factor, unidad = (100 if analisis.pct(ratio) else 1), analisis.unidad_vis(ratio)
    sub = df[(df.ratio == ratio) & (df.periodo == periodo)].dropna(subset=["valor"]).copy()
    sub["valor"] = sub.valor * factor
    if sub.empty:
        return False
    sub = sub.sort_values("valor", ascending=(m["mejor"] != "bajo"))  # el mejor queda arriba
    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=130)
    colores = [COLOR["foco"] if t == foco else COLOR["resto"] for t in sub.ticker]
    nombres = [analisis.nombre(t) for t in sub.ticker]
    ax.barh(nombres, sub.valor, color=colores, edgecolor=COLOR["fondo"], linewidth=2, height=0.7)
    sector = tsl[(tsl.ratio == ratio) & (tsl.periodo == periodo)].sector * factor
    if len(sector) and pd.notna(sector.iloc[0]):
        ax.axvline(sector.iloc[0], color=COLOR["texto"], linestyle="--", linewidth=1.2, zorder=1)
        ax.annotate(f"Sector {_num(sector.iloc[0], unidad)}", (sector.iloc[0], 1), xycoords=("data", "axes fraction"),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=11,
                    color=COLOR["texto"])
    for i, (v, tk) in enumerate(zip(sub.valor, sub.ticker)):
        ax.annotate(_num(v, unidad), (v, i), xytext=(5 if v >= 0 else -5, 0), textcoords="offset points",
                    va="center", ha="left" if v >= 0 else "right", fontsize=11, color=COLOR["texto"],
                    fontweight="bold" if tk == foco else "normal", zorder=3,
                    bbox=dict(boxstyle="round,pad=0.15", fc=COLOR["fondo"], ec="none"))
    ax.set_title(f"{m['nombre']} {periodo}: ranking de las {len(sub)} empresas", loc="left", pad=26)
    ax.set_xlabel(unidad + ("  (menor es mejor)" if m["mejor"] == "bajo" else "  (mayor es mejor)"))
    ax.grid(axis="x", color=COLOR["grilla"], linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.axvline(0, color=COLOR["texto2"], linewidth=0.8)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)
    return True


def grafico_dupont(tabla_dupont: pd.DataFrame, foco: str, periodos, ruta: Path):
    """Tres paneles (cada uno con su propio eje): margen neto, rotación y apalancamiento."""
    if tabla_dupont.empty:
        return False
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), dpi=130)
    nom_foco = analisis.nombre(foco)
    for ax, comp in zip(axes, analisis.COMPONENTES):
        m = config.DUPONT[comp]
        ancho = 0.26
        for i, (clave, filtro) in enumerate((("foco", lambda q: q == nom_foco),
                                             ("sector", lambda q: q == "Promedio sector"),
                                             ("lider", lambda q: q.startswith("Líder ROE")))):
            vals = [tabla_dupont[(tabla_dupont.periodo == p) & tabla_dupont.quien.map(filtro)][comp]
                    for p in periodos]
            vals = [v.iloc[0] if len(v) else math.nan for v in vals]
            pos = [j + (i - 1) * ancho for j in range(len(periodos))]
            ax.bar(pos, [0 if math.isnan(v) else v for v in vals], width=ancho, color=COLOR[clave],
                   edgecolor=COLOR["fondo"], linewidth=2,
                   label={"foco": nom_foco, "sector": "Sector (promedio)", "lider": "Líder en ROE"}[clave])
        ax.set_xticks(range(len(periodos)), [str(p) for p in periodos])
        ax.set_title(f"{m['nombre']} ({m['unidad']})", fontsize=13, loc="left")
        _estilo(ax)
    axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.08), ncol=3)
    fig.suptitle(f"DuPont: ROE = Margen neto × Rotación de activos × Apalancamiento — {nom_foco}",
                 x=0.01, ha="left", fontweight="bold", fontsize=16)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)
    return True
