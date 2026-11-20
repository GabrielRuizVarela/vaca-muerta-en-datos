# Libro de hallazgos

Cada hallazgo es una hipótesis en código (`pipeline/hallazgos.py`) que se re-evalúa en cada build. El historial muestra cómo cambia el veredicto entre versiones de los datos.

Estado: confirmado si cumple el umbral; debilitado si falla por menos del 25% del umbral; refutado si falla por más.

Estado no firme: la hipótesis del eje (`asimetria_de_superficie`, antes `anisotropia`) cumple el umbral, pero se marca no firme si el eje no es firme según la robustez y la validación fuera de tiempo. Eso pasa si el eje no está definido en algún subconjunto de `mart_robustez_eje` (IC de 90 grados o más, o p de permutación de 0,10 o más), si el IC de la muestra completa mide 90 grados o más, o si el eje estimado con datos viejos no se separa del SHmax publicado ni de ejes al azar en `mart_validacion_holdout`, o si dispara alguna pata de la regla de parada (`mart_eje_parada`: potencia, ventana previa, exposición, bloques). Se lee de esos marts; no es un análisis nuevo. Los umbrales de las demás hipótesis no cambian.

Estado de `hijo_depletado`: sale del veredicto de su propia regla (`pipeline/hijo.py`), no del umbral del valor. Confirmado si el veredicto es sostiene, refutado si es no se sostiene, y no firme en cualquier otro caso (ubicación, no firme o sin muestra). Su valor es el límite superior del IC del grupo muy depletado y no existe (s/d) cuando el control negativo no es nulo.

El ledger solo agrega filas: cuando cambia la regla de una hipótesis se registra una fila nueva con la misma versión de datos y la fila anterior queda en el historial. La última fila de cada hipótesis es la vigente.

## Estado actual

| Hallazgo | Estado | Valor | Expectativa | Datos |
|---|---|---|---|---|
| `brecha_mes1` | confirmado | -0,230 | < -0,100 | 2026-10 (b83ec7525506) |
| `recuperacion_mes6` | confirmado | -0,021 | abs< 0,050 | 2026-10 (b83ec7525506) |
| `salto_agua` | confirmado | 0,187 | > 0,100 | 2026-10 (b83ec7525506) |
| `parado_declarado` | confirmado | 0,070 | > 0,030 | 2026-10 (b83ec7525506) |
| `asimetria_de_superficie` | no firme | -0,248 | < -0,100 | 2026-10 (b83ec7525506) |
| `sincronia_mes0` | confirmado | -0,077 | < -0,020 | 2026-10 (b83ec7525506) |
| `brecha_mes1_bloques` | confirmado | -0,170 | < -0,100 | 2026-10 (b83ec7525506) |
| `sincronia_mes0_bloques` | confirmado | -0,083 | < -0,020 | 2026-10 (b83ec7525506) |
| `hijo_depletado` | no firme | s/d | < 0,000 | 2026-10 (b83ec7525506) |
| `inyeccion_r1` | confirmado | 0,505 | abs< 5,000 | 2026-10 (b83ec7525506) |
| `inyeccion_r2` | confirmado | 1,033 | > 0,800 | 2026-10 (b83ec7525506) |
| `inyeccion_r3` | confirmado | 1,000 | > 0,800 | 2026-10 (b83ec7525506) |
| `inyeccion_r4a` | confirmado | 0,067 | < 0,100 | 2026-10 (b83ec7525506) |
| `inyeccion_r4b` | confirmado | 0,484 | < 2,000 | 2026-10 (b83ec7525506) |
| `replicacion_colorado` | preregistrada | s/d | < 0,000 | 2026-10 (b83ec7525506) |
| `anio_2026_carga` | no firme | 0,109 | < 0,000 | 2026-10 (b83ec7525506) |
| `replicacion_wyoming` | preregistrada | s/d | < 0,000 | 2026-10 (b83ec7525506) |

## brecha_mes1

Al mes 1 de la fractura del hijo, el índice de los padres cercanos queda por debajo del de los controles (mediana cercano menos control).

Expectativa: valor < -0,100 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | -0,229 | confirmado |
| 2026-10 | b83ec7525506 | -0,230 | confirmado |

## recuperacion_mes6

Al mes 6 la brecha se cerró: la diferencia de medianas entre cercanos y controles es chica.

Expectativa: valor abs< 0,050 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | -0,021 | confirmado |
| 2026-10 | b83ec7525506 | -0,021 | confirmado |

## salto_agua

Los padres cercanos tienen saltos de corte de agua (más de 0,15) con más frecuencia que los controles (diferencia de proporciones).

Expectativa: valor > 0,100 (proporción).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | 0,188 | confirmado |
| 2026-10 | b83ec7525506 | 0,187 | confirmado |

## parado_declarado

Los padres cercanos figuran como Parado Transitoriamente en el mes de la fractura con más frecuencia que los controles (diferencia de proporciones).

Expectativa: valor > 0,030 (proporción).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | 0,070 | confirmado |
| 2026-10 | b83ec7525506 | 0,070 | confirmado |

## asimetria_de_superficie

Entre eventos cercanos a 0,3 a 1 km, el sector de rumbos de superficie de 56,25 a 101,25 grados pierde más producción al mes 1 que el sector de 0 +/- 22,5 grados (diferencia de medianas del índice). Es una descripción de la muestra: el sector contiene a la vez el eje estimado (93 grados) y el SHmax publicado (67,5), así que no distingue entre ellos, y con datos públicos esa dirección no se separa de cómo se disponen los pads, y la geometría de las ramas se probó con otra prueba (costado contra punta, mecanismo.md; regla de parada, eje_parada.md). Antes se llamaba `anisotropia` y figuraba como confirmado.

Expectativa: valor < -0,100 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | -0,260 | confirmado |
| 2026-09 | 1f07aee9b988 | -0,260 | no firme |
| 2026-09 | 1f07aee9b988 | -0,260 | no firme |
| 2026-10 | b83ec7525506 | -0,248 | no firme |

## sincronia_mes0

La brecha del mes de la fractura crece con la fracción del mes posterior al inicio de la fractura del hijo: el límite superior del IC de la pendiente (índice por unidad de fracción) queda por debajo de -0,02 (regla fijada antes de correr, pipeline/sincronia.py).

Expectativa: valor < -0,020 (índice por unidad de fracción).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | -0,097 | confirmado |
| 2026-10 | b83ec7525506 | -0,077 | confirmado |

## brecha_mes1_bloques

El IC 95% por bloques espaciales de 5 km de la brecha del mes 1 (base de los meses -3 a -1) tiene el límite superior por debajo de -0,10: no cruza -10 puntos (regla fijada antes de correr, pipeline/bloques.py).

Expectativa: valor < -0,100 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | -0,168 | confirmado |
| 2026-10 | b83ec7525506 | -0,170 | confirmado |

## sincronia_mes0_bloques

La pendiente de la brecha del mes 0 por fracción del mes tiene, con el IC por bloques espaciales de 5 km, el límite superior por debajo de -0,02 (regla fijada antes de correr, pipeline/bloques.py).

Expectativa: valor < -0,020 (índice por unidad de fracción).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | -0,080 | confirmado |
| 2026-10 | b83ec7525506 | -0,083 | confirmado |

## hijo_depletado

Un hijo cerca de pozos depletados rinde menos petróleo por metro de rama a 12 meses que un hijo en zona virgen y el control negativo, con pozos posteriores, es nulo: el valor es el límite superior del IC del grupo muy depletado, si el control negativo es nulo (sin valor si no lo es), y queda por debajo de cero, en bbl por metro (regla fijada antes de correr, pipeline/hijo.py). El estado sale del veredicto de esa regla: confirmado si sostiene, refutado si no se sostiene, y no firme en cualquier otro caso (ubicación, no firme o sin muestra).

Expectativa: valor < 0,000 (bbl por metro).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | 12,388 | refutado |
| 2026-09 | 1f07aee9b988 | s/d | no firme |
| 2026-10 | b83ec7525506 | s/d | no firme |

## inyeccion_r1

Un efecto plantado de 20% de caída de caudal en el mes 1 se recupera con la brecha del mes 1 a menos de 5 puntos de -20 (media entre mundos simulados, índice con base de los meses -3 a -1; regla fijada antes de correr, pipeline/inyeccion.py).

Expectativa: valor abs< 5,000 (puntos).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | 0,367 | confirmado |
| 2026-10 | b83ec7525506 | 0,505 | confirmado |

## inyeccion_r2

El reparto entre días y caudal por día se identifica: con un cierre plantado la parte de los días es de al menos 80% y con una caída de caudal plantada la parte del caudal por día es de al menos 80% (el menor de los dos valores; regla fijada antes de correr, pipeline/inyeccion.py).

Expectativa: valor > 0,800 (proporción).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | 1,035 | confirmado |
| 2026-10 | b83ec7525506 | 1,033 | confirmado |

## inyeccion_r3

Una caída plantada de 40% desde el día de inicio de la fractura se recupera con pendiente negativa y IC que excluye cero en al menos 80% de los mundos simulados (regla fijada antes de correr, pipeline/inyeccion.py).

Expectativa: valor > 0,800 (proporción de mundos).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | 0,933 | confirmado |
| 2026-10 | b83ec7525506 | 1,000 | confirmado |

## inyeccion_r4a

Sin efecto plantado, el IC de la brecha del mes 1 excluye cero en como máximo 10% de los mundos simulados (regla fijada antes de correr, pipeline/inyeccion.py).

Expectativa: valor < 0,100 (proporción de mundos).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | 0,100 | debilitado |
| 2026-10 | b83ec7525506 | 0,067 | confirmado |

## inyeccion_r4b

Una brecha previa de nivel de 5% se lee como previa a la fractura: la pretendencia y la brecha neta del mes 1 quedan a menos de 2 puntos de lo plantado (-5 y 0), restando el mundo nulo de los mismos sorteos (regla fijada antes de correr, pipeline/inyeccion.py).

Expectativa: valor < 2,000 (puntos).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | 0,504 | confirmado |
| 2026-10 | b83ec7525506 | 0,484 | confirmado |

## replicacion_colorado

Réplica en la cuenca DJ de Colorado: se sostiene si el IC 95% por bloques espaciales de 5 km de la brecha del mes 1 queda por debajo de cero y la brecha previa a la fractura con base limpia es menor, en valor absoluto, que la del mes 1; si no, no se replica. El valor es el mayor entre el límite superior de ese IC y la diferencia de valores absolutos (previa menos mes 1), y se sostiene si es menor que cero (regla fijada antes de correr, pipeline/replicacion.py).

Expectativa: valor < 0,000 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | s/d | preregistrada |
| 2026-09 | 1f07aee9b988 | -0,130 | confirmado |
| 2026-10 | b83ec7525506 | s/d | preregistrada |

## anio_2026_carga

La brecha del mes 1 de 2026 es mayor que la de 2021 a 2024 cuando todos los años se miran con la misma antigüedad de carga de fracturas (hijos cargados con hasta 3 meses de rezago). El valor es el límite superior del IC 95% por bloques de 5 km de la diferencia D (2026 menos 2021 a 2024) y se sostiene si es menor que cero y la diferencia con solo los hijos de YPF también es negativa (regla fijada antes de correr, pipeline/carga_anual.py).

Expectativa: valor < 0,000 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | 0,127 | no firme |
| 2026-10 | b83ec7525506 | 0,109 | no firme |

## replicacion_wyoming

Réplica en Wyoming (WOGCC): se sostiene si el IC 95% por bloques espaciales de 5 km de la brecha del mes 1 queda por debajo de cero y la brecha previa a la terminación con base limpia es menor, en valor absoluto, que la del mes 1; si no, no se replica. El valor es el mayor entre el límite superior de ese IC y la diferencia de valores absolutos (previa menos mes 1), y se sostiene si es menor que cero (misma regla que la de Colorado, fijada antes de bajar la producción de Wyoming, pipeline/wyoming/__init__.py).

Expectativa: valor < 0,000 (índice).

| Datos a | Hash de datos | Valor | Estado |
|---|---|---|---|
| 2026-09 | 1f07aee9b988 | 0,095 | refutado |
| 2026-10 | b83ec7525506 | s/d | preregistrada |

Ver también [Interferencia entre fracturas](interferencia.md).
