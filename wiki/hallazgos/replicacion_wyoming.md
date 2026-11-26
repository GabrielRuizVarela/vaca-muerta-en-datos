# Replicación en Wyoming (WOGCC)

Página generada por `pipeline/replicacion.py` sobre el warehouse de Wyoming (`data/wyoming/warehouse.duckdb`). Corre, sin cambiarlos, los estimadores del estudio de eventos de Vaca Muerta (`pipeline/placebo.py` y la clave de bloque de `pipeline/bloques.py`) sobre las tablas que armó `pipeline/wyoming` ([datos y conteos](wyoming_datos.md)). La regla se fijó antes de correr, en el commit d4a7355, antes de bajar la producción de Wyoming, y está en el libro de hallazgos como `replicacion_wyoming`. Complementa [Interferencia entre fracturas](interferencia.md) y [Bloques espaciales](bloques.md).

## Resumen

Veredicto contra la regla fijada antes de correr: **no se replica**. El límite superior del IC por bloques de 5 km de la brecha del mes 1 no queda por debajo de cero y la brecha previa a la terminación con base limpia no es menor, en valor absoluto, que la del mes 1. La segunda condición es una barrera baja: pide una brecha previa menor que la del mes 1, no una brecha previa igual a cero. Con base limpia la brecha del mes -1 (-11,9, IC 95% por bloques de 5 km: -20,0 a -6,5) y la del mes -2 (-5,0, IC: -11,0 a 0,7) no excluyen ambas cero. Medida por día producido, la brecha del mes 1 no es menor que por día calendario. Es la lectura de una cuenca, con las limitaciones de abajo, y no una afirmación causal.

- Brecha del mes 1 (padres horizontales a menos de 1 km frente a controles de 2 a 5 km, base de los meses -3 a -1): -2,5 puntos. IC 95% por pads hijo: -4,8 a 1,3; por bloques de 5 km: -5,5 a 2,2 (158 bloques).
- Brecha previa a la terminación con base limpia (mes -1, base de los meses -6 a -4): -11,9 puntos (IC 95% por bloques de 5 km: -20,0 a -6,5).
- Valor de la hipótesis: 0,095, el mayor entre el límite superior del IC por bloques, 0,022, y la diferencia de valores absolutos (previa menos mes 1), 0,095; se replica si es menor que cero.
- Eventos con dato al mes 1: 353 cercanos y 2.286 controles, de 292 pads hijo y 158 bloques de 5 km.
- Los resultados secundarios (pretendencia, mes 6, placebo con fechas corridas, robustez) se publican completos abajo; no son veredictos.

## Regla fijada antes de correr

Se replica si la brecha del mes 1 (mediana del índice de los padres cercanos menos la de los controles, base de los meses -3 a -1, padres a menos de 1 km y controles de 2 a 5 km, con los filtros de `pipeline/wyoming/__init__.py` (los de Colorado)) es negativa con un IC 95% que excluye cero, y si la brecha previa con base limpia (mes -1, base de los meses -6 a -4) es menor, en valor absoluto, que la del mes 1. Si no, no se replica. La lectura usa el IC por bloques espaciales de 5 km; el IC por pads hijo se publica al lado. Después de ver el primer resultado, a raíz de la revisión, se corrigió la lectura de FIRSTCOMP (no la regla de lectura ni los filtros): un valor de siete dígitos que se lee como fecha válida de dos maneras (AAAAMDD y AAAAMMD) es ambiguo y el pozo queda fuera de los hijos. Antes de la corrección: 1.177 hijos, 356 eventos cercanos y 2.291 controles, brecha del mes 1 de -2,5 puntos (IC por bloques de 5 km: -5,3 a 3,0), brecha previa de -12,1 y valor 0,096; tampoco se replicaba.

## Brecha por mes, con los dos intervalos

Índice = caudal de petróleo del mes sobre la media de la base; brecha = mediana de los cercanos menos mediana de los controles, en puntos de índice. k = 0 es el mes de la terminación del hijo.

| Base | k | Eventos cercanos | Eventos de control | Brecha (puntos) | IC 95% por pads | IC 95% por bloques de 5 km | Bloques |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| Meses -3 a -1 | 1 | 353 | 2.286 | -2,5 | -4,8 a 1,3 | -5,5 a 2,2 | 158 |
| Meses -3 a -1 | 6 | 353 | 2.286 | -5,7 | -10,3 a 1,8 | -11,3 a 2,9 | 158 |
| Meses -6 a -4 | -3 | 352 | 2.274 | -2,1 | -5,1 a 0,9 | -6,0 a 2,3 | 158 |
| Meses -6 a -4 | -2 | 352 | 2.274 | -5,0 | -8,8 a 0,0 | -11,0 a 0,7 | 158 |
| Meses -6 a -4 | -1 | 352 | 2.274 | -11,9 | -18,2 a -6,5 | -20,0 a -6,5 | 158 |
| Meses -6 a -4 | 0 | 352 | 2.274 | -13,4 | -20,0 a -6,6 | -20,1 a -4,9 | 158 |
| Meses -6 a -4 | 1 | 352 | 2.274 | -8,1 | -13,2 a 0,0 | -14,8 a 1,8 | 158 |
| Meses -6 a -4 | 2 | 352 | 2.274 | -8,3 | -14,3 a -0,3 | -16,0 a 0,9 | 158 |
| Meses -6 a -4 | 3 | 352 | 2.274 | -10,0 | -15,8 a -3,5 | -18,0 a -0,7 | 158 |

Con la base de los meses -6 a -4 los meses -3 a -1 son la pretendencia (la brecha previa a la terminación); con la base de los meses -3 a -1 el mes 1 es el resultado del veredicto y el mes 6 mide cuánto queda de la brecha. Al mes 6 la brecha es de -5,7 puntos; su IC por bloques incluye cero.

## Placebo con la fecha de terminación corrida

Se corre la fecha de terminación de todos los hijos 12 meses (hacia atrás y hacia adelante), se conservan los pares padre e hijo y se exige que el padre cumpla las mismas reglas en la fecha falsa (la misma máquina de `pipeline/placebo.py`, IC por pads). Con -12 meses la fecha falsa cae antes de la terminación real y es el placebo limpio; con +12 el mes falso puede caer sobre meses ya afectados, así que no refuta nada por sí solo.

| Desplazamiento (meses) | Eventos cercanos | Brecha del mes 1 (puntos) | IC 95% por pads | Brecha real en los mismos eventos (puntos) |
| ---: | ---: | ---: | --- | ---: |
| -12 | 159 | -1,1 | -6,9 a 3,1 | 1,4 |
| 12 | 358 | -0,7 | -2,0 a 0,7 | -2,5 |

## Robustez a los dos riesgos de la memoria de factibilidad

Un solo corte, sin veredicto adicional: padres horizontales (el corte principal) frente a todos los padres, y caudal por día calendario (el principal) frente a caudal por día producido (petróleo del mes sobre sus días efectivos; un mes sin días efectivos queda sin dato). Cada fila recalcula el mes 1 y la brecha previa del mes -1 con su propia regla.

| Corte | Eventos cercanos | Eventos de control | Brecha del mes 1 (puntos) | IC 95% por pads | IC 95% por bloques de 5 km | Brecha previa del mes -1 (puntos) |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Principal (padres horizontales, caudal por día calendario) | 353 | 2.286 | -2,5 | -4,8 a 1,3 | -5,5 a 2,2 | -11,9 |
| Todos los padres (horizontales, verticales y sin dato) | 949 | 9.346 | -2,5 | -4,8 a 0,3 | -5,3 a 0,1 | -10,4 |
| Caudal por día producido (petróleo sobre días efectivos) | 353 | 2.267 | -3,1 | -5,9 a -0,1 | -6,5 a 1,7 | -10,0 |

Medida por día producido la brecha del mes 1 no es menor en valor absoluto que por día calendario. En la medida principal un mes cerrado entra con caudal cero; por día producido queda sin dato. La brecha no depende entonces de meses o días sin producir.

## Recuentos

| Concepto | Cantidad |
| --- | ---: |
| Hijos (regla fijada de Wyoming) | 1.163 |
| Pads hijo | 456 |
| Bloques de 5 km con algún hijo | 242 |
| Eventos cercanos (a menos de 1 km) | 353 |
| Eventos intermedios (de 1 a 2 km, fuera de la brecha) | 475 |
| Eventos de control (de 2 a 5 km) | 2.286 |
| Padres distintos entre los eventos cercanos | 231 |
| Padres distintos entre los eventos de control | 696 |
| Eventos cercanos con dato al mes 1 | 353 |
| Eventos de control con dato al mes 1 | 2.286 |
| Pads hijo en la brecha del mes 1 | 292 |
| Bloques de 5 km en la brecha del mes 1 | 158 |

## Qué Wyoming no puede mostrar

- No hay fecha de fractura: el mes 0 de cada hijo es el mes de FIRSTCOMP, la fecha de primera terminación del regulador. Un error de semanas o meses entre la terminación y la fractura mueve el mes 0, y un refrac no se distingue de un hijo nuevo porque hay una sola fecha por pozo. Si la terminación cae después de la fractura, el mes 0 queda corrido hacia adelante y la base de los meses -3 a -1 incluye meses posteriores a ella: la lectura no separa "no hay huella" de "el mes 0 está corrido", y los conteos de la página de datos muestran cuánto se parece el mes de FIRSTCOMP al del primer petróleo.
- No hay etapas ni arena: el largo de rama es un proxy (profundidad medida menos vertical) y no se corre ningún resultado que dependa de ellas. TD se toma como profundidad vertical sin que se haya podido confirmar.
- La columna de dirección del encabezado no se usa: no distingue un pozo horizontal (marca 'H' en la mitad de los pozos). Un pozo es horizontal por TD y MD, sin trayectorias.
- La convención de reporte difiere: una fila por pozo y año con doce columnas por mes, que se abre en pozo-mes; los días son el máximo entre filas y un código de días fuera de 0 a 31 (casi siempre 99) se toma como desconocido.
- Los pozos con producción que no están en los encabezados no tienen coordenadas ni FIRSTCOMP y no entran como hijos, padres ni controles; no se midió cuánto cambiaría una cifra si entraran.
- La unidad (barriles de petróleo) es la convención del regulador y no está escrita en el archivo.
- Es una huella medida contra un control, sin ajuste por comparaciones múltiples; no se afirma causalidad.

## Qué significa para el resultado de Vaca Muerta

La huella no se confirma en Wyoming con los mismos estimadores y la regla fijada de antemano, y se publica así. Esta cuenca sola no confirma ni desmiente el resultado de Vaca Muerta: se lee junto con las otras cuencas, no sola. No es una estimación conjunta ni cambia las cifras de Vaca Muerta.
