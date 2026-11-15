# Libro de hallazgos

Cada hallazgo es una hipótesis en código (`pipeline/hallazgos.py`) que se re-evalúa en cada build. El historial muestra cómo cambia el veredicto entre versiones de los datos.

Estado: confirmado si cumple el umbral; debilitado si falla por menos del 25% del umbral; refutado si falla por más.

## Estado actual

| Hallazgo | Estado | Valor | Expectativa | Datos |
|---|---|---|---|---|
| `brecha_mes1` | confirmado | -0,229 | < -0,100 | 2026-09 (1f07aee9b988) |
| `recuperacion_mes6` | confirmado | -0,021 | abs< 0,050 | 2026-09 (1f07aee9b988) |
| `salto_agua` | confirmado | 0,188 | > 0,100 | 2026-09 (1f07aee9b988) |
| `parado_declarado` | confirmado | 0,070 | > 0,030 | 2026-09 (1f07aee9b988) |
| `anisotropia` | confirmado | -0,260 | < -0,100 | 2026-09 (1f07aee9b988) |

## brecha_mes1

Al mes 1 de la fractura del hijo, el índice de los padres cercanos queda por debajo del de los controles (mediana cercano menos control).

Expectativa: valor < -0,100 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | -0,229 | confirmado |

## recuperacion_mes6

Al mes 6 la brecha se cerró: la diferencia de medianas entre cercanos y controles es chica.

Expectativa: valor abs< 0,050 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | -0,021 | confirmado |

## salto_agua

Los padres cercanos tienen saltos de corte de agua (más de 0,15) con más frecuencia que los controles (diferencia de proporciones).

Expectativa: valor > 0,100 (proporción).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | 0,188 | confirmado |

## parado_declarado

Los padres cercanos figuran como Parado Transitoriamente en el mes de la fractura con más frecuencia que los controles (diferencia de proporciones).

Expectativa: valor > 0,030 (proporción).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | 0,070 | confirmado |

## anisotropia

Entre eventos cercanos a 0,3 a 1 km, el eje de 56,25 a 101,25 grados pierde más producción al mes 1 que el eje de 0 +/- 22,5 grados (diferencia de medianas del índice).

Expectativa: valor < -0,100 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | -0,260 | confirmado |

Ver también [Interferencia entre fracturas](interferencia.md).
