"""Orquestación: descargar -> combinar con ajustes -> ratios -> sector/líder -> KPI -> reportes."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import analisis, config, datos, graficos, ratios, reporte

DIR_SALIDA = datos.RAIZ / "salida"


def cmd_descargar(args):
    from . import descarga
    print(f"Descargando de Yahoo Finanzas (modo 2026: {args.modo_2026})...")
    tablas, info, avisos = descarga.descargar_todas(args.tickers, args.modo_2026)
    if not tablas:
        print("No se descargó ninguna empresa. Revisa tu conexión a internet.")
        return 1
    datos.guardar_estados(tablas, info, avisos)
    print(f"Guardado: {datos.ARCH_ESTADOS}")
    if datos.crear_plantilla_ajustes():
        print(f"Plantilla para correcciones del equipo: {datos.ARCH_AJUSTES}")
    return 0


def cmd_calcular(args):
    foco = args.empresa.upper()
    periodos = args.periodos or config.PERIODOS_REPORTE
    datos.crear_plantilla_ajustes()
    tablas, ajustadas = datos.cargar_datos()
    if not tablas:
        print("No hay datos. Ejecuta primero:  python ejecutar.py descargar\n"
              f"o completa a mano {datos.ARCH_AJUSTES}")
        return 1
    if foco not in tablas:
        print(f"No hay datos de {foco}. Empresas con datos: {', '.join(tablas)}")
        return 1
    faltan = [config.EMPRESAS[t] for t in config.EMPRESAS if t not in tablas]
    profesor = datos.leer_tabla_profesor() if args.tabla_profesor else None

    df, notas_calc = ratios.calcular_todas(tablas, periodos)
    tsl = analisis.tabla_sector_lider(df, foco, periodos, profesor)
    lista_kpis = analisis.kpis(tsl, foco, periodos)
    familias = analisis.conclusiones_familia(lista_kpis, foco)
    tabla_dp, textos_dp = analisis.dupont(df, foco, periodos)

    info, avisos = datos.leer_info()
    notas = []
    if faltan:
        notas.append(("Faltan empresas", "-", "Sin datos de: " + ", ".join(faltan) +
                      ". El sector se promedia solo con las empresas que tienen dato."))
    if profesor is not None:
        notas.append(("Fuente", "-", "Sector y líder reemplazados por la tabla del profesor donde había dato "
                                     f"({datos.ARCH_PROFESOR.name})."))
    for r in avisos.itertuples() if not avisos.empty else []:
        notas.append(("Descarga", analisis.nombre(r.ticker), str(r.aviso)))
    for a in ajustadas:
        notas.append(("Ajuste manual", analisis.nombre(a["ticker"]),
                      f"{a['partida']} {a['periodo']} = {a['valor']:,.2f} M USD"))
    for tk, ns in notas_calc.items():
        for n in ns:
            if int(n[:4]) in periodos:
                notas.append(("Cálculo", analisis.nombre(tk), n))

    salida = Path(args.salida) if args.salida else DIR_SALIDA
    dir_graf = salida / "graficos"
    dir_graf.mkdir(parents=True, exist_ok=True)
    print("Generando gráficos...")
    for ratio in config.RATIOS:
        graficos.grafico_ratio(tsl, ratio, foco, periodos, dir_graf / f"{ratio}.png")
        graficos.grafico_ranking(df, tsl, ratio, foco, periodos[-1], dir_graf / f"{ratio}_ranking.png")
    graficos.grafico_dupont(tabla_dp, foco, periodos, dir_graf / "dupont.png")

    base = f"PC3_{foco}"
    reporte.exportar_excel(salida / f"{base}.xlsx", foco, periodos, tsl, lista_kpis, familias, df,
                           tabla_dp, textos_dp, tablas, notas)
    reporte.exportar_guion(salida / f"{base}_guion.md", foco, periodos, lista_kpis, familias, textos_dp)
    reporte.exportar_html(salida / f"{base}.html", dir_graf, foco, periodos, tsl, lista_kpis, familias, df,
                          tabla_dp, textos_dp, notas, info)

    print(f"\n=== {analisis.nombre(foco)}: resumen de KPI ===")
    for familia, c in familias.items():
        print(f"- {c['pregunta']} [{analisis.ESTADOS[c['estado']]}] {c['respuesta']}")
    print(f"\nListo. Abre el reporte:\n  {salida / (base + '.html')}\n  {salida / (base + '.xlsx')}\n"
          f"  {salida / (base + '_guion.md')}\n  {dir_graf}/ (gráficos para las láminas)")
    if len(notas) > 0:
        print(f"Hay {len(notas)} avisos; revísalos en la hoja 'Notas' del Excel.")
    return 0


def cmd_publicar(args):
    """Genera el reporte dentro de docs/ (lo que GitHub Pages publica) con index.html como portada."""
    import shutil
    dir_web = datos.RAIZ / "docs"
    args.salida = str(dir_web)
    rc = cmd_calcular(args)
    if rc:
        return rc
    foco = args.empresa.upper()
    shutil.copyfile(dir_web / f"PC3_{foco}.html", dir_web / "index.html")
    (dir_web / ".nojekyll").write_text("")  # que GitHub sirva los archivos tal cual
    print("\nPágina lista en docs/index.html. Ahora súbela a GitHub:\n"
          "  git add docs\n  git commit -m \"Actualizar reporte PC3\"\n  git push\n"
          "El link se actualiza solo uno o dos minutos después del push.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pc3", description="Ratios financieros PC3: Yahoo Finanzas -> KPI, DuPont y tablas.")
    sub = ap.add_subparsers(dest="comando", required=True)

    d = sub.add_parser("descargar", help="Baja de Yahoo Finanzas los estados 2022-2026 de las 9 empresas.")
    d.add_argument("--tickers", nargs="*", help="Solo estas empresas (por defecto, las 9).")
    d.add_argument("--modo-2026", choices=["auto", "ttm"], default="auto",
                   help="auto: año fiscal 2026 cerrado si existe, si no TTM. ttm: siempre últimos 12 meses.")

    for nombre, ayuda in (("calcular", "Calcula ratios, sector, líder, KPI y genera los reportes."),
                          ("todo", "descargar + calcular."),
                          ("publicar", "Genera la página web en docs/ para compartirla con GitHub Pages.")):
        c = sub.add_parser(nombre, help=ayuda)
        c.add_argument("--empresa", default=config.EMPRESA_FOCO, help="Empresa foco (ticker). Por defecto INTC.")
        c.add_argument("--periodos", nargs="*", type=int, help="Periodos del reporte (por defecto 2023-2026).")
        c.add_argument("--tabla-profesor", action="store_true",
                       help="Usar el sector y líder de datos/tabla_profesor.csv donde haya dato.")
        c.add_argument("--salida", help="Carpeta de salida (por defecto ./salida).")
        if nombre == "todo":
            c.add_argument("--tickers", nargs="*")
            c.add_argument("--modo-2026", choices=["auto", "ttm"], default="auto")

    sub.add_parser("plantilla", help="Crea datos/ajustes_manuales.xlsx (si no existe).")

    args = ap.parse_args(argv)
    if args.comando == "descargar":
        return cmd_descargar(args)
    if args.comando == "calcular":
        return cmd_calcular(args)
    if args.comando == "todo":
        rc = cmd_descargar(args)
        return rc or cmd_calcular(args)
    if args.comando == "publicar":
        return cmd_publicar(args)
    if args.comando == "plantilla":
        creada = datos.crear_plantilla_ajustes()
        print(("Creada: " if creada else "Ya existe: ") + str(datos.ARCH_AJUSTES))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
