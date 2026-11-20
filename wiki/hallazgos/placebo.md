# Pruebas de falsación del estudio de eventos

Página generada por `pipeline/placebo.py`. Somete el resultado principal de interferencia (al mes 1 de la fractura de un hijo, los padres a menos de 1 km conservan unos 23 puntos menos de su caudal previo que los controles a 2 a 5 km) a tres pruebas en las que ese resultado no debería aparecer: una brecha previa a la fractura, brechas en fechas de fractura falsas y un eje de mayor merma con las fechas permutadas. Los intervalos son bootstrap por pads hijo (400 repeticiones, semilla fija); el resumen de las permutaciones usa 200 sorteos.

## Pretendencia

Brecha entre padres cercanos (menos de 1 km del hijo) y controles (2 a 5 km), en medianas del índice, en los meses alrededor de la fractura (k = 0 es el mes de la fractura). Como la base del índice principal son los meses -3 a -1, ahí el índice vale 1 por construcción en promedio y no puede mostrar una diferencia previa; por eso la tabla principal toma como base los meses -6 a -4, que no se usan como mes de prueba. Los padres deben tener datos en esa base y producir más de 1 m3/d.

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Índice cercanos | Índice controles | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| -3 | 2.048 | 17.788 | 0,906 | 0,931 | -2,5 | -4,8 a -0,6 |
| -2 | 2.048 | 17.778 | 0,855 | 0,891 | -3,6 | -6,0 a -1,3 |
| -1 | 2.040 | 17.744 | 0,793 | 0,856 | -6,3 | -9,7 a -3,5 |
| 0 | 2.044 | 17.792 | 0,607 | 0,817 | -21,0 | -25,6 a -17,5 |
| 1 | 2.048 | 17.757 | 0,524 | 0,780 | -25,6 | -31,3 a -21,2 |
| 2 | 2.048 | 17.753 | 0,587 | 0,757 | -17,0 | -21,5 a -12,9 |
| 3 | 2.034 | 17.595 | 0,611 | 0,727 | -11,6 | -16,2 a -6,9 |

Con la base del resultado principal (meses -3 a -1) la lectura de k = -3 a -1 queda forzada, pero k = 0 a 3 reproduce las cifras publicadas:

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Índice cercanos | Índice controles | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| -3 | 2.094 | 18.323 | 1,062 | 1,041 | 2,1 | 0,6 a 3,6 |
| -2 | 2.094 | 18.313 | 0,999 | 0,999 | 0,0 | -0,8 a 0,7 |
| -1 | 2.086 | 18.279 | 0,931 | 0,962 | -3,1 | -4,3 a -1,2 |
| 0 | 2.090 | 18.327 | 0,754 | 0,924 | -17,0 | -20,6 a -14,1 |
| 1 | 2.094 | 18.291 | 0,654 | 0,885 | -23,0 | -27,3 a -18,2 |
| 2 | 2.094 | 18.286 | 0,720 | 0,860 | -14,0 | -18,0 a -10,4 |
| 3 | 2.080 | 18.127 | 0,739 | 0,830 | -9,2 | -13,2 a -5,5 |

Sin los eventos en que el padre tuvo, en los 6 meses anteriores, la fractura de otro hijo a menos de 2 km (para descartar que la brecha previa sea un golpe anterior de un pozo vecino del mismo pad), con la base de -6 a -4:

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Índice cercanos | Índice controles | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| -3 | 1.213 | 12.114 | 0,908 | 0,940 | -3,2 | -5,7 a -1,0 |
| -2 | 1.213 | 12.104 | 0,872 | 0,905 | -3,4 | -5,5 a -1,2 |
| -1 | 1.209 | 12.070 | 0,816 | 0,875 | -6,0 | -9,6 a -3,0 |
| 0 | 1.209 | 12.118 | 0,644 | 0,837 | -19,3 | -23,6 a -15,8 |
| 1 | 1.213 | 12.083 | 0,531 | 0,795 | -26,4 | -33,6 a -21,2 |
| 2 | 1.213 | 12.086 | 0,591 | 0,773 | -18,2 | -22,6 a -11,9 |
| 3 | 1.201 | 12.015 | 0,615 | 0,743 | -12,8 | -17,5 a -7,1 |

## Fechas de fractura falsas

Se corre la fecha de fractura de todos los hijos d meses, se conservan los pares padre e hijo y se exige que el padre tenga al menos 6 meses de producción en la fecha falsa y datos en los meses -3 a -1 (el mes 1 puede faltar y entonces no entra). La brecha real se calcula en los mismos eventos con su fecha verdadera. d = 0 es el resultado principal. Solo los desplazamientos de -6 y -12 meses son placebos limpios (la fecha falsa cae antes de la fractura real); con +6 y +12 el mes 1 falso puede caer sobre meses ya afectados por la fractura real, así que una brecha ahí no refuta nada.

| Desplazamiento (meses) | Eventos cercanos | Brecha del mes 1 (puntos) | IC 95% (puntos) | Brecha real en los mismos eventos (puntos) |
| ---: | ---: | ---: | --- | ---: |
| -12 | 1.347 | -2,4 | -5,5 a 1,1 | -23,3 |
| -6 | 1.648 | -0,1 | -2,7 a 3,2 | -23,4 |
| 0 | 2.094 | -23,0 | -27,4 a -17,8 | -23,0 |
| 6 | 1.922 | 0,5 | -2,4 a 3,5 | -21,7 |
| 12 | 1.721 | 0,2 | -2,8 a 2,3 | -21,1 |

## Fechas permutadas

Con 200 permutaciones de las fechas de fractura entre hijos del mismo año (unos 6.332 eventos cercanos por sorteo), la brecha del mes 1 tiene media -6,4 puntos, desvío 0,7 y un rango de -7,8 a -5,1 (percentiles 2,5 y 97,5; extremos -8,1 y -4,9). La brecha real, -23,0 puntos, queda fuera de ese rango; la fracción de permutaciones con una brecha tan negativa o más es 0,005 (el mínimo posible con 200 sorteos es 0,005).

## Eje de mayor merma con fechas permutadas

Mismo ajuste axial coseno, mismos controles y efectos fijos de área que `pipeline/costo.py`, sobre los eventos de 0,3 a 1 km, con las fechas permutadas. El eje se considera definido si el p de permutación es menor que 0,10 y el IC mide menos de 90 grados. Para las primeras permutaciones se calcula el eje con su intervalo; el resumen compara la amplitud del término angular de todas las permutaciones con la real.

| Escenario | Eventos | Eje (grados) | IC 95% (grados) | Ancho IC | Amplitud | p permutación | Definido |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| real | 1.751 | 93 | 70 a 123 | 53 | 0,068 | 0,036 | sí |
| permutacion 1 | 1.751 | 49 | 8 a 77 | 69 | 0,042 | 0,194 | no |
| permutacion 2 | 1.751 | 57 | 156 a 135 | 159 | 0,015 | 0,726 | no |
| permutacion 3 | 1.751 | 7 | 108 a 89 | 160 | 0,010 | 0,960 | no |
| permutacion 4 | 1.751 | 111 | 37 a 11 | 154 | 0,024 | 0,624 | no |
| permutacion 5 | 1.751 | 41 | 170 a 93 | 102 | 0,030 | 0,382 | no |
| permutacion 6 | 1.751 | 2 | 119 a 65 | 126 | 0,026 | 0,480 | no |
| permutacion 7 | 1.751 | 99 | 30 a 171 | 141 | 0,024 | 0,572 | no |
| permutacion 8 | 1.751 | 26 | 136 a 102 | 145 | 0,015 | 0,744 | no |
| permutacion 9 | 1.751 | 150 | 78 a 49 | 151 | 0,021 | 0,652 | no |
| permutacion 10 | 1.751 | 116 | 85 a 153 | 68 | 0,047 | 0,076 | sí |
| resumen de permutaciones | 1.751 | n/d | n/d | n/d | mediana 0,028, p95 0,059 | 0,025 | n/d |

En la fila de resumen el p es la fracción de permutaciones con una amplitud al menos igual a la real. Un intervalo de ejes puede cruzar los 180 grados (el límite inferior queda numéricamente por encima del superior): el eje es axial y el intervalo cierra la vuelta.

## Qué se concluye

- Pretendencia: hay una brecha previa. Con la base de los meses -6 a -4, el IC excluye cero en k = -3, -2, -1 (brechas de -2,5, -3,6, -6,3 puntos), así que los padres cercanos ya rendían distinto antes de la fractura (por un nivel distinto de los padres cercanos o por un efecto anticipado; estos datos no los separan). La brecha del mes 1 con esta base es -25,6 puntos y la parte atribuible a la fractura es menor.
- Fechas falsas: en los cuatro desplazamientos el intervalo incluye cero (d = -12: -2,4, d = -6: -0,1, d = 6: 0,5, d = 12: 0,2 puntos).
- Permutación: la brecha real (-23,0 puntos) queda fuera de las 200 brechas permutadas (rango -8,1 a -4,9). La media permutada es -6,4 puntos, no cero: con la fecha de otro hijo del mismo año los padres cercanos rinden menos que los controles. Una lectura posible es que, en zonas de desarrollo denso, un padre cercano a un hijo también lo está de otro que sí fracturó en esa fecha; no se verificó.
- Eje: de 10 permutaciones con intervalo, 1 dejan un eje definido; la fracción de las 200 con una amplitud tan grande como la real es 0,025 (amplitud real 0,068, mediana permutada 0,028, percentil 95 0,059; las permutaciones se submuestrean a los mismos 1.751 eventos que la real).
- Qué significa para el resultado principal: la caída de 23,0 puntos del mes 1 no es un artefacto de una fecha cualquiera (las fechas falsas dan cerca de cero y las permutadas dan -6,4 en promedio), pero no sale limpia: los padres cercanos ya rendían unos 6,3 puntos menos en el mes -1, y la brecha previa sigue sin los golpes previos de vecinos (-3,2, -3,4, -6,0 puntos en k = -3, -2, -1). Medida contra el nivel previo con la misma base (-6 a -4), la caída adicional al mes 1 es de 19,3 puntos (20,5 sin los golpes previos de vecinos). Ese descuento supone que la brecha previa es un nivel distinto de los padres cercanos que no sigue creciendo; si fuera un efecto anticipado o una deriva que continúa, el descuento sería otro, y los datos mensuales no permiten separarlos. Por eso los puntos del resultado principal son una cota superior del efecto, y lo que queda después del descuento es del orden de 19,3 a 20,5 puntos, condicional a ese supuesto. La media permutada no es cero y las fechas permutadas pueden coincidir con golpes reales de hijos vecinos, así que el valor p de la permutación (0,005 como mínimo con 200 permutaciones) es un piso, no una probabilidad exacta.

## Qué no prueba

- Pasar estas pruebas no demuestra causalidad. Descarta una brecha previa y una brecha que aparezca en cualquier fecha; no separa el daño de un cierre o estrangulamiento protectivo del operador, que en datos mensuales se ve igual.
- Con fechas falsas el padre cercano pudo ser golpeado por otro hijo en la ventana, porque las fracturas se agrupan en el tiempo y el espacio; una brecha en una fecha falsa tiene entonces más de una lectura.
- Los intervalos son bootstrap por pads hijo sin ajuste por comparaciones múltiples; con 7 meses de prueba y 4 desplazamientos, alguno puede quedar fuera de su intervalo por azar.
- La base de -6 a -4 exige datos en esos meses y deja fuera padres muy jóvenes, así que la muestra de la tabla de pretendencia es algo menor que la del resultado principal.
