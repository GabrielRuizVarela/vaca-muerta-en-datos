# Alcance y dilución de la huella medidos entre ramas

Hasta acá, la distancia entre un hijo y un padre es la de sus bocas en superficie. La página de trayectorias (`trayectorias.md`) mostró que esa distancia clasifica mal los pares: hay pares cercanos en superficie con las ramas lejos y pares de control con las ramas cerca. Esta página repite el alcance y la dilución de la huella con la distancia entre ramas: la menor distancia en planta entre la rama del hijo y la del padre. La regla se fijó antes de calcular ninguna cifra, en el commit 76d9831. Se publican todos los resultados, favorables o no.

Esta página la escribe `python -m pipeline.wiki` con `pipeline.alcance_rama.pagina_alcance_rama`. No se edita a mano.

## Lectura

- Muestra: Son 10.173 eventos (el 42% de los 24.033 eventos del estudio) con la rama del hijo y la del padre medidas, en 89 bloques de 5 km. Las trayectorias laterales cubren el 86% de los hijos horizontales fracturados de 2016 a 2023 pero solo el 39% de los de 2024 y el 25% de los de 2025, así que la muestra es sobre todo de 2016 a 2023: el 82% de los eventos son de hijos fracturados hasta 2023.
- Alcance (H-R1): **alcance medido**. La brecha del mes 1 llega hasta 1.000 m entre ramas (borde superior de la última banda cuyo intervalo excluye cero) y no se distingue de cero entre 1.000 y 2.000 m. A menos de 300 m la brecha es -50,3 puntos (IC 95%: -60,2 a -40,4).
- Dilución (H-R2): **no se separa**. Medido entre ramas, la brecha de los padres a menos de 600 m (A, -28,2 puntos) y la medida por superficie con los mismos eventos (B, -24,2 puntos) no se distinguen: A menos B es -4,1 puntos (IC 95%: -11,7 a 2,7). Medir entre ramas no cambia la lectura.
- Control (H-R3): **control contaminado**. Los controles de 2 a 5 km con la rama a menos de 1.000 m de la del hijo rinden 7,8 puntos menos (IC 95% de la diferencia: -13,9 a -3,1) que los de 2.000 m o más (783 y 5.782 eventos). Contra el control lateral limpio la brecha del mes 1 es -22,7 puntos (IC 95%: -29,5 a -16,5) y contra el control de superficie -23,0 (IC 95%: -29,5 a -16,9): los intervalos se solapan y no se ve que el control de superficie subestime la brecha. La regla esperaba que el control de superficie subestimara el diferido; el recálculo descriptivo de la tabla de más abajo no lo muestra: los intervalos del diferido de los meses 0 a 6 se solapan.
- Previa (descriptivo): un mes antes de la fractura (base de los meses -6 a -4) la banda de 0 a 300 m ya estaba 8,0 puntos abajo del control lateral (IC 95% de la brecha: -13,5 a -1,6). Parte de la brecha existía antes de la fractura, y el alcance se lee con eso en cuenta.
- Nada de esto cambia los 19 a 23 puntos del estudio, que siguen en distancia de superficie.

## H-R1: la brecha del mes 1 por banda de distancia entre ramas

| Banda | Eventos | Brecha (puntos) | IC 95% | Un mes antes (puntos, IC; base de los meses -6 a -4) |
|---|---|---|---|---|
| 0 a 300 m | 360 | -50,3 | -60,2 a -40,4 | -8,0 (-13,5 a -1,6) |
| 300 a 600 m | 729 | -20,5 | -27,0 a -15,2 | -3,7 (-7,4 a 0,7) |
| 600 a 1.000 m | 968 | -9,0 | -13,8 a -4,4 | -5,7 (-9,1 a -3,1) |
| 1.000 a 2.000 m | 2.195 | -1,5 | -4,6 a 1,2 | -1,7 (-5,5 a 1,2) |
| Control lateral (2.000 m o más) | 5.918 | referencia | referencia | referencia |

Brecha = mediana del índice del mes 1 de la banda menos la del control lateral, en puntos de índice.

## H-R2: la dilución

| Medida | Padres cercanos | Eventos | Control | Eventos | Brecha | IC 95% |
|---|---|---|---|---|---|---|
| A (entre ramas) | menos de 600 m entre ramas | 1.089 | control lateral (2.000 m o más) | 5.918 | -28,2 | -36,3 a -22,7 |
| B (superficie) | menos de 1 km en superficie | 921 | 2 a 5 km en superficie | 7.872 | -24,2 | -32,0 a -16,8 |
| A menos B | n/d | n/d | n/d | n/d | -4,1 | -11,7 a 2,7 |

## H-R3: el control de superficie

| Grupo | Eventos | Descripción |
|---|---|---|
| Contaminado | 783 | control de superficie (2 a 5 km) con la rama a menos de 1.000 m de la del hijo |
| Limpio | 5.782 | control de superficie (2 a 5 km) con la rama a 2.000 m o más de la del hijo |
| Diferencia | n/d | contaminado menos limpio: -7,8 puntos (IC 95%: -13,9 a -3,1) |

| Control | Cercanos | Controles | Brecha del mes 1 (puntos) | IC 95% | Diferido de los meses 0 a 6 (millones de barriles) | IC 95% |
|---|---|---|---|---|---|---|
| control de superficie usual (2 a 5 km) | 2.094 | 18.291 | -23,0 | -29,5 a -16,9 | 19,2 | 11,6 a 28,8 |
| control lateral limpio | 2.094 | 5.918 | -22,7 | -29,5 a -16,5 | 18,4 | 11,5 a 27,2 |

Es un recálculo descriptivo y no es el rango del estudio (6,4 a 11,4 millones de barriles): suma los meses 0 a 6 de cada evento cercano contra la mediana de todos los controles, sin grupos de edad, sin descontar la brecha previa y sin quitar los meses repetidos, así que da un total más alto; sirve para comparar un control con el otro y no como el total del estudio.

## Sensibilidades (no cambian ningún veredicto)

| Cantidad | Principal | S1 (hijo más cercano por rama) | S2 (base de los meses -6 a -4) | S3 (hijos fracturados hasta 2023) |
|---|---|---|---|---|
| Brecha de 0 a 300 m | -50,3 (-60,2 a -40,4) | -41,2 (-52,3 a -30,2) | -46,3 (-51,9 a -37,8) | -49,3 (-60,7 a -38,7) |
| Brecha de 300 a 600 m | -20,5 (-27,0 a -15,2) | -19,3 (-25,9 a -13,5) | -23,4 (-30,3 a -17,6) | -19,0 (-27,6 a -12,8) |
| Brecha de 600 a 1.000 m | -9,0 (-13,8 a -4,4) | -6,5 (-12,1 a -2,3) | -11,3 (-17,1 a -7,4) | -8,9 (-14,2 a -3,2) |
| Brecha de 1.000 a 2.000 m | -1,5 (-4,6 a 1,2) | -1,7 (-4,7 a 0,8) | -1,4 (-4,2 a 1,6) | -1,1 (-3,9 a 1,9) |
| A | -28,2 (-36,3 a -22,7) | -25,4 (-33,1 a -20,6) | -30,4 (-36,9 a -23,9) | -26,1 (-36,1 a -20,3) |
| B | -24,2 (-32,0 a -16,8) | -24,2 (-32,0 a -16,8) | -25,0 (-32,0 a -19,1) | -24,3 (-32,9 a -15,1) |
| A menos B | -4,1 (-11,7 a 2,7) | -1,2 (-8,6 a 5,7) | -5,4 (-11,0 a 2,3) | -1,9 (-11,6 a 5,4) |

- S1: la distancia del evento es la menor distancia entre ramas sobre todos los hijos medidos de ese padre y de ese mes de fractura, no la del hijo más cercano en superficie; los mismos eventos, las mismas bandas y el mismo control.
- S2: lo mismo que el modelo principal con la base de los meses -6 a -4 en lugar de la de los meses -3 a -1.
- S3: el modelo principal con los eventos cuyo hijo se fracturó en 2023 o antes, la parte bien cubierta de la fuente.

## Eventos por año del hijo

| Año | Eventos | 0 a 300 m | 300 a 600 m | 600 a 1.000 m | 1.000 a 2.000 m | Control lateral |
|---|---|---|---|---|---|---|
| 2013 | 1 | 0 | 0 | 0 | 1 | 0 |
| 2014 | 3 | 0 | 0 | 0 | 0 | 3 |
| 2015 | 46 | 2 | 3 | 4 | 8 | 29 |
| 2016 | 241 | 3 | 16 | 19 | 46 | 157 |
| 2017 | 301 | 10 | 19 | 22 | 63 | 187 |
| 2018 | 491 | 10 | 38 | 43 | 95 | 305 |
| 2019 | 798 | 34 | 41 | 66 | 176 | 478 |
| 2020 | 424 | 13 | 24 | 33 | 100 | 254 |
| 2021 | 1.465 | 43 | 86 | 123 | 298 | 915 |
| 2022 | 2.032 | 78 | 169 | 216 | 450 | 1.119 |
| 2023 | 2.489 | 77 | 167 | 233 | 541 | 1.471 |
| 2024 | 1.244 | 57 | 84 | 138 | 286 | 679 |
| 2025 | 582 | 30 | 70 | 64 | 124 | 294 |
| 2026 | 56 | 3 | 12 | 7 | 7 | 27 |
| Total | 10.173 | 360 | 729 | 968 | 2.195 | 5.918 |

Eventos son los de la muestra de ese año; las bandas cuentan los que tienen el índice del mes 1 medido.

## Cómo se mide

- Los eventos son los del estudio: un padre y el mes de fractura de su hijo más cercano en superficie, que fija el mes y el hijo.
- La muestra son los eventos cuyo par (hijo, padre) está en `mart_trayectoria_par`: con la rama del hijo y la del padre medidas.
- La distancia es la menor distancia entre las dos ramas en planta (`m_min`), en metros.
- La brecha es la mediana del índice del grupo menos la mediana del índice del control lateral (`m_min` de 2.000 m o más); el índice es el caudal del mes 1 sobre la base de los meses -3 a -1.
- Los intervalos son bootstrap de percentiles 95% por bloques espaciales de 5 km (400 remuestras, las mismas para todas las cantidades).
- El veredicto sale solo del modelo principal. Las bandas incluyen el extremo de abajo y dejan afuera el de arriba.

## Qué no es

- Es una huella medida: la misma brecha del estudio con otra distancia, sin afirmación causal y sin ajuste por comparaciones múltiples.
- La muestra es sobre todo de 2016 a 2023: no dice nada de 2024 en adelante.
- El control lateral solo sabe de las ramas medidas: un padre con un hijo de rama no publicada puede estar golpeado igual.
- Solo hay pares con las bocas a menos de 5 km: un padre con la rama cerca pero la boca lejos no está.
- La distancia entre ramas es en planta: no tiene la cota de cada punto.
- Un alcance medido es el borde de las bandas probadas (300, 600, 1.000 y 2.000 m), no un borde exacto.

## Reproducir

1. `uv run python -m pipeline.alcance_rama` (necesita `pipeline.trayectorias` antes).
2. `uv run python -m pipeline.wiki`
3. `uv run python -m pipeline.claims`

