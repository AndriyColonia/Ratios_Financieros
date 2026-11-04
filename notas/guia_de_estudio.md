# Guía de estudio PC3: qué estoy exponiendo y por qué

Para aprender, no para leer en voz alta. Orden: reglas del juego, los 14 ratios (definición, fórmula, cuándo es bueno o malo y por qué), DuPont, los KPI, y cómo se compara con el sector y el líder.

Los umbrales ("bueno si es mayor que X") son **reglas prácticas** de análisis financiero, no leyes. El programa usa estas mismas reglas (función `veredicto` en `pc3/analisis.py`). Si el profesor dio otros umbrales en clase, usen los del profesor.

---

## 0. Las reglas del juego

- **Sector:** promedio simple de las 9 empresas en ese ratio y año (solo las que tienen dato).
- **Líder:** la empresa con el **mejor** valor. "Mejor" depende del ratio:
  - Mayor es mejor: liquidez, capital de trabajo, márgenes, ROA, ROE.
  - Menor es mejor: endeudamiento, cobertura de deuda (Deuda/EBITDA), días de inventario, días de cobro, días de pago y ciclo de efectivo.
- **Puesto:** en qué lugar queda Intel entre las 9, de mejor a peor (1 = el mejor).
- **2026 TTM:** TTM significa *trailing twelve months*, los últimos 12 meses publicados. El año 2026 aún no termina, así que se suman los últimos 4 trimestres. No es el mismo corte para todas las empresas porque sus años fiscales cierran en meses distintos.
- **Promedios:** inventario, cuentas por cobrar y por pagar, activo y patrimonio se promedian entre el cierre del año y el del año anterior. Por eso se descargó 2022.

---

## 1. LIQUIDEZ: ¿puede pagar lo que debe en el corto plazo?

### 1.1 Liquidez corriente
- **Definición:** cuántos dólares de activo corriente (caja, cuentas por cobrar, inventario) tiene la empresa por cada dólar de deuda que vence en menos de un año.
- **Fórmula:** Activo corriente / Pasivo corriente.
- **¿Bueno o malo?**
  - **Menor a 1:** malo. No alcanza a cubrir sus deudas de corto plazo con sus activos de corto plazo.
  - **Entre 1 y 1.5:** ajustado. Cubre, pero con poco margen.
  - **De 1.5 a 3:** bueno. Cubre con holgura.
  - **Mayor a 3:** muy líquida, pero puede haber dinero ocioso que no se invierte.
- **¿Por qué?** Una empresa con muchos activos pero poca liquidez puede quebrar por no poder pagar a tiempo. Demasiada liquidez también cuesta: ese dinero parado no rinde.

### 1.2 Capital de trabajo
- **Definición:** el colchón en dinero que queda tras pagar lo que vence en el corto plazo.
- **Fórmula:** Activo corriente − Pasivo corriente (en millones de dólares).
- **¿Bueno o malo?** Positivo es bueno; cero o negativo es malo (déficit de corto plazo).
- **¿Por qué?** Es la liquidez corriente expresada en dinero. Ojo: al estar en dólares, depende del tamaño de la empresa (NVIDIA lidera porque es enorme, no necesariamente porque sea más "sana").

---

## 2. SOLVENCIA: ¿puede sostener su deuda en el largo plazo?

### 2.1 Endeudamiento (Pasivo / Patrimonio)
- **Definición:** cuántos dólares de terceros (bancos, bonistas, proveedores) financian a la empresa por cada dólar de los accionistas.
- **Fórmula:** Pasivo total / Patrimonio total.
- **¿Bueno o malo?**
  - **Menor a 1:** se financia más con capital propio que con deuda. Es sano.
  - **Entre 1 y 2:** los terceros financian más que los accionistas. Atención.
  - **Mayor a 2:** alta dependencia de deuda. Riesgo.
  - Depende del sector: algunos soportan más deuda que otros.
- **¿Por qué?** Más deuda significa más intereses y más riesgo si bajan las ventas. Pero algo de deuda puede aumentar el ROE (eso se ve en DuPont).

### 2.2 Cobertura de deuda (Deuda financiera / EBITDA)
- **Definición:** cuántos años de EBITDA necesitaría la empresa para pagar toda su deuda financiera.
- **Fórmula:** Deuda financiera / EBITDA. El EBITDA es utilidad operativa + depreciación y amortización.
- **¿Bueno o malo?** Menos años es mejor.
  - **Hasta 3 años:** sano.
  - **Entre 3 y 4:** exigente.
  - **Más de 4:** riesgo alto.
  - Si el EBITDA es negativo, el ratio no se puede calcular: la empresa no genera caja para pagar deuda.
- **¿Por qué?** Compara la deuda con la capacidad de generar caja operativa, que es con lo que realmente se paga la deuda.
- **Nota del programa:** si el EBITDA contable es negativo, el programa usa el EBITDA normalizado de Yahoo (o el promedio de años vecinos) y marca el dato como "(est.)".

---

## 3. EFICIENCIA: ¿maneja bien su capital de trabajo?

### 3.1 Días de inventario
- **Definición:** cuántos días permanece el producto en almacén antes de venderse.
- **Fórmula:** Inventario promedio / (Costo de ventas / 365).
- **¿Bueno o malo?** Menos días es mejor. Demasiado bajo puede significar riesgo de quedarse sin stock.
- **¿Por qué?** Un inventario parado es dinero inmovilizado, ocupa espacio, y puede volverse obsoleto, sobre todo en tecnología.

### 3.2 Días de cobro
- **Definición:** cuántos días tarda la empresa en cobrar a sus clientes.
- **Fórmula:** Cuentas por cobrar promedio / (Ventas / 365).
- **¿Bueno o malo?** Menos días es mejor.
- **¿Por qué?** Mientras no cobra, la empresa está financiando a sus clientes con su propia caja. Cobrar rápido convierte ventas en dinero.

### 3.3 Días de pago
- **Definición:** cuántos días tarda la empresa en pagar a sus proveedores.
- **Fórmula:** Cuentas por pagar promedio / (Costo de ventas / 365).
- **¿Bueno o malo?** Es el ratio más matizado:
  - **Más días:** la empresa se financia con sus proveedores, lo que le da caja. Eso es favorable.
  - **Demasiados días:** puede ser señal de problemas para pagar, o de mucho poder de negociación. Debe leerse con la liquidez.
  - **Pocos días:** paga rápido, pero no aprovecha el crédito de proveedores.
- **Ojo con el "líder":** por regla del curso, el líder en días de pago es el que **menos** días tiene. Eso no significa que sea el mejor negociador; es una convención para comparar.

### 3.4 Ciclo de conversión de efectivo
- **Definición:** cuántos días de operación la empresa debe financiar con su propia caja.
- **Fórmula:** Días de inventario + Días de cobro − Días de pago.
- **¿Bueno o malo?** Menos días es mejor. Si es negativo, es excelente: los proveedores financian toda la operación.
- **¿Por qué?** Resume los tres anteriores. Es el tiempo que pasa desde que la empresa paga a sus proveedores hasta que cobra a sus clientes.
- **Conexión que el profesor puede preguntar:** si el ciclo sube, ¿cuál de los tres componentes cambió? (Mira el que más se movió.)

---

## 4. RENTABILIDAD: ¿gana dinero?

### 4.1 Margen bruto
- **Definición:** qué porcentaje de cada venta queda después de pagar el costo directo de producir.
- **Fórmula:** (Ventas − Costo de ventas) / Ventas.
- **¿Bueno o malo?** Mayor es mejor. Negativo significa que vende por debajo de su costo.
- **¿Por qué?** Mide el poder de la empresa para fijar precios y su eficiencia productiva.

### 4.2 Margen operativo
- **Definición:** qué porcentaje de cada venta queda después de los gastos de operación (investigación y desarrollo, ventas, administración).
- **Fórmula:** Utilidad operativa / Ventas.
- **¿Bueno o malo?** Mayor es mejor. Negativo significa que la operación pierde dinero.
- **¿Por qué?** Mide la rentabilidad del negocio en sí, sin intereses ni impuestos.

### 4.3 Margen neto
- **Definición:** qué porcentaje de cada venta queda como ganancia final, tras intereses e impuestos.
- **Fórmula:** Utilidad neta / Ventas.
- **¿Bueno o malo?** Mayor es mejor. Negativo significa que pierde dinero al final.
- **¿Por qué?** Es el resultado completo. Si el margen operativo es positivo pero el neto es negativo, el problema está en partidas no operativas: intereses, impuestos, pérdidas por inversiones, minoritarios u otros.

### 4.4 Margen EBITDA
- **Definición:** la caja operativa que genera cada venta, antes de depreciación, intereses e impuestos.
- **Fórmula:** (Utilidad operativa + Depreciación y amortización) / Ventas.
- **¿Bueno o malo?** Mayor es mejor.
- **¿Por qué?** La depreciación no es salida de caja, así que el EBITDA se acerca más a la caja que genera el negocio. En empresas con muchas fábricas, el EBITDA es mucho mayor que la utilidad operativa.

### 4.5 ROA (rentabilidad sobre activos)
- **Definición:** cuánta utilidad genera cada dólar invertido en activos.
- **Fórmula:** Utilidad neta / Activo total promedio.
- **¿Bueno o malo?** Mayor es mejor. Negativo significa que los activos destruyen valor.
- **¿Por qué?** Mide qué tan bien la empresa usa todo lo que tiene, sin importar cómo lo financió.

### 4.6 ROE (rentabilidad sobre patrimonio)
- **Definición:** cuánta utilidad genera cada dólar que pusieron los accionistas.
- **Fórmula:** Utilidad neta / Patrimonio promedio.
- **¿Bueno o malo?** Mayor es mejor. Negativo significa que destruye valor para el accionista.
- **¿Por qué?** Es el rendimiento para el dueño. Un ROE alto puede venir de buenos márgenes o de mucha deuda; DuPont lo separa.

---

## 5. DuPont: por qué el ROE es como es

- **Fórmula:** ROE = Margen neto × Rotación de activos × Apalancamiento.
  - **Margen neto** = Utilidad neta / Ventas. Qué tan rentable es cada venta.
  - **Rotación de activos** = Ventas / Activo total promedio. Cuántos dólares vende por cada dólar de activos.
  - **Apalancamiento** = Activo total promedio / Patrimonio promedio. Cuántos dólares de activo hay por cada dólar propio; más deuda, más apalancamiento.
- **¿Bueno o malo?** Mayor ROE es mejor, pero hay que ver **de dónde viene**:
  - **Por margen:** es la fuente más sana y sostenible.
  - **Por rotación:** negocio eficiente que aprovecha sus activos.
  - **Por apalancamiento:** más riesgoso, porque se apoya en deuda.
- **Truco para leerlo:** compara los tres componentes con el sector y busca cuál está más lejos; ese explica la diferencia del ROE.
- **Conexión:** si el margen neto es negativo, el ROE es negativo sin importar la rotación y el apalancamiento; estos solo amplifican el resultado.
- **Detalle técnico:** el promedio del sector se calcula componente por componente, así que su producto no es igual al ROE promedio del sector.

---

## 6. Los KPI: quién los determina y qué significan

**Qué son:** cuatro preguntas que resumen el estado de la empresa. Cada una se responde con un conjunto de ratios.

| KPI (la pregunta) | Los ratios que lo determinan |
|---|---|
| ¿Es líquida? | Liquidez corriente, capital de trabajo |
| ¿Es solvente? | Endeudamiento, cobertura de deuda |
| ¿Gestiona bien su capital de trabajo? (eficiencia) | Días de inventario, días de cobro, días de pago, ciclo de efectivo |
| ¿Es rentable? | Margen bruto, operativo, neto, EBITDA, ROA, ROE (DuPont explica el ROE) |

**Cada ratio recibe una calificación:**
- **Fortaleza:** el ratio está en un nivel sano o mejor que el sector.
- **Atención:** está en un nivel intermedio o justo; no es un problema grave, pero hay que vigilarlo.
- **Debilidad:** el ratio está en nivel de riesgo o claramente peor que el sector.

**Cómo se califica cada ratio:**

| Ratio | Fortaleza | Atención | Debilidad |
|---|---|---|---|
| Liquidez corriente | ≥ 1.5 | 1 a 1.5 | < 1 |
| Capital de trabajo | > 0 | — | ≤ 0 |
| Endeudamiento | < 1 | 1 a 2 | ≥ 2 |
| Deuda/EBITDA | ≤ 3 años | 3 a 4 | > 4 años o EBITDA negativo |
| Días de inventario, cobro y ciclo | menos días que el sector | similar (±10 %) | más días que el sector |
| Días de pago | menos días que el sector | similar o más días | — |
| Márgenes, ROA y ROE | positivo y mayor que el sector | positivo, similar o menor al sector | negativo |

**Cómo se resume cada KPI (familia):**
- Si **ningún** ratio es debilidad y **al menos la mitad** son fortaleza: **Sí** (fortaleza).
- Si **al menos la mitad** son debilidad: **No** (debilidad).
- En los demás casos: **En parte** (atención).

**Qué significan para la empresa:**
- **Liquidez:** capacidad de pagar a corto plazo.
- **Solvencia:** capacidad de sostener su deuda a largo plazo.
- **Eficiencia:** qué tan rápido convierte inventario y ventas en caja.
- **Rentabilidad:** capacidad de generar ganancias para sus dueños.

---

## 7. Cómo se compara con el sector y el líder

El programa calcula la brecha **solo para 2026 TTM** y la dice como comentario:

1. **Dirección:** ¿Intel está por encima o por debajo del referente (sector o líder)?
2. **Juicio (mejor, peor o en línea):** depende de si el ratio es "mayor es mejor" o "menor es mejor".
   - Mayor es mejor: estar por encima es mejor.
   - Menor es mejor: estar por debajo es mejor.
   - **En línea:** si la diferencia relativa es menor al 10 %, se considera "en línea".
3. **Cuánto:**
   - **Ratios en % (márgenes, ROA, ROE):** la brecha se da en **puntos porcentuales (p.p.)**, que es la resta directa. Ejemplo: margen bruto 39.90 % − 57.40 % del sector = **17.5 p.p. menos**. Se usan p.p. porque decir "30 % menos" sobre un porcentaje confunde.
   - **Ratios en veces, días, años o dólares:** se da la diferencia absoluta y el **% relativo** = (Intel − referente) / referente. Ejemplo: liquidez 2.21 − 2.47 = 0.26 por debajo; 0.26 / 2.47 = **10.7 % menos**.

**Ejemplos del 2026 TTM de Intel:**

| Ratio | Intel | Sector | Brecha frente al sector | Lectura |
|---|---|---|---|---|
| Liquidez corriente | 2.21x | 2.47x | 0.26x menos (10.7 % menos) | peor |
| Endeudamiento | 0.74x | 0.99x | 0.26x menos (25.8 % menos) | mejor (menos deuda) |
| Días de inventario | 125.15 | 142.59 | 17.4 días menos (12.2 % menos) | mejor (menos días) |
| Ciclo de efectivo | 54.45 | 130.77 | 76.3 días menos (58.4 % menos) | mejor |
| Margen bruto | 39.90 % | 57.40 % | 17.5 p.p. menos | peor |

---

## 8. Preguntas que pueden hacer (y la respuesta corta)

- **¿Cómo se relacionan los días?** Ciclo = días de inventario + días de cobro − días de pago.
- **¿Por qué el ROE de Intel es negativo?** Porque su margen neto es negativo; DuPont lo muestra: la rotación y el apalancamiento son similares o menores al sector, el problema es el margen.
- **¿Por qué el margen operativo es positivo y el neto negativo?** Entre ambos están intereses, impuestos y partidas no operativas. (Busquen la causa exacta en el estado de resultados del 10-Q.)
- **¿Por qué el EBITDA de Intel es alto si la utilidad operativa es casi cero?** Porque tiene una depreciación muy alta por sus fábricas; el EBITDA la suma de vuelta.
- **¿Más días de pago es bueno?** Da caja (los proveedores te financian), pero demasiados pueden mostrar presión de liquidez. Se lee junto con la liquidez.
- **¿Por qué el líder en capital de trabajo es NVIDIA?** Porque es la más grande; es un monto en dólares, no un ratio relativo.
- **¿Por qué "en línea" con el sector?** Si la diferencia es menor al 10 %, no se considera ni mejor ni peor.
- **¿Qué es el 2026 TTM?** Los últimos 12 meses publicados, porque el año aún no termina.
