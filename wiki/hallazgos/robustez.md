# Robustez del eje y del costo

Página generada por `pipeline/robustez.py`. Repite la estimación de `pipeline/costo.py` en subconjuntos de eventos y con especificaciones alternativas, para ver si el eje de mayor merma y el coeficiente de desvío respecto del eje dependen de una parte de la muestra. Usa las mismas repeticiones y semilla que la página de anisotropía (400 de bootstrap y 499 permutaciones para el eje, 300 de bootstrap para el costo), así que la muestra completa reproduce los números de aquella página.

## Estabilidad del eje

Eje de la cuenca con efectos fijos de área en eventos de 0,3 a 1 km: 93 grados (E-O), IC de 70 a 123 grados, n = 1.751, p de permutación 0,036. El SHmax publicado es unos 67,5 grados.

| Grupo | Subconjunto | n | Eje (grados) | IC 95% | Ancho IC | p perm. | Diferencia con el eje completo | Diferencia con SHmax |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| completa | Muestra completa | 1.751 | 93 | 70 a 123 | 53 | 0,036 | 0 | 26 |
| periodo | Fractura del hijo 2011 a 2021 | 583 | 105 | 50 a 151 | 100 | 0,314 | 12 | 38 |
| periodo | Fractura del hijo 2021 a 2024 | 584 | 88 | 52 a 115 | 63 | 0,068 | -6 | 20 |
| periodo | Fractura del hijo 2024 a 2026 | 584 | 73 | 170 a 148 | 158 | 0,582 | -20 | 5 |
| operador | Padre YPF | 1.147 | 99 | 71 a 125 | 55 | 0,034 | 6 | 32 |
| operador | Padre de otros operadores | 604 | 70 | 174 a 139 | 145 | 0,440 | -23 | 3 |
| area | Sin LOMA CAMPANA | 1.057 | 79 | 36 a 139 | 103 | 0,262 | -14 | 11 |
| area | Sin LA AMARGA CHICA | 1.476 | 98 | 61 a 130 | 69 | 0,102 | 5 | 31 |
| area | Sin FORTIN DE PIEDRA | 1.608 | 99 | 72 a 130 | 58 | 0,044 | 6 | 32 |
| area | Sin BAJADA DEL PALO OESTE | 1.619 | 96 | 71 a 124 | 53 | 0,030 | 3 | 29 |
| area | Sin BANDURRIA SUR | 1.625 | 93 | 73 a 120 | 47 | 0,008 | 0 | 26 |
| distancia | 0,3 a 0,6 km | 633 | 98 | 64 a 125 | 61 | 0,038 | 5 | 31 |
| distancia | 0,6 a 1 km | 1.118 | 96 | 61 a 144 | 83 | 0,308 | 3 | 29 |
| recortada | Sin el 5% de mayor caída absoluta | 1.664 | 83 | 60 a 108 | 48 | 0,008 | -10 | 15 |

El IC de 13 de 13 subconjuntos contiene el eje de la muestra completa (93 grados). En 4 el IC mide 90 grados o más, así que el eje no está definido ahí (Fractura del hijo 2011 a 2021; Fractura del hijo 2024 a 2026; Padre de otros operadores; Sin LOMA CAMPANA); de los 9 restantes, 9 lo contienen. En 7 de los 9 con eje definido el p de permutación es menor que 0,10. Con p de permutación de 0,10 o más, o sea sin evidencia de anisotropía en ese corte, quedan 6 subconjuntos: Fractura del hijo 2011 a 2021; Fractura del hijo 2024 a 2026; Padre de otros operadores; Sin LOMA CAMPANA; Sin LA AMARGA CHICA; 0,6 a 1 km. El IC incluye el SHmax publicado (67,5 grados) en 5 de los 9 con eje definido y no en la muestra completa. Donde el eje está definido, el IC no lo separa del completo; donde no está definido, el corte no permite decir nada.

Las diferencias son con signo, en grados, módulo 180 y en el rango de menos 90 a 90. Un IC que mide 90 grados o más no define un eje. Un subconjunto más chico tiene un IC más ancho solo por tener menos pads hijo, así que un IC ancho no es evidencia contra el eje completo.

## Estabilidad del coeficiente de desvío respecto del eje

Coeficiente `desvio_eje_10` (bbl diferidos en los meses 0 a 6 por cada 10 grados que el padre se aparta del eje de mayor merma, con el eje estimado fuera de muestra), reajustado con el mismo modelo de costo.

| Especificación | n | Coeficiente (bbl) | IC 95% | Mismo signo que la muestra completa | IC excluye cero |
| --- | ---: | ---: | --- | --- | --- |
| Muestra completa | 2.094 | -941 | -1.581 a 278 | sí | no |
| Resultado winsorizado al 1% y 99% | 2.094 | -555 | -1.108 a 376 | sí | no |
| Sin padres parados | 1.803 | -1.061 | -1.931 a 443 | sí | no |
| Sin LOMA CAMPANA | 1.306 | -983 | -2.665 a 1.584 | sí | no |
| Sin LA AMARGA CHICA | 1.778 | -538 | -1.320 a 635 | sí | no |
| Sin BAJADA DEL PALO OESTE | 1.928 | -570 | -1.281 a 547 | sí | no |
| Solo eventos de 0,3 a 1 km | 1.751 | -416 | -1.781 a 654 | sí | no |

El coeficiente de la muestra completa es -941 bbl por 10 grados (IC -1.581 a 278); no excluye el cero. El signo se repite en 6 de 6 especificaciones alternativas y el IC excluye el cero en 0. Ninguna especificación permite afirmar el efecto.

## Límites

- Los subconjuntos no son independientes de la muestra completa: comparten eventos, así que coincidir con ella no es una réplica.
- Cortar por período, operador o distancia reduce la cantidad de pads hijo, y con pocos pads el bootstrap es poco fiable.
- Es un análisis de sensibilidad, no una prueba causal: el eje es la dirección de la merma observada, no del esfuerzo.
- Las especificaciones de costo no prueban que el modelo lineal esté bien especificado.
