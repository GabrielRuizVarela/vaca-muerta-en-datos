# Golpes en el mismo mes, con el padre como su propio control

Cuando se fracturan varios hijos a menos de 1 km de un padre en el mismo mes, ¿le cuesta al padre menos que si esos mismos hijos se fracturaran en meses separados? El modelo agrupado de pipeline.golpes_mismo_mes no pudo decidirlo: la pérdida de un mes de golpe varía mucho de un padre a otro y los intervalos incluían el cero. Acá cada padre se compara consigo mismo: los padres con 2 meses de golpe aislados o más y con distinta cantidad de hijos en cada uno aportan la diferencia de su pérdida entre un mes y otro, y lo que es propio del padre (su roca, su caudal, su operador, su terminación) queda fuera de b. Es la segunda pieza del optimizador de calendario: la unidad siguiente son las matrices de costo, el optimizador y el backtest.

## Lectura

- Vaca Muerta (regla informada): **sin muestra**. No hay eventos suficientes para aplicar la regla: el dato no decide. La muestra de partida tiene 728 meses de golpe aislados con la ventana completa, de 587 padres; 118 de esos padres tienen 2 meses de golpe o más y 87 tienen además 2 valores distintos de k, así que la muestra restringida queda en 197 meses de golpe de 87 padres. La regla pide 150 padres y 400 meses de golpe.
- Colorado (confirmatoria, misma regla): **sin muestra**. No hay eventos suficientes para aplicar la regla: el dato no decide. La muestra de partida tiene 630 meses de golpe aislados con la ventana completa, de 607 padres; 23 de esos padres tienen 2 meses de golpe o más y 19 tienen además 2 valores distintos de k, así que la muestra restringida queda en 38 meses de golpe de 19 padres. La regla pide 150 padres y 400 meses de golpe.
- Descriptivo, la muestra no alcanza y no es una estimación de la que la regla pueda decir algo. El costo por hijo es b = 24,5 días de producción de base (IC 95% -16,7 a 64,3); 56 de 400 repeticiones del bootstrap dieron b menor que cero.
- Descriptivo, la muestra no alcanza y no es una estimación de la que la regla pueda decir algo. Comparación con el modelo agrupado de pipeline.golpes_mismo_mes (PR #83) sobre la misma muestra de padres, sin efecto fijo de padre: b = 19,0 días de producción de base (IC 95% -4,2 a 46,5) contra b = 24,5 días de producción de base (IC 95% -16,7 a 64,3) de comparar cada padre consigo mismo. Es descriptiva: no cambia el veredicto.
- Para la unidad siguiente (matrices de costo, optimizador de calendario y backtest): esta prueba no aporta ningún valor de a ni de b, y la estimación puntual de esta página no se usa. Con «sin muestra» queda lo último publicado, el modelo agrupado de pipeline.golpes_mismo_mes (PR #83): el optimizador corre los dos casos, costo aditivo por hijo y costo fijo más costo por hijo con esa estimación puntual, con b acotado a 0 o más antes de usarla, y publica el arrepentimiento con cada uno.

## El modelo

Mínimos cuadrados con efecto fijo de padre: P_it = alpha_i + b k_it + gamma' X_it, con i el padre y t su mes de golpe. P es la pérdida del mes de golpe en días de producción de base (meses -1 a 6 contra el índice mediano de los controles), k la cantidad de hijos a menos de 1 km fracturados ese mes, y X los efectos fijos del grupo de edad del padre al momento del golpe y del año del golpe. La transformación intra-padre resta a cada variable la media de los meses de su padre, así que lo propio del padre queda fuera de b. a es la media entre padres de alpha_i, con los controles centrados en la media de las medias de cada padre: no depende de qué categoría de edad o de año sea la de referencia. Un mes con un solo hijo cuesta a + b; juntos, k hijos cuestan a + b k; separados, k (a + b). φ = a / (a + b) es la parte fija del costo de un mes con un solo hijo, y ρ es el costo de k hijos juntos sobre el de los mismos k separados.

| Prueba | Estadístico | Vaca Muerta | IC 95% | Colorado | IC 95% |
| --- | --- | ---: | ---: | ---: | ---: |
| Principal (cada padre consigo mismo) | a: costo fijo del mes (días de base) | -105,4 | -281,3 a 70,0 | 50,7 | -213,0 a 61,1 |
| Principal (cada padre consigo mismo) | b: costo de cada hijo (días de base) | 24,5 | -16,7 a 64,3 | -1,1 | -1,4 a 52,6 |
| Principal (cada padre consigo mismo) | a + b: un mes con un solo hijo (días de base) | -80,9 | -215,9 a 55,8 | 49,6 | -160,4 a 60,0 |
| Principal (cada padre consigo mismo) | φ = a / (a + b) | n/d |  | 1,02 | -2,82 a 1,03 |
| Principal (cada padre consigo mismo) | ρ con 2 hijos (juntos sobre separados) | n/d |  | 0,49 | 0,48 a 2,41 |
| Principal (cada padre consigo mismo) | ρ con 3 hijos (juntos sobre separados) | n/d |  | 0,32 | 0,31 a 2,88 |
| Principal (cada padre consigo mismo) | ρ con 4 hijos (juntos sobre separados) | n/d |  | 0,23 | 0,23 a 3,11 |
| Principal (cada padre consigo mismo) | ρ con 6 hijos (juntos sobre separados) | n/d |  | 0,15 | 0,14 a 3,35 |
| S1, volumen | a (m3) | 847 | -3.700 a 5.709 | 1.836 | -4.676 a 2.189 |
| S1, volumen | b (m3) | 21 | -1.074 a 1.139 | -81 | -95 a 1.812 |
| S1, volumen | a + b (m3) | 868 | -2.557 a 4.633 | 1.755 | -2.864 a 2.106 |
| S1, volumen | φ en volumen | 0,98 | -0,83 a 1,29 | 1,05 | -0,12 a 1,06 |
| S2, más controles | a (días de base) | -104,3 | -201,3 a 54,3 | -36,7 | -35.012,9 a 8.168,9 |
| S2, más controles | b (días de base) | 24,2 | -14,0 a 48,5 | 11,5 | -2.194,5 a 8.006,9 |
| S2, más controles | a + b (días de base) | -80,1 | -153,2 a 42,2 | -25,2 | -27.006,0 a 6.078,3 |
| S2, más controles | φ | n/d |  | n/d |  |
| Agrupado de #83, misma muestra | a (días de base) | -84,9 | -213,2 a 24,1 | 15,7 | -1.888,9 a 2.362,1 |
| Agrupado de #83, misma muestra | b (días de base) | 19,0 | -4,2 a 46,5 | 3,9 | -859,4 a 495,7 |
| Agrupado de #83, misma muestra | a + b (días de base) | -65,9 | -166,0 a 20,0 | 19,7 | -1.393,2 a 1.502,7 |
| Agrupado de #83, misma muestra | φ | n/d |  | 0,80 | 0,62 a 1,57 |

Los IC son de percentiles por pads del padre (400 repeticiones). Para φ y ρ se descartan las repeticiones con a + b de cero o menos: 346 en Vaca Muerta y 111 en Colorado. Error de φ (desvío de las repeticiones) en Vaca Muerta: 0,41. Con la muestra por debajo de lo que pide la regla, estas cifras se publican porque la regla manda publicar todos los resultados, no como estimaciones: con tan pocos pads del padre en el bootstrap los intervalos no informan, y un a + b negativo no tiene lectura como costo.

## Pérdida por cantidad de hijos en el mes

Descriptivo: en la muestra restringida, la cantidad de hijos que trae el mes de golpe, la pérdida media del mes y el desvío de la pérdida de cada mes respecto de la media de los meses de su propio padre. No lleva intervalos: es la forma de la muestra, no una estimación.

| Hijos a menos de 1 km en el mes | Meses de golpe | Padres | k media | Pérdida media (días de base) | Desvío dentro del padre |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 5 | 5 | 1,0 | 36,3 | -7,9 |
| 2 | 18 | 17 | 2,0 | -58,6 | -32,6 |
| 3 | 27 | 27 | 3,0 | -16,1 | 18,6 |
| 4 | 71 | 61 | 4,0 | -13,2 | -11,5 |
| 5 a 6 | 76 | 57 | 5,3 | 12,2 | 12,4 |
| 7 o más | 0 | 0 | | | |

## Muestra

| Muestra | Vaca Muerta | Colorado |
| --- | ---: | ---: |
| Meses de golpe aislados con la ventana completa (muestra de partida) | 728 | 630 |
| Padres de la muestra de partida | 587 | 607 |
| De ellos, con dos o más meses de golpe | 118 | 23 |
| De ellos, con distinta cantidad de hijos entre esos meses | 87 | 19 |
| Meses de golpe de la muestra restringida | 197 | 38 |
| Padres de la muestra restringida | 87 | 19 |
| Pads del padre de la muestra restringida | 39 | 4 |
| Valores distintos de k | 6 | 5 |
| Meses de golpe por padre (media) | 2 | 2 |
| Último mes de producción | 2026-10 | 2024-12 |

## Colorado (confirmatoria)

La misma regla, con las adaptaciones de pipeline.dias_perdidos a Colorado (padres horizontales, hijos con la fecha de inicio de FracFocus, el operador del último mes informado y un grupo de edad propio para los padres con el primer petróleo censurado). En Colorado no se había mirado ninguna pérdida dentro de un padre antes de fijar la regla.

- Veredicto: **sin muestra**. No hay eventos suficientes para aplicar la regla: el dato no decide. La muestra de partida tiene 630 meses de golpe aislados con la ventana completa, de 607 padres; 23 de esos padres tienen 2 meses de golpe o más y 19 tienen además 2 valores distintos de k, así que la muestra restringida queda en 38 meses de golpe de 19 padres. La regla pide 150 padres y 400 meses de golpe.

| Hijos a menos de 1 km en el mes | Meses de golpe | Padres | k media | Pérdida media (días de base) | Desvío dentro del padre |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 15 | 15 | 1,0 | 54,9 | 5,0 |
| 2 | 0 | 0 | | | |
| 3 | 3 | 3 | 3,0 | 66,3 | -4,0 |
| 4 | 3 | 3 | 4,0 | 7,0 | -16,0 |
| 5 a 6 | 4 | 4 | 5,0 | 50,0 | 32,8 |
| 7 o más | 13 | 13 | 16,0 | 30,3 | -11,2 |

## Regla fijada antes de correr

- La regla está en el encabezado de `pipeline/golpes_mismo_padre.py`, en un commit que solo trae el encabezado y las constantes, anterior a cualquier cálculo de este módulo. No se cambió después de ver los resultados. Se publican todos los resultados, favorables o no: «no firme» o «sin muestra» es un resultado terminado, no se rediseña la regla para evitarlo.
- Veredicto, en orden: «sin muestra» con menos de 150 padres o menos de 400 meses de golpe en la muestra restringida; «sin pérdida medible» si el límite bajo del IC de a + b no pasa de cero; «agrupar ahorra» si el límite bajo del IC de φ es mayor que cero y φ es de al menos 0,25; «agrupar no ahorra» si el límite alto del IC de φ es menor que 0,25; «no firme» en otro caso.
- Qué se había mirado antes: todo lo publicado de pipeline.golpes_mismo_mes (PR #83), en las dos cuencas: el modelo agrupado P = a + b k con controles, sus intervalos y el veredicto de esa prueba. Lo que NO se había calculado era ninguna cantidad de esta prueba: ni cuántos padres tienen dos o más meses de golpe aislados, ni cuántos de ellos con distinta k, ni ninguna pérdida dentro de un padre. El tamaño de la muestra restringida se ve por primera vez cuando corre el módulo, y puede ser «sin muestra».
- Por eso en Vaca Muerta la prueba es de regla informada y en Colorado es confirmatoria, en el sentido de #81 y #83: la misma regla, corrida después de Vaca Muerta y sin tocarla.
- El bootstrap es por pads del padre, no por los pads hijo de #83 ni por el bootstrap espacial de 5 km: la dependencia que importa aquí es la de los padres de un mismo pad, que comparten hijos. Cada pad remuestreado cuenta como un padre distinto.
- Datos: el warehouse con el último mes de producción de 2026-10; Colorado, 2024-12.

## Qué no prueba

- Con dato mensual, «el mismo mes» no es «al mismo tiempo»: dos hijos del mismo mes pueden fracturarse con semanas de diferencia.
- Solo los padres con distinta k identifican b: un padre cuyos golpes tienen la misma k no aporta nada a b. Los padres que entran son los que vivieron más de un desarrollo separado, con otro pad hijo, otro tamaño y otra época; el efecto fijo de padre absorbe lo estable del padre, no lo que cambia entre un golpe y otro (la edad y el año entran como controles, el diseño del pad hijo no).
- La pérdida es volumen diferido contra la trayectoria de los controles en la ventana: no dice que ese petróleo se pierda.
- Solo el lado del padre: lo que pierde el hijo por la depleción del padre no está en la prueba.
- El aislamiento mira 6 meses hacia atrás y la base son los meses -6 a -4: dos golpes aislados del mismo padre tienen que estar al menos a 7 meses de distancia.
