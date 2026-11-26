# Sincronía dentro del mes

Página generada por `pipeline/sincronia.py`. Pregunta si la brecha del mes de la fractura crece con la fracción del mes posterior al inicio de la fractura del hijo. Complementa [Interferencia entre fracturas](interferencia.md) y la [descomposición de la brecha](descomposicion.md); la regla se fijó antes de correr y está en el libro de hallazgos como `sincronia_mes0`.

## Resumen

Veredicto contra la regla fijada: **sostiene**. La caída sigue a la fecha de fractura dentro del mes: la pendiente es negativa, su IC excluye cero y pasa el umbral.

- Pendiente de la brecha del mes 0: -2,1 puntos de índice por cada 0,1 de fracción del mes (IC 95%: -3,3 a -0,8), sobre 2.044 eventos cercanos y 17.792 controles de 745 pads hijo. Entre un inicio el último día y uno el primer día del mes la brecha cambia -20,8 puntos.
- Pendiente del mes -1, sin días expuestos: -0,7 puntos por cada 0,1 (IC 95%: -1,9 a 0,6), sobre 2.040 eventos cercanos.
- Se publican los tres grupos y las dos pendientes calculados; no se eligió el mejor.

## Regla fijada antes de correr

La fracción es f0 = (días del mes - día de inicio + 1) / días del mes, con la primera fecha de inicio de fractura del hijo y los días reales del mes (28, 29, 30 o 31). Los eventos, la base de los meses -6 a -4, los cercanos (menos de 1 km) y los controles (2 a 5 km) son los de la página de falsación; el índice se acota a 0 a 2. La pendiente sale de una regresión del índice sobre cercano, f0 y su producto, con efectos fijos de área y de año de fractura; el IC 95% es bootstrap de percentiles por pads hijo (400 repeticiones, semilla de la pretendencia para el mismo k). La brecha es negativa si el cercano rinde menos, así que una dosis en el tiempo es una pendiente negativa.

- Con dosis: el límite superior del IC de la pendiente del mes 0 es menor que -0,02 (al menos 2 puntos de cambio entre f0 = 0 y 1, sin incluir cero).
- Plana: el IC incluye cero. Opuesta: el límite inferior del IC es mayor que cero. No firme: el límite superior está entre -0,02 y 0, o la pendiente del mes -1 también es negativa con IC que excluye cero.
- Mínimo de 30 eventos cercanos y 30 controles por grupo.

## Brecha del mes 0 por grupo de f0

Los cortes son los terciles de f0 de los eventos cercanos y control juntos, los mismos para los dos grupos (el grupo 1 es de f0 hasta el primer corte, el 3 es de f0 mayor que el segundo). La brecha es cercano menos control, en medianas del índice y en puntos.

| Grupo | f0 desde | f0 hasta | Eventos cercanos | Eventos control | Brecha del mes 0 (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 0,032 | 0,387 | 673 | 6.041 | -14,5 | -19,4 a -8,4 |
| 2 | 0,393 | 0,710 | 753 | 6.131 | -22,1 | -28,9 a -15,5 |
| 3 | 0,714 | 1,000 | 618 | 5.620 | -32,4 | -39,0 a -23,7 |

## Pendiente

| Mes | Eventos cercanos | Eventos control | Pads hijo | Pendiente (puntos por 0,1 de f0) | IC 95% (puntos por 0,1) |
| ---: | ---: | ---: | ---: | ---: | --- |
| -1 | 2.040 | 17.744 | 745 | -0,7 | -1,9 a 0,6 |
| 0 | 2.044 | 17.792 | 745 | -2,1 | -3,3 a -0,8 |

El mes -1 es el control de calendario: ahí la fractura del hijo todavía no empezó, así que una pendiente negativa en ese mes no puede ser una dosis posterior al inicio.
La pendiente del mes -1 tiene el mismo signo que la del mes 0 pero su IC incluye cero: no se puede descartar que una parte de la pendiente del mes 0 sea calendario o anticipación, y el IC no alcanza para medir cuánta.

## Límites

- El índice es mensual: el mes 0 mezcla días antes y después del inicio, de modo que la dosis está atenuada. La prueba mira el signo y el orden de los grupos, no la magnitud por día.
- Hay brecha previa al inicio (la página de falsación la mide en el mes -1); si depende de la fecha de inicio, la pendiente del mes 0 no se separa de ella.
- Los controles tienen su propio hijo a 2 a 5 km con su propia fecha de inicio; la comparación dentro de cada grupo supone que el calendario afecta igual a los dos.
- El IC es bootstrap por pads hijo sin ajuste por comparaciones múltiples. Es una huella medida de sincronía entre las fechas de fractura y el caudal mensual, no una prueba de causa.
