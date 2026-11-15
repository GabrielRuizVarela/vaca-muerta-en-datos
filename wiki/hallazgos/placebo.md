# Pruebas de falsación del estudio de eventos

Página generada por `pipeline/placebo.py`. Somete el resultado principal de interferencia (al mes 1 de la fractura de un hijo, los padres a menos de 1 km conservan unos 23 puntos menos de su caudal previo que los controles a 2 a 5 km) a tres pruebas en las que ese resultado no debería aparecer: una brecha previa a la fractura, brechas en fechas de fractura falsas y un eje de mayor merma con las fechas permutadas. Los intervalos son bootstrap por pads hijo (400 repeticiones, semilla fija); el resumen de las permutaciones usa 200 sorteos.

## Pretendencia

Brecha entre padres cercanos (menos de 1 km del hijo) y controles (2 a 5 km), en medianas del índice, en los meses alrededor de la fractura (k = 0 es el mes de la fractura). Como la base del índice principal son los meses -3 a -1, ahí el índice vale 1 por construcción en promedio y no puede mostrar una diferencia previa; por eso la tabla principal toma como base los meses -6 a -4, que no se usan como mes de prueba. Los padres deben tener datos en esa base y producir más de 1 m3/d.

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Índice cercanos | Índice controles | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| -3 | 2.031 | 17.756 | 0,905 | 0,931 | -2,5 | -4,9 a -0,7 |
| -2 | 2.031 | 17.746 | 0,856 | 0,891 | -3,5 | -6,0 a -1,1 |
| -1 | 2.023 | 17.712 | 0,793 | 0,856 | -6,3 | -9,7 a -3,2 |
| 0 | 2.027 | 17.760 | 0,608 | 0,817 | -20,9 | -25,4 a -16,9 |
| 1 | 2.031 | 17.732 | 0,526 | 0,780 | -25,5 | -30,6 a -21,2 |
| 2 | 2.018 | 17.591 | 0,589 | 0,756 | -16,7 | -21,1 a -12,3 |
| 3 | 2.008 | 17.503 | 0,616 | 0,727 | -11,1 | -16,1 a -6,7 |

Con la base del resultado principal (meses -3 a -1) la lectura de k = -3 a -1 queda forzada, pero k = 0 a 3 reproduce las cifras publicadas:

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Índice cercanos | Índice controles | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| -3 | 2.077 | 18.288 | 1,058 | 1,041 | 1,7 | 0,4 a 3,5 |
| -2 | 2.077 | 18.278 | 0,999 | 0,999 | 0,0 | -0,7 a 0,8 |
| -1 | 2.069 | 18.244 | 0,931 | 0,962 | -3,1 | -4,3 a -1,2 |
| 0 | 2.073 | 18.292 | 0,754 | 0,924 | -17,0 | -20,8 a -14,1 |
| 1 | 2.077 | 18.262 | 0,655 | 0,884 | -22,9 | -27,4 a -18,1 |
| 2 | 2.064 | 18.119 | 0,723 | 0,860 | -13,7 | -18,1 a -9,9 |
| 3 | 2.054 | 18.031 | 0,743 | 0,830 | -8,8 | -13,4 a -5,6 |

Sin los eventos en que el padre tuvo, en los 6 meses anteriores, la fractura de otro hijo a menos de 2 km (para descartar que la brecha previa sea un golpe anterior de un pozo vecino del mismo pad), con la base de -6 a -4:

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Índice cercanos | Índice controles | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| -3 | 1.205 | 12.087 | 0,906 | 0,940 | -3,4 | -5,7 a -1,7 |
| -2 | 1.205 | 12.077 | 0,872 | 0,905 | -3,3 | -5,5 a -0,4 |
| -1 | 1.201 | 12.043 | 0,816 | 0,875 | -5,9 | -9,7 a -2,5 |
| 0 | 1.201 | 12.091 | 0,645 | 0,837 | -19,1 | -23,8 a -15,0 |
| 1 | 1.205 | 12.070 | 0,532 | 0,795 | -26,3 | -34,2 a -20,7 |
| 2 | 1.194 | 12.016 | 0,594 | 0,772 | -17,8 | -22,2 a -11,2 |
| 3 | 1.188 | 11.985 | 0,619 | 0,743 | -12,3 | -16,9 a -7,2 |

## Fechas de fractura falsas

Se corre la fecha de fractura de todos los hijos d meses, se conservan los pares padre e hijo y se exige que el padre tenga al menos 6 meses de producción en la fecha falsa y datos en los meses -3 a -1 (el mes 1 puede faltar y entonces no entra). La brecha real se calcula en los mismos eventos con su fecha verdadera. d = 0 es el resultado principal. Solo los desplazamientos de -6 y -12 meses son placebos limpios (la fecha falsa cae antes de la fractura real); con +6 y +12 el mes 1 falso puede caer sobre meses ya afectados por la fractura real, así que una brecha ahí no refuta nada.

| Desplazamiento (meses) | Eventos cercanos | Brecha del mes 1 (puntos) | IC 95% (puntos) | Brecha real en los mismos eventos (puntos) |
| ---: | ---: | ---: | --- | ---: |
| -12 | 1.338 | -2,4 | -5,4 a 1,0 | -23,1 |
| -6 | 1.634 | -0,4 | -3,2 a 3,0 | -23,1 |
| 0 | 2.077 | -22,9 | -27,1 a -18,0 | -22,9 |
| 6 | 1.883 | 0,6 | -2,5 a 4,1 | -21,5 |
| 12 | 1.711 | 0,2 | -2,4 a 2,7 | -20,8 |

## Fechas permutadas

Con 200 permutaciones de las fechas de fractura entre hijos del mismo año (unos 6.276 eventos cercanos por sorteo), la brecha del mes 1 tiene media -6,5 puntos, desvío 0,7 y un rango de -7,8 a -5,3 (percentiles 2,5 y 97,5; extremos -8,4 y -4,8). La brecha real, -22,9 puntos, queda fuera de ese rango; la fracción de permutaciones con una brecha tan negativa o más es 0,005 (el mínimo posible con 200 sorteos es 0,005).

## Eje de mayor merma con fechas permutadas

Mismo ajuste axial coseno, mismos controles y efectos fijos de área que `pipeline/costo.py`, sobre los eventos de 0,3 a 1 km, con las fechas permutadas. El eje se considera definido si el p de permutación es menor que 0,10 y el IC mide menos de 90 grados. Para las primeras permutaciones se calcula el eje con su intervalo; el resumen compara la amplitud del término angular de todas las permutaciones con la real.

| Escenario | Eventos | Eje (grados) | IC 95% (grados) | Ancho IC | Amplitud | p permutación | Definido |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| real | 1.734 | 93 | 70 a 122 | 53 | 0,071 | 0,022 | sí |
| permutacion 1 | 1.734 | 24 | 140 a 92 | 133 | 0,026 | 0,444 | no |
| permutacion 2 | 1.734 | 159 | 75 a 60 | 165 | 0,010 | 0,914 | no |
| permutacion 3 | 1.734 | 98 | 43 a 168 | 125 | 0,036 | 0,264 | no |
| permutacion 4 | 1.734 | 58 | 160 a 129 | 150 | 0,018 | 0,780 | no |
| permutacion 5 | 1.734 | 100 | 47 a 153 | 105 | 0,036 | 0,242 | no |
| permutacion 6 | 1.734 | 33 | 135 a 107 | 152 | 0,015 | 0,820 | no |
| permutacion 7 | 1.734 | 117 | 85 a 150 | 65 | 0,049 | 0,114 | no |
| permutacion 8 | 1.734 | 130 | 75 a 18 | 124 | 0,027 | 0,562 | no |
| permutacion 9 | 1.734 | 169 | 93 a 62 | 149 | 0,022 | 0,650 | no |
| permutacion 10 | 1.734 | 104 | 49 a 144 | 95 | 0,036 | 0,320 | no |
| resumen de permutaciones | 1.734 | n/d | n/d | n/d | mediana 0,029, p95 0,052 | 0,005 | n/d |

En la fila de resumen el p es la fracción de permutaciones con una amplitud al menos igual a la real. Un intervalo de ejes puede cruzar los 180 grados (el límite inferior queda numéricamente por encima del superior): el eje es axial y el intervalo cierra la vuelta.

## Qué se concluye

- Pretendencia: hay una brecha previa. Con la base de los meses -6 a -4, el IC excluye cero en k = -3, -2, -1 (brechas de -2,5, -3,5, -6,3 puntos), así que los padres cercanos ya rendían distinto antes de la fractura (por un nivel distinto de los padres cercanos o por un efecto anticipado; estos datos no los separan). La brecha del mes 1 con esta base es -25,5 puntos y la parte atribuible a la fractura es menor.
- Fechas falsas: en los cuatro desplazamientos el intervalo incluye cero (d = -12: -2,4, d = -6: -0,4, d = 6: 0,6, d = 12: 0,2 puntos).
- Permutación: la brecha real (-22,9 puntos) queda fuera de las 200 brechas permutadas (rango -8,4 a -4,8). La media permutada es -6,5 puntos, no cero: con la fecha de otro hijo del mismo año los padres cercanos rinden menos que los controles. Una lectura posible es que, en zonas de desarrollo denso, un padre cercano a un hijo también lo está de otro que sí fracturó en esa fecha; no se verificó.
- Eje: de 10 permutaciones con intervalo, 0 dejan un eje definido; la fracción de las 200 con una amplitud tan grande como la real es 0,005 (amplitud real 0,071, mediana permutada 0,029, percentil 95 0,052; las permutaciones se submuestrean a los mismos 1.734 eventos que la real).
- Qué significa para el resultado principal: la caída de 22,9 puntos del mes 1 no es un artefacto de una fecha cualquiera (las fechas falsas dan cerca de cero y las permutadas dan -6,5 en promedio), pero no sale limpia: los padres cercanos ya rendían unos 6,3 puntos menos en el mes -1, y la brecha previa sigue sin los golpes previos de vecinos (-3,4, -3,3, -5,9 puntos en k = -3, -2, -1). Medida contra el nivel previo con la misma base (-6 a -4), la caída adicional al mes 1 es de 19,2 puntos (20,4 sin los golpes previos de vecinos). Ese descuento supone que la brecha previa es un nivel distinto de los padres cercanos que no sigue creciendo; si fuera un efecto anticipado o una deriva que continúa, el descuento sería otro, y los datos mensuales no permiten separarlos. Por eso los puntos del resultado principal son una cota superior del efecto, y lo que queda después del descuento es del orden de 19,2 a 20,4 puntos, condicional a ese supuesto. La media permutada no es cero y las fechas permutadas pueden coincidir con golpes reales de hijos vecinos, así que el valor p de la permutación (0,005 como mínimo con 200 permutaciones) es un piso, no una probabilidad exacta.

## Qué no prueba

- Pasar estas pruebas no demuestra causalidad. Descarta una brecha previa y una brecha que aparezca en cualquier fecha; no separa el daño de un cierre o estrangulamiento protectivo del operador, que en datos mensuales se ve igual.
- Con fechas falsas el padre cercano pudo ser golpeado por otro hijo en la ventana, porque las fracturas se agrupan en el tiempo y el espacio; una brecha en una fecha falsa tiene entonces más de una lectura.
- Los intervalos son bootstrap por pads hijo sin ajuste por comparaciones múltiples; con 7 meses de prueba y 4 desplazamientos, alguno puede quedar fuera de su intervalo por azar.
- La base de -6 a -4 exige datos en esos meses y deja fuera padres muy jóvenes, así que la muestra de la tabla de pretendencia es algo menor que la del resultado principal.
