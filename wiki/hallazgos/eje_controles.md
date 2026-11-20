# Controles del eje

Página generada por `pipeline/eje_controles.py`. Pone al eje de mayor merma (93 grados) dos controles negativos: el eje en la ventana previa a la fractura del hijo y el eje con remuestreo por bloques espaciales en vez de pads.

## Resumen

- Eje previo (mes -1, base de los meses -6 a -4): 112 grados, IC 85 a 141 (ancho 57), p 0,058, a 18,8 grados de 93. Veredicto: **definido y cercano**. Dispara la regla de parada.
- Bloques de 5 km (74 bloques): 93 grados, IC 63 a 129 (ancho 66), p 0,394. Veredicto: **deja de estar definido**. Dispara la regla de parada.
- Comparación con la misma base limpia: el eje del mes 1 queda en 96 grados (a 2,7 de 93) y el principal reconstruido en 93.
- Referencia por pads: eje 93, IC 70 a 123, p 0,036; por bloques de 2 km (162 bloques): eje 93, IC 66 a 127, p 0,044.

## Resultados

Unidades son pads hijo o bloques según la prueba. El contraste es dos veces la amplitud, en puntos de índice.

| Prueba | Eventos | Unidades | Eje (grados) | IC 95% (grados) | Ancho IC | Contraste (puntos) | p permutación | Definido | Dist a 93 | Dist a SHmax | SHmax en IC |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `eje_previo_k-1` | 1.715 | 323 | 112 | 85 a 141 | 57 | 11,4 | 0,058 | sí | 18,8 | 44,3 | no |
| `eje_k1_base_limpia` | 1.716 | 323 | 96 | 63 a 131 | 68 | 14,4 | 0,024 | sí | 2,7 | 28,2 | sí |
| `eje_principal` | 1.751 | 325 | 93 | 67 a 124 | 57 | 13,7 | 0,022 | sí | 0,2 | 25,7 | sí |
| `bloques_5km` | 1.751 | 74 | 93 | 63 a 129 | 66 | 13,7 | 0,394 | no | 0,2 | 25,7 | sí |
| `bloques_2km` | 1.751 | 162 | 93 | 66 a 127 | 61 | 13,7 | 0,044 | sí | 0,2 | 25,7 | sí |
| `pads` | 1.751 | 325 | 93 | 70 a 123 | 53 | 13,7 | 0,036 | sí | 0,2 | 25,7 | no |

## Diagnóstico de la permutación por bloques (agregado después de ver los resultados)

La permutación de la regla intercambia los rumbos entre unidades del mismo tamaño. Con bloques grandes casi cada bloque tiene un tamaño propio y no se mueve, así que su p es poco informativo. Como control se rota el conjunto de rumbos de cada unidad por un ángulo uniforme propio (999 sorteos), que conserva la estructura interna de la unidad y rompe su relación con la caída. Este diagnóstico no cambia el veredicto de la regla, que se fijó antes de correr; se publica al lado.

| Unidad de remuestreo | Unidades | Eventos en unidades de tamaño único | p de la regla (mismo tamaño) | p por rotación |
| --- | ---: | ---: | ---: | ---: |
| pads | 325 | 101 | 0,036 | 0,040 |
| bloques de 2 km | 162 | 513 | 0,044 | 0,044 |
| bloques de 5 km | 74 | 907 | 0,394 | 0,078 |

## Regla fijada antes de correr

La muestra es la del eje principal (eventos de 0,3 a 1 km, controles de 2 a 5 km del mismo grupo de edad), con el mismo ajuste axial con efectos fijos de área y las mismas repeticiones (400 de bootstrap y 499 de permutación).
El eje previo usa el índice del mes -1 sobre la base de los meses -6 a -4; se publica junto al eje del mes 1 sobre esa misma base y al principal con la base original.
Un eje está definido si su p de permutación es menor que 0,10 y su IC mide menos de 90 grados; cerca de 93 es a menos de 30 grados.
El eje por bloques usa la muestra del resultado principal y remuestrea celdas de 5 km (2 km como referencia) en vez de pads, con la misma semilla; con menos de 30 bloques de 5 km no hay veredicto.
Para cada eje se informa si el SHmax publicado (67,5 grados) cae dentro de su IC.

## Qué no prueba

- El eje previo usa la misma muestra que el posterior, así que comparten ruido y no son independientes.
- La ventana previa mezcla pretendencia con selección de padres: un eje previo definido no separa esas dos lecturas.
- Es una condición necesaria, no un test de causa: solo pide que el eje no esté ya antes de la fractura.
