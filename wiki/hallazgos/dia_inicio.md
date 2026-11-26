# El día de inicio como dosis

Página generada por `pipeline/dia_inicio.py`. Pregunta si la caída de los padres a menos de 1 km en el mes de la fractura del hijo crece con la parte del mes del padre que la fractura expone: un inicio el día 3 expone casi todo el mes 0, uno el día 27 casi nada, y nadie elige el día mirando la cifra mensual del padre. Se compara cada padre cercano solo con padres cercanos; ningún pozo lejano entra en la pendiente. La regla completa, con sus razones, es [plan-dia-inicio](../../docs/plan-dia-inicio.md) y se fijó en el commit `d370e0b`, antes de calcular ninguna cifra de este estudio. Complementa [Sincronía dentro del mes](sincronia.md), que mide la misma fracción contra controles lejanos.

## Resumen

Veredicto contra la regla fijada (posición 5 de 7 en el orden de la regla): **no sobrevive a su placebo**. Motivos: pozos de control; fecha falsa -6; días sorteados (sesgo).

La misma pendiente aparece donde no hay exposición (controles, fechas falsas, días sorteados): la huella no se separa del calendario o de la selección y no se lee como dosis.

- Pendiente de f0 entre padres cercanos: -2,7 puntos de índice por cada 0,1 de f0 (IC 95% por bloques de 5 km: -4,3 a -1,6), sobre 2.044 eventos cercanos de 377 pads hijo en 91 bloques de 5 km. Entre un inicio el último día del mes y uno el primer día el índice cambia -27,4 puntos.
- Eventos de control (2 a 5 km): 17.792, con pendiente -0,4 puntos por cada 0,1 de f0.
- p bilateral de los días sorteados: 0,005.

Lectura conjunta con Colorado: Vaca Muerta no sobrevive a su placebo, Colorado se repite.

## Regla fijada antes de correr

- Exposición f0 = (días del mes - día de inicio + 1) / días del mes, con la primera fecha de inicio de fractura del hijo en su mes 0 y los días reales del mes. La sensibilidad fd cuenta solo los días hasta el fin de la fractura; no entra en el veredicto.
- Muestra: padres a menos de 1 km del hijo más cercano, con los filtros del titular (base limpia de los meses -6 a -4, edad del padre de al menos 6 meses, caudal base mayor que 1 m3/d). Resultado: índice de petróleo del mes 0, acotado a 0 a 2.
- Umbral de dosis: límite superior del IC de la pendiente menor que -0,05 por unidad de f0 (-5 puntos entre el primer y el último día). Un chequeo negativo rompe si su IC excluye cero y su pendiente es al menos 0,025 por unidad (el de días sorteados, si su media es al menos 0,0125).
- Orden del veredicto: sin muestra, opuesta o plana, no equilibrado, no sobrevive a su placebo, no firme, con dosis.

## Pendientes y chequeos negativos

La pendiente se lee por cada 0,1 de f0 (un décimo del mes del padre) en puntos de índice. Una dosis en el tiempo es negativa: más caída cuanto más del mes expone la fractura. Cada fila es la misma regresión con los efectos fijos de área y de año de fractura; el IC es bootstrap de percentiles por bloques de 5 km.

| Estimación | Eventos o sorteos | Pendiente (puntos por 0,1 de f0) | IC 95% (puntos por 0,1) |
| --- | ---: | ---: | --- |
| Cercanos, principal | 2.044 | -2,7 | -4,3 a -1,6 |
| Cercanos, ajustada por operador, edad y caudal base | 2.044 | -2,5 | -4,0 a -1,3 |
| Controles (2 a 5 km) | 17.792 | -0,4 | -0,7 a -0,1 |
| Cercanos, con fd en lugar de f0 | 2.037 | -3,1 | -4,7 a -1,7 |
| Cercanos sin el operador grande 1 | 1.837 | -2,6 | -4,0 a -1,4 |
| Cercanos sin el operador grande 2 | 775 | -2,4 | -5,6 a 0,0 |
| Fecha falsa, 12 meses antes | 1.320 | -0,1 | -1,5 a 1,4 |
| Fecha falsa, 6 meses antes | 1.606 | 1,1 | 0,2 a 2,1 |
| Días sorteados (media y rango 2,5 a 97,5 de los sorteos) | 200 | -0,5 | -1,7 a 0,6 |

Los operadores grandes (10% o más de los eventos cercanos) son, en orden alfabético y como los numera la tabla: 1 Vista, 2 YPF.

- p bilateral de los días sorteados: 0,005.

## Equilibrio del día de inicio

| Chequeo | Eventos | Valor | IC 95% por bloques de 5 km |
| --- | ---: | ---: | --- |
| Eta cuadrado de f0 contra el operador del hijo | 2.044 | 0,022 | 0,010 a 0,080 |
| Spearman de f0 con la edad del padre | 2.044 | 0,023 | -0,052 a 0,112 |
| Spearman de f0 con el caudal base del padre | 2.044 | 0,039 | -0,034 a 0,117 |

Equilibrado si el eta cuadrado es menor que 0,10 y los dos Spearman tienen valor absoluto menor que 0,10.

## Día de inicio por operador del hijo

| Operador del hijo | Eventos cercanos | f0 media | Parte con inicio en los tres primeros días |
| --- | ---: | ---: | ---: |
| YPF | 1.269 | 0,528 | 13,0 % |
| Vista | 207 | 0,581 | 11,1 % |
| Tecpetrol | 156 | 0,520 | 16,7 % |
| Pluspetrol | 123 | 0,527 | 12,2 % |
| Pan American Energy | 121 | 0,465 | 3,3 % |
| Shell | 70 | 0,614 | 22,9 % |
| Chevron | 57 | 0,639 | 15,8 % |

## Tercios del día de inicio

Grupo 1: inicio tarde en el mes (poca exposición); grupo 3: inicio temprano (mucha). Índice mediano del mes 0 en puntos (la base vale 100).

| Grupo | f0 desde | f0 hasta | Eventos cercanos | Índice mediano |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0,032 | 0,400 | 714 | 68,6 |
| 2 | 0,419 | 0,679 | 652 | 57,6 |
| 3 | 0,690 | 1,000 | 678 | 48,6 |

- Grupo 3 menos grupo 1: -20,0 puntos de índice (IC 95% por bloques de 5 km: -29,7 a -9,2), sobre 2.044 eventos cercanos.

## Intercepto a exposición cero

Brecha entre cercanos y controles que la regresión predice con f0 = 0, comparada con la brecha que el estudio mide el mes anterior a la fractura. No tiene veredicto propio.

- Brecha a exposición cero, cercanos menos controles: -8,0 puntos de índice (IC 95% por bloques de 5 km: -15,8 a 2,3), sobre 2.044 eventos cercanos.
- Brecha previa de referencia, mes -1: -5,0 puntos de índice (IC 95% por bloques de 5 km: -9,1 a -0,7), sobre 2.040 eventos cercanos.

Lectura fijada por la regla: la brecha a exposición cero **coincide con la previa**.

## Qué dice el estudio con este veredicto

La misma pendiente aparece donde no hay exposición (controles, fechas falsas, días sorteados): la huella no se separa del calendario o de la selección y no se lee como dosis.

Si el veredicto no es «con dosis», el README y el sitio no ganan ninguna frase nueva: la fila «Sincronía dentro del mes» se vuelve a leer con esta página al lado.

## Colorado

Veredicto de Colorado (posición 1 de 4): **se repite**. El límite superior del IC de la pendiente de los cercanos es menor que 0 y los pozos de control no rompen.

Mismo diseño, mismas constantes y mismas semillas sobre el warehouse opcional de Colorado; la fecha de cada hijo es la de inicio de trabajo de su primera divulgación de FracFocus. Efectos fijos: condado y año de fractura. No tiene fd.

### Pendientes y chequeos negativos

La pendiente se lee por cada 0,1 de f0 (un décimo del mes del padre) en puntos de índice. Una dosis en el tiempo es negativa: más caída cuanto más del mes expone la fractura. Cada fila es la misma regresión con los efectos fijos de área y de año de fractura; el IC es bootstrap de percentiles por bloques de 5 km.

| Estimación | Eventos o sorteos | Pendiente (puntos por 0,1 de f0) | IC 95% (puntos por 0,1) |
| --- | ---: | ---: | --- |
| Colorado: Cercanos, principal | 3.526 | -1,7 | -2,5 a -0,8 |
| Colorado: Cercanos, ajustada por operador, edad y caudal base | 3.526 | -1,7 | -2,4 a -0,9 |
| Colorado: Controles (2 a 5 km) | 50.637 | -0,2 | -0,5 a 0,0 |
| Colorado: Cercanos sin el operador grande 1 | 3.155 | -1,7 | -2,7 a -0,7 |
| Colorado: Cercanos sin el operador grande 2 | 3.012 | -1,9 | -2,7 a -0,9 |
| Colorado: Cercanos sin el operador grande 3 | 3.076 | -1,8 | -2,7 a -1,0 |
| Colorado: Cercanos sin el operador grande 4 | 2.437 | -1,9 | -3,0 a -0,8 |
| Colorado: Fecha falsa, 12 meses antes | 2.592 | -0,2 | -0,8 a 0,3 |
| Colorado: Fecha falsa, 6 meses antes | 3.167 | 0,1 | -0,5 a 0,8 |
| Colorado: Días sorteados (media y rango 2,5 a 97,5 de los sorteos) | 200 | 0,0 | -1,0 a 1,0 |

Los operadores grandes (10% o más de los eventos cercanos) son, en orden alfabético y como los numera la tabla: 1 EXTRACTION OIL & GAS INC, 2 KERR MCGEE OIL & GAS ONSHORE LP, 3 NOBLE ENERGY INC, 4 PDC ENERGY INC.

- Colorado: p bilateral de los días sorteados: 0,005.

### Equilibrio del día de inicio

| Chequeo | Eventos | Valor | IC 95% por bloques de 5 km |
| --- | ---: | ---: | --- |
| Colorado: Eta cuadrado de f0 contra el operador del hijo | 3.526 | 0,037 | 0,021 a 0,098 |
| Colorado: Spearman de f0 con la edad del padre | 3.526 | -0,026 | -0,120 a 0,056 |
| Colorado: Spearman de f0 con el caudal base del padre | 3.526 | 0,024 | -0,059 a 0,099 |

Equilibrado si el eta cuadrado es menor que 0,10 y los dos Spearman tienen valor absoluto menor que 0,10.

### Día de inicio por operador del hijo

| Operador del hijo | Eventos cercanos | f0 media | Parte con inicio en los tres primeros días |
| --- | ---: | ---: | ---: |
| Colorado: PDC ENERGY INC | 1.089 | 0,547 | 16,9 % |
| Colorado: KERR MCGEE OIL & GAS ONSHORE LP | 514 | 0,591 | 29,2 % |
| Colorado: NOBLE ENERGY INC | 450 | 0,544 | 13,1 % |
| Colorado: EXTRACTION OIL & GAS INC | 371 | 0,524 | 5,4 % |
| Colorado: CRESTONE PEAK RESOURCES OPERATING LLC | 291 | 0,509 | 16,8 % |
| Colorado: BONANZA CREEK ENERGY OPERATING COMPANY LLC | 158 | 0,432 | 13,3 % |
| Colorado: VERDAD RESOURCES LLC | 153 | 0,422 | 7,8 % |
| Colorado: PRAIRIE OPERATING CO LLC | 144 | 0,692 | 25,7 % |
| Colorado: HIGHPOINT OPERATING CORPORATION | 120 | 0,391 | 0,8 % |
| Colorado: PETRO OPERATING COMPANY LLC | 54 | 0,561 | 14,8 % |

### Tercios del día de inicio

Grupo 1: inicio tarde en el mes (poca exposición); grupo 3: inicio temprano (mucha). Índice mediano del mes 0 en puntos (la base vale 100).

| Grupo | f0 desde | f0 hasta | Eventos cercanos | Índice mediano |
| ---: | ---: | ---: | ---: | ---: |
| Colorado: 1 | 0,032 | 0,367 | 1.187 | 65,6 |
| Colorado: 2 | 0,387 | 0,742 | 1.214 | 59,7 |
| Colorado: 3 | 0,767 | 1,000 | 1.125 | 53,5 |

- Colorado: Grupo 3 menos grupo 1: -12,1 puntos de índice (IC 95% por bloques de 5 km: -19,7 a -5,0), sobre 3.526 eventos cercanos.

### Intercepto a exposición cero

Brecha entre cercanos y controles que la regresión predice con f0 = 0, comparada con la brecha que el estudio mide el mes anterior a la fractura. No tiene veredicto propio.

- Colorado: Brecha a exposición cero, cercanos menos controles: -15,8 puntos de índice (IC 95% por bloques de 5 km: -23,2 a -9,1), sobre 3.526 eventos cercanos.
- Colorado: Brecha previa de referencia, mes -1: -10,0 puntos de índice (IC 95% por bloques de 5 km: -14,1 a -6,5), sobre 3.530 eventos cercanos.

Lectura fijada por la regla: la brecha a exposición cero **coincide con la previa**.

## Lectura posterior a la regla (no entra en el veredicto)

Esta sección se escribió después de ver los resultados y está fuera de la regla fijada en el commit `d370e0b`. No cambia el veredicto ni ninguna constante; solo mira de dónde viene el sesgo de los días sorteados.

El sorteo de la regla permuta la f0 entre hijos del mismo mes de fractura y puede devolverle a un hijo su propia f0. Se repitió con dos sorteos que no lo permiten: una rotación dentro del mes (ningún hijo recibe la suya) y una rotación entre pads del mismo mes (ningún hijo recibe la f0 de un hijo de su pad), salvo en los meses con un solo hijo o un solo pad, que no rotan (una fracción mínima de los eventos cercanos).

- Parte de los eventos cercanos que en un sorteo de la regla conserva la f0 de su propio hijo, en promedio: 5,0 %.

| Estimación | Sorteos | Media (puntos por 0,1) | Rango 2,5 a 97,5 (puntos por 0,1) |
| --- | ---: | ---: | --- |
| Días sorteados (media y rango 2,5 a 97,5 de los sorteos) | 200 | -0,5 | -1,7 a 0,6 |
| Sorteo sin autoasignación (rotación dentro del mes) | 200 | -0,3 | -1,3 a 0,7 |
| Sorteo sin f0 de un hijo del mismo pad (rotación entre pads del mes) | 200 | -0,2 | -1,1 a 0,7 |

Con cualquiera de los dos sorteos la media sorteada sigue en valor absoluto por encima del límite de sesgo de la regla (0,125 puntos por 0,1): el sesgo no viene de que un hijo conserve su propio día ni de que reciba el de un hijo de su pad. No se investigó otra causa. El veredicto queda como lo fijó la regla.

## Límites

- Es una pendiente de un caudal mensual contra un día: el mes 0 mezcla días antes y después del inicio, así que la dosis está atenuada; la prueba lee signo y orden, no magnitud por día.
- No separa un cierre preventivo del operador de un daño del pozo: los dos empiezan con la fractura.
- «El día de inicio no se relaciona con la tendencia del padre» no se puede comprobar; el equilibrio y los placebos la hacen creíble y no la prueban.
- Los controles heredan la f0 de su hijo más cercano: la prueba de controles mide que esa f0 no mueve a un pozo lejano, no que no haya derrame a 2 km.
- El IC es bootstrap por bloques de 5 km sin ajuste por comparaciones múltiples. Es una huella medida, no una prueba de causa.
