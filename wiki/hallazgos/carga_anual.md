# La subida de 2026 con la misma antigüedad de carga

Se prueba si la brecha del mes 1 de 2026 sigue mayor que la de 2021 a 2024 cuando todos los años se miran con el mismo criterio de visibilidad de carga: hijos con rezago de 0 a 3 meses e inicio hasta U menos 3 meses, y eventos del resultado principal sobre los pares que quedan. La regla de esta prueba se fijó antes de calcular ninguna cifra (ver el docstring de pipeline/carga_anual.py) y no se cambió después de ver resultados.

## Veredicto

**no firme**.

D (brecha de 2026 menos brecha de 2021 a 2024, muestra de antigüedad constante): -14,7 puntos, IC 95 % [-46,2, 12,7].

Eventos cercanos de 2026 con el mes 1 medido: 195. Bloques de 5 km en total: 69.

Remuestras del bootstrap con D definido: 400 de 400. El IC sale de los percentiles de esas; una remuestra en la que un período queda sin cercanos o sin controles no tiene D y no entra.

Guarda de operador: D_YPF = -20,7 puntos con 157 eventos cercanos de YPF en 2026.

## Qué cambia con este veredicto

La frase que decía que la brecha del mes 1 llega a 44 puntos en 2026 sale del README y del caso de estudio, y la operación interferencia_anual del agente avisa cuando el año consultado tiene carga incompleta (completitud estimada del último mes del año menor que 0,80, según pipeline.carga). El perfil por año se sigue publicando como dato.

En los dos casos la hipótesis anio_2026_carga queda en el libro de hallazgos (expectativa: límite superior del IC de D menor que 0).

## Perfil anual

Brecha del mes 1 por año en puntos (índice por 100), con IC 95 % por bloques de 5 km.

| Año | Muestra | Hijos | Cercanos | Controles | Bloques 5 km | Brecha | IC bajo | IC alto |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2019 | constante | 23 | 15 | 209 | 14 | 8,7 | -74,1 | 15,8 |
| 2020 | constante | 9 | 17 | 35 | 5 | -10,6 | -17,0 | -5,5 |
| 2021 | constante | 33 | 63 | 503 | 16 | -11,0 | -35,0 | 0,5 |
| 2022 | constante | 43 | 71 | 718 | 19 | -40,8 | -69,3 | -6,1 |
| 2023 | constante | 63 | 76 | 1051 | 25 | -27,9 | -57,1 | -13,4 |
| 2024 | constante | 87 | 133 | 1540 | 32 | -9,6 | -27,7 | -1,0 |
| 2025 | constante | 122 | 206 | 2123 | 40 | -48,6 | -73,2 | -25,6 |
| 2026 | constante | 88 | 195 | 1788 | 30 | -35,6 | -66,8 | -11,9 |
| 2019 | completa | 74 | 80 | 820 | 31 | -16,2 | -53,0 | 5,5 |
| 2020 | completa | 38 | 41 | 459 | 17 | -4,3 | -88,3 | 30,1 |
| 2021 | completa | 106 | 137 | 1482 | 36 | -20,7 | -41,3 | -6,4 |
| 2022 | completa | 140 | 232 | 1761 | 47 | -34,5 | -48,3 | -15,4 |
| 2023 | completa | 157 | 213 | 2397 | 51 | -19,7 | -33,3 | -12,4 |
| 2024 | completa | 176 | 279 | 2540 | 56 | -22,6 | -33,6 | -10,2 |
| 2025 | completa | 200 | 372 | 3132 | 66 | -32,4 | -55,6 | -18,9 |
| 2026 | completa | 125 | 243 | 2081 | 41 | -44,5 | -70,9 | -21,4 |

## Descriptivo

D con 2025 y 2026 juntos: -22,4 puntos, IC 95 % [-42,3, -2,3] (401 cercanos, 77 bloques, 400 de 400 remuestras con D definido).

La muestra completa reproduce mart_interferencia_anual 2019 a 2026: sí (misma cantidad de eventos cercanos y la misma brecha en cada año, con una tolerancia de 1e-9 en el índice).

## Qué no prueba

- La muestra restringida ve solo a los hijos de carga rápida: dice si la subida existe entre esos hijos, no en toda la cuenca.
- Un hijo de carga tardía sigue existiendo en el terreno: un control puede estar cerca de uno sin que se vea, en todos los años por igual. La prueba iguala esa contaminación entre años; no la quita.
