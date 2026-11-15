# Validación del eje este-oeste

Página generada por `pipeline/validacion.py`. Somete el eje de mayor merma de `pipeline/costo.py` a tres pruebas: otros resultados medidos sobre los mismos eventos, el eje año por año y una prueba fuera de tiempo en la que el eje se estima con los eventos viejos y se evalúa en los nuevos. Usa las mismas repeticiones y semilla que la página de anisotropía (400 de bootstrap por pads hijo y 499 permutaciones por bloques).

## Resultados alternativos

Eje principal (caída del caudal al mes 1, efectos fijos de área, eventos de 0,3 a 1 km): 93 grados (E-O), IC de 70 a 122 grados, n = 1.734, p de permutación 0,022. El SHmax publicado es unos 67,5 grados. Cada fila repite el mismo ajuste con otra variable de resultado, en los mismos eventos (se descartan los que no tienen el dato).

| Resultado | n | Eje (grados) | IC 95% | Ancho IC | p perm. | Dif. con el eje principal | Dif. con SHmax | Apunta al eje principal | Definido |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| Caída del caudal al mes 1 (estimación principal) | 1.734 | 93 | 70 a 122 | 53 | 0,022 | 0 | 25 | sí | sí |
| Salto del corte de agua (meses 0 a 1 contra 3 previos) | 1.687 | 82 | 61 a 101 | 39 | 0,036 | -10 | 15 | sí | sí |
| Caída de la fracción de días efectivos (TEF) | 1.734 | 116 | 76 a 150 | 75 | 0,196 | 23 | 49 | sí | no |
| Caída del caudal al mes 2 | 1.721 | 75 | 176 a 155 | 159 | 0,848 | -18 | 7 | sí | no |
| Caída del caudal al mes 3 | 1.712 | 0 | 98 a 84 | 166 | 0,932 | 87 | -67 | no | no |
| Cierre declarado en los meses 0 a 1 (probabilidad lineal) | 1.734 | 137 | 66 a 26 | 140 | 0,522 | 44 | 69 | sí | no |

El IC contiene el eje principal (93 grados) en 4 de 5 resultados alternativos y el eje queda definido (IC de menos de 90 grados y p de permutación menor que 0,10) en 1: Salto del corte de agua (meses 0 a 1 contra 3 previos) (82 grados). El único que tiene un eje definido apunta al mismo eje que el principal; los demás no permiten decir nada porque su IC es ancho o su p no baja de 0,10. El IC no contiene el eje principal en: Caída del caudal al mes 3.

Un eje se considera definido si el IC mide menos de 90 grados y el p de permutación es menor que 0,10. Las diferencias son con signo, en grados, módulo 180 y en el rango de menos 90 a 90. El salto del corte de agua y el cierre declarado miden cosas distintas de la caída del caudal (un golpe de agua o una decisión operativa), así que que apunten o no al mismo eje es información, no un error.

## Eje por año de fractura del hijo

Se usan los años con al menos 120 eventos; los años con menos se juntan con los siguientes hasta llegar a ese mínimo y un resto final corto se suma al grupo anterior.

| Resultado | n | Eje (grados) | IC 95% | Ancho IC | p perm. | Dif. con el eje principal | Dif. con SHmax | Apunta al eje principal | Definido |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 2011 a 2015 | 266 | 104 | 50 a 159 | 109 | 0,586 | 11 | 37 | sí | no |
| 2016 a 2018 | 156 | 102 | 17 a 0 | 163 | 0,606 | 9 | 34 | sí | no |
| 2019 a 2021 | 227 | 81 | 180 a 165 | 165 | 0,940 | -11 | 14 | sí | no |
| 2022 | 198 | 99 | 44 a 144 | 101 | 0,282 | 6 | 31 | sí | no |
| 2023 | 172 | 75 | 3 a 138 | 136 | 0,868 | -18 | 7 | sí | no |
| 2024 | 224 | 85 | 29 a 115 | 86 | 0,200 | -8 | 17 | sí | no |
| 2025 | 297 | 8 | 123 a 67 | 124 | 0,184 | -85 | -59 | no | no |
| 2026 | 194 | 84 | 56 a 142 | 86 | 0,344 | -9 | 17 | sí | no |

El IC contiene el eje principal en 7 de 8 grupos de años y el eje queda definido en 0. El IC no contiene el eje principal en: 2025. Que los IC contengan el eje principal se debe sobre todo a que son anchos (cada grupo tiene pocos pads hijo). La diferencia con el eje principal, ponderada por 1 sobre el ancho del IC al cuadrado, tiene una pendiente de -3,0 grados por año en 8 grupos. Con tan pocos grupos y los IC anchos es una descripción, no una tendencia demostrada.

## Fuera de tiempo

Entrenamiento: eventos cuyo hijo se fractura hasta 2023-06 (925 eventos). Prueba: los posteriores (809). El corte deja al menos 500 eventos de cada lado y se fijó antes de ver el resultado. El eje de entrenamiento sale de `ajustar_eje` con los mismos controles y efectos fijos de área.

| Resultado | n | Eje (grados) | IC 95% | Ancho IC | p perm. | Dif. con el eje principal | Dif. con SHmax | Apunta al eje principal | Definido |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| Entrenamiento (hasta 2023-06) | 925 | 92 | 66 a 120 | 54 | 0,028 | -1 | 25 | sí | sí |
| Prueba (después de 2023-06) | 809 | 88 | 34 a 161 | 128 | 0,432 | -5 | 21 | sí | no |

En la prueba se ajusta la caída sobre distancia, log de la edad, efectos fijos de área y un solo término cos(2 * (rumbo - eje)). La mejora es la fracción de la suma de cuadrados de los residuos que se elimina respecto del modelo sin ángulo, para el eje de entrenamiento, el SHmax y 200 ejes al azar. El IC de las filas con eje es un bootstrap por pads hijo de la prueba; el de la fila de ejes al azar son los percentiles 2,5 y 97,5 de esa distribución. La mejora de un eje nunca es negativa, así que el límite inferior de esos IC queda en 0 y la comparación informativa es la de las diferencias.

| Modelo | n entrenamiento | n prueba | Eje (grados) | Mejora de la suma de cuadrados | IC 95% |
| --- | ---: | ---: | ---: | ---: | --- |
| Eje de entrenamiento | 925 | 809 | 92 | 0,40% | 0,00% a 3,06% |
| SHmax publicado | 925 | 809 | 68 | 0,22% | 0,00% a 2,97% |
| Eje aleatorio (mediana de 200) | 925 | 809 |  | 0,21% | 0,00% a 0,41% |
| Entrenamiento menos SHmax | 925 | 809 |  | 0,18% | -1,23% a 1,73% |
| Entrenamiento menos la mediana de los ejes aleatorios | 925 | 809 |  | 0,19% | -0,63% a 1,41% |
| Proporción de ejes aleatorios con mejora igual o mayor que el de entrenamiento | 925 | 809 |  | 6,50% |  |
| Eje ajustado en la prueba (cota, dentro de muestra) | 925 | 809 | 88 | 0,41% |  |

El eje estimado solo con el entrenamiento (925 eventos) es 92 grados. En la prueba (809 eventos) reduce la suma de cuadrados de los residuos en 0,40% (IC 0,00% a 3,06%); el SHmax publicado, en 0,22%; la mediana de 200 ejes al azar, en 0,21%. 6,5% de los ejes al azar mejora tanto o más que el de entrenamiento. La mejora del eje de entrenamiento menos la del SHmax es 0,18% (IC -1,23% a 1,73%); menos la mediana de los ejes al azar, 0,19% (IC -0,63% a 1,41%). Ajustado en la prueba, el eje queda en 88 grados (IC 34 a 161, p de permutación 0,432), a 4 grados del de entrenamiento; en la prueba el eje no está definido. No se puede afirmar que el eje de entrenamiento generalice mejor que el SHmax ni que los ejes al azar: los IC de ambas diferencias incluyen cero. En todos los casos la mejora es chica, de menos del 1% de la suma de cuadrados de los residuos del modelo sin ángulo: el ángulo explica poco de la caída.

## Límites

- La prueba fuera de tiempo no es una réplica independiente: sale del mismo warehouse, el mismo campo y los mismos padres, y un padre puede aparecer a ambos lados del corte.
- En la prueba fuera de tiempo solo el eje sale de los datos de entrenamiento: los coeficientes de distancia y edad, los efectos fijos de área y el índice de los controles (que se construye con todos los períodos) se calculan con los eventos de la prueba. Es fuera de muestra para el eje, no para el modelo completo.
- Se prueban cinco resultados alternativos y ocho grupos de años sin corregir por comparaciones múltiples; solo uno de los resultados alternativos llega a p de permutación menor que 0,10. El corte de la prueba es una sola elección y no se varió.
- Un IC que cruza los 180 grados se lee como un intervalo que da la vuelta: por ejemplo, de 176 a 155 es de 176 pasando por 0 hasta 155.
- Los resultados alternativos comparten eventos y controles con el principal: que apunten al mismo eje es consistencia, no una prueba aparte.
- El término angular tiene coeficiente libre: un eje a 90 grados del verdadero también reduce la suma de cuadrados. Por eso se informa el eje ajustado en la prueba.
- Con grupos chicos el bootstrap por pads hijo es poco fiable, y los IC anchos no son evidencia contra el eje principal.
- Es una comparación estadística: el eje es la dirección de la merma observada, no una medición de esfuerzos.
