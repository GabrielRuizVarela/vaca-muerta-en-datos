# Riesgo de golpe fuerte

El modelo puntual de costo (`anisotropia.md`) predice barriles y falla fuera de muestra. Esta página hace la pregunta que un operador puede usar: dado un padre y un hijo que se va a fracturar a menos de 1 km, cuán probable es un golpe fuerte. Es un modelo de clasificación probado hacia adelante en el tiempo: entrena con los hijos fracturados de 2016 a 2022 y se prueba con los de 2023 y 2024. La regla se fijó antes de calcular ninguna cifra, en el commit 4b19b90. Se publican todos los modelos, favorables o no.

Esta página la escribe `python -m pipeline.wiki` con `pipeline.riesgo.pagina_riesgo`. No se edita a mano.

## Lectura

- Muestra: Son 2.094 eventos cercanos del estudio (el padre a menos de 1 km en superficie del hijo más cercano, con el índice del mes 1 medido): 673 de entrenamiento (hijos fracturados de 2016-01 a 2022-12) y 492 de prueba (de 2023-01 a 2024-12); 929 quedan fuera de las dos ventanas y no se usan. De los de prueba, 302 tienen la rama del par medida y el resto entra con la distancia entre ramas faltante y su indicador. Las trayectorias laterales cubren el 86% de los hijos horizontales fracturados de 2016 a 2023 pero solo el 39% de los de 2024 y el 25% de los de 2025, así que la muestra es sobre todo de 2016 a 2023 y la prueba de 2023 a 2024 es fina en 2024: 126 de sus 279 eventos tienen la rama del par medida.
- Golpe fuerte: el índice del mes 1 del padre menos la mediana del mismo grupo de edad de los controles queda por debajo de -30 puntos. Ocurre en el 44,7% de los eventos de entrenamiento y en el 42,3% de los de prueba.
- Riesgo: **no predice el riesgo**. En la prueba el AUC es 0,67 (IC 95%: 0,60 a 0,74) y la habilidad de Brier contra la tasa de entrenamiento por área es 0,09 (IC 95%: -0,04 a 0,21). El AUC pasa el umbral de la regla (0,65 con límite bajo sobre 0,55) pero la habilidad de Brier no excluye cero: el modelo ordena los eventos de la prueba y no se puede afirmar que sus probabilidades mejoren la tasa de entrenamiento por área. La regla pide las dos cosas.
- Calibración (descriptivo, tabla de abajo): el décimo de mayor riesgo predice 82,6% y observa 61,2%; el de menor riesgo predice 17,7% y observa 14,0%.
- Geometría (descriptivo, sin veredicto): sin las variables de las ramas el AUC es 0,60 (0,52 a 0,66) y con la distancia de superficie sola 0,47 (0,40 a 0,55). La diferencia de AUC contra el principal es -0,08 (-0,13 a -0,02) sin las ramas y -0,20 (-0,28 a -0,11) con la distancia de superficie sola. Es una lectura de esta muestra y no cambia el veredicto.

## Modelos

| Modelo | Umbral (puntos) | Entrenamiento | Prueba | Golpes en la prueba (%) | AUC (IC 95%) | Habilidad de Brier (IC 95%) | AUC menos el del principal (IC 95%) |
|---|---|---|---|---|---|---|---|
| Principal (todas las variables) | -30 | 673 | 492 | 42,3 | 0,67 (0,60 a 0,74) | 0,09 (-0,04 a 0,21) | n/d |
| M2: sin la geometría de las ramas | -30 | 673 | 492 | 42,3 | 0,60 (0,52 a 0,66) | 0,02 (-0,08 a 0,10) | -0,08 (-0,13 a -0,02) |
| M3: solo la distancia de superficie | -30 | 673 | 492 | 42,3 | 0,47 (0,40 a 0,55) | 0,03 (-0,05 a 0,12) | -0,20 (-0,28 a -0,11) |
| M4: solo eventos con la rama del par medida | -30 | 515 | 302 | 44,7 | 0,66 (0,57 a 0,74) | 0,07 (-0,20 a 0,25) | n/d |
| S1: golpe fuerte desde -20 puntos | -20 | 673 | 492 | 50,0 | 0,67 (0,60 a 0,73) | 0,14 (0,02 a 0,25) | n/d |
| S2: golpe fuerte desde -40 puntos | -40 | 673 | 492 | 35,6 | 0,69 (0,61 a 0,76) | 0,04 (-0,11 a 0,19) | n/d |

La habilidad de Brier es 1 menos el Brier del modelo sobre el de la referencia (la prevalencia de entrenamiento por área; en M4 la de ese subconjunto). Solo el modelo principal decide el veredicto; los demás son descriptivos.

## Calibración por decil (modelo principal, eventos de prueba)

| Decil de riesgo | Eventos | Riesgo medio predicho (%) | Frecuencia observada (%) |
|---|---|---|---|
| 1 | 50 | 17,7 | 14,0 |
| 2 | 50 | 25,1 | 26,0 |
| 3 | 49 | 31,0 | 36,7 |
| 4 | 49 | 37,6 | 36,7 |
| 5 | 49 | 43,9 | 28,6 |
| 6 | 49 | 51,3 | 53,1 |
| 7 | 49 | 58,5 | 51,0 |
| 8 | 49 | 63,8 | 53,1 |
| 9 | 49 | 70,1 | 63,3 |
| 10 | 49 | 82,6 | 61,2 |

Los eventos de la prueba van ordenados por el riesgo predicho en 10 grupos de tamaño casi igual (el décimo es el de mayor riesgo).

## Coeficientes del modelo principal (unidades estandarizadas)

| Variable | Coeficiente |
|---|---|
| intercepto | -0,30 |
| km | 0,02 |
| m_min | -0,39 |
| falta_rama | 0,09 |
| dif_azimut | -0,04 |
| posicion_costado | 0,25 |
| posicion_mixto | -0,59 |
| posicion_punta | -0,18 |
| edad_meses | 0,02 |
| acum_m3_por_m | 0,30 |
| falta_largo_padre | 0,13 |
| base_m3_d | 0,36 |
| arena_por_m | -0,17 |
| etapas | 0,22 |
| falta_largo_hijo | -0,19 |
| mismo_pad | 0,16 |
| hijos_1km | 0,04 |
| operador_Shell | -0,10 |
| operador_Tecpetrol | 0,12 |
| operador_Vista | 0,03 |
| operador_YPF | 0,21 |
| operador_otro | -0,50 |
| area_BAJADA DEL PALO OESTE | -0,17 |
| area_BANDURRIA SUR | -0,20 |
| area_FORTIN DE PIEDRA | 0,12 |
| area_LA AMARGA CHICA | -0,16 |
| area_LOMA CAMPANA | -0,13 |
| area_otro | 0,41 |

Son descriptivos: no tienen intervalo ni prueba de significancia, y con variables correlacionadas no se leen una por una.

## Con y sin la rama del par medida (modelo principal, eventos de prueba)

| Grupo | Eventos | Golpes fuertes | AUC |
|---|---|---|---|
| Con la rama del par medida | 302 | 135 | 0,69 |
| Sin la rama del par medida | 190 | 73 | 0,62 |

## Eventos por año del hijo

| Año | Ventana | Eventos | Con la rama del par medida | Golpes fuertes |
|---|---|---|---|---|
| 2011 | fuera | 1 | 0 | 0 |
| 2012 | fuera | 9 | 0 | 5 |
| 2013 | fuera | 14 | 0 | 3 |
| 2014 | fuera | 72 | 0 | 16 |
| 2015 | fuera | 201 | 7 | 46 |
| 2016 | entrenamiento | 70 | 13 | 34 |
| 2017 | entrenamiento | 58 | 36 | 24 |
| 2018 | entrenamiento | 55 | 44 | 19 |
| 2019 | entrenamiento | 80 | 71 | 33 |
| 2020 | entrenamiento | 41 | 24 | 15 |
| 2021 | entrenamiento | 137 | 120 | 56 |
| 2022 | entrenamiento | 232 | 207 | 120 |
| 2023 | prueba | 213 | 176 | 84 |
| 2024 | prueba | 279 | 126 | 124 |
| 2025 | fuera | 372 | 89 | 186 |
| 2026 | fuera | 260 | 8 | 142 |

## Cómo se mide

- Los eventos son los cercanos del estudio: un padre a menos de 1 km en superficie de su hijo más cercano, en el mes de fractura de ese hijo.
- El resultado es golpe fuerte si el índice del mes 1 del padre menos la mediana de los controles de 2 a 5 km de su grupo de edad queda por debajo de -30 puntos.
- Las variables son la distancia de superficie, la menor distancia entre ramas con su indicador de falta, la posición y la diferencia de azimut, la edad y el caudal base del padre, su petróleo acumulado por metro de rama, la arena por metro y las etapas del hijo, si comparten pad, los hijos a menos de 1 km ese mes, el operador y el área.
- El modelo principal es una regresión logística con penalización L2 (C = 1,0), variables estandarizadas con el entrenamiento y sin ningún ajuste.
- Los intervalos son bootstrap de percentiles 95% que remuestrea pads de hijo completos de los eventos de prueba (400 remuestras, 81 pads, las mismas para todos los modelos). El modelo se ajusta una vez: el intervalo cubre el muestreo de la prueba y no el del entrenamiento.
- El veredicto sale solo del modelo principal: "predice el riesgo" pide un AUC de 0,65 o más con límite bajo sobre 0,55 y una habilidad de Brier mayor que cero con intervalo que excluye cero; "sin muestra" es menos de 300 eventos de prueba.

## Qué no es

- Es una asociación probada hacia adelante, sin afirmación causal: un riesgo alto no dice que la fractura del hijo cause el golpe.
- La mediana de control del resultado sale de todo el periodo, como en el estudio principal; no es una variable del modelo, pero el resultado de los eventos de entrenamiento y el de los de prueba comparten esa mediana.
- El entrenamiento tiene cientos de eventos y muchas variables: un "no predice el riesgo" es contra estas variables y este modelo (logístico L2 sin ajuste) y no prueba que nada prediga el riesgo. Los intervalos cubren el muestreo de la prueba, no el del entrenamiento.
- La rama medida cubre sobre todo hijos de 2016 a 2023: las variables de rama de la prueba están medidas en una parte de los eventos y la muestra no dice nada de los hijos de 2025 en adelante.
- Solo están los eventos con el hijo cercano a menos de 1 km en superficie: un padre con la rama cerca pero la boca lejos no está.
- La referencia por área usa la prevalencia de entrenamiento: una mejora sobre ella no es una mejora sobre un operador que ya conoce su campo.

## Reproducir

1. `uv run python -m pipeline.riesgo` (necesita `pipeline.trayectorias` antes).
2. `uv run python -m pipeline.wiki`
3. `uv run python -m pipeline.claims`

