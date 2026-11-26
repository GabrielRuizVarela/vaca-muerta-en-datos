# Replicación en Colorado (cuenca DJ)

Página generada por `pipeline/replicacion.py` sobre el warehouse del Colorado (`data/colorado/warehouse.duckdb`). Corre, sin cambiarlos, los estimadores del estudio de eventos de Vaca Muerta (`pipeline/placebo.py` y la clave de bloque de `pipeline/bloques.py`) sobre las tablas que armó `pipeline/colorado` ([datos y conteos](colorado_datos.md)). La regla se fijó antes de correr, en el primer commit de este tramo, y está en el libro de hallazgos como `replicacion_colorado`. Complementa [Interferencia entre fracturas](interferencia.md) y [Bloques espaciales](bloques.md).

## Resumen

Veredicto contra la regla fijada antes de correr: **se replica**. El límite superior del IC por bloques de 5 km de la brecha del mes 1 queda por debajo de cero y la brecha previa a la fractura con base limpia es menor, en valor absoluto, que la del mes 1. La segunda condición es una barrera baja: pide una brecha previa menor que la del mes 1, no una brecha previa igual a cero. Con base limpia la brecha del mes -1 (-6,9, IC 95% por bloques de 5 km: -10,2 a -4,2) y la del mes -2 (-2,8, IC: -4,9 a -1,0) también excluyen cero. Medida por día producido, la brecha del mes 1 es de -8,1 puntos (IC 95% por bloques de 5 km: -11,3 a -5,2), cerca de 60% menor en valor absoluto que los -19,9 de la medida principal, y con menos eventos cercanos (3.190 frente a 3.691). La regla se aplica a la medida principal (por día calendario): una parte grande de la brecha principal pasa entonces por meses o días sin producción, en línea con la descomposición en días y caudal por día de Vaca Muerta (`descomposicion.md`). Es la lectura de una cuenca, con las limitaciones de abajo, y no una afirmación causal.

- Brecha del mes 1 (padres horizontales a menos de 1 km frente a controles de 2 a 5 km, base de los meses -3 a -1): -19,9 puntos. IC 95% por pads hijo: -26,9 a -15,0; por bloques de 5 km: -27,5 a -14,8 (190 bloques).
- Brecha previa a la fractura con base limpia (mes -1, base de los meses -6 a -4): -6,9 puntos (IC 95% por bloques de 5 km: -10,2 a -4,2).
- Valor de la hipótesis: -0,130, el mayor entre el límite superior del IC por bloques, -0,148, y la diferencia de valores absolutos (previa menos mes 1), -0,130; se replica si es menor que cero.
- Eventos con dato al mes 1: 3.691 cercanos y 53.326 controles, de 572 pads hijo y 190 bloques de 5 km.
- Los resultados secundarios (pretendencia, mes 6, placebo con fechas corridas, robustez) se publican completos abajo; no son veredictos.

## Regla fijada antes de correr

Se replica si la brecha del mes 1 (mediana del índice de los padres cercanos menos la de los controles, base de los meses -3 a -1, padres a menos de 1 km y controles de 2 a 5 km, con los filtros de P5a) es negativa con un IC 95% que excluye cero, y si la brecha previa con base limpia (mes -1, base de los meses -6 a -4) es menor, en valor absoluto, que la del mes 1. Si no, no se replica. La lectura usa el IC por bloques espaciales de 5 km; el IC por pads hijo se publica al lado. Después del primer commit se agregó `limit 1` a la consulta SQL del libro (`replicacion_colorado` en `pipeline/hallazgos.py`) solo para que la consulta de la hipótesis devuelva una única fila: el texto, el operador y el umbral son los mismos y el valor no cambió, pero cambió la `firma` registrada en el libro. Los umbrales no se tocaron después de ver resultados.

## Brecha por mes, con los dos intervalos

Índice = caudal de petróleo del mes sobre la media de la base; brecha = mediana de los cercanos menos mediana de los controles, en puntos de índice. k = 0 es el mes de la fractura del hijo.

| Base | k | Eventos cercanos | Eventos de control | Brecha (puntos) | IC 95% por pads | IC 95% por bloques de 5 km | Bloques |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| Meses -3 a -1 | 1 | 3.691 | 53.326 | -19,9 | -26,9 a -15,0 | -27,5 a -14,8 | 190 |
| Meses -3 a -1 | 6 | 3.691 | 53.311 | -5,9 | -8,6 a -2,9 | -9,4 a -2,3 | 190 |
| Meses -6 a -4 | -3 | 3.530 | 50.660 | -1,1 | -2,4 a 0,5 | -2,6 a 0,4 | 190 |
| Meses -6 a -4 | -2 | 3.531 | 50.640 | -2,8 | -4,4 a -1,0 | -4,9 a -1,0 | 190 |
| Meses -6 a -4 | -1 | 3.530 | 50.638 | -6,9 | -9,8 a -4,2 | -10,2 a -4,2 | 190 |
| Meses -6 a -4 | 0 | 3.526 | 50.637 | -18,9 | -24,8 a -14,1 | -26,5 a -13,6 | 190 |
| Meses -6 a -4 | 1 | 3.530 | 50.650 | -23,3 | -30,0 a -16,1 | -30,3 a -16,3 | 190 |
| Meses -6 a -4 | 2 | 3.531 | 50.659 | -15,7 | -21,7 a -11,5 | -22,7 a -11,0 | 190 |
| Meses -6 a -4 | 3 | 3.530 | 50.657 | -11,4 | -15,9 a -8,1 | -16,3 a -8,1 | 190 |

Con la base de los meses -6 a -4 los meses -3 a -1 son la pretendencia (la brecha previa a la fractura); con la base de los meses -3 a -1 el mes 1 es el resultado del veredicto y el mes 6 mide cuánto queda de la brecha. Al mes 6 la brecha es de -5,9 puntos; su IC por bloques excluye cero.

## Placebo con la fecha de fractura corrida

Se corre la fecha de fractura de todos los hijos 12 meses (hacia atrás y hacia adelante), se conservan los pares padre e hijo y se exige que el padre cumpla las mismas reglas en la fecha falsa (la misma máquina de `pipeline/placebo.py`, IC por pads). Con -12 meses la fecha falsa cae antes de la fractura real y es el placebo limpio; con +12 el mes falso puede caer sobre meses ya afectados, así que no refuta nada por sí solo.

| Desplazamiento (meses) | Eventos cercanos | Brecha del mes 1 (puntos) | IC 95% por pads | Brecha real en los mismos eventos (puntos) |
| ---: | ---: | ---: | --- | ---: |
| -12 | 2.681 | -0,2 | -2,2 a 2,3 | -19,9 |
| 12 | 3.168 | -0,8 | -2,4 a 0,7 | -15,5 |

## Robustez a los dos riesgos de la memoria de factibilidad

Un solo corte, sin veredicto adicional: padres horizontales (el corte principal) frente a todos los padres, y caudal por día calendario (el principal) frente a caudal por día producido (petróleo del mes sobre sus días efectivos; un mes sin días efectivos queda sin dato). Cada fila recalcula el mes 1 y la brecha previa del mes -1 con su propia regla.

| Corte | Eventos cercanos | Eventos de control | Brecha del mes 1 (puntos) | IC 95% por pads | IC 95% por bloques de 5 km | Brecha previa del mes -1 (puntos) |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Principal (padres horizontales, caudal por día calendario) | 3.691 | 53.326 | -19,9 | -26,9 a -15,0 | -27,5 a -14,8 | -6,9 |
| Todos los padres (horizontales, verticales y sin dato) | 3.707 | 53.662 | -19,9 | -26,9 a -15,2 | -27,4 a -14,9 | -6,9 |
| Caudal por día producido (petróleo sobre días efectivos) | 3.190 | 53.288 | -8,1 | -10,1 a -5,6 | -11,3 a -5,2 | -3,9 |

Medida por día producido la brecha del mes 1 es menor en valor absoluto que por día calendario. En la medida principal un mes cerrado entra con caudal cero; por día producido queda sin dato. La brecha por día producido es de -8,1 puntos, cerca de 60% menor que la principal, con 3.190 eventos cercanos frente a 3.691; la regla se aplica a la medida principal, así que una parte grande de la brecha pasa por meses o días sin producir, en línea con la descomposición en días y caudal por día de Vaca Muerta (`descomposicion.md`).

## Recuentos

| Concepto | Cantidad |
| --- | ---: |
| Hijos (regla de P5a) | 4.789 |
| Pads hijo | 588 |
| Bloques de 5 km con algún hijo | 197 |
| Eventos cercanos (a menos de 1 km) | 3.692 |
| Eventos intermedios (de 1 a 2 km, fuera de la brecha) | 7.990 |
| Eventos de control (de 2 a 5 km) | 53.339 |
| Padres distintos entre los eventos cercanos | 2.046 |
| Padres distintos entre los eventos de control | 8.766 |
| Eventos cercanos con dato al mes 1 | 3.691 |
| Eventos de control con dato al mes 1 | 53.326 |
| Pads hijo en la brecha del mes 1 | 572 |
| Bloques de 5 km en la brecha del mes 1 | 190 |

## Qué Colorado no puede mostrar

- No hay etapas ni arena: el largo de rama es un proxy (profundidad medida menos vertical) y no se corre ningún resultado que dependa de ellas.
- La rama lateral es un proxy y la ubicación es la de superficie, igual que en Vaca Muerta; no hay trayectorias.
- La fecha de fractura sale del formulario de divulgación de FracFocus (inicio del trabajo), no de un mes calendario de reporte; un error de unos días mueve el mes 0 de un hijo.
- La convención de reporte difiere: una fila por formación, sidetracks sumados al pozo y días efectivos como el máximo entre filas.
- Los cierres aparecen como meses con cero días producidos, no como una marca de parada; no se separa un cierre del operador de un daño.
- La población de padres es distinta (muchos pozos verticales); por eso el corte principal usa solo padres horizontales.
- El bloque de 5 km de un pad usa el centroide de todos sus pozos con ubicación (también verticales y sin producción), no solo el de los pozos filtrados; solo importa para pads cerca del borde de una celda.
- Es una huella medida contra un control, sin ajuste por comparaciones múltiples; no se afirma causalidad.

## Qué significa para el resultado de Vaca Muerta

La brecha del mes 1 y la regla fijada de antemano se sostienen también en una segunda cuenca con los mismos estimadores: es una validación externa de eso, no una estimación conjunta ni una cifra que se pueda trasladar de una cuenca a otra. Al mes 6 la brecha de Colorado es de -5,9 puntos y su IC por bloques excluye cero: la caída no se cierra del todo al mes 6, a diferencia de la lectura de recuperación de Vaca Muerta. La forma más allá del mes 1 no formó parte de la regla.
