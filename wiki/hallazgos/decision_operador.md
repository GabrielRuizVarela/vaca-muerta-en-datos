# Capa de decisión para un operador

Página generada por `pipeline/decision.py`. Traduce los hallazgos del estudio de eventos a unidades de decisión para un operador que va a fracturar un hijo cerca de un padre en produccion: caída del padre en el mes 1, parte de la brecha que se cierra a los 6 meses, metros cúbicos diferidos por padre, cota de lo que podría no volver y su valor indicativo con precio y tasa que pone quien lo usa. No estima modelos nuevos: solo promedia un diferido por evento que ya existe y reordena brechas ya publicadas.

## Resumen

- Diferido medio por evento de todos los cercanos: 869 m3 por padre (IC 95%: 574 a 1.150; rango bajo a alto: 485 a 869).
- A los 6 meses la brecha queda dentro de 5 puntos, no en cero: con el control de 2 a 5 km (V0) es de -2,1 puntos, y entre las cuatro variantes de control va de -4,8 a -2,1.
- El diferido es el volumen que falta contra el control en los meses 0 a 6 (no se sabe si llega después), no una pérdida demostrada: a los 24 meses el acumulado por evento no se distingue de cero.
- Cota superior de lo que podría no volver: 646 bbl (103 m3) por evento, sin descontar; no es una estimación de la pérdida.
- La caída del mes 1 va de -24,8 a -14,7 puntos segun la edad del padre (tabla de abajo).

## Por edad del padre

Brechas en puntos del nivel propio del padre (índice por 100, negativa si el padre rinde menos). Base de los meses -3 a -1 y control de la misma edad a 2 a 5 km, de mart_interferencia_brecha. La fila todos usa las brechas V0 de mart_anillo (cercanos juntos, control 2 a 5 km). La parte recuperada es 1 menos el cociente entre la brecha del mes 6 y la del mes 1, solo si la brecha del mes 1 es menor que -0,05; si no, queda vacia. El diferido medio es el promedio por evento de mart_interferencia_diferida, con IC bootstrap por pads hijo; el valor bajo multiplica el promedio por la razón neto_previa sobre original de toda la cuenca (aproximación, no cálculo por grupo).

| Grupo de edad del padre (meses) | Eventos | Brecha mes 1 (puntos) | Brecha mes 6 (puntos) | Parte recuperada | Diferido medio por padre (m3) | IC 95% (m3) | Rango bajo a alto (m3) |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 06-11 | 474 | -14,7 | 0,4 | 103,0% | 1.216 | 20 a 2.173 | 678 a 1.216 |
| 12-23 | 666 | -21,2 | -1,0 | 95,4% | 1.197 | 685 a 1.614 | 668 a 1.197 |
| 24-47 | 588 | -21,6 | 3,4 | 115,6% | 571 | 208 a 982 | 319 a 571 |
| 48+ | 366 | -24,8 | -6,2 | 75,2% | 302 | 65 a 521 | 168 a 302 |
| todos | 2.094 | -23,0 | -2,1 | 90,7% | 869 | 574 a 1.150 | 485 a 869 |

Por edad las brechas son diferencias de medianas, sin intervalo. Una parte recuperada mayor que 100% quiere decir que la mediana del padre cercano queda por encima de la del control en el mes 6.
La fila de 48 meses o más queda en -6,2 puntos en el mes 6, fuera de los 5 puntos del total: con padres viejos el cierre a los 6 meses es el menos completo de los cuatro grupos.

## Por banda de espaciamiento

Base de los meses -6 a -4 y control de 5 a 10 km, de mart_descomposicion_distancia. Las cifras no son intercambiables con la tabla por edad (bases distintas). El mes 6 no está publicado por distancia. Las bandas 1 a 2 y 2 a 5 km son de referencia (no son cercanos) y no tienen diferido. La columna Eventos es la de la brecha; el diferido promedia los eventos de mart_interferencia_diferida cuya distancia cae en la banda.

| Banda de distancia al hijo más cercano (km) | Eventos | Brecha mes 1 (puntos) | IC 95% (puntos) | Diferido medio por padre (m3) |
| --- | ---: | ---: | --- | ---: |
| 0 a 0,3 | 332 | -28,1 | -36,8 a -22,2 | 545 |
| 0,3 a 0,6 | 623 | -32,1 | -42,0 a -23,0 | 563 |
| 0,6 a 1 | 1.093 | -29,0 | -35,1 a -24,8 | 1.142 |
| 1 a 2 | 2.654 | -10,8 | -13,9 a -7,0 | n/d |
| 2 a 5 | 14.269 | -2,9 | -4,5 a -1,2 | n/d |

## Cierre a 6 meses

Brechas de mart_anillo en k = 1 y k = 6 con cuatro controles distintos (los cercanos son siempre los mismos, a menos de 1 km). La parte recuperada es 1 menos el cociente entre la brecha del mes 6 y la del mes 1, por variante.

| Variante | Control | Brecha k = 1 (puntos) | Brecha k = 6 (puntos) | Parte recuperada |
| --- | --- | ---: | ---: | ---: |
| V0 | 2 a 5 km | -23,0 | -2,1 | 90,7% |
| V1 | 5 a 10 km, limpio a 1 km | -24,6 | -4,1 | 83,4% |
| V2 | 2 a 10 km, limpio a 1 km | -24,1 | -3,5 | 85,3% |
| V3 | 2 a 5 km, limpio a 2 km | -24,0 | -4,8 | 79,9% |

La parte recuperada va de 79,9% a 90,7% entre variantes, y lo que no se recupera (valor absoluto de la brecha del mes 6) va de 2,1 a 4,8 puntos. Un cierre dentro de 5 puntos no es cero: la página no llama recuperado a lo que queda.

## Diferido o pérdida

El diferido medio por evento de todos los cercanos es 869 m3 por padre (IC 95%: 574 a 1.150 m3; rango bajo a alto: 485 a 869 m3). En barriles: 5.466 bbl por evento (IC 95%: 3.608 a 7.233; rango bajo a alto: 3.050 a 5.466).

Acumulado por evento a 24 meses (toda la cuenca): media -2.797 bbl, IC 95% -6.855 a 646: no se distingue de cero.

La cota superior de pérdida es de 646 bbl (103 m3) por evento, sin descontar; no es una estimación de la pérdida.

El exceso de padres que no recuperan el umbral (90% de la trayectoria del control) al mes 12 es de -1,6 puntos (IC 95%: -4,8 a 1,5).

Lo que se ve es un diferido de los meses 0 a 6 contra el control; a los 6 meses la brecha queda dentro de 5 puntos (no en cero) y a los 24 meses el acumulado por evento no se distingue de cero. Eso es compatible con diferimiento, pero el dato mensual público no prueba que el volumen se recupere, ni que el cierre sea preventivo y no daño.

## Valor indicativo

Precio y tasa son entradas de quien usa el módulo; ningúna cifra de precio es una afirmación de este proyecto. Fórmulas: costo_de_diferir = barriles * precio * (1 - (1 + tasa) ** (-rezago_meses / 12)); valor_cota_perdida = barriles * precio. Con 1 m3 = 6,2898 bbl. El costo de diferir supone que el volumen diferido se recupera; el dato no lo prueba.

Precios, tasas y rezagos de las grillas son entradas, no pronóstico ni precio observado.

Sobre el diferido medio por evento de todos los cercanos (869 m3 por padre): costo de diferir en USD por padre.

| Precio (USD/bbl) | Tasa anual | Rezago (meses) | Costo de diferir (USD por padre) |
| ---: | ---: | ---: | ---: |
| 40 | 10% | 6 | 10.175 |
| 40 | 10% | 12 | 19.876 |
| 40 | 10% | 24 | 37.945 |
| 40 | 15% | 6 | 14.757 |
| 40 | 15% | 12 | 28.518 |
| 40 | 15% | 24 | 53.316 |
| 60 | 10% | 6 | 15.262 |
| 60 | 10% | 12 | 29.814 |
| 60 | 10% | 24 | 56.918 |
| 60 | 15% | 6 | 22.135 |
| 60 | 15% | 12 | 42.777 |
| 60 | 15% | 24 | 79.974 |
| 80 | 10% | 6 | 20.350 |
| 80 | 10% | 12 | 39.752 |
| 80 | 10% | 24 | 75.890 |
| 80 | 15% | 6 | 29.514 |
| 80 | 15% | 12 | 57.036 |
| 80 | 15% | 24 | 106.632 |

Sobre la cota de pérdida (103 m3 por evento): valor sin descontar en USD por evento.

| Precio (USD/bbl) | Valor de la cota (USD) |
| ---: | ---: |
| 40 | 25.832 |
| 60 | 38.747 |
| 80 | 51.663 |

## Qué no se resuelve y qué dato interno lo resolvería

| Tema | Estado con el dato público | Dato interno que lo resolvería |
| --- | --- | --- |
| Dosis y respuesta (arena, etapas, presión, depleción) | Sin respuesta en el dato público; pipeline.potencia_dosis dice el tamaño minimo detectable | Geometría real de la fractura y espaciamiento real entre ramas |
| Dirección (eje de mayor merma contra el SHmax publicado) | No se separa con este dato | Azimut de las ramas y orientación de fracturas medida en pozo |
| Cierre preventivo contra daño | Con datos mensuales se ven igual | Registros de cierres (shut-in) con fecha y hora y presión de cabeza o de fondo del padre durante la fractura del hijo |
| Recuperación real del volumen diferido | El dato mensual público no prueba que el volumen se recupere | Curvas diarias o horarias del padre y pruebas de pozo antes y despues |

## Cómo se reproduce

`uv run python -m pipeline.decision` escribe los marts mart_decision_edad, mart_decision_distancia, mart_decision_cierre y mart_decision_perdida; `uv run python -m pipeline.wiki` genera esta página.

Con `uv run python -m pipeline.decision --precio P --tasa R --rezago M` también imprime el valor indicativo por grupo con esas entradas.

Promedios con IC bootstrap de percentiles por pads hijo (400 repeticiones, semilla fija); un grupo con menos de 30 eventos o 10 pads hijo no publica intervalo.

El valor bajo multiplica el promedio por la razón neto_previa sobre original de toda la cuenca: aproximación, no cálculo por grupo. La suma sobre todos los cercanos reproduce el total original de mart_diferido_rango (el módulo falla si difiere en más de 1 barril).
