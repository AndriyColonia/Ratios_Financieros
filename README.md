# PC3 · Ratios financieros (GE-605 Sistema y Gestión Financiera, UNI 26-2)

Programa en Python que:

1. **Descarga de Yahoo Finanzas** los estados financieros de las 9 empresas del sector
   (Intel, NVIDIA, AMD, Cisco, Lam Research, Broadcom, Applied Materials, ASML, KLA)
   para **2022, 2023, 2024, 2025 y 2026 (TTM)**.
2. **Calcula los 14 ratios** del curso, la prueba ácida (de reserva) y la descomposición **DuPont**.
3. Saca el **sector** (promedio de las 9) y el **líder** de cada ratio.
4. Se enfoca en **Intel** (o la empresa que elijas) y genera:
   - **KPI con veredicto**: por cada ratio responde la pregunta (¿es líquida?, ¿es solvente?,
     ¿cobra rápido?, ¿es rentable?...) con **sí/no y por qué**, más una conclusión por familia.
   - **Tablas tipo profesor** (Intel / Sector / Líder / empresa líder / puesto) por año.
   - **Gráficos** para las láminas: Intel vs sector vs líder por año, ranking de las 9 empresas y DuPont.
   - **Guion de 3 frases por ratio** (qué mide, dónde está, qué significa) para estudiar la exposición.

## Instalación (una sola vez)

Necesitas Python 3.10 o superior.

```bash
pip install -r requirements.txt
```

## Uso

Descargar todo y generar el reporte de Intel:

```bash
python ejecutar.py todo
```

Abre los resultados de la carpeta `salida/`:

| Archivo | Qué tiene |
|---|---|
| `salida/PC3_INTC.html` | Reporte completo (doble clic para abrirlo en el navegador): KPI, ratios, DuPont, gráficos y las 9 empresas |
| `salida/PC3_INTC.xlsx` | Hojas: Conclusiones, KPI, Tablas PC3, DuPont, Todas las empresas, Datos base y Notas |
| `salida/PC3_INTC_guion.md` | Guion de estudio: 3 frases por ratio + DuPont + conexiones que pregunta el profesor |
| `salida/graficos/*.png` | Gráficos listos para pegar en el PPT (16:9) |

Otros comandos:

```bash
python ejecutar.py descargar
```

```bash
python ejecutar.py calcular
```

```bash
python ejecutar.py calcular --tabla-profesor
```

```bash
python ejecutar.py calcular --empresa AMD
```

```bash
python ejecutar.py descargar --modo-2026 ttm
```

- `descargar` solo baja los datos a `datos/estados_financieros.xlsx`.
- `calcular` solo recalcula (sin internet), por ejemplo después de corregir datos.
- `--tabla-profesor` usa el sector y el líder de `datos/tabla_profesor.csv` donde haya dato.
- `--empresa` cambia la empresa foco (sirve para otros grupos).
- `--modo-2026 ttm` fuerza 2026 = últimos 12 meses para todas las empresas.

## Cómo trabaja el equipo con los datos

1. Una persona corre `python ejecutar.py descargar` y sube `datos/estados_financieros.xlsx` al repo.
2. Si un dato de Yahoo no cuadra con el 10-K o el PDF del grupo, o falta un año, se escribe en
   **`datos/ajustes_manuales.xlsx`** (misma forma: una hoja por empresa, partidas × años, en **millones de USD**).
   Lo que se escriba ahí **reemplaza** al dato de Yahoo. Ese archivo nunca se sobrescribe al descargar.
3. Cualquiera corre `python ejecutar.py calcular` y obtiene los mismos reportes.
4. Todo ajuste manual y todo aviso (año faltante, promedio con saldo de cierre, conversión de moneda)
   aparece en la hoja **Notas** del Excel y al final del HTML.

Si Yahoo no responde, se puede llenar `ajustes_manuales.xlsx` completo a mano y correr solo `calcular`.

## Reglas de cálculo

| Familia | Ratio | Fórmula | Líder |
|---|---|---|---|
| Liquidez | Liquidez corriente | Activo corriente / Pasivo corriente | mayor |
| Liquidez | Capital de trabajo | Activo corriente − Pasivo corriente (M USD) | mayor |
| Liquidez | Prueba ácida (reserva) | (Activo corriente − Inventario) / Pasivo corriente | mayor |
| Solvencia | Endeudamiento | Pasivo total / Patrimonio total | menor |
| Solvencia | Cobertura de deuda | Deuda financiera / EBITDA | menor |
| Eficiencia | Días de inventario | Inventario promedio / (Costo de ventas / 365) | menor |
| Eficiencia | Días de cobro | Cuentas por cobrar promedio / (Ventas / 365) | menor |
| Eficiencia | Días de pago | Cuentas por pagar promedio / (Costo de ventas / 365) | menor |
| Eficiencia | Ciclo de efectivo | Días inventario + Días cobro − Días pago | menor |
| Rentabilidad | Margen bruto | (Ventas − Costo de ventas) / Ventas | mayor |
| Rentabilidad | Margen operativo | Utilidad operativa / Ventas | mayor |
| Rentabilidad | Margen neto | Utilidad neta / Ventas | mayor |
| Rentabilidad | Margen EBITDA | (Utilidad operativa + D&A) / Ventas | mayor |
| Rentabilidad | ROA | Utilidad neta / Activo total promedio | mayor |
| Rentabilidad | ROE | Utilidad neta / Patrimonio promedio | mayor |
| DuPont | ROE | Margen neto × Rotación de activos (Ventas / Activo prom.) × Apalancamiento (Activo prom. / Patrimonio prom.) | — |

- **Promedios**: (saldo de cierre del año + saldo de cierre del año anterior) / 2. Por eso se descarga 2022:
  es la base de los promedios de 2023. Si falta el año anterior se usa el saldo de cierre y queda anotado.
  Para 2026 (TTM) el promedio es entre el último trimestre publicado y el cierre de 2025.
- **Sector** = promedio simple de las empresas con dato ese año. **Líder** = mejor valor de las 9.
- **n.s.** (no significativo): Deuda/EBITDA con EBITDA ≤ 0; ROE o endeudamiento con patrimonio ≤ 0.
- **Años fiscales**: cada año se nombra por el año en que cierra (Cisco, Lam y KLA cierran a mitad de año;
  Applied Materials y Broadcom en oct-nov). NVIDIA cierra a fines de enero, así que su ejercicio se
  asigna al año anterior (FY ene-2026 → 2025).
- **2026**: si la empresa ya cerró su año fiscal 2026 se usa ese; si no, TTM = suma de los 4 últimos
  trimestres y balance del último trimestre (`--modo-2026 ttm` fuerza TTM para todas).
- **ASML** reporta en euros: se convierte a USD (solo afecta a capital de trabajo).
- **Veredicto de cada KPI**: umbrales de clase (liquidez < 1 no es líquida, 1–1.5 ajustada;
  Deuda/EBITDA ≤ 3 sana, > 4 riesgo; márgenes negativos = pérdida) y comparación con el sector
  (±10 % se considera "en línea con el sector").

Todo lo configurable (empresas, empresa foco, años, partidas de Yahoo, umbrales) está en `pc3/config.py`.

## Ojo con Yahoo Finanzas

- Yahoo suele dar 4 años anuales. Si alguna empresa no trae 2022, complétalo en `ajustes_manuales.xlsx`
  (sale como aviso).
- Las cifras de Yahoo pueden diferir un poco del 10-K (reclasificaciones, cargos de reestructuración).
  Para Intel, comparen con los valores ya validados por el grupo y corrijan en `ajustes_manuales.xlsx`.

## Pruebas

```bash
python -m unittest discover tests
```

Las pruebas usan datos inventados; solo verifican las fórmulas y que se generen los reportes.
