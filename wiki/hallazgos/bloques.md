# Bloques espaciales

Página generada por `pipeline/bloques.py`. Repite los intervalos de los resultados principales remuestreando bloques de una grilla espacial en vez de pads hijo, para ver si el intervalo por pads era optimista cuando pads vecinos comparten geología y programa de fractura. Complementa [Interferencia entre fracturas](interferencia.md), la [sincronía](sincronia.md) y la [descomposición](descomposicion.md); las reglas se fijaron antes de correr y están en el libro de hallazgos como `brecha_mes1_bloques` y `sincronia_mes0_bloques`.

## Resumen

Veredictos contra las reglas fijadas antes de correr (las estimaciones puntuales no cambian; solo cambia la unidad que se remuestrea):

- **R1, brecha del mes 1: no cruza.** El límite superior del IC por bloques de 5 km queda por debajo de -10 puntos: no cruza el umbral fijado. El rango titular de 19 a 23 puntos se mantiene; lo que cambia es el IC publicado, que pasa a ser el de bloques de 5 km.
- Brecha del mes 1 con la base de los meses -3 a -1: -23,0 puntos. IC 95% por pads: -27,3 a -18,2; por bloques de 2 km: -28,3 a -18,1 (350 bloques); por bloques de 5 km: -30,0 a -17,0 (145 bloques).
- **R2, sincronía: sostiene.** Con bloques de 5 km el límite superior del IC de la pendiente del mes 0 sigue por debajo de -0,02 y el del mes -1 no excluye cero: el veredicto se mantiene.
- Pendiente del mes 0: -2,1 puntos por cada 0,1 de f0. IC 95% por pads: -3,3 a -0,8; por bloques de 2 km: -3,2 a -0,8; por bloques de 5 km: -3,5 a -0,8 (145 bloques). Mes -1, por bloques de 5 km: -1,9 a 0,5.
- Partes al mes 1 con los meses cerrados: los días explican el 52,4% de la brecha del volumen (IC 95% por bloques de 5 km: 42,2 a 63,3) y el caudal por día el 47,6% (36,7 a 57,8).
- Ancho del IC por bloques de 5 km sobre el de pads: de 0,96 a 1,45 veces en las 15 filas.
- Pruebas estadísticas del libro: 193 (17 hipótesis del libro, 13 subconjuntos de robustez, 141 intervalos de la descomposición, 9 intervalos descriptivos del lado del hijo y 13 intervalos por bloques que no son hipótesis), sin ajuste por comparaciones múltiples. No cuenta los diseños causales, con sus placebos y cortes, ni las escalas de bloques ni las permutaciones de D2: esas se cuentan aparte en `inferencia.md`.

## Regla fijada antes de correr

El pad hijo de cada evento se ubica en el promedio de las coordenadas de superficie de sus pozos y se proyecta a kilómetros con una proyección equirectangular alrededor de (-38,0, -69,0). El bloque es la celda de una grilla de 2 km o de 5 km. Cada IC es bootstrap de percentiles (2,5 y 97,5) con 400 repeticiones que remuestrean bloques completos, con el mismo estimador, los mismos eventos y la misma semilla por k que el intervalo por pads.

- R1: el IC del mes 1 del README y del caso pasa a ser el de bloques de 5 km si tiene 30 bloques o más. Si su límite superior queda por encima de -10 puntos, el rango 19 a 23 se reescribe con los IC por bloques de 5 km de sus dos extremos.
- R2: el veredicto de la pendiente de sincronía se vuelve a derivar con el IC de bloques de 5 km y la regla de la página de sincronía (límite superior menor que -0,02 por unidad de f0, y el mes -1 sin pendiente negativa que excluya cero).
- R3: se cuentan todas las pruebas estadísticas del proyecto en una línea (arriba).

## Resultados

Brechas en puntos de índice, pendientes en puntos por cada 0,1 de f0, partes en %. La estimación puntual es la de la página original.

| Métrica | k | Estimador | Estimación | IC 95% por pads | IC 95% por bloques de 2 km | IC 95% por bloques de 5 km |
| --- | ---: | --- | ---: | --- | --- | --- |
| `brecha_mes1_base_original` | 1 | mediana | -23,0 | -27,3 a -18,2 | -28,3 a -18,1 | -30,0 a -17,0 |
| `brecha_mes1_descontada` | 1 | mediana | -19,3 | -23,8 a -15,0 | -24,6 a -15,2 | -25,7 a -14,3 |
| `brecha_base_limpia` | -3 | mediana | -2,5 | -4,8 a -0,6 | -5,1 a -0,7 | -5,4 a 0,1 |
| `brecha_base_limpia` | -2 | mediana | -3,6 | -6,0 a -1,3 | -6,8 a -1,0 | -6,5 a -0,7 |
| `brecha_base_limpia` | -1 | mediana | -6,3 | -9,7 a -3,5 | -10,7 a -2,8 | -10,2 a -1,7 |
| `brecha_base_limpia` | 0 | mediana | -21,0 | -25,6 a -17,5 | -25,3 a -17,6 | -25,5 a -17,8 |
| `brecha_base_limpia` | 1 | mediana | -25,6 | -31,3 a -21,2 | -31,2 a -21,3 | -32,0 a -20,7 |
| `brecha_base_limpia` | 2 | mediana | -17,0 | -21,5 a -12,9 | -22,1 a -12,4 | -23,6 a -11,1 |
| `brecha_base_limpia` | 3 | mediana | -11,6 | -16,2 a -6,9 | -15,9 a -6,4 | -16,7 a -5,9 |
| `sincronia_pendiente` | 0 | pendiente | -2,1 | -3,3 a -0,8 | -3,2 a -0,8 | -3,5 a -0,8 |
| `sincronia_pendiente` | -1 | pendiente | -0,7 | -1,9 a 0,6 | -1,7 a 0,5 | -1,9 a 0,5 |
| `parte_dias` | 1 | con_cerrados | 52,4 | 44,0 a 60,6 | 43,2 a 62,0 | 42,2 a 63,3 |
| `parte_dias` | 1 | sin_cerrados | 42,0 | 35,9 a 50,6 | 33,8 a 49,3 | 33,8 a 53,3 |
| `parte_tasa` | 1 | con_cerrados | 47,6 | 39,4 a 56,0 | 38,0 a 56,8 | 36,7 a 57,8 |
| `parte_tasa` | 1 | sin_cerrados | 58,0 | 49,4 a 64,1 | 50,7 a 66,2 | 46,7 a 66,2 |

Pads y bloques con eventos, y el ancho de cada IC por bloques sobre el de pads:

| Métrica | k | Estimador | Pads hijo | Bloques de 2 km | Bloques de 5 km | Ancho de 2 km sobre pads | Ancho de 5 km sobre pads |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `brecha_mes1_base_original` | 1 | mediana | 751 | 350 | 145 | 1,14 | 1,44 |
| `brecha_mes1_descontada` | 1 | mediana | 744 | 347 | 144 | 1,08 | 1,29 |
| `brecha_base_limpia` | -3 | mediana | 745 | 348 | 145 | 1,08 | 1,32 |
| `brecha_base_limpia` | -2 | mediana | 745 | 348 | 145 | 1,21 | 1,24 |
| `brecha_base_limpia` | -1 | mediana | 745 | 348 | 145 | 1,27 | 1,36 |
| `brecha_base_limpia` | 0 | mediana | 745 | 348 | 145 | 0,96 | 0,96 |
| `brecha_base_limpia` | 1 | mediana | 744 | 347 | 144 | 0,99 | 1,12 |
| `brecha_base_limpia` | 2 | mediana | 742 | 346 | 144 | 1,13 | 1,45 |
| `brecha_base_limpia` | 3 | mediana | 738 | 344 | 143 | 1,02 | 1,17 |
| `sincronia_pendiente` | 0 | pendiente | 745 | 348 | 145 | 0,96 | 1,08 |
| `sincronia_pendiente` | -1 | pendiente | 745 | 348 | 145 | 0,87 | 0,97 |
| `parte_dias` | 1 | con_cerrados | 741 | 345 | 144 | 1,14 | 1,27 |
| `parte_dias` | 1 | sin_cerrados | 735 | 340 | 142 | 1,05 | 1,32 |
| `parte_tasa` | 1 | con_cerrados | 741 | 345 | 144 | 1,14 | 1,27 |
| `parte_tasa` | 1 | sin_cerrados | 735 | 340 | 142 | 1,05 | 1,32 |

Las métricas, por nombre:

- `brecha_mes1_base_original`: Brecha del mes 1 con la base de los meses -3 a -1 (puntos).
- `brecha_mes1_descontada`: Brecha del mes 1 menos la del mes -1, base -6 a -4 (puntos).
- `brecha_base_limpia`: Brecha con la base de los meses -6 a -4 (puntos).
- `sincronia_pendiente`: Pendiente de la brecha por f0 (puntos por 0,1 de f0).
- `parte_dias`: Parte de los días en la brecha del volumen al mes 1 (%).
- `parte_tasa`: Parte del caudal por día en la brecha del volumen al mes 1 (%).

## Límites

- Un bloque es un proxy grueso de geología compartida: no mide la correlación espacial real ni la separa de otras fuentes de dependencia. Un IC por bloques más ancho dice que el intervalo por pads era optimista, no que el efecto sea otro.
- No hay una única grilla correcta: por eso se publican dos y la regla R1 usa solo la de 5 km.
- No se hizo la variante de pads dentro de bloques (remuestrear bloques y luego pads).
- Es una huella medida de la brecha entre padres cercanos y controles, no una prueba de causa, y los intervalos no se ajustan por comparaciones múltiples.
