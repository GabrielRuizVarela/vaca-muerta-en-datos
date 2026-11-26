# Golpes en el mismo mes: si agrupar hijos le cuesta menos al padre

Cuando se fracturan varios hijos a menos de 1 km de un padre en el mismo mes, ¿le cuesta al padre menos que si esos mismos hijos se fracturaran en meses separados? Si una parte de la pérdida es fija por mes de golpe, agrupar ahorra esa parte por cada hijo que se suma; si es toda por hijo, agrupar no ahorra nada del lado del padre. Es la primera pieza del optimizador de calendario. La regla se fijó antes de calcular; en Vaca Muerta es de regla informada (un coeficiente de costo por hijo ya se había visto) y en Colorado es confirmatoria.

## Lectura

- Vaca Muerta (regla informada): **sin pérdida medible**. La pérdida de un mes de golpe con un solo hijo no se distingue de cero, así que no hay nada medible que ahorrar agrupando: el dato no decide. Un mes con un solo hijo, a + b = 12,2 días de producción de base (IC 95% -16,6 a 45,8); 728 meses de golpe aislados, de 163 pads hijo; φ = 1,14 (IC 95% 0,41 a 1,42).
- Por qué no decide: la pérdida de un mes de golpe varía mucho de un evento a otro. En la muestra principal de Vaca Muerta el desvío es de 98,7 días contra una media de 7,2 y una mediana de 26,2.
- Colorado (confirmatoria, misma regla): **sin pérdida medible**. La pérdida de un mes de golpe con un solo hijo no se distingue de cero, así que no hay nada medible que ahorrar agrupando: el dato no decide. Un mes con un solo hijo, a + b = 29,4 días de producción de base (IC 95% -12,7 a 67,4); 630 meses de golpe aislados, de 83 pads hijo; φ = 1,07 (IC 95% -1,94 a 1,18).
- Las sensibilidades no cambian el veredicto. Las variantes en las que un mes con un solo hijo sí tiene una pérdida distinta de cero: Vaca Muerta, S1 (volumen): φ = 1,05 (IC 95% 0,04 a 1,20); Colorado, S1 (volumen): φ = 1,03 (IC 95% 0,86 a 1,10); Colorado, S2 (sin aislamiento): φ = 0,93 (IC 95% 0,64 a 1,02).
- La estimación puntual de φ va de 0,93 a 1,14 en las 6 variantes (principal, S1 y S2 de las dos cuencas): si hay una pérdida, el punto la pone casi toda en el mes de golpe y no en cada hijo. Es una estimación puntual, no un veredicto.
- Para la unidad siguiente (matrices de costo, optimizador de calendario y backtest): con este veredicto el optimizador corre los dos casos y publica el arrepentimiento con cada uno, costo aditivo por hijo y costo fijo más costo por hijo con la estimación puntual (a = 13,9 y b = -1,7 días de base). La estimación puntual de b es negativa y su IC incluye el cero: un hijo de más no puede restarle pérdida al padre, así que esa unidad tiene que decir cómo acota b antes de usarla.
- Agregado después de ver, sin cambiar el veredicto: contra la media de los controles en lugar de su mediana, a + b sería 28,8 días (IC 95% -0,4 a 64,5) en Vaca Muerta y 33,5 días (IC 95% -9,1 a 70,8) en Colorado. La sección «Diagnóstico» dice por qué se publica.

## El modelo: costo fijo del mes y costo por hijo

Mínimos cuadrados de la pérdida del mes de golpe P (días de producción de base, meses -1 a 6 contra el índice mediano de los controles) sobre la cantidad k de hijos a menos de 1 km fracturados ese mes: P = a + b k, con la distancia de los hijos, los hijos de 1 a 2 km del mismo mes, el caudal de base y efectos fijos de edad del padre, año y operador como controles. a es lo que cuesta el mes de golpe sin importar cuántos hijos traiga; b, cada hijo. Juntos, k hijos cuestan a + b k; separados, k (a + b). φ = a / (a + b) es la parte fija del costo de un mes con un solo hijo, y ρ es el costo de k hijos juntos sobre el de los mismos k separados.

| Prueba | Estadístico | Vaca Muerta | IC 95% | Colorado | IC 95% |
| --- | --- | ---: | ---: | ---: | ---: |
| Principal | a: costo fijo del mes (días de base) | 13,9 | -21,1 a 58,2 | 31,6 | -18,6 a 74,3 |
| Principal | b: costo de cada hijo (días de base) | -1,7 | -11,4 a 6,4 | -2,2 | -8,9 a 5,2 |
| Principal | a + b: un mes con un solo hijo (días de base) | 12,2 | -16,6 a 45,8 | 29,4 | -12,7 a 67,4 |
| Principal | φ = a / (a + b) | 1,14 | 0,41 a 1,42 | 1,07 | -1,94 a 1,18 |
| Principal | ρ con 2 hijos (juntos sobre separados) | 0,43 | 0,29 a 0,80 | 0,46 | 0,41 a 1,97 |
| Principal | ρ con 3 hijos (juntos sobre separados) | 0,24 | 0,05 a 0,73 | 0,28 | 0,21 a 2,29 |
| Principal | ρ con 4 hijos (juntos sobre separados) | 0,15 | -0,07 a 0,69 | 0,20 | 0,11 a 2,45 |
| Principal | ρ con 6 hijos (juntos sobre separados) | 0,05 | -0,19 a 0,66 | 0,11 | 0,02 a 2,62 |
| S1, volumen | a (m3) | 2.794 | -279 a 6.314 | 918 | 345 a 1.290 |
| S1, volumen | b (m3) | -139 | -961 a 573 | -30 | -104 a 74 |
| S1, volumen | a + b (m3) | 2.655 | 200 a 5.354 | 889 | 381 a 1.213 |
| S1, volumen | φ en volumen | 1,05 | 0,04 a 1,20 | 1,03 | 0,86 a 1,10 |
| S2, sin aislamiento | a (días de base) | 8,6 | -5,5 a 23,5 | 17,6 | 5,3 a 28,3 |
| S2, sin aislamiento | b (días de base) | 0,0 | -3,8 a 3,7 | 1,4 | -0,5 a 3,6 |
| S2, sin aislamiento | a + b (días de base) | 8,6 | -3,2 a 20,0 | 19,0 | 8,9 a 28,6 |
| S2, sin aislamiento | φ | 1,00 | -0,77 a 1,30 | 0,93 | 0,64 a 1,02 |

Los IC son de percentiles por pads hijo (400 repeticiones). Para φ y ρ se descartan las repeticiones con a + b de cero o menos: 61 en Vaca Muerta y 52 en Colorado. Error de φ (desvío de las repeticiones) en Vaca Muerta: 0,47. S1 mide lo mismo en volumen (P por el caudal de base). S2 suma los cercanos que no están aislados y controla por los hijos a menos de 2 km de los 6 meses de antes y de después.

## Pérdida por cantidad de hijos en el mes

El mismo modelo con un efecto fijo por grupo de k en lugar de la recta: la pérdida ajustada de un mes de cada grupo, sin el supuesto lineal. Es descriptiva. La última columna es la recta a + b k en la k media del grupo.

| Hijos a menos de 1 km en el mes | Eventos | Pads hijo | k media | Pérdida del mes (días de base) | IC 95% | Por hijo | IC 95% por hijo | Recta a + b k |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 22 | 16 | 1,0 | 17,6 | -46,3 a 53,3 | 17,6 | -46,3 a 53,3 | 12,2 |
| 2 | 78 | 25 | 2,0 | 6,7 | -21,5 a 50,7 | 3,4 | -10,8 a 25,3 | 10,6 |
| 3 | 137 | 42 | 3,0 | 10,8 | -22,4 a 50,7 | 3,6 | -7,5 a 16,9 | 8,9 |
| 4 | 277 | 65 | 4,0 | 4,8 | -11,9 a 19,1 | 1,2 | -3,0 a 4,8 | 7,3 |
| 5 a 6 | 208 | 34 | 5,6 | 7,7 | -12,6 a 25,1 | 1,4 | -2,3 a 4,5 | 4,6 |
| 7 o más | 6 | 1 | 9,8 | -5,1 | -46,9 a 25,8 | -0,5 | -4,8 a 2,6 | -2,4 |

## Cuánto vale

El veredicto de Vaca Muerta no es «agrupar ahorra», así que no hay ahorro que valuar: la regla fija que el valor en dinero se publica solo con ese veredicto.

## Muestra

| Muestra | Vaca Muerta | Colorado |
| --- | ---: | ---: |
| Eventos cercanos (hijo más cercano a menos de 1 km) | 2.048 | 3.531 |
| Con la ventana completa (muestra de S2) | 1.933 | 3.523 |
| Aislados con la ventana completa (muestra principal) | 728 | 630 |
| De ellos, con un solo hijo en el mes | 22 | 64 |
| Controles con la ventana completa (índice de control) | 16.845 | 50.569 |
| Pads hijo de la muestra principal | 163 | 83 |
| Padres de la muestra principal | 587 | 607 |
| Valores de k con al menos 20 eventos | 6 | 12 |

## Diagnóstico (agregado después de ver; no cambia el veredicto)

La regla mide la pérdida contra la mediana del índice de los controles, mes a mes. La pérdida de los propios controles contra esa mediana tiene media -16,6 días (IC 95% -19,6 a -13,5) en Vaca Muerta y -4,1 días (IC 95% -6,5 a -1,7) en Colorado, con mediana cerca de cero: algunos controles suben mucho y la media de los controles queda por encima de su mediana. Contra esa media, a + b sería 28,8 días (IC 95% -0,4 a 64,5) en Vaca Muerta y 33,5 días (IC 95% -9,1 a 70,8) en Colorado (el IC resta, repetición a repetición, dos remuestras independientes por pads). Se publica para que se vea cuánto pesa esa elección. Elegir la referencia después de ver sería aflojar la regla, así que el veredicto queda como está.

## Colorado (confirmatoria)

La misma regla, con las adaptaciones de pipeline.dias_perdidos a Colorado (padres horizontales, hijos con la fecha de inicio de FracFocus, el operador del último mes informado y un grupo de edad propio para los padres con el primer petróleo censurado). En Colorado no se había mirado ninguna pérdida con varios hijos en el mes antes de fijar la regla.

- Veredicto: **sin pérdida medible**. La pérdida de un mes de golpe con un solo hijo no se distingue de cero, así que no hay nada medible que ahorrar agrupando: el dato no decide. Un mes con un solo hijo, a + b = 29,4 días de producción de base (IC 95% -12,7 a 67,4); 630 meses de golpe aislados, de 83 pads hijo; φ = 1,07 (IC 95% -1,94 a 1,18).

| Hijos a menos de 1 km en el mes | Eventos | Pads hijo | k media | Pérdida del mes (días de base) | IC 95% | Por hijo | IC 95% por hijo | Recta a + b k |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 64 | 15 | 1,0 | 13,9 | -29,1 a 72,5 | 13,9 | -29,1 a 72,5 | 29,4 |
| 2 | 37 | 11 | 2,0 | 46,2 | -41,9 a 108,9 | 23,1 | -20,9 a 54,4 | 27,3 |
| 3 | 52 | 11 | 3,0 | 19,3 | -32,0 a 61,0 | 6,4 | -10,7 a 20,3 | 25,1 |
| 4 | 65 | 16 | 4,0 | 6,3 | -34,7 a 47,9 | 1,6 | -8,7 a 12,0 | 23,0 |
| 5 a 6 | 177 | 20 | 5,4 | 26,0 | -19,5 a 69,4 | 4,8 | -3,6 a 12,8 | 19,9 |
| 7 o más | 235 | 28 | 10,1 | 12,5 | -16,4 a 51,7 | 1,2 | -1,6 a 5,1 | 9,9 |

## Regla fijada antes de correr

- La regla está en el encabezado de `pipeline/golpes_mismo_mes.py`, en un commit que solo trae el encabezado y las constantes, anterior a cualquier cálculo de este módulo. No se cambió después de ver los resultados.
- Veredicto, en orden: «sin muestra» con menos de 300 eventos, de 60 pads hijo o de 3 valores de k con al menos 20 eventos; «sin pérdida medible» si el límite bajo del IC de a + b no pasa de cero; «agrupar ahorra» si el límite bajo del IC de φ es mayor que cero y φ es de al menos 0,25; «agrupar no ahorra» si el límite alto del IC de φ es menor que 0,25; «no firme» en otro caso.
- Qué se había mirado antes en Vaca Muerta: el coeficiente de hijos a menos de 1 km del modelo de costo por evento (pipeline.costo), el diferido por evento cercano y los conteos de eventos por k, sin ninguna pérdida. Por eso Vaca Muerta es de regla informada y Colorado es confirmatoria.
- Lo único agregado después de ver es la sección «Diagnóstico», que no cambia ningún veredicto.
- Aclaraciones posteriores, sin cambiar la regla, el código ni ninguna cifra: placebo.marco, que la regla nombra, también pide que la base original (meses -3 a -1) dé más de 1 m3/d, y los conteos ya la incluyen; y con la ventana de -1 a 6, dos hijos a 7 meses de distancia comparten un mes de ventana (el 6 del primero es el -1 del segundo).
- La distancia entre ramas (pipeline.trayectorias) no se usa: la prueba queda en distancia de superficie, como el resto del estudio.

## Qué no prueba

- Con dato mensual, «el mismo mes» no es «al mismo tiempo»: dos hijos del mismo mes pueden fracturarse con semanas de diferencia.
- Los hijos de un mismo mes son casi siempre del mismo pad: la comparación es entre pads de distinto tamaño tanto como entre calendarios. Los controles cubren el operador y la época, no el diseño.
- La recta en k es un supuesto; la tabla por k muestra la forma sin ella.
- La pérdida es volumen diferido contra la trayectoria de los controles en los meses -1 a 6: no dice que ese petróleo se pierda.
- Solo el lado del padre: lo que pierde el hijo por la depleción del padre no está en la prueba.
- Un padre en medio de un desarrollo continuo no entra en la muestra principal; S2 lo incluye.
- El aislamiento mira 6 meses hacia atrás y la base son los meses -6 a -4: un hijo a menos de 2 km fracturado más de 6 meses antes todavía puede caer con su golpe sobre la base del evento, y eso no se descarta.
