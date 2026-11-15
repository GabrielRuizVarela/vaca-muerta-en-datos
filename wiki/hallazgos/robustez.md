# Robustez del eje y del costo

Página generada por `pipeline/robustez.py`. Repite la estimación de `pipeline/costo.py` en subconjuntos de eventos y con especificaciones alternativas, para ver si el eje de mayor merma y el coeficiente de desvío respecto del eje dependen de una parte de la muestra. Usa las mismas repeticiones y semilla que la página de anisotropía (400 de bootstrap y 499 permutaciones para el eje, 300 de bootstrap para el costo), así que la muestra completa reproduce los números de aquella página.

## Estabilidad del eje

Eje de la cuenca con efectos fijos de área en eventos de 0,3 a 1 km: 93 grados (E-O), IC de 70 a 122 grados, n = 1.734, p de permutación 0,022. El SHmax publicado es unos 67,5 grados.

| Grupo | Subconjunto | n | Eje (grados) | IC 95% | Ancho IC | p perm. | Diferencia con el eje completo | Diferencia con SHmax |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| completa | Muestra completa | 1.734 | 93 | 70 a 122 | 53 | 0,022 | 0 | 25 |
| periodo | Fractura del hijo 2011 a 2021 | 578 | 109 | 55 a 156 | 101 | 0,370 | 16 | 42 |
| periodo | Fractura del hijo 2021 a 2024 | 578 | 85 | 44 a 107 | 64 | 0,016 | -8 | 17 |
| periodo | Fractura del hijo 2024 a 2026 | 578 | 77 | 4 a 154 | 150 | 0,516 | -16 | 9 |
| operador | Padre YPF | 1.147 | 99 | 71 a 125 | 55 | 0,034 | 6 | 32 |
| operador | Padre de otros operadores | 587 | 71 | 4 a 150 | 145 | 0,298 | -22 | 4 |
| area | Sin LOMA CAMPANA | 1.040 | 79 | 30 a 122 | 93 | 0,220 | -14 | 11 |
| area | Sin LA AMARGA CHICA | 1.459 | 98 | 64 a 127 | 63 | 0,050 | 5 | 30 |
| area | Sin FORTIN DE PIEDRA | 1.591 | 99 | 73 a 127 | 55 | 0,032 | 6 | 31 |
| area | Sin BAJADA DEL PALO OESTE | 1.602 | 96 | 70 a 124 | 54 | 0,022 | 3 | 28 |
| area | Sin BANDURRIA SUR | 1.608 | 93 | 70 a 121 | 51 | 0,006 | 0 | 25 |
| distancia | 0,3 a 0,6 km | 627 | 98 | 58 a 128 | 70 | 0,028 | 5 | 30 |
| distancia | 0,6 a 1 km | 1.107 | 96 | 62 a 138 | 77 | 0,314 | 3 | 28 |
| recortada | Sin el 5% de mayor caída absoluta | 1.647 | 83 | 59 a 108 | 48 | 0,006 | -10 | 15 |

El IC de 13 de 13 subconjuntos contiene el eje de la muestra completa (93 grados). En 4 el IC mide 90 grados o más, así que el eje no está definido ahí (Fractura del hijo 2011 a 2021; Fractura del hijo 2024 a 2026; Padre de otros operadores; Sin LOMA CAMPANA); de los 9 restantes, 9 lo contienen. En 8 de los 9 con eje definido el p de permutación es menor que 0,10. Con p de permutación de 0,10 o más, o sea sin evidencia de anisotropía en ese corte, quedan 5 subconjuntos: Fractura del hijo 2011 a 2021; Fractura del hijo 2024 a 2026; Padre de otros operadores; Sin LOMA CAMPANA; 0,6 a 1 km. El IC incluye el SHmax publicado (67,5 grados) en 5 de los 9 con eje definido y no en la muestra completa. Donde el eje está definido, el IC no lo separa del completo; donde no está definido, el corte no permite decir nada.

Las diferencias son con signo, en grados, módulo 180 y en el rango de menos 90 a 90. Un IC que mide 90 grados o más no define un eje. Un subconjunto más chico tiene un IC más ancho solo por tener menos pads hijo, así que un IC ancho no es evidencia contra el eje completo.

## Estabilidad del coeficiente de desvío respecto del eje

Coeficiente `desvio_eje_10` (bbl diferidos en los meses 0 a 6 por cada 10 grados que el padre se aparta del eje de mayor merma, con el eje estimado fuera de muestra), reajustado con el mismo modelo de costo.

| Especificación | n | Coeficiente (bbl) | IC 95% | Mismo signo que la muestra completa | IC excluye cero |
| --- | ---: | ---: | --- | --- | --- |
| Muestra completa | 2.077 | -963 | -1.841 a 231 | sí | no |
| Resultado winsorizado al 1% y 99% | 2.077 | -597 | -1.228 a 213 | sí | no |
| Sin padres parados | 1.786 | -909 | -1.897 a 621 | sí | no |
| Sin LOMA CAMPANA | 1.289 | -881 | -2.557 a 2.163 | sí | no |
| Sin LA AMARGA CHICA | 1.761 | -740 | -1.481 a 550 | sí | no |
| Sin BAJADA DEL PALO OESTE | 1.911 | -729 | -1.692 a 173 | sí | no |
| Solo eventos de 0,3 a 1 km | 1.734 | -814 | -2.054 a 488 | sí | no |

El coeficiente de la muestra completa es -963 bbl por 10 grados (IC -1.841 a 231); no excluye el cero. El signo se repite en 6 de 6 especificaciones alternativas y el IC excluye el cero en 0. Ninguna especificación permite afirmar el efecto: sigue siendo una tendencia, no una conclusión.

## Límites

- Los subconjuntos no son independientes de la muestra completa: comparten eventos, así que coincidir con ella no es una réplica.
- Cortar por período, operador o distancia reduce la cantidad de pads hijo, y con pocos pads el bootstrap es poco fiable.
- Es un análisis de sensibilidad, no una prueba causal: el eje es la dirección de la merma observada, no del esfuerzo.
- Las especificaciones de costo no prueban que el modelo lineal esté bien especificado.
