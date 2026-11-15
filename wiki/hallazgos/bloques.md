# Bloques espaciales

Página generada por `pipeline/bloques.py`. Repite los intervalos de los resultados principales remuestreando bloques de una grilla espacial en vez de pads hijo, para ver si el intervalo por pads era optimista cuando pads vecinos comparten geología y programa de fractura. Complementa [Interferencia entre fracturas](interferencia.md), la [sincronía](sincronia.md) y la [descomposición](descomposicion.md); las reglas se fijaron antes de correr y están en el libro de hallazgos como `brecha_mes1_bloques` y `sincronia_mes0_bloques`.

## Resumen

Veredictos contra las reglas fijadas antes de correr (las estimaciones puntuales no cambian; solo cambia la unidad que se remuestrea):

- **R1, brecha del mes 1: no cruza.** El límite superior del IC por bloques de 5 km queda por debajo de -10 puntos: no cruza el umbral fijado. El rango titular de 19 a 23 puntos se mantiene; lo que cambia es el IC publicado, que pasa a ser el de bloques de 5 km.
- Brecha del mes 1 con la base de los meses -3 a -1: -22,9 puntos. IC 95% por pads: -27,4 a -18,1; por bloques de 2 km: -28,6 a -17,4 (347 bloques); por bloques de 5 km: -28,7 a -16,8 (144 bloques).
- **R2, sincronía: sostiene.** Con bloques de 5 km el límite superior del IC de la pendiente del mes 0 sigue por debajo de -0,02 y el del mes -1 no excluye cero: el veredicto se mantiene.
- Pendiente del mes 0: -2,1 puntos por cada 0,1 de f0. IC 95% por pads: -3,1 a -1,0; por bloques de 2 km: -3,4 a -0,9; por bloques de 5 km: -3,5 a -0,8 (143 bloques). Mes -1, por bloques de 5 km: -1,9 a 0,6.
- Partes al mes 1 con los meses cerrados: los días explican el 52,8% de la brecha del volumen (IC 95% por bloques de 5 km: 43,4 a 65,0) y el caudal por día el 47,2% (35,0 a 56,6).
- Ancho del IC por bloques de 5 km sobre el de pads: de 0,89 a 1,49 veces en las 15 filas.
- Pruebas estadísticas corridas en el proyecto: 191 (15 hipótesis del libro, 13 subconjuntos de robustez, 141 intervalos de la descomposición, 9 intervalos descriptivos del lado del hijo y 13 intervalos por bloques que no son hipótesis), sin ajuste por comparaciones múltiples.

## Regla fijada antes de correr

El pad hijo de cada evento se ubica en el promedio de las coordenadas de superficie de sus pozos y se proyecta a kilómetros con una proyección equirectangular alrededor de (-38,0, -69,0). El bloque es la celda de una grilla de 2 km o de 5 km. Cada IC es bootstrap de percentiles (2,5 y 97,5) con 400 repeticiones que remuestrean bloques completos, con el mismo estimador, los mismos eventos y la misma semilla por k que el intervalo por pads.

- R1: el IC del mes 1 del README y del caso pasa a ser el de bloques de 5 km si tiene 30 bloques o más. Si su límite superior queda por encima de -10 puntos, el rango 19 a 23 se reescribe con los IC por bloques de 5 km de sus dos extremos.
- R2: el veredicto de la pendiente de sincronía se vuelve a derivar con el IC de bloques de 5 km y la regla de la página de sincronía (límite superior menor que -0,02 por unidad de f0, y el mes -1 sin pendiente negativa que excluya cero).
- R3: se cuentan todas las pruebas estadísticas del proyecto en una línea (arriba).

## Resultados

Brechas en puntos de índice, pendientes en puntos por cada 0,1 de f0, partes en %. La estimación puntual es la de la página original.

| Métrica | k | Estimador | Estimación | IC 95% por pads | IC 95% por bloques de 2 km | IC 95% por bloques de 5 km |
| --- | ---: | --- | ---: | --- | --- | --- |
| `brecha_mes1_base_original` | 1 | mediana | -22,9 | -27,4 a -18,1 | -28,6 a -17,4 | -28,7 a -16,8 |
| `brecha_mes1_descontada` | 1 | mediana | -19,2 | -23,4 a -14,9 | -24,7 a -15,2 | -25,7 a -14,1 |
| `brecha_base_limpia` | -3 | mediana | -2,5 | -4,9 a -0,7 | -4,8 a -0,3 | -5,6 a -0,1 |
| `brecha_base_limpia` | -2 | mediana | -3,5 | -6,0 a -1,1 | -6,4 a -0,8 | -6,5 a -0,2 |
| `brecha_base_limpia` | -1 | mediana | -6,3 | -9,7 a -3,2 | -10,4 a -2,9 | -10,0 a -2,0 |
| `brecha_base_limpia` | 0 | mediana | -20,9 | -25,4 a -16,9 | -25,4 a -17,2 | -25,1 a -17,6 |
| `brecha_base_limpia` | 1 | mediana | -25,5 | -30,6 a -21,2 | -31,6 a -21,1 | -31,1 a -20,4 |
| `brecha_base_limpia` | 2 | mediana | -16,7 | -21,1 a -12,3 | -21,5 a -11,0 | -23,4 a -10,3 |
| `brecha_base_limpia` | 3 | mediana | -11,1 | -16,1 a -6,7 | -16,5 a -6,1 | -16,6 a -5,6 |
| `sincronia_pendiente` | 0 | pendiente | -2,1 | -3,1 a -1,0 | -3,4 a -0,9 | -3,5 a -0,8 |
| `sincronia_pendiente` | -1 | pendiente | -0,7 | -1,8 a 0,5 | -1,7 a 0,4 | -1,9 a 0,6 |
| `parte_dias` | 1 | con_cerrados | 52,8 | 45,0 a 62,2 | 42,7 a 62,0 | 43,4 a 65,0 |
| `parte_dias` | 1 | sin_cerrados | 42,2 | 35,3 a 49,9 | 33,6 a 50,4 | 33,6 a 54,5 |
| `parte_tasa` | 1 | con_cerrados | 47,2 | 37,8 a 55,0 | 38,0 a 57,3 | 35,0 a 56,6 |
| `parte_tasa` | 1 | sin_cerrados | 57,8 | 50,1 a 64,7 | 49,6 a 66,4 | 45,5 a 66,4 |

Pads y bloques con eventos, y el ancho de cada IC por bloques sobre el de pads:

| Métrica | k | Estimador | Pads hijo | Bloques de 2 km | Bloques de 5 km | Ancho de 2 km sobre pads | Ancho de 5 km sobre pads |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `brecha_mes1_base_original` | 1 | mediana | 748 | 347 | 144 | 1,20 | 1,29 |
| `brecha_mes1_descontada` | 1 | mediana | 741 | 344 | 143 | 1,11 | 1,37 |
| `brecha_base_limpia` | -3 | mediana | 742 | 345 | 143 | 1,07 | 1,33 |
| `brecha_base_limpia` | -2 | mediana | 742 | 345 | 143 | 1,15 | 1,28 |
| `brecha_base_limpia` | -1 | mediana | 742 | 345 | 143 | 1,17 | 1,23 |
| `brecha_base_limpia` | 0 | mediana | 742 | 345 | 143 | 0,96 | 0,89 |
| `brecha_base_limpia` | 1 | mediana | 741 | 344 | 143 | 1,12 | 1,14 |
| `brecha_base_limpia` | 2 | mediana | 737 | 343 | 143 | 1,20 | 1,49 |
| `brecha_base_limpia` | 3 | mediana | 734 | 342 | 143 | 1,11 | 1,18 |
| `sincronia_pendiente` | 0 | pendiente | 742 | 345 | 143 | 1,17 | 1,26 |
| `sincronia_pendiente` | -1 | pendiente | 742 | 345 | 143 | 0,91 | 1,04 |
| `parte_dias` | 1 | con_cerrados | 738 | 342 | 143 | 1,12 | 1,26 |
| `parte_dias` | 1 | sin_cerrados | 732 | 337 | 141 | 1,15 | 1,44 |
| `parte_tasa` | 1 | con_cerrados | 738 | 342 | 143 | 1,12 | 1,26 |
| `parte_tasa` | 1 | sin_cerrados | 732 | 337 | 141 | 1,15 | 1,44 |

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
