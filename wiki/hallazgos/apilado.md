# Estimador apilado del petróleo: una pila por evento con controles limpios emparejados

Página generada por `pipeline/stacked.py` desde `mart_apilado` y `mart_apilado_e2`. Esta es la regla fijada en el commit 857d434 antes de calcular.

## Qué estima

El diseño de `causal.md` promedia celdas de padres tratados con controles aún no tratados de toda la cuenca, y su placebo de nunca tratados da un efecto donde no debería haberlo: los padres que reciben un hijo a menos de 1 km ya rendían distinto. Acá cada evento (un padre con su primer golpe a menos de 1 km) tiene su propia pila: hasta 5 controles a 2 a 5 km de la misma edad, limpios en la ventana, emparejados por el nivel y la pendiente de la base (caliper de 0,5 desvíos de los eventos). El efecto es la diferencia del índice de caudal contra la media de sus controles, en puntos de índice; el IC 95% sale de remuestrear bloques de 5 km.

## Veredicto

**sin muestra.** ATT(1) = -15,0 puntos (IC 95%: -26,7 a -4,6), 81 eventos con efecto en e = 1 y 147 controles distintos. Placebos que rompen: ninguno. Cota RR: resiste solo con Mbar menor que 1 (se rompe con Mbar = 0,32). IC alto sin cada operador: YPF -15,8. Bloques: 26.

La muestra no alcanza el mínimo de la regla: el valor se publica pero no decide nada.

## Serie ATT(e)

| e | eventos | controles | ATT(e), puntos | IC 95% |
|---:|---:|---:|---:|---|
| -3 | 81 | 147 | 8,1 | -3,6 a 19,0 |
| -2 | 81 | 147 | 10,2 | -0,1 a 18,9 |
| -1 | 81 | 147 | 7,4 | -8,7 a 22,7 |
| 0 | 81 | 147 | -16,6 | -27,0 a -7,7 |
| 1 | 81 | 147 | -15,0 | -26,7 a -4,6 |
| 2 | 81 | 147 | -1,5 | -20,7 a 16,6 |
| 3 | 81 | 147 | 4,4 | -11,6 a 21,5 |
| 4 | 81 | 147 | 3,5 | -13,2 a 19,7 |
| 5 | 81 | 147 | 8,0 | -7,0 a 21,7 |
| 6 | 81 | 147 | 9,4 | -5,9 a 24,3 |

Los meses previos (e negativo) son un diagnóstico: con emparejamiento exacto en la base deberían quedar cerca de cero. No son un placebo; van a la cota.

## Placebos

Cada uno pasa por la misma maquinaria (candidatos, emparejamiento, ATT(1)). Rompe si su IC excluye cero y su valor absoluto es 5,0 puntos o más.

| placebo | eventos | ATT(1), puntos | IC 95% | resultado |
|---|---:|---:|---|---|
| fecha falsa | 34 | 10,8 | -8,1 a 30,9 | no rompe |
| distancia falsa | 79 | -0,8 | -16,8 a 16,1 | no rompe |
| nunca tratados | 282 | -5,0 | -9,6 a 1,6 | no rompe |

## Balance

Diferencia estandarizada de medias entre eventos y controles, antes (todos los candidatos de los eventos) y después de emparejar (controles con multiplicidad).

| variable | antes | después | controles antes | controles después |
|---|---:|---:|---:|---:|
| nivel de la base (log) | 0,42 | 0,08 | 709 | 321 |
| pendiente previa | -0,01 | -0,10 | 709 | 321 |

Eventos fuera por falta de controles: 576 de 657 con nivel y pendiente válidos. De los tratados de la cohorte, sin nivel o pendiente válida (no son evento): 1; con menos de 3 controles a 2 a 5 km dentro del caliper: 576.

## Cota de Rambachan y Roth

Con ATT(1) y los previos e = -3, -2, -1 de esta misma serie, sorteo por sorteo. Un Mbar de 1 deja que el salto posterior sea tan grande como el mayor salto previo. La cota toma el valor de e = -1 como sesgo que ya estaba y lo descuenta: con Mbar = 0 el conjunto es ATT(1) menos el valor de e = -1, no ATT(1).

| Mbar | conjunto identificado | intervalo 95% |
|---:|---|---|
| 0,00 | -22,4 a -22,4 | -37,6 a -6,4 |
| 0,25 | -26,4 a -18,3 | -44,5 a -1,2 |
| 0,50 | -30,5 a -14,3 | -53,0 a 4,7 |
| 0,75 | -34,5 a -10,2 | -60,3 a 11,8 |
| 1,00 | -38,6 a -6,1 | -68,6 a 20,2 |
| 1,25 | -42,7 a -2,1 | -76,7 a 29,5 |
| 1,50 | -46,7 a 2,0 | -86,2 a 39,3 |
| 1,75 | -50,8 a 6,0 | -97,4 a 49,3 |
| 2,00 | -54,8 a 10,1 | -108,0 a 58,3 |

Quiebre: 0,32 (Mbar del quiebre). Veredicto de la cota: **resiste solo con Mbar menor que 1**.

## Dejar un operador afuera

| sin el operador | eventos | ATT(1), puntos | IC 95% |
|---|---:|---:|---|
| YPF | 20 | -33,8 | -62,2 a -15,8 |

Bloques de 5 km con eventos que entran en e = 1: 26 (la regla pide 30).

## Lo que no dice

Aun con "sostiene" es causa bajo supuestos nombrados (tendencias paralelas condicionales al emparejamiento, anticipación acotada por la cota, sin derrame sobre controles a 2 a 5 km: lo prueba H), no un hecho físico medido.

## E2: la misma pila con donantes a 2 a 10 km

Regla fijada en el commit 82d58c0 antes de calcular (docstring de `pipeline/stacked.py`, bloque E2), desde `mart_apilado_e2`. Es E con un solo cambio: los candidatos a control están a 2 a 10 km de la boca del padre del evento, en lugar de 2 a 5. Todo lo demás es lo de E. Donantes más lejos dan más eventos pero geología menos comparable: lo que los hace comparables es emparejar por el nivel y la pendiente de la base, y el balance después de emparejar es la prueba.

El balance después de emparejar de E2 no es peor que el de E (nivel: E 0,08, E2 0,02; pendiente: E 0,10, E2 0,02, en valor absoluto).

### Veredicto

**sin muestra.** ATT(1) = -21,9 puntos (IC 95%: -30,6 a -13,4), 210 eventos con efecto en e = 1 y 324 controles distintos. Placebos que rompen: ninguno. Cota RR: resiste solo con Mbar menor que 1 (se rompe con Mbar = 0,51). IC alto sin cada operador: YPF -11,3. Bloques: 44.

La muestra no alcanza el mínimo de la regla: el valor se publica pero no decide nada.

### Serie ATT(e)

| e | eventos | controles | ATT(e), puntos | IC 95% |
|---:|---:|---:|---:|---|
| -3 | 209 | 321 | -1,1 | -9,4 a 7,5 |
| -2 | 210 | 324 | 1,7 | -5,9 a 8,3 |
| -1 | 210 | 324 | -2,4 | -10,4 a 8,4 |
| 0 | 210 | 324 | -23,2 | -33,1 a -13,3 |
| 1 | 210 | 324 | -21,9 | -30,6 a -13,4 |
| 2 | 210 | 324 | -6,5 | -17,8 a 4,3 |
| 3 | 210 | 324 | 3,4 | -5,7 a 13,1 |
| 4 | 210 | 324 | 5,8 | -2,8 a 14,0 |
| 5 | 210 | 324 | 6,4 | -3,6 a 15,6 |
| 6 | 208 | 323 | 11,9 | 1,3 a 21,8 |

Los meses previos (e negativo) son un diagnóstico: con emparejamiento exacto en la base deberían quedar cerca de cero. No son un placebo; van a la cota.

### Placebos

Cada uno pasa por la misma maquinaria (candidatos, emparejamiento, ATT(1)). Rompe si su IC excluye cero y su valor absoluto es 5,0 puntos o más.

| placebo | eventos | ATT(1), puntos | IC 95% | resultado |
|---|---:|---:|---|---|
| fecha falsa | 78 | 6,7 | -7,1 a 20,8 | no rompe |
| distancia falsa | 146 | -1,6 | -12,7 a 10,4 | no rompe |
| nunca tratados | 509 | -1,8 | -6,0 a 3,0 | no rompe |

### Balance

Diferencia estandarizada de medias entre eventos y controles, antes (todos los candidatos de los eventos) y después de emparejar (controles con multiplicidad).

| variable | antes | después | controles antes | controles después |
|---|---:|---:|---:|---:|
| nivel de la base (log) | 0,24 | 0,02 | 3.541 | 923 |
| pendiente previa | -0,14 | -0,02 | 3.541 | 923 |

Eventos fuera por falta de controles: 447 de 657 con nivel y pendiente válidos. De los tratados de la cohorte, sin nivel o pendiente válida (no son evento): 1; con menos de 3 controles a 2 a 10 km dentro del caliper: 447.

### Cota de Rambachan y Roth

Con ATT(1) y los previos e = -3, -2, -1 de esta misma serie, sorteo por sorteo. Un Mbar de 1 deja que el salto posterior sea tan grande como el mayor salto previo. La cota toma el valor de e = -1 como sesgo que ya estaba y lo descuenta: con Mbar = 0 el conjunto es ATT(1) menos el valor de e = -1, no ATT(1).

| Mbar | conjunto identificado | intervalo 95% |
|---:|---|---|
| 0,00 | -19,5 a -19,5 | -30,3 a -10,3 |
| 0,25 | -21,6 a -17,5 | -32,9 a -5,4 |
| 0,50 | -23,6 a -15,4 | -36,0 a -0,2 |
| 0,75 | -25,6 a -13,4 | -39,1 a 4,8 |
| 1,00 | -27,7 a -11,3 | -43,0 a 10,9 |
| 1,25 | -29,7 a -9,3 | -48,6 a 16,1 |
| 1,50 | -31,8 a -7,2 | -53,4 a 21,5 |
| 1,75 | -33,8 a -5,2 | -58,7 a 26,8 |
| 2,00 | -35,9 a -3,2 | -64,3 a 32,4 |

Quiebre: 0,51 (Mbar del quiebre). Veredicto de la cota: **resiste solo con Mbar menor que 1**.

### Dejar un operador afuera

| sin el operador | eventos | ATT(1), puntos | IC 95% |
|---|---:|---:|---|
| YPF | 45 | -30,3 | -53,3 a -11,3 |

Bloques de 5 km con eventos que entran en e = 1: 44 (la regla pide 30).

Lo que no dice E2: lo mismo que arriba, con controles a 2 a 10 km en lugar de 2 a 5 (el derrame sobre ese anillo más ancho lo prueba H solo hasta lo que H mide).
