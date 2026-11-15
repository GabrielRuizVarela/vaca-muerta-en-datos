# Libro de hallazgos

Cada hallazgo es una hipótesis en código (`pipeline/hallazgos.py`) que se re-evalúa en cada build. El historial muestra cómo cambia el veredicto entre versiones de los datos.

Estado: confirmado si cumple el umbral; debilitado si falla por menos del 25% del umbral; refutado si falla por más.

Estado no firme: la hipótesis del eje (`anisotropia`) cumple el umbral, pero se marca no firme si el eje no es firme según la robustez y la validación fuera de tiempo. Eso pasa si el eje no está definido en algún subconjunto de `mart_robustez_eje` (IC de 90 grados o más, o p de permutación de 0,10 o más), si el IC de la muestra completa mide 90 grados o más, o si el eje estimado con datos viejos no se separa del SHmax publicado ni de ejes al azar en `mart_validacion_holdout`. Se lee de esos marts; no es un análisis nuevo. Los umbrales de las demás hipótesis no cambian.

El ledger solo agrega filas: cuando cambia la regla de una hipótesis se registra una fila nueva con la misma versión de datos y la fila anterior queda en el historial. La última fila de cada hipótesis es la vigente.

## Estado actual

| Hallazgo | Estado | Valor | Expectativa | Datos |
|---|---|---|---|---|
| `brecha_mes1` | confirmado | -0,229 | < -0,100 | 2026-09 (1f07aee9b988) |
| `recuperacion_mes6` | confirmado | -0,021 | abs< 0,050 | 2026-09 (1f07aee9b988) |
| `salto_agua` | confirmado | 0,188 | > 0,100 | 2026-09 (1f07aee9b988) |
| `parado_declarado` | confirmado | 0,070 | > 0,030 | 2026-09 (1f07aee9b988) |
| `anisotropia` | no firme | -0,260 | < -0,100 | 2026-09 (1f07aee9b988) |
| `sincronia_mes0` | confirmado | -0,097 | < -0,020 | 2026-09 (1f07aee9b988) |

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
| 2026-09 | 1f07aee9b988 | -0,260 | no firme |

## sincronia_mes0

La brecha del mes de la fractura crece con la fracción del mes posterior al inicio de la fractura del hijo: el límite superior del IC de la pendiente (índice por unidad de fracción) queda por debajo de -0,02 (regla fijada antes de correr, pipeline/sincronia.py).

Expectativa: valor < -0,020 (índice por unidad de fracción).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | -0,097 | confirmado |

Ver también [Interferencia entre fracturas](interferencia.md).
