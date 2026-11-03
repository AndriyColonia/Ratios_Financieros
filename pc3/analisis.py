"""Sector, líder, lectura de cada KPI (¿es líquida o no y por qué?) y DuPont."""
from __future__ import annotations

import math

import pandas as pd

from . import config

NOMBRE_A_TICKER = {v.lower(): k for k, v in config.EMPRESAS.items()}
ESTADOS = {"bueno": "Fortaleza", "regular": "Atención", "malo": "Debilidad", "ns": "No significativo",
           "sd": "Sin datos"}


# ---------------------------------------------------------------------------
# Formato
# ---------------------------------------------------------------------------
def meta(ratio: str) -> dict:
    return config.RATIOS.get(ratio) or config.DUPONT[ratio]


def fmt(valor, unidad: str, ns: bool = False) -> str:
    if ns:
        return "n.s."
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "s/d"
    if unidad == "%":
        return f"{valor:,.2f} %"
    if unidad == "días":
        return f"{valor:,.2f} días"
    if unidad == "M USD":
        return f"{valor:,.0f} M USD"
    if unidad == "años":
        return f"{valor:,.2f} años"
    return f"{valor:,.2f}x"


def pct(ratio: str) -> bool:
    """True si el ratio se muestra en % (liquidez, prueba ácida, endeudamiento: 1.54x -> 154.00 %)."""
    return bool(meta(ratio).get("pct"))


def unidad_vis(ratio: str) -> str:
    return "%" if pct(ratio) else meta(ratio)["unidad"]


def fmt_ratio(valor, ratio: str, ns: bool = False, est: bool = False) -> str:
    """Formato de un valor de ratio según cómo se muestra. est=True marca un dato estimado."""
    if not ns and not _nan(valor) and pct(ratio):
        valor = valor * 100
    txt = fmt(valor, unidad_vis(ratio), ns)
    return txt + " (est.)" if est and not ns and not _nan(valor) else txt


def nombre(tk) -> str:
    return config.EMPRESAS.get(tk, tk) if isinstance(tk, str) else "s/d"


def _nan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


# ---------------------------------------------------------------------------
# Sector y líder
# ---------------------------------------------------------------------------
def tabla_sector_lider(df: pd.DataFrame, foco: str, periodos, profesor: pd.DataFrame | None = None):
    """Una fila por (ratio, periodo) con foco, sector (promedio de las empresas
    con dato), líder (mejor valor según el ratio) y puesto del foco."""
    filas = []
    ratios = list(config.RATIOS) + ["rotacion_activos", "apalancamiento", "roe_dupont"]
    for ratio in ratios:
        m = meta(ratio)
        for p in periodos:
            sub = df[(df.ratio == ratio) & (df.periodo == p)]
            validos = sub.dropna(subset=["valor"])
            fila_foco = sub[sub.ticker == foco]
            v_foco = fila_foco.valor.iloc[0] if len(fila_foco) else math.nan
            ns_foco = bool(fila_foco.ns.iloc[0]) if len(fila_foco) else False
            est_foco = bool(fila_foco.est.iloc[0]) if len(fila_foco) and "est" in fila_foco else False
            fila = dict(ratio=ratio, nombre=m["nombre"], familia=m.get("familia", "DuPont"),
                        unidad=m["unidad"], periodo=p, foco=v_foco, foco_ns=ns_foco, foco_est=est_foco,
                        sector=validos.valor.mean() if len(validos) else math.nan,
                        n_empresas=len(validos), lider_valor=math.nan, lider_ticker=None,
                        puesto=None, fuente="calculado")
            if len(validos):
                orden = validos.sort_values("valor", ascending=(m["mejor"] == "bajo"))
                fila["lider_valor"] = orden.valor.iloc[0]
                fila["lider_ticker"] = orden.ticker.iloc[0]
                if foco in list(orden.ticker):
                    fila["puesto"] = list(orden.ticker).index(foco) + 1
            filas.append(fila)
    out = pd.DataFrame(filas)
    if profesor is not None:
        out = _aplicar_profesor(out, df, profesor)
    out["lider_nombre"] = out.lider_ticker.map(nombre)
    return out


def _aplicar_profesor(out, df, prof):
    for _, r in prof.iterrows():
        mask = (out.ratio == r["ratio"]) & (out.periodo == int(r["periodo"]))
        if not mask.any():
            continue
        if pd.notna(r.get("sector")):
            out.loc[mask, "sector"] = float(r["sector"])
            out.loc[mask, "fuente"] = "tabla del profesor"
        emp = r.get("lider_empresa")
        if isinstance(emp, str) and emp.strip():
            tk = NOMBRE_A_TICKER.get(emp.strip().lower(), emp.strip().upper())
            out.loc[mask, "lider_ticker"] = tk
            valor = r.get("lider_valor")
            if pd.isna(valor):
                calc = df[(df.ratio == r["ratio"]) & (df.periodo == int(r["periodo"])) & (df.ticker == tk)]
                valor = calc.valor.iloc[0] if len(calc) else math.nan
            out.loc[mask, "lider_valor"] = float(valor)
            out.loc[mask, "fuente"] = "tabla del profesor"
    return out


def matriz_empresas(df: pd.DataFrame, ratio: str, periodos) -> pd.DataFrame:
    sub = df[(df.ratio == ratio) & (df.periodo.isin(periodos))]
    m = sub.pivot(index="ticker", columns="periodo", values="valor")
    m.index = [nombre(t) for t in m.index]
    return m


# ---------------------------------------------------------------------------
# Veredicto de cada KPI
# ---------------------------------------------------------------------------
def comparar(v, s, mejor):
    """'mejor' / 'similar' / 'peor' que el sector (tolerancia ±10 %)."""
    if _nan(v) or _nan(s):
        return None
    if s == 0:
        dif = v - s
    else:
        dif = (v - s) / abs(s)
    if mejor == "bajo":
        dif = -dif
    if dif > config.TOLERANCIA_SECTOR:
        return "mejor"
    if dif < -config.TOLERANCIA_SECTOR:
        return "peor"
    return "similar"


def veredicto(ratio: str, v, s, ns: bool = False) -> tuple[str, str]:
    """Devuelve (estado, respuesta corta a la pregunta del KPI)."""
    m = meta(ratio)
    rel = comparar(v, s, m["mejor"])
    s_txt = fmt_ratio(s, ratio)

    if ns:
        if ratio == "cobertura_deuda":
            return "malo", ("No se puede medir: el EBITDA es negativo, la operación no genera caja para "
                            "pagar deuda. Es una señal de riesgo.")
        return "malo", "No significativo: el patrimonio es negativo o cero, señal de alto riesgo."
    if _nan(v):
        return "sd", "Sin datos suficientes para calcularlo; complétalo en datos/ajustes_manuales.xlsx."

    if ratio == "liquidez_corriente":
        if v < 1:
            return "malo", (f"No. Por cada US$ 1 que debe a corto plazo solo tiene US$ {v:.2f} de activo "
                            "corriente; no alcanza a cubrir sus obligaciones de corto plazo.")
        if v < 1.5:
            return "regular", (f"Sí, pero ajustada: cubre {v:.2f} veces su pasivo corriente, con poco margen "
                               f"de holgura (sector: {s_txt}).")
        if v <= 3:
            return "bueno", (f"Sí. Cubre {v:.2f} veces sus deudas de corto plazo (sector: {s_txt}).")
        return "bueno", (f"Sí, muy líquida ({v:.2f} veces), aunque un nivel tan alto puede indicar dinero "
                         f"ocioso que no se está invirtiendo (sector: {s_txt}).")

    if ratio == "prueba_acida":
        if v < 0.8:
            return "malo", f"No. Sin vender inventario solo cubre {v:.2f} veces su pasivo corriente."
        if v < 1:
            return "regular", (f"Casi: sin inventario cubre {v:.2f} veces su pasivo corriente; depende en "
                               "parte de vender su inventario.")
        return "bueno", f"Sí. Aun sin vender inventario cubre {v:.2f} veces su pasivo corriente."

    if ratio == "capital_trabajo":
        if v <= 0:
            return "malo", (f"No. Su pasivo corriente supera al activo corriente en {fmt(-v, 'M USD')}; "
                            "tiene un déficit de corto plazo.")
        return "bueno", (f"Sí. Le quedan {fmt(v, 'M USD')} después de cubrir todas sus deudas de corto plazo "
                         f"(promedio del sector: {s_txt}).")

    if ratio == "endeudamiento":
        if v < 0.5:
            return "bueno", f"No. Por cada US$ 1 de patrimonio debe US$ {v:.2f}; se financia sobre todo con capital propio."
        if v < 1:
            return "bueno", (f"Moderadamente: debe US$ {v:.2f} por cada US$ 1 de patrimonio; usa más capital "
                             f"propio que deuda (sector: {s_txt}).")
        if v < 2:
            return "regular", (f"Sí. Debe US$ {v:.2f} por cada US$ 1 de patrimonio: los terceros financian más "
                               f"que los accionistas (sector: {s_txt}).")
        return "malo", (f"Sí, mucho: debe US$ {v:.2f} por cada US$ 1 de patrimonio; alta dependencia de "
                        f"terceros (sector: {s_txt}).")

    if ratio == "cobertura_deuda":
        if v < 1:
            return "bueno", f"Sí, con holgura: pagaría toda su deuda con {v:.2f} años de EBITDA (sector: {s_txt})."
        if v <= 3:
            return "bueno", f"Sí. Necesitaría {v:.2f} años de EBITDA para pagar su deuda, nivel sano (≤ 3)."
        if v <= 4:
            return "regular", f"Con esfuerzo: necesitaría {v:.2f} años de EBITDA, nivel exigente (sector: {s_txt})."
        return "malo", (f"Con dificultad: necesitaría {v:.2f} años de EBITDA para pagar su deuda (> 4 años es "
                        f"alto riesgo; sector: {s_txt}).")

    if ratio in ("margen_bruto", "margen_operativo", "margen_neto", "margen_ebitda", "roa", "roe") and v < 0:
        textos = {
            "margen_bruto": "No. Vende por debajo de su costo de fabricación.",
            "margen_operativo": f"No. Su operación pierde {abs(v):.2f} centavos por cada dólar vendido.",
            "margen_neto": f"No. Pierde {abs(v):.2f} centavos por cada dólar vendido.",
            "margen_ebitda": "No. Su operación consume caja en vez de generarla.",
            "roa": f"No. Sus activos destruyen valor: pierde {abs(v):.2f} centavos por cada dólar de activo.",
            "roe": f"No. Destruye valor para el accionista: pierde {abs(v):.2f} centavos por cada dólar de patrimonio.",
        }
        return "malo", textos[ratio] + f" (sector: {s_txt})."

    # Ratios que solo se leen contra el sector
    v_txt = fmt_ratio(v, ratio)
    textos = {
        "dias_inventario": {
            "mejor": f"Sí. Su producto pasa {v_txt} en almacén frente a {s_txt} del sector: rota más rápido.",
            "similar": f"Como el sector: {v_txt} frente a {s_txt}.",
            "peor": f"No. Su producto pasa {v_txt} en almacén frente a {s_txt} del sector: inventario más lento.",
        },
        "dias_cobro": {
            "mejor": f"Sí. Cobra en {v_txt} frente a {s_txt} del sector: convierte sus ventas en caja más rápido.",
            "similar": f"Como el sector: {v_txt} frente a {s_txt}.",
            "peor": f"No. Tarda {v_txt} en cobrar frente a {s_txt} del sector: financia a sus clientes.",
        },
        "dias_pago": {
            "mejor": (f"Paga en {v_txt}, más rápido que el sector ({s_txt}): no depende de estirar el plazo "
                      "a sus proveedores."),
            "similar": f"Como el sector: paga en {v_txt} frente a {s_txt}.",
            "peor": (f"Paga en {v_txt}, más lento que el sector ({s_txt}): se financia con sus proveedores, lo "
                     "que le da caja, pero un plazo tan alto puede reflejar presión de liquidez."),
        },
        "ciclo_efectivo": {
            "mejor": f"Pocos: {v_txt} frente a {s_txt} del sector; necesita menos caja propia para operar.",
            "similar": f"Como el sector: {v_txt} frente a {s_txt}.",
            "peor": f"Muchos: {v_txt} frente a {s_txt} del sector; necesita más caja propia para operar.",
        },
    }
    if ratio in textos:
        estado = {"mejor": "bueno", "similar": "regular", "peor": "malo"}[rel] if rel else "sd"
        if ratio == "dias_pago" and rel == "peor":
            estado = "regular"
        txt = textos[ratio].get(rel, "Sin dato del sector para comparar.")
        if ratio == "ciclo_efectivo" and v < 0:
            txt += " Su ciclo es negativo: los proveedores financian toda su operación."
        return estado, txt

    # Márgenes, ROA y ROE positivos
    if rel == "mejor":
        return "bueno", f"Sí, y por encima del sector: {v_txt} frente a {s_txt}."
    if rel == "similar":
        return "regular", f"Sí, en línea con el sector: {v_txt} frente a {s_txt}."
    if rel == "peor":
        return "regular" if v > 0 else "malo", f"Sí, pero por debajo del sector: {v_txt} frente a {s_txt}."
    return "sd", f"{v_txt}; sin dato del sector para comparar."


# ---------------------------------------------------------------------------
# KPI con las 3 frases para exponer
# ---------------------------------------------------------------------------
def _tendencia(serie: list, mejor: str, ratio: str) -> str:
    pares = [(p, v) for p, v in serie if not _nan(v)]
    if len(pares) < 2:
        return ""
    (p0, v0), (p1, v1) = pares[0], pares[-1]
    sube = v1 > v0
    mejora = sube if mejor == "alto" else not sube
    if math.isclose(v0, v1, rel_tol=0.02, abs_tol=1e-9):
        return f"Entre {p0} y {p1} se mantuvo estable ({fmt_ratio(v0, ratio)} → {fmt_ratio(v1, ratio)})."
    return (f"Entre {p0} y {p1} {'mejoró' if mejora else 'empeoró'} "
            f"({fmt_ratio(v0, ratio)} → {fmt_ratio(v1, ratio)}).")


def kpis(tsl: pd.DataFrame, foco: str, periodos) -> list[dict]:
    out = []
    for ratio, m in config.RATIOS.items():
        sub = tsl[tsl.ratio == ratio].set_index("periodo").reindex(periodos)
        ultimo = sub.dropna(subset=["foco"]).index.max() if sub.foco.notna().any() else periodos[-1]
        if pd.isna(ultimo):
            ultimo = periodos[-1]
        f = sub.loc[ultimo]
        ns = bool(f.foco_ns) if pd.notna(f.foco_ns) else False
        estado, respuesta = veredicto(ratio, f.foco, f.sector, ns)

        out.append(dict(
            ratio=ratio, nombre=m["nombre"], familia=m["familia"], unidad=m["unidad"], formula=m["formula"],
            pregunta=m["pregunta"], reserva=m.get("reserva", False), periodo=int(ultimo),
            estado=estado, estado_txt=ESTADOS[estado], respuesta=respuesta,
            evolucion=_tendencia(list(sub.foco.items()), m["mejor"], ratio),
            serie={int(p): sub.at[p, "foco"] for p in periodos},
            serie_est={int(p): bool(sub.at[p, "foco_est"]) if pd.notna(sub.at[p, "foco_est"]) else False for p in periodos},
        ))
    return out


def conclusiones_familia(lista_kpis: list[dict], foco: str) -> dict:
    out = {}
    for familia, pregunta in config.FAMILIAS.items():
        ks = [k for k in lista_kpis if k["familia"] == familia and not k["reserva"] and k["estado"] != "sd"]
        if not ks:
            out[familia] = dict(pregunta=pregunta, estado="sd", respuesta="Sin datos.", detalle=[])
            continue
        n_malo = sum(k["estado"] == "malo" for k in ks)
        n_bueno = sum(k["estado"] == "bueno" for k in ks)
        if n_malo == 0 and n_bueno >= len(ks) / 2:
            estado, inicio = "bueno", "Sí"
        elif n_malo >= len(ks) / 2:
            estado, inicio = "malo", "No"
        else:
            estado, inicio = "regular", "En parte"
        partes = []
        for est, etiqueta in (("bueno", "A favor"), ("regular", "Atención"), ("malo", "En contra")):
            nombres = [k["nombre"] for k in ks if k["estado"] == est]
            if nombres:
                partes.append(f"{etiqueta}: " + ", ".join(nombres))
        out[familia] = dict(pregunta=pregunta, estado=estado,
                            respuesta=f"{inicio}. " + (". ".join(partes) + "." if partes else ""),
                            detalle=[f"{k['nombre']}: {k['respuesta']}" for k in ks])
    return out


# ---------------------------------------------------------------------------
# DuPont
# ---------------------------------------------------------------------------
COMPONENTES = ["margen_neto", "rotacion_activos", "apalancamiento"]


def dupont(df: pd.DataFrame, foco: str, periodos) -> tuple[pd.DataFrame, dict]:
    """Tabla DuPont (foco, promedio del sector y líder en ROE) y lectura por periodo."""
    filas, textos = [], {}
    for p in periodos:
        sub = df[df.periodo == p].pivot(index="ticker", columns="ratio", values="valor")
        if sub.empty:
            continue
        roe = sub["roe_dupont"].dropna()
        lider = roe.idxmax() if len(roe) else None
        for quien, etiqueta in ((foco, nombre(foco)), ("sector", "Promedio sector"), (lider, None)):
            if quien is None:
                continue
            if quien == "sector":
                vals = sub[COMPONENTES + ["roe_dupont"]].mean()
            elif quien in sub.index:
                vals = sub.loc[quien, COMPONENTES + ["roe_dupont"]]
            else:
                continue
            filas.append(dict(periodo=p, quien=etiqueta or f"Líder ROE: {nombre(quien)}",
                              **{c: vals[c] for c in COMPONENTES}, roe=vals["roe_dupont"]))

        if foco not in sub.index:
            continue
        f = sub.loc[foco]
        s = sub[COMPONENTES].mean()
        if _nan(f["roe_dupont"]):
            textos[p] = "Sin datos suficientes para la descomposición DuPont."
            continue
        txt = (f"ROE {fmt(f['roe_dupont'], '%')} = margen neto {fmt(f['margen_neto'], '%')} × rotación "
               f"{fmt(f['rotacion_activos'], 'veces')} × apalancamiento {fmt(f['apalancamiento'], 'veces')}. ")
        if f["margen_neto"] < 0:
            txt += ("El ROE es negativo porque el margen neto es negativo: la empresa pierde dinero en cada "
                    "venta, y la rotación y el apalancamiento solo amplifican esa pérdida. ")
        relativos = {c: (f[c] / s[c] if s[c] and not _nan(f[c]) and s[c] > 0 else math.nan) for c in COMPONENTES}
        validos = {c: r for c, r in relativos.items() if not _nan(r)}
        if validos:
            peor = min(validos, key=validos.get)
            mejor = max(validos, key=validos.get)
            nom = {c: config.DUPONT[c]["nombre"].lower() for c in COMPONENTES}
            if validos[peor] < 1:
                txt += (f"Frente al sector, su principal debilidad es el {nom[peor]} "
                        f"({fmt(f[peor], config.DUPONT[peor]['unidad'])} vs "
                        f"{fmt(s[peor], config.DUPONT[peor]['unidad'])}). ")
            if validos[mejor] > 1:
                txt += (f"Su componente más fuerte es el {nom[mejor]} "
                        f"({fmt(f[mejor], config.DUPONT[mejor]['unidad'])} vs "
                        f"{fmt(s[mejor], config.DUPONT[mejor]['unidad'])}).")
        if lider and lider != foco:
            txt += f" El líder en ROE es {nombre(lider)} con {fmt(sub.at[lider, 'roe_dupont'], '%')}."
        elif lider == foco:
            txt += f" {nombre(foco)} es el líder del sector en ROE."
        textos[p] = txt.strip()
    return pd.DataFrame(filas), textos


# ---------------------------------------------------------------------------
# Brecha del último periodo (2026 TTM) frente al sector y al líder
# ---------------------------------------------------------------------------
NOTA_EST = ("(est.) Dato estimado: el EBITDA contable de ese año fue negativo y Deuda/EBITDA no se puede calcular "
            "con él; se usó el EBITDA normalizado de Yahoo o el promedio de los años vecinos (detalle en Notas).")


def etiqueta_periodo(p) -> str:
    return f"{p} TTM" if int(p) == config.ANIO_TTM else str(p)


def _brecha(v, ref, ratio: str):
    """Diferencia entre v y ref en la unidad que se muestra. Devuelve None si falta un dato, o
    (texto de la diferencia, texto relativo, está_por_encima, juicio). 'igual' si no hay diferencia."""
    m = meta(ratio)
    if _nan(v) or _nan(ref):
        return None
    factor = 100 if pct(ratio) else 1
    unidad = unidad_vis(ratio)
    dif = (v - ref) * factor
    if abs(dif) < 0.005:
        return "igual"
    arriba = dif > 0
    juicio = comparar(v, ref, m["mejor"])      # mejor / similar (±10 %) / peor: igual que la lectura del KPI
    a = abs(dif)
    texto = {"%": f"{a:,.2f} p.p.", "días": f"{a:,.2f} días", "años": f"{a:,.2f} años",
             "M USD": f"{a:,.0f} M USD"}.get(unidad, f"{a:,.2f}x")
    # El % relativo solo tiene sentido si el ratio no es ya un % (en márgenes se usan p.p.)
    rel = ""
    if (unidad != "%" or pct(ratio)) and ref != 0:
        r = (v - ref) / abs(ref) * 100
        rel = f" ({abs(r):,.2f} % {'más' if r > 0 else 'menos'})"
    return texto, rel, arriba, juicio


def comentario_brecha(tsl: pd.DataFrame, ratio: str, foco: str, periodo: int) -> str:
    """Comentario para el último periodo: cuánto mejor o peor está la empresa que el sector y el líder."""
    f = tsl[(tsl.ratio == ratio) & (tsl.periodo == periodo)]
    if f.empty:
        return ""
    f = f.iloc[0]
    nom = nombre(foco)
    inicio = f"Comentario {etiqueta_periodo(periodo)}: "
    if f.foco_ns:
        return inicio + f"el ratio de {nom} no es significativo (n.s.), no se puede comparar."

    def frase(ref, del_quien):
        b = _brecha(f.foco, ref, ratio)
        if b is None:
            return f"sin dato {del_quien} para comparar"
        if b == "igual":
            return f"igual {del_quien}"
        texto, rel, arriba, juicio = b
        return (f"{texto} {'por encima' if arriba else 'por debajo'} {del_quien}{rel}, "
                f"es decir, {'en línea (±10 %)' if juicio == 'similar' else juicio}")

    txt = inicio + f"{nom} está {frase(f.sector, 'del sector')}."
    if f.lider_ticker == foco:
        txt += f" {nom} es el líder del sector en este ratio."
    else:
        txt += f" Frente al líder ({f.lider_nombre}) está {frase(f.lider_valor, 'del líder')}."
    return txt
