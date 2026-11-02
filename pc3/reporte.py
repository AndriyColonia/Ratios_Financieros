"""Salidas: Excel con tablas, HTML con KPI/ratios/DuPont/gráficos y guion para exponer."""
from __future__ import annotations

import base64
import datetime as dt
import html
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

from . import analisis, config

RELLENO_ESTADO = {"bueno": "D9F2E6", "regular": "FFF1CC", "malo": "FADBD8", "ns": "FADBD8", "sd": "EEEEEE"}


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def _bloques_tablas(tsl: pd.DataFrame, foco: str, periodos) -> list[tuple[str, pd.DataFrame]]:
    bloques = []
    for ratio in list(config.RATIOS):
        sub = tsl[tsl.ratio == ratio].set_index("periodo").reindex(periodos)
        m = analisis.meta(ratio)
        filas = {
            analisis.nombre(foco): [analisis.fmt(v, m["unidad"], ns) for v, ns in zip(sub.foco, sub.foco_ns)],
            "Sector (promedio)": [analisis.fmt(v, m["unidad"]) for v in sub.sector],
            "Líder (valor)": [analisis.fmt(v, m["unidad"]) for v in sub.lider_valor],
            "Líder (empresa)": list(sub.lider_nombre.fillna("s/d")),
            f"Puesto de {analisis.nombre(foco)}": [f"{int(p)} de {int(n)}" if pd.notna(p) else "s/d"
                                                   for p, n in zip(sub.puesto, sub.n_empresas)],
        }
        bloques.append((f"{m['nombre']}  —  {m['formula']}",
                        pd.DataFrame(filas, index=[str(p) for p in periodos]).T))
    return bloques


def exportar_excel(ruta: Path, foco, periodos, tsl, lista_kpis, familias, df, tabla_dp, textos_dp,
                   tablas, notas):
    with pd.ExcelWriter(ruta, engine="openpyxl") as w:
        # 1. Resumen por familia
        pd.DataFrame([dict(Familia=f, Pregunta=c["pregunta"], Estado=analisis.ESTADOS[c["estado"]],
                           Respuesta=c["respuesta"]) for f, c in familias.items()]
                     ).to_excel(w, sheet_name="Conclusiones", index=False)
        # 2. KPI
        filas = []
        for k in lista_kpis:
            fila = dict(Familia=k["familia"], KPI=k["nombre"], Pregunta=k["pregunta"], Estado=k["estado_txt"])
            for p in periodos:
                fila[str(p)] = analisis.fmt(k["serie"].get(p), k["unidad"],
                                            bool(tsl[(tsl.ratio == k["ratio"]) & (tsl.periodo == p)].foco_ns.any()))
            fila.update({"Respuesta (¿cómo se comporta?)": k["respuesta"],
                         "Qué mide": k["frase_mide"], "Posición vs sector y líder": k["frase_posicion"],
                         "Qué significa": k["frase_significa"], "Fórmula": k["formula"]})
            filas.append(fila)
        pd.DataFrame(filas).to_excel(w, sheet_name="KPI", index=False)
        ws = w.sheets["KPI"]
        for i, k in enumerate(lista_kpis, start=2):
            ws.cell(i, 4).fill = PatternFill("solid", fgColor=RELLENO_ESTADO[k["estado"]])

        # 3. Tablas PC3 (formato tabla del profesor)
        fila = 0
        for titulo, bloque in _bloques_tablas(tsl, foco, periodos):
            pd.DataFrame([[titulo]]).to_excel(w, sheet_name="Tablas PC3", startrow=fila, index=False, header=False)
            bloque.to_excel(w, sheet_name="Tablas PC3", startrow=fila + 1)
            ws = w.sheets["Tablas PC3"]
            ws.cell(fila + 1, 1).font = Font(bold=True, size=12)
            fila += len(bloque) + 4

        # 4. DuPont
        dp = tabla_dp.copy()
        if not dp.empty:
            dp = dp.rename(columns={"periodo": "Periodo", "quien": "Empresa", "margen_neto": "Margen neto (%)",
                                    "rotacion_activos": "Rotación de activos (x)",
                                    "apalancamiento": "Apalancamiento (x)", "roe": "ROE (%)"}).round(2)
        dp.to_excel(w, sheet_name="DuPont", index=False)
        inicio = len(dp) + 3
        pd.DataFrame([dict(Periodo=p, Lectura=t) for p, t in textos_dp.items()]).to_excel(
            w, sheet_name="DuPont", startrow=inicio, index=False)

        # 5. Las 9 empresas por ratio
        fila = 0
        for ratio in list(config.RATIOS) + ["rotacion_activos", "apalancamiento"]:
            m = analisis.meta(ratio)
            mat = analisis.matriz_empresas(df, ratio, periodos).round(2)
            pd.DataFrame([[f"{m['nombre']} ({m['unidad']})"]]).to_excel(
                w, sheet_name="Todas las empresas", startrow=fila, index=False, header=False)
            mat.to_excel(w, sheet_name="Todas las empresas", startrow=fila + 1)
            w.sheets["Todas las empresas"].cell(fila + 1, 1).font = Font(bold=True, size=12)
            fila += len(mat) + 4

        # 6. Datos base
        base = []
        for tk, tabla in tablas.items():
            t = tabla.copy()
            t.insert(0, "Partida", [config.PARTIDAS[k][0] for k in t.index])
            t.insert(0, "Empresa", analisis.nombre(tk))
            base.append(t.reset_index(drop=True))
        if base:
            pd.concat(base).to_excel(w, sheet_name="Datos base (M USD)", index=False)

        # 7. Notas
        pd.DataFrame(notas, columns=["Tipo", "Empresa", "Nota"]).to_excel(w, sheet_name="Notas", index=False)

        for ws in w.book.worksheets:
            for col in ws.columns:
                largo = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(12, largo + 2), 70)
            for fila_celdas in ws.iter_rows(min_row=1, max_row=1):
                for c in fila_celdas:
                    if c.value is not None:
                        c.font = Font(bold=True)
            if ws.title in ("KPI", "Conclusiones", "DuPont"):
                for fila_celdas in ws.iter_rows(min_row=2):
                    for c in fila_celdas:
                        c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.freeze_panes = "A2" if ws.title in ("KPI", "Conclusiones", "Datos base (M USD)") else None


# ---------------------------------------------------------------------------
# Guion (Markdown) para estudiar y exponer
# ---------------------------------------------------------------------------
def exportar_guion(ruta: Path, foco, periodos, lista_kpis, familias, textos_dp):
    nom = analisis.nombre(foco)
    lineas = [f"# Guion PC3: ratios financieros de {nom}", "",
              f"Generado el {dt.date.today().isoformat()}. Periodos: {', '.join(map(str, periodos))}. "
              "Plantilla de 3 frases por lámina: qué mide, dónde está frente al sector y al líder, qué significa.", ""]
    for familia, c in familias.items():
        lineas += [f"## {familia}: {c['pregunta']}", "", f"**{c['respuesta']}**", ""]
        for k in [k for k in lista_kpis if k["familia"] == familia]:
            reserva = " (reserva, no entra en la tabla del profesor)" if k["reserva"] else ""
            lineas += [f"### {k['nombre']}{reserva}", "",
                       f"*Fórmula:* {k['formula']}  ",
                       f"*{k['pregunta']}* **{k['estado_txt']}**", "",
                       f"1. {k['frase_mide']}",
                       f"2. {k['frase_posicion'] or 'Sin datos para comparar.'}",
                       f"3. {k['frase_significa'].strip()}", ""]
    lineas += ["## DuPont: ¿qué explica su ROE?", ""]
    for p, t in textos_dp.items():
        lineas += [f"- **{p}:** {t}"]
    lineas += ["", "## Conexiones que suele preguntar el profesor", "",
               "- Ciclo de efectivo = días de inventario + días de cobro − días de pago.",
               "- ROE = margen neto × rotación de activos × apalancamiento.",
               "- Si el margen cae, el ROA y el ROE caen con él."]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
CSS = """
:root{--bg:#f7f7f5;--card:#ffffff;--txt:#0b0b0b;--txt2:#52514e;--borde:#e5e4df;--foco:#2a78d6;
--bueno:#0a7a3e;--bueno-bg:#e3f4ea;--regular:#8a5a00;--regular-bg:#fff3d6;--malo:#b42318;--malo-bg:#fde7e5;
--sd:#52514e;--sd-bg:#eeeeec}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#141413;--card:#1f1f1e;--txt:#f0efec;
--txt2:#c3c2b7;--borde:#3a3936;--foco:#3987e5;--bueno:#6fd39b;--bueno-bg:#16301f;--regular:#f2c46b;
--regular-bg:#33280f;--malo:#f39b92;--malo-bg:#3a1a17;--sd:#c3c2b7;--sd-bg:#2a2a28}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:22px;margin:40px 0 12px;border-bottom:2px solid var(--borde);padding-bottom:6px}
h3{font-size:17px;margin:0 0 6px}.sub{color:var(--txt2);margin:0 0 16px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}nav a{color:var(--foco);text-decoration:none;
border:1px solid var(--borde);border-radius:999px;padding:4px 12px;background:var(--card)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--borde);border-radius:10px;padding:14px 16px}
.badge{display:inline-flex;align-items:center;gap:6px;font-weight:600;font-size:13px;border-radius:999px;padding:2px 10px}
.bueno{color:var(--bueno);background:var(--bueno-bg)}.regular{color:var(--regular);background:var(--regular-bg)}
.malo,.ns{color:var(--malo);background:var(--malo-bg)}.sd{color:var(--sd);background:var(--sd-bg)}
.valor{font-size:24px;font-weight:700;margin:6px 0 2px;font-variant-numeric:tabular-nums}
.muted{color:var(--txt2);font-size:13px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px}
th,td{border-bottom:1px solid var(--borde);padding:6px 8px;text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}thead th{color:var(--txt2);font-weight:600}
tr.foco td{font-weight:700;color:var(--foco)}.scroll{overflow-x:auto}
.ratio{margin:18px 0}.ratio img{width:100%;height:auto;border-radius:8px;border:1px solid var(--borde);background:#fff}
.dos{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media (max-width:760px){.dos{grid-template-columns:1fr}}
ol{padding-left:20px;margin:8px 0}details summary{cursor:pointer;color:var(--foco);margin-top:8px}
"""

ICONO = {"bueno": "▲", "regular": "●", "malo": "▼", "ns": "▼", "sd": "–"}


def _img(ruta: Path) -> str:
    if not ruta.exists():
        return ""
    datos = base64.b64encode(ruta.read_bytes()).decode()
    return f'<img alt="{html.escape(ruta.stem)}" src="data:image/png;base64,{datos}">'


def _badge(estado: str, texto: str | None = None) -> str:
    return f'<span class="badge {estado}">{ICONO[estado]} {html.escape(texto or analisis.ESTADOS[estado])}</span>'


def exportar_html(ruta: Path, dir_graf: Path, foco, periodos, tsl, lista_kpis, familias, df, tabla_dp,
                  textos_dp, notas, info):
    e = html.escape
    nom = analisis.nombre(foco)
    partes = [f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
              f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
              f"<title>PC3 Ratios {e(nom)}</title><style>{CSS}</style></head><body><main>",
              f"<h1>PC3 · Ratios financieros de {e(nom)}</h1>",
              f"<p class='sub'>Frente al sector ({len(config.EMPRESAS)} empresas: "
              f"{e(', '.join(config.EMPRESAS.values()))}) y al líder de cada ratio. Periodos "
              f"{e(', '.join(map(str, periodos)))}. Generado el {dt.date.today().isoformat()}.</p>",
              "<nav><a href='#kpi'>KPI</a><a href='#ratios'>Ratios</a><a href='#dupont'>DuPont</a>"
              "<a href='#empresas'>Las 9 empresas</a><a href='#notas'>Notas</a>"
              f"<a href='PC3_{e(foco)}.xlsx' download>Descargar Excel</a>"
              f"<a href='PC3_{e(foco)}_guion.md' download>Descargar guion</a></nav>"]

    # Conclusiones por familia
    partes.append("<h2 id='kpi'>KPI: ¿cómo está la empresa?</h2><div class='grid'>")
    for familia, c in familias.items():
        partes.append(f"<div class='card'><h3>{e(familia)}</h3><p class='muted'>{e(c['pregunta'])}</p>"
                      f"{_badge(c['estado'])}<p>{e(c['respuesta'])}</p></div>")
    partes.append("</div>")

    # Tarjetas por KPI
    partes.append("<h2>Cada KPI, uno por uno</h2><div class='grid'>")
    for k in lista_kpis:
        fila = tsl[(tsl.ratio == k["ratio"]) & (tsl.periodo == k["periodo"])]
        ns = bool(fila.foco_ns.any())
        valor = analisis.fmt(k["serie"].get(k["periodo"]), k["unidad"], ns)
        reserva = " <span class='muted'>(reserva)</span>" if k["reserva"] else ""
        partes.append(
            f"<div class='card'><h3>{e(k['nombre'])}{reserva}</h3>"
            f"<div class='muted'>{e(k['pregunta'])} · {k['periodo']}</div>"
            f"<div class='valor'>{e(valor)}</div>{_badge(k['estado'])}"
            f"<p>{e(k['respuesta'])}</p></div>")
    partes.append("</div>")

    # Ratios: tabla + gráficos + 3 frases
    partes.append("<h2 id='ratios'>Ratios: tabla, gráfico y guion de 3 frases</h2>")
    bloques = dict(_bloques_tablas(tsl, foco, periodos))
    for (titulo, bloque), k in zip(bloques.items(), lista_kpis):
        filas_html = "".join(
            f"<tr class='{'foco' if i == 0 else ''}'><td>{e(str(idx))}</td>"
            + "".join(f"<td>{e(str(v))}</td>" for v in fila) + "</tr>"
            for i, (idx, fila) in enumerate(bloque.iterrows()))
        cab = "".join(f"<th>{e(c)}</th>" for c in bloque.columns)
        img_ratio = _img(dir_graf / (k["ratio"] + ".png"))
        img_rank = _img(dir_graf / (k["ratio"] + "_ranking.png"))
        partes.append(
            f"<section class='ratio card' id='{k['ratio']}'><h3>{e(k['nombre'])} {_badge(k['estado'])}</h3>"
            f"<div class='muted'>{e(k['formula'])}</div>"
            f"<div class='scroll'><table><thead><tr><th></th>{cab}</tr></thead><tbody>{filas_html}</tbody></table></div>"
            f"<ol><li>{e(k['frase_mide'])}</li><li>{e(k['frase_posicion'] or 'Sin datos para comparar.')}</li>"
            f"<li>{e(k['frase_significa'].strip())}</li></ol>"
            f"<div class='dos'>{img_ratio}{img_rank}</div></section>")

    # DuPont
    partes.append("<h2 id='dupont'>DuPont: ROE = Margen neto × Rotación × Apalancamiento</h2>")
    if not tabla_dp.empty:
        cab = ("<tr><th>Periodo</th><th>Empresa</th><th>Margen neto</th><th>Rotación de activos</th>"
               "<th>Apalancamiento</th><th>ROE</th></tr>")
        filas_html = "".join(
            f"<tr class='{'foco' if r.quien == nom else ''}'><td>{r.periodo}</td><td>{e(r.quien)}</td>"
            f"<td>{analisis.fmt(r.margen_neto, '%')}</td><td>{analisis.fmt(r.rotacion_activos, 'veces')}</td>"
            f"<td>{analisis.fmt(r.apalancamiento, 'veces')}</td><td>{analisis.fmt(r.roe, '%')}</td></tr>"
            for r in tabla_dp.itertuples())
        partes.append(f"<div class='card'><div class='scroll'><table><thead>{cab}</thead><tbody>{filas_html}"
                      f"</tbody></table></div><p class='muted'>El promedio del sector se calcula componente por "
                      f"componente, por eso su producto no es igual al ROE promedio.</p>"
                      + "".join(f"<p><b>{p}:</b> {e(t)}</p>" for p, t in textos_dp.items())
                      + f"<div class='ratio'>{_img(dir_graf / 'dupont.png')}</div></div>")

    # Matriz de las 9 empresas
    partes.append("<h2 id='empresas'>Las 9 empresas por ratio</h2>")
    for ratio in list(config.RATIOS) + ["rotacion_activos", "apalancamiento"]:
        m = analisis.meta(ratio)
        mat = analisis.matriz_empresas(df, ratio, periodos)
        cab = "".join(f"<th>{p}</th>" for p in mat.columns)
        filas_html = "".join(
            f"<tr class='{'foco' if idx == nom else ''}'><td>{e(idx)}</td>"
            + "".join(f"<td>{e(analisis.fmt(v, m['unidad']))}</td>" for v in fila) + "</tr>"
            for idx, fila in mat.iterrows())
        partes.append(f"<details><summary>{e(m['nombre'])}</summary><div class='card scroll'><table>"
                      f"<thead><tr><th>Empresa</th>{cab}</tr></thead><tbody>{filas_html}</tbody></table></div></details>")

    # Notas
    partes.append("<h2 id='notas'>Notas y fuentes</h2><div class='card'>")
    if info is not None and not info.empty:
        filas_html = "".join(f"<tr><td>{e(analisis.nombre(r.ticker))}</td><td>{r.periodo}</td>"
                             f"<td>{e(str(r.fecha_cierre))}</td><td>{e(str(r.tipo))}</td></tr>"
                             for r in info.itertuples())
        partes.append("<h3>Periodos usados (Yahoo Finanzas)</h3><div class='scroll'><table><thead><tr>"
                      "<th>Empresa</th><th>Periodo</th><th>Cierre</th><th>Tipo</th></tr></thead>"
                      f"<tbody>{filas_html}</tbody></table></div>")
    partes.append("<h3>Avisos</h3><ul>" + "".join(
        f"<li><b>{e(t)}</b> · {e(emp)}: {e(n)}</li>" for t, emp, n in notas) + "</ul></div>")
    partes.append("</main></body></html>")
    ruta.write_text("".join(partes), encoding="utf-8")
