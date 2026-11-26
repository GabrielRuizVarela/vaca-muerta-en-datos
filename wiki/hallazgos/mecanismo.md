# Mecanismo por la geometría de las ramas

Página generada por `pipeline/mecanismo.py`. Prueba nueva: la posición del padre se mide respecto de la rama de cada hijo (su costado o su punta), no respecto de la disposición de pads de la cuenca. No es una repetición del eje de la brújula, que sigue retirado, y no mide esfuerzos.

## Resumen

Veredicto contra la regla fijada: **sostiene**. Entre los padres cercanos (menos de 1.000 m entre ramas) y paralelos, el que queda al costado de la rama del hijo rinde menos al mes 1 que el que queda en su punta, y el mismo contraste antes de la fractura (mes -1) tiene un intervalo que incluye cero. Es una huella medida compatible con un efecto de la geometría de las ramas; no es una prueba de causa ni una medición de esfuerzos.

- Contraste costado menos punta al mes 1 (principal): -28,0 puntos (IC 95% por bloques de 5 km: -35,9 a -19,7), sobre 1.201 costados y 915 puntas y 85 bloques.
- Mismo contraste en el mes -1 con la base de los meses -6 a -4: -5,6 puntos (IC 95% por bloques de 5 km: -13,9 a 2,5). Un IC que incluye cero no descarta una diferencia previa: el límite más lejano de cero es 13,9 puntos, una cota superior de lo que ya podía haber antes.
- En la serie con la base limpia el contraste vale -2,4 puntos en el mes -3, -0,3 puntos en el mes -2 y -28,8 puntos en el mes 0.
- Por banda de distancia entre ramas, el contraste del mes 1 es de -53,2 puntos en la banda de 0 a 300 m (351 costados, 123 puntas), de -27,8 puntos en la banda de 300 a 600 m (413 costados, 360 puntas), de -14,4 puntos en la banda de 600 a 1.000 m (437 costados, 432 puntas).
- El mismo contraste con otros intervalos: por pads hijo, de -34,8 a -21,0; por bloques de 2 km, de -34,1 a -21,1.
- Sin pesar por eventos: -31,8 puntos; con el costado definido por un solape de 0,5 o más: -28,1 puntos.
- Muestra: las ramas medidas cubren de 76 a 97% de los hijos fracturados de 2016 a 2023 pero solo 39% de los de 2024 y 25% de los de 2025, así que la muestra es sobre todo de 2016 a 2023.
- De los 2.116 eventos cercanos del modelo principal, 78,2% corresponden a hijos fracturados de 2016 a 2023.

## Regla fijada antes de correr

Eventos: los pares de `mart_trayectoria_par` con el padre que cumple la regla de edad del estudio principal; un evento es un padre y el mes de fractura del hijo, y el hijo que lo fija es el de menor distancia entre ramas. Muestra: padres a menos de 1.000 m entre ramas, en paralelo (20 grados o menos de diferencia de azimut) y con posición clara de costado o de punta; bandas de 0 a 300, de 300 a 600 y de 600 a 1.000 m. Control lateral: los padres cuyo hijo más cercano queda a 2.000 m o más de la rama del padre, comparados por la edad del padre en el mes del evento (6 a 11, 12 a 23, 24 a 47, 48 meses o más) y por el mismo mes, con al menos 5 controles por grupo de edad. Estimador: cada padre indexado contra su propia base, brecha entre medianas contra el control de su grupo de edad, y el contraste como la brecha del costado menos la brecha de la punta en cada banda, promediado por los eventos de cada banda; una banda con menos de 5 eventos en el costado o en la punta no entra. IC 95%: bootstrap de percentiles que remuestrea bloques de 5 km, con semilla fija. Veredicto: sin muestra si hay menos de 80 eventos en el costado o en la punta; sostiene si el IC del contraste del mes 1 queda entero por debajo de cero y el placebo del mes -1 tiene un IC que incluye cero; ubicación si el placebo también excluye cero; no firme en cualquier otro caso. Placebo: el mismo contraste en el mes -1 con la base limpia de los meses -6 a -4. La regla se fijó en el commit bddf1e0771 de la rama de esta prueba, antes de calcular ninguna cifra.

## Resultados

Todos los modelos calculados. El contraste es el del costado menos la punta, en puntos: negativo significa que el costado rinde menos. Las filas del mes -1 (el placebo y la serie con la base limpia) usan los mismos eventos y el mismo estimador, y sus intervalos difieren solo por la semilla del bootstrap.

| Modelo | k | Costados | Puntas | Contraste (puntos) | IC 95% por bloques de 5 km | IC 95% por pads | IC 95% por bloques de 2 km |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Principal (decide) | 1 | 1.201 | 915 | -28,0 | -35,9 a -19,7 | -34,8 a -21,0 | -34,1 a -21,1 |
| Placebo en k = -1, base de los meses -6 a -4 | -1 | 1.168 | 884 | -5,6 | -13,9 a 2,5 | -12,1 a 2,0 | -13,5 a 1,9 |
| k = 1 con la base limpia | 1 | 1.171 | 888 | -26,9 | -34,7 a -19,1 | -35,9 a -18,9 | -36,0 a -19,1 |
| Serie con la base limpia | -3 | 1.171 | 888 | -2,4 | -6,3 a 2,8 | -6,4 a 2,6 | -6,0 a 1,9 |
| Serie con la base limpia | -2 | 1.171 | 888 | -0,3 | -6,8 a 4,1 | -5,4 a 4,3 | -5,7 a 4,0 |
| Serie con la base limpia | -1 | 1.168 | 884 | -5,6 | -12,3 a 2,5 | -13,4 a 1,5 | -12,9 a 0,4 |
| Serie con la base limpia | 0 | 1.169 | 885 | -28,8 | -36,2 a -20,9 | -37,0 a -19,8 | -36,0 a -21,0 |
| Serie con la base limpia | 1 | 1.171 | 888 | -26,9 | -34,5 a -17,6 | -35,9 a -18,3 | -35,4 a -18,2 |
| Serie con la base limpia | 2 | 1.171 | 888 | -11,8 | -20,4 a -3,4 | -20,8 a -3,0 | -18,9 a -2,4 |
| Serie con la base limpia | 3 | 1.171 | 887 | -8,4 | -15,1 a -0,4 | -15,6 a 0,3 | -15,3 a 0,2 |
| Principal sin pesar por eventos | 1 | 1.201 | 915 | -31,8 | -39,7 a -24,0 | -40,9 a -24,3 | -39,3 a -25,1 |
| Costado con solape de 0,5 o más | 1 | 973 | 915 | -28,1 | -37,0 a -19,2 | -37,7 a -21,8 | -37,4 a -20,6 |

Contraste por banda de distancia entre ramas, en puntos. El peso es el número de eventos de la banda (costados más puntas).

| Modelo | Banda | k | Costados | Puntas | Brecha costado | Brecha punta | Contraste | Peso |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Principal (decide) | 0 a 300 m | 1 | 351 | 123 | -58,6 | -5,4 | -53,2 | 474 |
| Principal (decide) | 300 a 600 m | 1 | 413 | 360 | -37,4 | -9,6 | -27,8 | 773 |
| Principal (decide) | 600 a 1.000 m | 1 | 437 | 432 | -20,2 | -5,8 | -14,4 | 869 |
| Placebo en k = -1, base de los meses -6 a -4 | 0 a 300 m | -1 | 344 | 119 | -14,7 | -0,9 | -13,8 | 463 |
| Placebo en k = -1, base de los meses -6 a -4 | 300 a 600 m | -1 | 400 | 348 | -9,7 | -7,1 | -2,6 | 748 |
| Placebo en k = -1, base de los meses -6 a -4 | 600 a 1.000 m | -1 | 424 | 417 | -9,9 | -6,1 | -3,8 | 841 |
| k = 1 con la base limpia | 0 a 300 m | 1 | 344 | 119 | -58,0 | -5,8 | -52,1 | 463 |
| k = 1 con la base limpia | 300 a 600 m | 1 | 400 | 348 | -42,8 | -15,8 | -27,0 | 748 |
| k = 1 con la base limpia | 600 a 1.000 m | 1 | 427 | 421 | -23,8 | -10,7 | -13,2 | 848 |

Brecha del mes 1 por tercil del ángulo al SHmax del hijo (67,5 grados desde el norte). Descriptivo: no decide nada.

| Tercil | Ángulo al SHmax (grados) | Posición | Eventos | Brecha al mes 1 (puntos) | IC 95% |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | 0,0 a 67,5 | todos | 704 | -18,8 | -27,6 a -12,3 |
| 1 | 0,0 a 67,5 | costado | 412 | -31,8 | -41,6 a -25,0 |
| 1 | 0,0 a 67,5 | punta | 292 | -6,5 | -11,1 a -0,5 |
| 2 | 67,5 a 67,8 | todos | 704 | -20,1 | -26,2 a -12,5 |
| 2 | 67,5 a 67,8 | costado | 394 | -39,6 | -48,8 a -22,6 |
| 2 | 67,5 a 67,8 | punta | 310 | -7,5 | -16,8 a -0,1 |
| 3 | 67,8 a 90,0 | todos | 708 | -22,3 | -29,5 a -16,3 |
| 3 | 67,8 a 90,0 | costado | 395 | -36,5 | -45,2 a -30,4 |
| 3 | 67,8 a 90,0 | punta | 313 | -6,4 | -15,1 a -0,1 |

Los cortes de los terciles son 67,5 y 67,8 grados: casi todas las ramas de la muestra son norte sur y el ángulo al SHmax casi no varía, así que esta tabla es descriptiva y no prueba ninguna dirección.

Eventos por año de la fractura del hijo, en la muestra del contraste y en el control lateral.

| Año | Costados | Puntas | Controles |
| ---: | ---: | ---: | ---: |
| 2013 | 0 | 0 | 0 |
| 2014 | 0 | 0 | 3 |
| 2015 | 8 | 1 | 31 |
| 2016 | 17 | 24 | 144 |
| 2017 | 35 | 26 | 171 |
| 2018 | 37 | 52 | 285 |
| 2019 | 87 | 73 | 440 |
| 2020 | 35 | 37 | 243 |
| 2021 | 162 | 96 | 856 |
| 2022 | 299 | 180 | 1.061 |
| 2023 | 259 | 235 | 1.414 |
| 2024 | 153 | 113 | 728 |
| 2025 | 96 | 63 | 324 |
| 2026 | 13 | 15 | 31 |

## Límites

- Es una asociación medida, no la causa: el costado y la punta pueden diferir en lo que el contraste no ve (profundidad, unidad navegada, tamaño de la fractura, tiempo desde la puesta en producción del padre).
- La prueba placebo del mes -1 cubre las diferencias que ya existían antes de la fractura, no las que aparecen justo con ella.
- El placebo por banda no es plano en la banda de 0 a 300 m: allí el contraste del mes -1 ya es de -13,8 puntos (sin IC por banda). El veredicto decide con el promedio ponderado de las tres bandas; en esa banda el contraste del mes 1 es de -53,2 puntos y pesa 474 de 2.116 eventos en el promedio.
- Con datos mensuales de caudal, un cierre preventivo del padre que queda al costado mientras se fractura el hijo da el mismo contraste sin que intervenga la geometría de la roca: la prueba no separa la geometría de las ramas de esa decisión del operador (el índice cuenta días calendario, así que los días cerrados también bajan el caudal).
- La muestra es sobre todo de 2016 a 2023: las ramas medidas cubren de 76 a 97% de los hijos fracturados de 2016 a 2023 pero solo 39% de los de 2024 y 25% de los de 2025.
- Solo entran los pares con las dos ramas medidas y con menos de 5 km de superficie: un padre cuya rama no se publicó queda afuera, tanto de la muestra cercana como del control lateral, y un control puede tener otro hijo cercano cuya rama no se publicó (pesa más en 2024 y 2025, donde la cobertura es menor).
- La posición y el paralelismo se miden entre los ejes principales de las ramas en planta, sin la profundidad.
- Los IC no tienen ajuste por comparaciones múltiples, y los eventos de un mismo padre con varios hijos no son independientes: un mismo padre puede aportar al costado o a la punta con un hijo cercano y al control lateral con otro hijo a más de 2.000 m en otro mes, así que el control no es un grupo de padres aparte del grupo tratado. El bootstrap por bloques de 5 km remuestrea juntos esos eventos, pero esa dependencia no se midió por separado.
- El veredicto sale solo del modelo principal; todos los demás modelos se publican y no deciden nada.
