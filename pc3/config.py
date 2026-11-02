"""Configuración del programa PC3 (GE-605 Sistema y Gestión Financiera).

Todo lo que el grupo podría querer cambiar está aquí: empresas, empresa foco,
periodos, partidas que se leen de Yahoo Finanzas y la definición de cada ratio.
"""

# ---------------------------------------------------------------------------
# Empresas del sector (9) y empresa foco
# ---------------------------------------------------------------------------
EMPRESAS = {
    "INTC": "Intel",
    "NVDA": "NVIDIA",
    "AMD": "AMD",
    "CSCO": "Cisco",
    "LRCX": "Lam Research",
    "AVGO": "Broadcom",
    "AMAT": "Applied Materials",
    "ASML": "ASML",
    "KLAC": "KLA",
}

EMPRESA_FOCO = "INTC"

# ---------------------------------------------------------------------------
# Periodos
# ---------------------------------------------------------------------------
# 2022 se descarga como BASE: sirve para los promedios (inventario, cobro, pago,
# activo y patrimonio promedio) de 2023. Los ratios de la PC3 son 2023-2026.
PERIODOS = [2022, 2023, 2024, 2025, 2026]
PERIODOS_REPORTE = [2023, 2024, 2025, 2026]

# El año en curso (aún no termina): se arma con los últimos 12 meses (TTM).
ANIO_TTM = 2026

# Etiqueta de periodo: el año fiscal se nombra por el año en que cierra.
# Excepción: si cierra en enero-marzo (NVIDIA cierra a fines de enero) se
# considera que el ejercicio corresponde al año anterior.
MES_CORTE_ANIO_ANTERIOR = 3

# ---------------------------------------------------------------------------
# Moneda. Los estados se guardan en MILLONES DE USD.
# ASML reporta en euros; solo afecta a capital de trabajo (los demás ratios no
# tienen unidades). Si Yahoo no da el tipo de cambio se usa el de respaldo.
# ---------------------------------------------------------------------------
MONEDA_FINANCIERA = {"ASML": "EUR"}
TIPO_CAMBIO_RESPALDO = {  # USD por 1 unidad de moneda, al cierre (aproximado; revisar)
    "EUR": {2022: 1.07, 2023: 1.10, 2024: 1.04, 2025: 1.17, 2026: 1.16},
}

# ---------------------------------------------------------------------------
# Partidas de los estados financieros
# clave -> (nombre en español, [(estado, etiqueta de Yahoo), ...])
# Se toma la primera etiqueta que tenga dato. Estados: resultados, balance, flujo.
# ---------------------------------------------------------------------------
PARTIDAS = {
    # Estado de resultados
    "ventas": ("Ventas", [("resultados", "Total Revenue"), ("resultados", "Operating Revenue")]),
    "costo_ventas": ("Costo de ventas", [("resultados", "Cost Of Revenue"),
                                         ("resultados", "Reconciled Cost Of Revenue")]),
    "utilidad_bruta": ("Utilidad bruta", [("resultados", "Gross Profit")]),
    "utilidad_operativa": ("Utilidad operativa", [("resultados", "Total Operating Income As Reported"),
                                                  ("resultados", "Operating Income")]),
    "utilidad_neta": ("Utilidad neta", [("resultados", "Net Income"),
                                        ("resultados", "Net Income Common Stockholders")]),
    "dep_amort": ("Depreciación y amortización", [("flujo", "Depreciation And Amortization"),
                                                  ("flujo", "Depreciation Amortization Depletion"),
                                                  ("resultados", "Reconciled Depreciation")]),
    # Balance general
    "activo_corriente": ("Activo corriente", [("balance", "Current Assets")]),
    "pasivo_corriente": ("Pasivo corriente", [("balance", "Current Liabilities")]),
    "efectivo": ("Efectivo y equivalentes", [("balance", "Cash And Cash Equivalents")]),
    "inventario": ("Inventario", [("balance", "Inventory")]),
    "cuentas_por_cobrar": ("Cuentas por cobrar", [("balance", "Accounts Receivable"),
                                                  ("balance", "Receivables")]),
    "cuentas_por_pagar": ("Cuentas por pagar", [("balance", "Accounts Payable"),
                                                ("balance", "Payables")]),
    "activo_total": ("Activo total", [("balance", "Total Assets")]),
    "pasivo_total": ("Pasivo total", [("balance", "Total Liabilities Net Minority Interest")]),
    "patrimonio": ("Patrimonio de los accionistas", [("balance", "Stockholders Equity"),
                                                     ("balance", "Common Stock Equity")]),
    "patrimonio_total": ("Patrimonio total (incl. minoritarios)",
                         [("balance", "Total Equity Gross Minority Interest")]),
    "deuda_financiera": ("Deuda financiera", [("balance", "Total Debt")]),
}

PARTIDAS_BALANCE = [k for k, (_, cands) in PARTIDAS.items() if cands[0][0] == "balance"]

# ---------------------------------------------------------------------------
# Ratios
# mejor: "alto" o "bajo" -> define al LÍDER (regla del curso: menor valor en
# días, ciclo y deuda; mayor en liquidez, márgenes y rentabilidad).
# ---------------------------------------------------------------------------
FAMILIAS = {
    "Liquidez": "¿Es líquida?",
    "Solvencia": "¿Es solvente?",
    "Eficiencia": "¿Gestiona bien su capital de trabajo?",
    "Rentabilidad": "¿Es rentable?",
}

RATIOS = {
    "liquidez_corriente": dict(
        nombre="Liquidez corriente", familia="Liquidez", unidad="veces", pct=True, mejor="alto",
        formula="Activo corriente / Pasivo corriente",
        que_mide="Mide cuántos dólares de activo corriente tiene la empresa por cada dólar que debe a corto plazo.",
        pregunta="¿Es líquida?"),
    "prueba_acida": dict(
        nombre="Prueba ácida", familia="Liquidez", unidad="veces", pct=True, mejor="alto",
        formula="(Activo corriente − Inventario) / Pasivo corriente",
        que_mide="Mide la liquidez sin contar el inventario, que es el activo corriente más difícil de convertir en caja.",
        pregunta="¿Puede pagar sin vender inventario?", reserva=True),
    "capital_trabajo": dict(
        nombre="Capital de trabajo", familia="Liquidez", unidad="M USD", mejor="alto",
        formula="Activo corriente − Pasivo corriente",
        que_mide="Mide el colchón en dinero que queda después de cubrir las deudas de corto plazo.",
        pregunta="¿Tiene colchón de corto plazo?"),
    "endeudamiento": dict(
        nombre="Endeudamiento (Pasivo/Patrimonio)", familia="Solvencia", unidad="veces", pct=True, mejor="bajo",
        formula="Pasivo total / Patrimonio total",
        que_mide="Mide cuántos dólares de terceros financian la empresa por cada dólar de los accionistas.",
        pregunta="¿Depende mucho de la deuda?"),
    "cobertura_deuda": dict(
        nombre="Cobertura de deuda (Deuda/EBITDA)", familia="Solvencia", unidad="años", mejor="bajo",
        formula="Deuda financiera / EBITDA",
        que_mide="Mide cuántos años de EBITDA necesitaría la empresa para pagar toda su deuda financiera.",
        pregunta="¿Puede pagar su deuda con lo que genera?"),
    "dias_inventario": dict(
        nombre="Días de inventario", familia="Eficiencia", unidad="días", mejor="bajo",
        formula="Inventario promedio / (Costo de ventas / 365)",
        que_mide="Mide cuántos días permanece el producto en almacén antes de venderse.",
        pregunta="¿Rota rápido su inventario?"),
    "dias_cobro": dict(
        nombre="Días de cobro", familia="Eficiencia", unidad="días", mejor="bajo",
        formula="Cuentas por cobrar promedio / (Ventas / 365)",
        que_mide="Mide cuántos días tarda la empresa en cobrar a sus clientes.",
        pregunta="¿Cobra rápido?"),
    "dias_pago": dict(
        nombre="Días de pago", familia="Eficiencia", unidad="días", mejor="bajo",
        formula="Cuentas por pagar promedio / (Costo de ventas / 365)",
        que_mide="Mide cuántos días tarda la empresa en pagar a sus proveedores.",
        pregunta="¿Cómo usa el crédito de sus proveedores?"),
    "ciclo_efectivo": dict(
        nombre="Ciclo de conversión de efectivo", familia="Eficiencia", unidad="días", mejor="bajo",
        formula="Días de inventario + Días de cobro − Días de pago",
        que_mide="Mide cuántos días de operación la empresa debe financiar con su propia caja.",
        pregunta="¿Cuántos días de caja debe financiar?"),
    "margen_bruto": dict(
        nombre="Margen bruto", familia="Rentabilidad", unidad="%", mejor="alto",
        formula="(Ventas − Costo de ventas) / Ventas",
        que_mide="Mide qué porcentaje de cada venta queda después de pagar el costo de fabricar el producto.",
        pregunta="¿Su producto deja buen margen?"),
    "margen_operativo": dict(
        nombre="Margen operativo", familia="Rentabilidad", unidad="%", mejor="alto",
        formula="Utilidad operativa / Ventas",
        que_mide="Mide qué porcentaje de cada venta queda después de los gastos de operación (I+D, ventas, administración).",
        pregunta="¿Su operación es rentable?"),
    "margen_neto": dict(
        nombre="Margen neto", familia="Rentabilidad", unidad="%", mejor="alto",
        formula="Utilidad neta / Ventas",
        que_mide="Mide qué porcentaje de cada venta queda como ganancia final, después de intereses e impuestos.",
        pregunta="¿Gana dinero al final?"),
    "margen_ebitda": dict(
        nombre="Margen EBITDA", familia="Rentabilidad", unidad="%", mejor="alto",
        formula="(Utilidad operativa + Depreciación y amortización) / Ventas",
        que_mide="Mide la caja operativa que genera cada venta, antes de depreciación, intereses e impuestos.",
        pregunta="¿Genera caja con su operación?"),
    "roa": dict(
        nombre="ROA", familia="Rentabilidad", unidad="%", mejor="alto",
        formula="Utilidad neta / Activo total promedio",
        que_mide="Mide cuánta utilidad genera cada dólar invertido en activos.",
        pregunta="¿Rinden sus activos?"),
    "roe": dict(
        nombre="ROE", familia="Rentabilidad", unidad="%", mejor="alto",
        formula="Utilidad neta / Patrimonio promedio",
        que_mide="Mide cuánta utilidad genera cada dólar que pusieron los accionistas.",
        pregunta="¿Gana dinero para el accionista?"),
}

# Componentes DuPont: ROE = Margen neto × Rotación de activos × Apalancamiento
DUPONT = {
    "margen_neto": dict(nombre="Margen neto", unidad="%", mejor="alto"),
    "rotacion_activos": dict(nombre="Rotación de activos", unidad="veces", mejor="alto",
                             formula="Ventas / Activo total promedio"),
    "apalancamiento": dict(nombre="Apalancamiento", unidad="veces", mejor="alto",
                           formula="Activo total promedio / Patrimonio promedio"),
    "roe_dupont": dict(nombre="ROE (DuPont)", unidad="%", mejor="alto"),
}

# Tolerancia para decir "similar al sector" (±10 %)
TOLERANCIA_SECTOR = 0.10
