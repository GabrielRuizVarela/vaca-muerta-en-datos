# Capa de decisión para un operador

Página generada por `pipeline/decision.py`. Traduce los hallazgos del estudio de eventos a unidades de decisión para un operador que va a fracturar un hijo cerca de un padre en produccion: caída del padre en el mes 1, parte de la brecha que se cierra a los 6 meses, metros cúbicos diferidos por padre, cota de lo que podría no volver y su valor indicativo con precio y tasa que pone quien lo usa. No estima modelos nuevos: solo promedia un diferido por evento que ya existe y reordena brechas ya publicadas.

## Resumen

- Diferido medio por evento de todos los cercanos: 821 m3 por padre (IC 95%: 505 a 1.105; rango bajo a alto: 446 a 821).
- A los 6 meses la brecha queda dentro de 5 puntos, no en cero: con el control de 2 a 5 km (V0) es de -2,1 puntos, y entre las cuatro variantes de control va de -4,7 a -2,1.
- El diferido es el volumen que falta contra el control en los meses 0 a 6 (no se sabe si llega después), no una pérdida demostrada: a los 24 meses el acumulado por evento no se distingue de cero.
- Cota superior de lo que podría no volver: 1.337 bbl (213 m3) por evento, sin descontar; no es una estimación de la pérdida.
- La caída del mes 1 va de -24,2 a -14,6 puntos segun la edad del padre (tabla de abajo).

## Por edad del padre

Brechas en puntos del nivel propio del padre (índice por 100, negativa si el padre rinde menos). Base de los meses -3 a -1 y control de la misma edad a 2 a 5 km, de mart_interferencia_brecha. La fila todos usa las brechas V0 de mart_anillo (cercanos juntos, control 2 a 5 km). La parte recuperada es 1 menos el cociente entre la brecha del mes 6 y la del mes 1, solo si la brecha del mes 1 es menor que -0,05; si no, queda vacia. El diferido medio es el promedio por evento de mart_interferencia_diferida, con IC bootstrap por pads hijo; el valor bajo multiplica el promedio por la razón neto_previa sobre original de toda la cuenca (aproximación, no cálculo por grupo).

| Grupo de edad del padre (meses) | Eventos | Brecha mes 1 (puntos) | Brecha mes 6 (puntos) | Parte recuperada | Diferido medio por padre (m3) | IC 95% (m3) | Rango bajo a alto (m3) |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 06-11 | 471 | -14,6 | 0,6 | 104,4% | 1.191 | 253 a 2.346 | 647 a 1.191 |
| 12-23 | 658 | -20,9 | -0,8 | 96,4% | 1.077 | 655 a 1.575 | 585 a 1.077 |
| 24-47 | 587 | -22,0 | 2,6 | 112,0% | 559 | 167 a 953 | 304 a 559 |
| 48+ | 361 | -24,2 | -5,9 | 75,8% | 297 | 39 a 501 | 161 a 297 |
| todos | 2.077 | -22,9 | -2,1 | 90,9% | 821 | 505 a 1.105 | 446 a 821 |

Por edad las brechas son diferencias de medianas, sin intervalo. Una parte recuperada mayor que 100% quiere decir que la mediana del padre cercano queda por encima de la del control en el mes 6.
La fila de 48 meses o más queda en -5,9 puntos en el mes 6, fuera de los 5 puntos del total: con padres viejos el cierre a los 6 meses es el menos completo de los cuatro grupos.

## Por banda de espaciamiento

Base de los meses -6 a -4 y control de 5 a 10 km, de mart_descomposicion_distancia. Las cifras no son intercambiables con la tabla por edad (bases distintas). El mes 6 no está publicado por distancia. Las bandas 1 a 2 y 2 a 5 km son de referencia (no son cercanos) y no tienen diferido. La columna Eventos es la de la brecha; el diferido promedia los eventos de mart_interferencia_diferida cuya distancia cae en la banda.

| Banda de distancia al hijo más cercano (km) | Eventos | Brecha mes 1 (puntos) | IC 95% (puntos) | Diferido medio por padre (m3) |
| --- | ---: | ---: | --- | ---: |
| 0 a 0,3 | 332 | -28,0 | -36,9 a -21,6 | 509 |
| 0,3 a 0,6 | 617 | -31,9 | -40,9 a -23,0 | 561 |
| 0,6 a 1 | 1.082 | -28,8 | -34,2 a -23,9 | 1.065 |
| 1 a 2 | 2.648 | -10,6 | -14,1 a -7,1 | n/d |
| 2 a 5 | 14.253 | -2,8 | -4,5 a -1,1 | n/d |

## Cierre a 6 meses

Brechas de mart_anillo en k = 1 y k = 6 con cuatro controles distintos (los cercanos son siempre los mismos, a menos de 1 km). La parte recuperada es 1 menos el cociente entre la brecha del mes 6 y la del mes 1, por variante.

| Variante | Control | Brecha k = 1 (puntos) | Brecha k = 6 (puntos) | Parte recuperada |
| --- | --- | ---: | ---: | ---: |
| V0 | 2 a 5 km | -22,9 | -2,1 | 90,9% |
| V1 | 5 a 10 km, limpio a 1 km | -24,5 | -4,0 | 83,7% |
| V2 | 2 a 10 km, limpio a 1 km | -24,0 | -3,5 | 85,5% |
| V3 | 2 a 5 km, limpio a 2 km | -23,9 | -4,7 | 80,4% |

La parte recuperada va de 80,4% a 90,9% entre variantes, y lo que no se recupera (valor absoluto de la brecha del mes 6) va de 2,1 a 4,7 puntos. Un cierre dentro de 5 puntos no es cero: la página no llama recuperado a lo que queda.

## Diferido o pérdida

El diferido medio por evento de todos los cercanos es 821 m3 por padre (IC 95%: 505 a 1.105 m3; rango bajo a alto: 446 a 821 m3). En barriles: 5.163 bbl por evento (IC 95%: 3.174 a 6.952; rango bajo a alto: 2.804 a 5.163).

Acumulado por evento a 24 meses (toda la cuenca): media -2.830 bbl, IC 95% -6.503 a 1.337: no se distingue de cero.

La cota superior de pérdida es de 1.337 bbl (213 m3) por evento, sin descontar; no es una estimación de la pérdida.

El exceso de padres que no recuperan el umbral (90% de la trayectoria del control) al mes 12 es de -1,9 puntos (IC 95%: -5,1 a 1,2).

Lo que se ve es un diferido de los meses 0 a 6 contra el control; a los 6 meses la brecha queda dentro de 5 puntos (no en cero) y a los 24 meses el acumulado por evento no se distingue de cero. Eso es compatible con diferimiento, pero el dato mensual público no prueba que el volumen se recupere, ni que el cierre sea preventivo y no daño.

## Valor indicativo

Precio y tasa son entradas de quien usa el módulo; ningúna cifra de precio es una afirmación de este proyecto. Fórmulas: costo_de_diferir = barriles * precio * (1 - (1 + tasa) ** (-rezago_meses / 12)); valor_cota_perdida = barriles * precio. Con 1 m3 = 6,2898 bbl. El costo de diferir supone que el volumen diferido se recupera; el dato no lo prueba.

Precios, tasas y rezagos de las grillas son entradas, no pronóstico ni precio observado.

Sobre el diferido medio por evento de todos los cercanos (821 m3 por padre): costo de diferir en USD por padre.

| Precio (USD/bbl) | Tasa anual | Rezago (meses) | Costo de diferir (USD por padre) |
| ---: | ---: | ---: | ---: |
| 40 | 10% | 6 | 9.611 |
| 40 | 10% | 12 | 18.775 |
| 40 | 10% | 24 | 35.843 |
| 40 | 15% | 6 | 13.939 |
| 40 | 15% | 12 | 26.938 |
| 40 | 15% | 24 | 50.362 |
| 60 | 10% | 6 | 14.417 |
| 60 | 10% | 12 | 28.162 |
| 60 | 10% | 24 | 53.764 |
| 60 | 15% | 6 | 20.909 |
| 60 | 15% | 12 | 40.407 |
| 60 | 15% | 24 | 75.543 |
| 80 | 10% | 6 | 19.222 |
| 80 | 10% | 12 | 37.550 |
| 80 | 10% | 24 | 71.686 |
| 80 | 15% | 6 | 27.879 |
| 80 | 15% | 12 | 53.876 |
| 80 | 15% | 24 | 100.724 |

Sobre la cota de pérdida (213 m3 por evento): valor sin descontar en USD por evento.

| Precio (USD/bbl) | Valor de la cota (USD) |
| ---: | ---: |
| 40 | 53.483 |
| 60 | 80.225 |
| 80 | 106.967 |

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
