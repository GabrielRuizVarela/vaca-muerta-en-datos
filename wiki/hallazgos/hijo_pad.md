# El hijo contra sus hermanos del mismo pad

Página generada por `pipeline/hijo_pad.py`. Pregunta si, dentro de un mismo pad, el hijo que se fracturó cuando ya producían pozos cuya rama pasa a menos de 600 m de la suya rinde menos petróleo por metro de rama en sus primeros 12 meses que su hermano fracturado con menos exposición. Compara hijos del mismo pad, así que el área, el operador, la época y casi todo el diseño de la terminación quedan fijos. Complementa [Hijos cerca de pozos depletados](hijo.md) y [Hijos dentro de celdas de 2 km](hijo_celdas.md), que miden la distancia en superficie y dieron no firme. La regla se fijó antes de correr: está en el encabezado de `pipeline/hijo_pad.py`, en el commit que solo trae las constantes.

## Resumen

Veredicto contra la regla fijada: **no se ve degradación**. Dentro del pad, el hijo que se fracturó con más petróleo ya producido por ramas a menos de 600 m no se ve que rinda menos que el que se fracturó con menos: el IC de la pendiente incluye cero y está dentro de 5% del rendimiento virgen por cada 100 bbl por metro de exposición, y el control negativo también incluye cero. Es lo que se ve con esta medición, y no es que no haya degradación (ver Límites).

- Rendimiento de los hijos sin exposición a 12 meses: mediana de 85,8 bbl por metro de rama, sobre 328 hijos.
- Pendiente dentro del pad: 0,1 bbl por metro de rama por cada 100 bbl por metro de exposición (IC 95%: -0,8 a 1,1), o sea 0,1% del rendimiento virgen (IC 95%: -0,9% a 1,2%), sobre 850 hijos de 234 pads.
- Control negativo, la misma pendiente con la exposición de pozos posteriores a la ventana del hijo: 0,3 bbl por metro de rama (IC 95%: -0,1 a 0,9). Incluye cero.
- Cota superior de la pérdida (el extremo bajo del IC, no una estimación): 0,8 bbl por metro de rama por cada 100 bbl por metro de exposición, o 0,9% del rendimiento virgen; a la mediana de las exposiciones positivas, 388 bbl por metro, son 2,9 bbl por metro de rama.
- Pads que informan: 132 de 234 tienen una dispersión de la exposición de al menos 50 bbl por metro entre sus hijos (mediana de la dispersión: 269 bbl por metro); 39% de los hijos no tienen exposición.
- Se publican todos los modelos calculados; el veredicto sale solo del modelo principal y su control negativo.

## Muestra y cobertura

Las ramas medidas cubren entre 76% y 98% de los hijos horizontales fracturados de 2016 a 2023, pero solo 39% de los de 2024 y 25% de los de 2025: la muestra es toda de 2016 a 2023 y no habla de los hijos recientes. La exposición cuenta solo pozos con la rama medida, así que es una cota inferior de la exposición verdadera.

- Paso 1, mart_pozo_12m (petrolíferos de shale con 12 meses): 2.100 hijos.
- Paso 2, con área, pad, coordenadas y primer petróleo: 2.100 hijos.
- Paso 3, con rama, etapas y arena: 1.653 hijos.
- Paso 4, con fecha de primera fractura: 1.653 hijos.
- Paso 5, primer petróleo entre 0 y 12 meses después de la fractura: 1.612 hijos.
- Paso 6, primera fractura entre 2016 y 2023: 977 hijos en 302 pads.
- Paso 7, con la rama horizontal medida: 878 hijos en 262 pads.
- Paso 8, pad con al menos 2 hijos con la rama medida: 850 hijos en 234 pads.

| Año de la primera fractura | Hijos | Pads | Hijos en pads con dispersión |
| --- | ---: | ---: | ---: |
| 2016 | 63 | 26 | 29 |
| 2017 | 61 | 24 | 30 |
| 2018 | 50 | 16 | 30 |
| 2019 | 90 | 28 | 37 |
| 2020 | 53 | 15 | 40 |
| 2021 | 175 | 47 | 104 |
| 2022 | 179 | 48 | 141 |
| 2023 | 179 | 42 | 135 |

## Regla fijada antes de correr

La unidad es el hijo con 12 meses publicados, con rama, etapas, arena y fecha de primera fractura, cuyo primer petróleo llega entre 0 y 12 meses después de la fractura, fracturado de 2016 a 2023, con la rama medida y en un pad con al menos 2 hijos así. El resultado es el petróleo de 12 meses por metro de rama. La exposición es el petróleo acumulado, hasta el mes anterior a la fractura del hijo, de los pozos de shale con la rama medida cuya rama pasa a menos de 600 m de la suya (distancia mínima entre ramas), por metro de rama del hijo.

El modelo es de mínimos cuadrados con efectos fijos de pad, la rama del hijo, la unidad donde navega y la parte de la exposición que viene de la misma unidad. El IC 95% es de percentiles de un bootstrap por pads, con 2.000 repeticiones y la misma semilla para el modelo y su control negativo. El control negativo es el mismo modelo con la exposición de los pozos cuyo primer petróleo es posterior a la ventana de 12 meses del hijo: no pudieron depletarlo ni interferirlo. El rendimiento virgen es la mediana del resultado entre los hijos sin exposición.

- Sostiene degradación: el IC de la pendiente queda por debajo de cero y el del control negativo incluye cero.
- No se ve degradación: los dos IC incluyen cero y los extremos del IC de la pendiente están dentro de 5% del rendimiento virgen por cada 100 bbl por metro de exposición.
- Ubicación: el IC del control negativo excluye cero.
- No firme: cualquier otro caso. Sin muestra: menos de 100 pads con dispersión de exposición de al menos 50 bbl por metro, o una estimación que no se puede calcular.

## Coeficientes

Pendiente dentro del pad en bbl por metro de rama por cada 100 bbl por metro de exposición. Cada modelo tiene su control negativo con la exposición de pozos posteriores. El porcentaje es contra el rendimiento virgen del modelo. Solo el modelo principal tiene veredicto.

| Modelo | Exposición | Pendiente | IC 95% | % del virgen | Hijos | Pads | Pads con dispersión |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| Principal (decide el veredicto) | real | 0,10 | -0,76 a 1,06 | 0,1% | 850 | 234 | 132 |
| Principal (decide el veredicto) | control negativo | 0,35 | -0,14 a 0,95 | 0,4% | 850 | 234 | 142 |
| Sin controles, solo efectos fijos de pad | real | 0,75 | -0,07 a 1,75 | 0,9% | 850 | 234 | 132 |
| Sin controles, solo efectos fijos de pad | control negativo | 0,41 | -0,09 a 0,99 | 0,5% | 850 | 234 | 142 |
| Ramas a menos de 300 m | real | -0,32 | -1,80 a 1,20 | -0,4% | 850 | 234 | 99 |
| Ramas a menos de 300 m | control negativo | 0,65 | -0,13 a 1,53 | 0,7% | 850 | 234 | 107 |
| Ramas a menos de 1.000 m | real | -0,06 | -0,67 a 0,65 | -0,1% | 850 | 234 | 146 |
| Ramas a menos de 1.000 m | control negativo | 0,20 | -0,11 a 0,61 | 0,2% | 850 | 234 | 147 |
| Solo exposición de otros pads | real | 0,07 | -0,78 a 1,02 | 0,1% | 850 | 234 | 130 |
| Solo exposición de otros pads | control negativo | 0,42 | -0,09 a 1,00 | 0,5% | 850 | 234 | 138 |
| Solo exposición de la misma unidad | real | -0,03 | -1,20 a 1,22 | 0,0% | 850 | 234 | 132 |
| Solo exposición de la misma unidad | control negativo | 1,69 | 0,85 a 2,44 | 1,9% | 850 | 234 | 134 |
| Con los meses desde la primera fractura del pad | real | -0,07 | -0,87 a 0,87 | -0,1% | 850 | 234 | 132 |
| Con los meses desde la primera fractura del pad | control negativo | 0,53 | 0,00 a 1,03 | 0,6% | 850 | 234 | 142 |

## Equilibrio dentro del pad, antes del resultado

Pendiente dentro del pad de cada variable de diseño sobre la exposición (por cada 100 bbl por metro), con el mismo bootstrap. Dice cuánto de la exposición dentro del pad es el orden de las fracturas o el diseño.

| Variable | Pendiente | IC 95% |
| --- | ---: | --- |
| Rama horizontal (m) | -44,5 | -64,5 a -26,1 |
| Etapas | -0,79 | -1,13 a -0,47 |
| Arena por metro (tn/m) | -0,005 | -0,014 a 0,002 |
| Meses desde la primera fractura del pad | 0,23 | 0,01 a 0,63 |

Variables que cambian con la exposición dentro del pad, con IC que excluye cero: Rama horizontal (m), Etapas, Meses desde la primera fractura del pad.

## Límites

- La exposición cuenta solo ramas medidas: es una cota inferior de la exposición verdadera. Con un error de medición de ese tipo la pendiente por barril medido se atenúa hacia cero y la cota superior de la pérdida queda corta. Por eso "no se ve degradación" no es "no hay degradación".
- El control negativo es menos potente que la exposición real: cuenta pozos posteriores a la ventana del hijo, muchos de 2024 a 2026, y la fuente cubre pocos de 2024 y 2025. Un IC del control que incluye cero informa menos que el de la exposición real, y que el control del modelo principal incluya cero no lo vuelve una prueba fuerte. En el modelo de la misma unidad el control excluye cero, y ese modelo no se lee como nulo.
- Dentro del pad, la exposición es sobre todo el orden de las fracturas y la posición de cada rama, no solo la depleción: los efectos fijos de pad no quitan una tendencia dentro del pad. El equilibrio de arriba muestra cuánto cambia el diseño con la exposición, y el modelo con los meses desde la primera fractura del pad mira el orden; ninguno lo elimina. Por lo mismo, el control negativo se mueve en sentido contrario a la exposición real (el hijo fracturado primero tiene la menor exposición real y la mayor de control, por los hermanos que vienen después): no es una prueba independiente del orden.
- El resultado es por metro de rama de la fractura, y la exposición también: los dos comparten el denominador, así que un hijo de rama corta tiene a la vez un rendimiento y una exposición por metro más altos.
- Hijos y expositores del mismo pad comparten la roca, pero no la profundidad: la unidad es un control, no la zona de aterrizaje.
- La distancia entre ramas es la mínima, no el espaciamiento a lo largo de la rama.
- Es una asociación dentro del pad con controles de diseño, no una afirmación causal.
- Los intervalos no tienen ajuste por comparaciones múltiples: se publican todos los modelos calculados, favorables o no.
