# Calendario de golpes: matrices de costo, optimizador y backtest

¿Conviene mover cuándo se fractura cada hijo para que los hijos cercanos a un padre caigan en menos meses? Esta página es la tercera pieza del optimizador de calendario. Parte de lo que midieron golpes_mismo_mes (PR #83, el modelo agrupado) y golpes_mismo_padre (PR #86, cada padre consigo mismo, que terminó «sin muestra»), valúa los dos modelos de costo posibles, calcula el calendario que menos pérdida tendría y mide si un modelo ajustado en 2023 predice la pérdida de 2024 a 2026.

## Lectura

- Backtest: **sin muestra**. El dato no decide. El entrenamiento de 2023 tiene 81 eventos aislados (28 pads del padre y 3 valores de k con al menos 10 eventos) y la regla pide 100 eventos y 20 pads. La prueba de 2024 a 2026 tiene 344 eventos en 105 pads, que alcanzan (150 y 30). Las cifras del backtest de abajo son descriptivas, no un resultado de la regla.
- Descriptivo. No es una recomendación al operador. Como la prueba de #86 quedó «sin muestra» y este backtest tampoco decide, el calendario óptimo, el arrepentimiento y los dólares de esta página salen del modelo agrupado de #83 y del ajuste de esta página: dicen qué haría el modelo, no qué conviene hacer, y no hay un calendario recomendado.
- Supuesto que sostiene el optimizador: b, el costo por hijo adicional dentro de un mes, se acota en 0 cuando sale negativo, igual que en #83 (b acotado en 0, heredado de #83). Con b = 0 todos los hijos de un mes cuestan lo mismo que uno solo, el extremo de más ahorro por agrupar, así que el arrepentimiento y los dólares son una cota superior y no una estimación. Es una decisión de la regla, no un dato.
- Descriptivo. Con #86 sin decidir un caso de costo, queda lo último publicado, el modelo agrupado de #83, y se corren los dos casos. En toda la muestra el ajuste es a = 13,9 y b = -1,7 días de base: b sale negativo, así que se acota en 0 y a pasa a ser la media de la pérdida, 7,2 días. Con b = 0 todos los hijos de un mes cuestan lo mismo que uno solo: es el extremo de más ahorro por agrupar, una decisión de la regla y no un dato.
- Descriptivo. Fuera de muestra, con el ajuste de 2023, el modelo de costo fijo más hijo predice peor que el aditivo en la estimación puntual: D = -0,127 (IC 95% -2,86 a 0,03), con habilidad -0,116 contra 0,011 del aditivo. Ninguno de los dos supera claramente a la media de 2023. El intervalo incluye el cero; con una muestra de entrenamiento que no alcanza, eso no es una prueba de que no haya diferencia.
- Descriptivo. El ajuste de 2023 no tiene un costo fijo: el aditivo sale con c = 0,00 (la media de 2023 es negativa, -5,0 días) y el fijo más hijo con a = 0,0 y b = 11,7 días, es decir, un modelo por hijo. Con ese ajuste el arrepentimiento del calendario es cero.
- Descriptivo. El arrepentimiento del calendario observado contra el óptimo (cada hijo puede moverse hasta 3 meses), caso fijo más hijo con el ajuste de toda la muestra: 3.197 (0 a 8.034) días de base en 1.032 padres (IC 95% entre paréntesis). Es una cota superior de lo que agrupar podría ahorrar si el costo fijo con b = 0 fuera real, no una estimación; en el caso aditivo es cero por construcción.
- Medido contra supuesto: lo medido es el ajuste y su puntaje fuera de muestra; lo supuesto es que el costo de un calendario es la suma del costo de sus meses y que un hijo puede moverse esos meses. De los meses de golpe de los programas, el 56% (2024 a 2026) y el 62% (toda la muestra) no son aislados, y el modelo se ajustó solo con meses aislados.

## Los dos casos de costo

Los dos modelos de la pérdida P de un mes de golpe, en días de producción de base, con k hijos a menos de 1 km fracturados en ese mes: el aditivo, P = c k, donde cada hijo cuesta lo mismo y mover hijos entre meses no cambia nada; y el fijo más hijo, P = a + b k, donde el mes cuesta a aunque tenga un solo hijo y agrupar ahorra. Se ajustan en 2023 (o en toda la muestra, para el descriptivo) y antes de usarlos se acotan: c mayor o igual que cero; b menor que cero pasa a 0 y a se vuelve la media; a menor que cero pasa a 0.

| Ajuste | Parámetro | Sin acotar | Usado | Acotado |
| --- | --- | ---: | ---: | --- |
| 2023 (entrenamiento) | c, caso aditivo (días de base por hijo) | n/d | 0,00 | sí |
| 2023 (entrenamiento) | b, caso fijo más hijo (días de base por hijo) | 11,7 | 11,7 | no |
| 2023 (entrenamiento) | a, caso fijo más hijo (días de base por mes de golpe) | n/d | 0,0 | sí |
| Muestra completa (descriptivo) | c, caso aditivo (días de base por hijo) | 1,59 | 1,59 | no |
| Muestra completa (descriptivo) | b, caso fijo más hijo (días de base por hijo) | -1,7 | 0,0 | sí |
| Muestra completa (descriptivo) | a, caso fijo más hijo (días de base por mes de golpe) | 13,9 | 7,2 | no |

En las 400 repeticiones del bootstrap de 2023, el b salió acotado en 72. El b sin acotar de 2023 es 11,7 y el de toda la muestra -1,7: el ajuste de 2023 y el de toda la muestra dicen cosas distintas sobre el signo y ninguno es una estimación firme. El c sin acotar de 2023 no se guarda: un c igual a cero solo sale de la cota.

## Matriz de costo por cantidad de hijos

La pérdida de un mes con k hijos juntos contra los mismos k hijos en k meses separados, y la razón ρ entre las dos. Más allá de k = 6 el modelo extrapola: la tabla por k de #83 respalda hasta ahí.

| Ajuste | Caso | Hijos en el mes | Pérdida juntos (días de base) | Los mismos hijos separados (días de base) | ρ (juntos sobre separados) |
| --- | --- | ---: | ---: | ---: | ---: |
| 2023 | aditivo | 1 | 0,0 | 0,0 | n/d |
| 2023 | aditivo | 2 | 0,0 | 0,0 | n/d |
| 2023 | aditivo | 3 | 0,0 | 0,0 | n/d |
| 2023 | aditivo | 4 | 0,0 | 0,0 | n/d |
| 2023 | aditivo | 5 | 0,0 | 0,0 | n/d |
| 2023 | aditivo | 6 | 0,0 | 0,0 | n/d |
| 2023 | fijo más hijo | 1 | 11,7 | 11,7 | 1,00 |
| 2023 | fijo más hijo | 2 | 23,3 | 23,3 | 1,00 |
| 2023 | fijo más hijo | 3 | 35,0 | 35,0 | 1,00 |
| 2023 | fijo más hijo | 4 | 46,6 | 46,6 | 1,00 |
| 2023 | fijo más hijo | 5 | 58,3 | 58,3 | 1,00 |
| 2023 | fijo más hijo | 6 | 70,0 | 70,0 | 1,00 |
| muestra completa | aditivo | 1 | 1,6 | 1,6 | 1,00 |
| muestra completa | aditivo | 2 | 3,2 | 3,2 | 1,00 |
| muestra completa | aditivo | 3 | 4,8 | 4,8 | 1,00 |
| muestra completa | aditivo | 4 | 6,4 | 6,4 | 1,00 |
| muestra completa | aditivo | 5 | 8,0 | 8,0 | 1,00 |
| muestra completa | aditivo | 6 | 9,6 | 9,6 | 1,00 |
| muestra completa | fijo más hijo | 1 | 7,2 | 7,2 | 1,00 |
| muestra completa | fijo más hijo | 2 | 7,2 | 14,5 | 0,50 |
| muestra completa | fijo más hijo | 3 | 7,2 | 21,7 | 0,33 |
| muestra completa | fijo más hijo | 4 | 7,2 | 29,0 | 0,25 |
| muestra completa | fijo más hijo | 5 | 7,2 | 36,2 | 0,20 |
| muestra completa | fijo más hijo | 6 | 7,2 | 43,5 | 0,17 |

## Backtest: ajustado en 2023, puntuado en 2024 a 2026

El error cuadrático medio (ECM) y el error absoluto medio de cada modelo en los eventos aislados de 2024 a 2026, y la habilidad SK = 1 - ECM / ECM de M0, donde M0 es la media de 2023. D es la habilidad del modelo fijo más hijo menos la del aditivo: D positivo dice que el costo fijo predice mejor. Las columnas S1 repiten el ajuste con la k de 12 meses y el caudal de base como controles. El intervalo es de percentiles por pads del padre, 400 repeticiones, de las que 0 se descartaron por ECM de M0 igual a cero.

| Modelo | ECM | Error absoluto medio | Habilidad contra M0 | ECM con controles (S1) | Habilidad con controles (S1) |
| --- | ---: | ---: | ---: | ---: | ---: |
| M0 (media de 2023) | 10.642,6 | 80,6 |  | 10.642,6 |  |
| Aditivo, P = c k | 10.529,7 | 78,8 | 0,011 | 9.001,0 | 0,154 |
| Fijo más hijo, P = a + b k | 11.878,0 | 76,3 | -0,116 | 9.819,5 | 0,077 |
| D = habilidad del fijo menos la del aditivo | | | -0,127 (IC 95% -2,86 a 0,03) | | -0,077 (IC 95% -3,52 a 0,02) |

### Lo predicho contra lo observado por k

| Hijos a menos de 1 km en el mes | Eventos de 2024 a 2026 | k media | Pérdida observada (días de base) | Predicha por M0 | Predicha por el aditivo | Predicha por el fijo más hijo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 7 | 1,0 | -53,6 | -5,0 | 0,0 | 11,7 |
| 2 | 23 | 2,0 | -39,6 | -5,0 | 0,0 | 23,3 |
| 3 | 67 | 3,0 | 23,1 | -5,0 | 0,0 | 35,0 |
| 4 | 149 | 4,0 | 1,5 | -5,0 | 0,0 | 46,6 |
| 5 a 6 | 92 | 5,8 | 23,0 | -5,0 | 0,0 | 67,8 |
| 7 o más | 6 | 9,8 | 69,8 | -5,0 | 0,0 | 114,6 |

## Arrepentimiento del calendario

Descriptivo, no una recomendación al operador. Arrepentimiento = costo del calendario observado menos el del óptimo, en días de base. El óptimo es exacto: con a y b no negativos agrupa los meses observados, de menor a mayor, mientras el primero y el último del grupo estén a no más de dos veces el máximo de meses que puede moverse un hijo (3 en la regla, con 1, 2 y 6 como sensibilidades). Es una entrada, no sale del dato. No hay tope de hijos por mes: la parte de los meses del programa óptimo con más de 6 hijos es una extrapolación (en 2024 a 2026, 7,2% con el máximo de 3 meses; en toda la muestra, 8,9%).

### Con el ajuste de 2023, sobre los programas de 2024 a 2026

| Caso | Máximo de meses que se mueve un hijo | Arrepentimiento (días de base) | IC 95% | Por padre (días de base) | IC 95% por padre |
| --- | ---: | ---: | ---: | ---: | ---: |
| aditivo | 1 | 0 | 0 a 0 | 0,00 | 0,00 a 0,00 |
| aditivo | 2 | 0 | 0 a 0 | 0,00 | 0,00 a 0,00 |
| aditivo | 3 (la del veredicto) | 0 | 0 a 0 | 0,00 | 0,00 a 0,00 |
| aditivo | 6 | 0 | 0 a 0 | 0,00 | 0,00 a 0,00 |
| fijo más hijo | 1 | 0 | 0 a 2.601 | 0,00 | 0,00 a 4,79 |
| fijo más hijo | 2 | 0 | 0 a 3.209 | 0,00 | 0,00 a 5,91 |
| fijo más hijo | 3 (la del veredicto) | 0 | 0 a 3.679 | 0,00 | 0,00 a 6,78 |
| fijo más hijo | 6 | 0 | 0 a 4.953 | 0,00 | 0,00 a 9,12 |

### Con el ajuste de toda la muestra (descriptivo, dentro de muestra)

| Caso | Máximo de meses que se mueve un hijo | Arrepentimiento (días de base) | IC 95% | Por padre (días de base) | IC 95% por padre |
| --- | ---: | ---: | ---: | ---: | ---: |
| aditivo | 1 | 0 | 0 a 0 | 0,00 | 0,00 a 0,00 |
| aditivo | 2 | 0 | 0 a 0 | 0,00 | 0,00 a 0,00 |
| aditivo | 3 (la del veredicto) | 0 | 0 a 0 | 0,00 | 0,00 a 0,00 |
| aditivo | 6 | 0 | 0 a 0 | 0,00 | 0,00 a 0,00 |
| fijo más hijo | 1 | 2.327 | 0 a 5.751 | 2,25 | 0,00 a 5,57 |
| fijo más hijo | 2 | 3.030 | 0 a 7.531 | 2,94 | 0,00 a 7,30 |
| fijo más hijo | 3 (la del veredicto) | 3.197 | 0 a 8.034 | 3,10 | 0,00 a 7,78 |
| fijo más hijo | 6 | 4.327 | 0 a 10.648 | 4,19 | 0,00 a 10,32 |

## Valor en dólares

Descriptivo, no una recomendación al operador. El arrepentimiento en días se pasa a volumen con el caudal de base medio de cada padre y a dólares con el costo de diferir de pipeline.decision.valor_indicativo, que es el valor tiempo de cobrar ese petróleo más tarde, no un ingreso perdido. La grilla es la de decision (precio, tasa y rezago de cobro) y son entradas ilustrativas, no un pronóstico. Celda central: 60 USD por barril, tasa 0,10 por año, rezago de 12 meses. El calendario «separado» pone cada hijo en su propio mes, para ver cuánto del costo ya evita la práctica. Los IC de cada fila son los de esa fila, no de una resta entre filas.

| Ajuste | Caso | Calendario | Padres | Días de base | m3 | USD (millones) | IC 95% (USD millones) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | aditivo | observado | 543 | 0 | 0 | 0,0 | 0,0 a 47,3 |
| 2023 | aditivo | óptimo | 543 | 0 | 0 | 0,0 | 0,0 a 47,3 |
| 2023 | aditivo | separado | 543 | 0 | 0 | 0,0 | 0,0 a 47,3 |
| 2023 | fijo más hijo | observado | 543 | 33.064 | 2.225.820 | 76,4 | 0,0 a 314,8 |
| 2023 | fijo más hijo | óptimo | 543 | 33.064 | 2.225.820 | 76,4 | 0,0 a 314,8 |
| 2023 | fijo más hijo | separado | 543 | 33.064 | 2.225.820 | 76,4 | 0,0 a 315,6 |
| muestra completa | aditivo | observado | 1.032 | 10.386 | 531.383 | 18,2 | 0,0 a 44,9 |
| muestra completa | aditivo | óptimo | 1.032 | 10.386 | 531.383 | 18,2 | 0,0 a 44,9 |
| muestra completa | aditivo | separado | 1.032 | 10.386 | 531.383 | 18,2 | 0,0 a 44,9 |
| muestra completa | fijo más hijo | observado | 1.032 | 14.011 | 662.007 | 22,7 | 0,0 a 75,2 |
| muestra completa | fijo más hijo | óptimo | 1.032 | 10.814 | 530.055 | 18,2 | 0,0 a 73,9 |
| muestra completa | fijo más hijo | separado | 1.032 | 47.288 | 2.419.494 | 83,0 | 0,0 a 201,8 |

Arrepentimiento en dólares (millones), caso fijo más hijo, con el ajuste de toda la muestra, en las 18 celdas de la grilla (máximo de 3 meses). Es el mismo arrepentimiento de arriba valuado en cada celda; el intervalo es el de la tabla en días.

| Precio (USD por barril) | Tasa por año | Rezago 6 meses | Rezago 12 meses | Rezago 24 meses |
| ---: | ---: | ---: | ---: | ---: |
| 40 | 0,10 | 1,5 | 3,0 | 5,8 |
| 40 | 0,15 | 2,2 | 4,3 | 8,1 |
| 60 | 0,10 | 2,3 | 4,5 | 8,6 |
| 60 | 0,15 | 3,4 | 6,5 | 12,1 |
| 80 | 0,10 | 3,1 | 6,0 | 11,5 |
| 80 | 0,15 | 4,5 | 8,7 | 16,2 |

El mismo arrepentimiento con el ajuste de 2023 es cero en todas las celdas, porque ese ajuste no tiene costo fijo.

## Muestra

| Muestra | Valor |
| --- | ---: |
| Eventos aislados de 2023 (entrenamiento) | 81 |
| Pads del padre de 2023 | 28 |
| Padres de 2023 | 81 |
| Valores distintos de k con al menos 10 eventos en 2023 | 3 |
| Eventos aislados de 2024 a 2026 (prueba) | 344 |
| Pads del padre de 2024 a 2026 | 105 |
| Padres con programa de 2024 a 2026 (cercanos con la ventana completa) | 543 |
| Meses de golpe de esos programas | 790 |
| Padres con programa en toda la muestra | 1.032 |
| Meses de golpe de esos programas | 1.933 |
| Eventos aislados de toda la muestra (descriptivo) | 728 |

## Regla fijada antes de correr

- La regla está en el encabezado de `pipeline/calendario_golpes.py`, en el commit `c71f3a50` que trae solo el encabezado y las constantes, anterior a cualquier cálculo de este módulo. No se cambió después de ver los resultados. Se publican todos los resultados, favorables o no: «no firme» o «sin muestra» es un resultado terminado.
- El plan decía solo «matrices de costo valuadas en la grilla de decision, bajo los dos casos, y un backtest ajustado en 2023 que predice 2024 a 2026, con b acotado a 0 o más». La regla cerró antes de calcular lo que el plan no decía: qué elige el optimizador, contra qué se compara el arrepentimiento, cómo se puntúa el backtest y con qué umbrales, cómo se acota b y qué se hace con a, y que no se corre Colorado.
- Veredicto, en orden: «sin muestra» con menos de 100 eventos o 20 pads del padre en 2023, menos de 3 valores de k con al menos 10 eventos, o menos de 150 eventos o 30 pads en 2024 a 2026; «costo aditivo» si el límite alto del IC de D es menor que cero; «sostiene» si el límite bajo del IC de D y el del arrepentimiento del caso fijo más hijo son mayores que cero; «no firme» en otro caso. El veredicto no depende de la grilla de precios.
- Qué se había mirado antes: lo publicado de #83 y #86 en las dos cuencas, incluidos los coeficientes agrupados y sus intervalos. No se había calculado ninguna cantidad de esta prueba: ni los eventos de 2023 y de 2024 a 2026, ni ningún calendario, arrepentimiento o puntaje fuera de muestra.
- El bootstrap es por pads del padre, no por los pads hijo ni por bloques de 5 km: un programa es de un padre y tiene que moverse entero.
- Colorado no se corre: su warehouse termina en 2024-12 y el backtest pide predecir hasta 2026.

## Qué no prueba

- Con dato mensual, «el mismo mes» no es «al mismo tiempo», y un hijo que se mueve 3 meses no es un hijo que se mueve en la práctica: hay que perforar, fracturar y completar en un orden que el dato público no ve. El optimizador no tiene tope de hijos ni de equipos por mes.
- Solo el lado del padre: el costo de producir un hijo antes o después y lo que el hijo pierde por el padre no están.
- La pérdida es volumen diferido contra la trayectoria de los controles en la ventana, no petróleo perdido. Los dólares son el valor tiempo de cobrarlo más tarde, con precios y tasas que son entradas.
- La referencia de la pérdida usa los controles de toda la muestra, incluidos los de 2024 a 2026: no es del todo fuera de muestra, aunque el modelo que se ajusta y se predice sí lo es.
- Un solo año de entrenamiento: los coeficientes de 2023 pueden no valer para 2024 a 2026, y el IC mide el ruido del muestreo, no ese cambio.
- El costo de un calendario como suma del de sus meses es un supuesto: los modelos se ajustaron en meses aislados y una parte grande de los meses de los programas no lo es.
