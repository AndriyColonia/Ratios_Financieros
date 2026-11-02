"""Pruebas con datos SINTÉTICOS (inventados): solo verifican que las fórmulas y el
flujo funcionen. No son datos reales de ninguna empresa.

Ejecutar:  python -m unittest discover tests
"""
import math
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pc3 import analisis, config, datos, descarga, principal, ratios


def _frame(filas: dict, fechas):
    return pd.DataFrame(filas, index=[pd.Timestamp(f) for f in fechas]).T


class TestDescarga(unittest.TestCase):
    def test_anuales_y_ttm(self):
        anuales = ["2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"]
        res = _frame({"Total Revenue": [100e6, 110e6, 120e6, 130e6],
                      "Cost Of Revenue": [60e6, 66e6, 72e6, 78e6]}, anuales)
        bal = _frame({"Current Assets": [50e6, 55e6, 60e6, 65e6]}, anuales)
        trimestres = ["2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30", "2026-09-30"]
        q_res = _frame({"Total Revenue": [30e6, 35e6, 36e6, 37e6, 38e6],
                        "Cost Of Revenue": [18e6, 20e6, 21e6, 22e6, 23e6]}, trimestres)
        q_bal = _frame({"Current Assets": [60e6, 65e6, 66e6, 67e6, 70e6]}, trimestres)
        datos_, info, avisos = descarga.construir_tabla(
            {"resultados": res, "balance": bal, "flujo": None},
            {"resultados": q_res, "balance": q_bal, "flujo": None})
        self.assertEqual(datos_[2022]["ventas"], 100e6)
        # TTM = últimos 4 trimestres (dic-25 a sep-26)
        self.assertEqual(datos_[2026]["ventas"], (35 + 36 + 37 + 38) * 1e6)
        self.assertEqual(datos_[2026]["activo_corriente"], 70e6)
        self.assertEqual([i["tipo"] for i in info][-1], "TTM (últimos 12 meses)")

    def test_anio_fiscal_enero_es_anio_anterior(self):
        self.assertEqual(descarga.etiqueta_periodo("2025-01-26"), 2024)
        self.assertEqual(descarga.etiqueta_periodo("2026-06-28"), 2026)

    def test_2026_cerrado_en_modo_auto_y_ttm_forzado(self):
        anuales = ["2023-07-29", "2024-07-27", "2025-07-26", "2026-07-25"]
        res = _frame({"Total Revenue": [1e6, 2e6, 3e6, 4e6]}, anuales)
        trimestres = ["2025-10-25", "2026-01-24", "2026-04-25", "2026-07-25", "2026-10-24"]
        q = _frame({"Total Revenue": [1e6, 1e6, 1e6, 1e6, 2e6]}, trimestres)
        auto, _, _ = descarga.construir_tabla({"resultados": res}, {"resultados": q})
        self.assertEqual(auto[2026]["ventas"], 4e6)
        ttm, _, _ = descarga.construir_tabla({"resultados": res}, {"resultados": q}, modo_2026="ttm")
        self.assertEqual(ttm[2026]["ventas"], 5e6)


def _tabla(**valores_por_periodo):
    t = pd.DataFrame(index=list(config.PARTIDAS), columns=config.PERIODOS, dtype=float)
    for clave, serie in valores_por_periodo.items():
        for p, v in serie.items():
            t.at[clave, p] = v
    return t


def tabla_ejemplo(escala=1.0, perdida=False):
    p = {2022: 1, 2023: 1}
    return _tabla(
        ventas={2023: 1000 * escala}, costo_ventas={2023: 600 * escala},
        utilidad_operativa={2023: (-50 if perdida else 200) * escala}, utilidad_neta={2023: (-80 if perdida else 150) * escala},
        dep_amort={2023: 100 * escala},
        activo_corriente={2023: 500 * escala}, pasivo_corriente={2023: 250 * escala},
        inventario={k: 120 * escala * v for k, v in p.items()},
        cuentas_por_cobrar={2022: 80 * escala, 2023: 120 * escala},
        cuentas_por_pagar={2022: 50 * escala, 2023: 70 * escala},
        activo_total={2022: 1800 * escala, 2023: 2200 * escala},
        pasivo_total={2023: 1000 * escala}, patrimonio={2022: 900 * escala, 2023: 1100 * escala},
        patrimonio_total={2023: 1200 * escala}, deuda_financiera={2023: 600 * escala},
    )


class TestRatios(unittest.TestCase):
    def test_formulas(self):
        v, ns, _ = ratios.calcular_empresa(tabla_ejemplo(), [2023])
        r = v.loc[2023]
        self.assertAlmostEqual(r.liquidez_corriente, 2.0)
        self.assertAlmostEqual(r.capital_trabajo, 250)
        self.assertAlmostEqual(r.prueba_acida, (500 - 120) / 250)
        self.assertAlmostEqual(r.endeudamiento, 1000 / 1200)
        self.assertAlmostEqual(r.cobertura_deuda, 600 / 300)            # EBITDA = 200 + 100
        self.assertAlmostEqual(r.dias_inventario, 120 / (600 / 365))
        self.assertAlmostEqual(r.dias_cobro, 100 / (1000 / 365))         # promedio (80+120)/2
        self.assertAlmostEqual(r.dias_pago, 60 / (600 / 365))
        self.assertAlmostEqual(r.ciclo_efectivo, r.dias_inventario + r.dias_cobro - r.dias_pago)
        self.assertAlmostEqual(r.margen_bruto, 40)
        self.assertAlmostEqual(r.margen_operativo, 20)
        self.assertAlmostEqual(r.margen_neto, 15)
        self.assertAlmostEqual(r.margen_ebitda, 30)
        self.assertAlmostEqual(r.roa, 150 / 2000 * 100)
        self.assertAlmostEqual(r.roe, 150 / 1000 * 100)
        self.assertAlmostEqual(r.roe_dupont, r.roe)                    # DuPont cuadra con el ROE
        self.assertFalse(ns)

    def test_ebitda_negativo_es_no_significativo(self):
        t = tabla_ejemplo(perdida=True)
        t.at["dep_amort", 2023] = 10
        v, ns, _ = ratios.calcular_empresa(t, [2023])
        self.assertTrue(math.isnan(v.loc[2023].cobertura_deuda))
        self.assertIn((2023, "cobertura_deuda"), ns)

    def test_sin_saldo_anterior_usa_cierre(self):
        t = tabla_ejemplo()
        t[2022] = math.nan
        v, _, notas = ratios.calcular_empresa(t, [2023])
        self.assertAlmostEqual(v.loc[2023].roa, 150 / 2200 * 100)
        self.assertTrue(any("saldo de cierre" in n for n in notas))


class TestAnalisis(unittest.TestCase):
    def setUp(self):
        tablas = {"INTC": tabla_ejemplo(perdida=True), "NVDA": tabla_ejemplo(2.0), "AMD": tabla_ejemplo(0.5)}
        tablas["NVDA"].at["utilidad_neta", 2023] = 600   # NVDA: margen neto 30 %
        self.df, _ = ratios.calcular_todas(tablas, [2023])
        self.tsl = analisis.tabla_sector_lider(self.df, "INTC", [2023])

    def test_sector_y_lider(self):
        f = self.tsl[(self.tsl.ratio == "margen_neto") & (self.tsl.periodo == 2023)].iloc[0]
        self.assertAlmostEqual(f.sector, (-8 + 30 + 15) / 3)
        self.assertEqual(f.lider_ticker, "NVDA")
        self.assertEqual(f.puesto, 3)

    def test_lider_en_dias_es_el_menor(self):
        f = self.tsl[(self.tsl.ratio == "dias_cobro")].iloc[0]
        self.assertEqual(f.lider_valor, self.df[self.df.ratio == "dias_cobro"].valor.min())

    def test_kpi_tiene_veredicto_y_tres_frases(self):
        ks = analisis.kpis(self.tsl, "INTC", [2023])
        mn = next(k for k in ks if k["ratio"] == "margen_neto")
        self.assertEqual(mn["estado"], "malo")
        self.assertTrue(mn["respuesta"].startswith("No."))
        liq = next(k for k in ks if k["ratio"] == "liquidez_corriente")
        self.assertEqual(liq["estado"], "bueno")
        self.assertTrue(liq["frase_posicion"])
        fam = analisis.conclusiones_familia(ks, "INTC")
        self.assertEqual(set(fam), set(config.FAMILIAS))

    def test_dupont(self):
        tabla, textos = analisis.dupont(self.df, "INTC", [2023])
        self.assertIn("margen neto es negativo", textos[2023])
        self.assertIn("NVIDIA", textos[2023])
        self.assertEqual(len(tabla), 3)

    def test_tabla_profesor_reemplaza(self):
        prof = pd.DataFrame([dict(ratio="dias_pago", periodo=2023, sector=52.96,
                                  lider_empresa="Lam Research", lider_valor=28.25)])
        tsl = analisis.tabla_sector_lider(self.df, "INTC", [2023], prof)
        f = tsl[tsl.ratio == "dias_pago"].iloc[0]
        self.assertEqual((f.sector, f.lider_valor, f.lider_nombre), (52.96, 28.25, "Lam Research"))


class TestFlujoCompleto(unittest.TestCase):
    def test_genera_reportes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            orig = (datos.ARCH_ESTADOS, datos.ARCH_AJUSTES)
            datos.ARCH_ESTADOS, datos.ARCH_AJUSTES = tmp / "estados.xlsx", tmp / "ajustes.xlsx"
            try:
                tablas = {tk: tabla_ejemplo(1 + i / 4) for i, tk in enumerate(config.EMPRESAS)}
                datos.guardar_estados(tablas, [], [])
                datos.crear_plantilla_ajustes()
                # el equipo corrige una celda en la plantilla
                import openpyxl
                wb = openpyxl.load_workbook(datos.ARCH_AJUSTES)
                ws = wb["INTC"]
                fila = next(r for r in range(2, ws.max_row + 1) if ws.cell(r, 1).value == "ventas")
                col = next(c for c in range(1, ws.max_column + 1) if ws.cell(1, c).value == 2023)
                ws.cell(fila, col).value = 2000
                wb.save(datos.ARCH_AJUSTES)

                rc = principal.main(["calcular", "--periodos", "2023", "--salida", str(tmp / "out")])
                self.assertEqual(rc, 0)
                for f in ("PC3_INTC.xlsx", "PC3_INTC.html", "PC3_INTC_guion.md",
                          "graficos/liquidez_corriente.png", "graficos/dupont.png"):
                    self.assertTrue((tmp / "out" / f).exists(), f)
                tablas_leidas, ajustadas = datos.cargar_datos()
                self.assertEqual(tablas_leidas["INTC"].at["ventas", 2023], 2000)
                self.assertEqual(len(ajustadas), 1)
            finally:
                datos.ARCH_ESTADOS, datos.ARCH_AJUSTES = orig


if __name__ == "__main__":
    unittest.main()
