# Inferencia: escala de los bloques, permutación de D2 y Holm

Regla fijada en el commit 857d434 (y f72c10c, que solo cambia el docstring). La primera aclaración se fijó en 88a9168, antes de calcular ninguna cifra; la segunda, que suma la fila D11c a la familia de Holm, en eb1c51b, después de la primera corrida y cuando ya se conocían las cifras de D11. La permutación dentro de las celdas (I4) y la fila de D3 en la familia de Holm se fijaron en 19415b3, antes de calcular ninguna cifra de I4, y después de ver las de I2; la fila de D3 se fijó después de ver el p de D3 con el volumen de agua del mes, cuando el valor y el IC de dA_pd ya eran cifras publicadas del veredicto de D3. La permutación por pad padre (I5) se fijó en 052ee98, antes de calcular ninguna cifra de I5. Ningún número de esta página está escrito a mano: salen de `mart_inferencia_escala`, `mart_inferencia_permutacion` y `mart_inferencia_holm`. Se corre con `uv run python -m pipeline.inferencia`.

## I1. ¿El intervalo depende del tamaño del bloque?

Se repite el bootstrap de D1 y D2 con bloques de 2, 5, 10 km (mismos 400 sorteos y misma semilla que el análisis principal; 5 km es el publicado).

**D1: depende de la escala: placebo de nunca tratados.**

| Cantidad | Bloque (km) | Bloques | Tratados | Valor | IC 95% | ¿Excluye cero? |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ATT(1) | 2 | 157 | 468 | -25,75 | -35,12 a -19,19 | sí |
| ATT(1) | 5 | 89 | 468 | -25,75 | -33,95 a -17,94 | sí |
| ATT(1) | 10 | 44 | 468 | -25,75 | -34,95 a -20,10 | sí |
| placebo de distancia falsa | 2 | 157 | 302 | 0,87 | -9,16 a 12,04 | no |
| placebo de distancia falsa | 5 | 89 | 302 | 0,87 | -9,28 a 10,94 | no |
| placebo de distancia falsa | 10 | 44 | 302 | 0,87 | -7,73 a 8,70 | no |
| placebo de fecha falsa | 2 | 157 | 218 | 3,90 | -4,06 a 10,61 | no |
| placebo de fecha falsa | 5 | 89 | 218 | 3,90 | -4,60 a 11,67 | no |
| placebo de fecha falsa | 10 | 44 | 218 | 3,90 | -4,08 a 12,35 | no |
| placebo de nunca tratados | 2 | 157 | 567 | -8,05 | -15,65 a -1,23 | sí |
| placebo de nunca tratados | 5 | 89 | 567 | -8,05 | -15,19 a -0,46 | sí |
| placebo de nunca tratados | 10 | 44 | 567 | -8,05 | -16,22 a 0,14 | no |

**D2: no depende de la escala.**

| Cantidad | Bloque (km) | Bloques | Tratados | Valor | IC 95% | ¿Excluye cero? |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ATT_W | 2 | 157 | 447 | 13,76 | 9,67 a 19,32 | sí |
| ATT_W | 5 | 89 | 447 | 13,76 | 9,51 a 19,89 | sí |
| ATT_W | 10 | 44 | 447 | 13,76 | 9,05 a 20,02 | sí |
| placebo de distancia falsa | 2 | 157 | 287 | -0,83 | -3,77 a 2,01 | no |
| placebo de distancia falsa | 5 | 89 | 287 | -0,83 | -4,02 a 2,32 | no |
| placebo de distancia falsa | 10 | 44 | 287 | -0,83 | -4,25 a 2,38 | no |
| placebo de fecha falsa | 2 | 157 | 214 | -0,40 | -1,82 a 1,25 | no |
| placebo de fecha falsa | 5 | 89 | 214 | -0,40 | -2,51 a 1,04 | no |
| placebo de fecha falsa | 10 | 44 | 214 | -0,40 | -2,55 a 1,16 | no |
| placebo previo | 2 | 157 | 451 | 1,13 | -1,17 a 4,12 | no |
| placebo previo | 5 | 89 | 451 | 1,13 | -1,35 a 4,70 | no |
| placebo previo | 10 | 44 | 451 | 1,13 | -1,17 a 4,46 | no |

## I2. Permutación de D2 (débil; la reemplaza I4)

Esta prueba se publica con su debilidad dicha. La prueba de permutación que citan los textos es I4, más abajo.

**Sobrevive a la permutación** (p = 0,0005, α = 0,05).

| Cantidad | Valor | Permutaciones | Semilla | p a dos colas | Observaciones | Estratos | Observaciones en estratos con las dos etiquetas | Tratados |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATT_W (pp) | 13,76 | 2000 | 20261235 | 0,0005 | 2362 | 416 | 8,0% | 447 |

Los percentiles 2,5 y 97,5 de ATT_W bajo la permutación son 11,75 y 13,09 pp.

Qué no prueba: la permutación reparte las etiquetas de tratado entre pozos del mismo bloque, año de la cohorte y grupo de edad. Prueba que el ATT_W observado no sale de repartir al azar la etiqueta dentro de esos estratos. No prueba las tendencias paralelas, ni que la elección de controles sea la correcta, ni que no haya otra causa que siga al golpe (la ubicación fina, la geología, el calendario de cada operador). Los estratos con una sola etiqueta no cambian en ninguna permutación y por eso se informa la parte de las observaciones que sí se mezcla.

Una consecuencia que se ve en los números: solo el 8,0% de las observaciones está en estratos con las dos etiquetas. El resto conserva su etiqueta en todas las permutaciones, así que la distribución de ATT_W bajo la permutación (11,75 a 13,09 pp) no se centra en cero. El p mide cuánto se aleja el valor observado (13,76 pp) de lo que queda al mezclar solo esa parte; con 2000 permutaciones el p no puede bajar de 0,0005 y es ese mínimo. Es una prueba débil y se lee así.

## I4. Permutación dentro de las celdas de D2

**Sobrevive a la permutación** (p = 0,0005, α = 0,05).

Cada estrato es la celda de D2 (cohorte y mes de cada tratado con sus controles). Toda celda que D2 usa tiene al menos un tratado y 5 controles, así que toda observación se mezcla. En cada permutación se reparten al azar las etiquetas de tratado dentro de cada celda, con la cantidad de tratados de esa celda, y ATT_W se recalcula con la regla de D2 (los pesos de las celdas no cambian).

| Cantidad | Valor | Permutaciones | Semilla | p a dos colas | Observaciones | Celdas | Observaciones que se mezclan | Tratados |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATT_W (pp) | 13,76 | 2000 | 20261236 | 0,0005 | 2362 | 113 | 100,0% | 447 |

Bajo la permutación, ATT_W tiene media 0,02 pp y percentiles 2,5 y 97,5 de -2,29 y 2,38 pp. Con 2000 permutaciones el p no puede bajar de 0,0005 y es ese mínimo.

I4 se agregó después de ver las cifras de I2 (solo el 8,0% de las observaciones se mezclaba y la nula no se centraba en cero) y antes de calcular ninguna cifra de I4.

Qué no prueba: la permutación supone que, dentro de una celda, tratados y controles son intercambiables si no hay efecto. Ese es el supuesto que D2 ya hace, así que I4 no prueba las tendencias paralelas, ni que la elección de controles sea la correcta, ni que no haya otra causa que siga al golpe. Solo dice que el ATT_W observado no sale de repartir al azar la etiqueta dentro de cada celda. Reparte los pozos de a uno, no por pad; I5, más abajo, lo hace por pad.

## I5. Permutación por pad padre dentro de las celdas de D2

**Sobrevive a la permutación** (p = 0,0005, α = 0,05).

I4 reparte los pozos de a uno, pero los pozos de un mismo pad comparten tratamiento (un pad hijo los fractura juntos) y comparten shocks, así que esa permutación puede exagerar la precisión. En I5 el cluster son los pozos de una celda que comparten `pad_id` en `int_pozo_pad` (un pozo sin pad es su propio cluster). Los clusters del mismo tamaño en la misma celda son intercambiables: en cada permutación se reparten entre ellos las cantidades de tratados y, dentro de cada cluster, se sortea cuáles pozos son los tratados. Cada celda conserva su cantidad de tratados y ATT_W se recalcula con la regla de D2.

| Cantidad | Valor | Permutaciones | Semilla | p a dos colas | Observaciones | Estratos (celda y tamaño) | Clusters | Observaciones en clusters de más de un pozo | Observaciones que se mezclan | Tratados |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ATT_W (pp) | 13,76 | 2000 | 20261237 | 0,0005 | 2362 | 398 | 928 | 88,4% | 38,5% | 447 |

Bajo la permutación por pad, ATT_W tiene media 6,39 pp y percentiles 2,5 y 97,5 de 3,22 y 9,49 pp. Con 2000 permutaciones el p no puede bajar de 0,0005 y es ese mínimo. La nula no está centrada en cero, a diferencia de la de I4: solo se mezcla una parte de las observaciones, así que muchas permutaciones dejan a los tratados en su lugar y conservan parte del efecto. Por eso, como I2, es una prueba débil y se lee así. El valor observado queda por encima del percentil 97,5 de esa nula.

I5 se agregó después de ver las cifras de I4 (p en su mínimo, nula centrada en cero) y la observación de la revisión, y antes de calcular ninguna cifra de I5 (regla en 052ee98). No entra en la familia de Holm, como I4.

Qué no prueba: los pads son clusters de bocas de pozo, no de laterales; un pad hijo puede alcanzar varios pads padres, que siguen correlacionados entre clusters; y la intercambiabilidad dentro de la celda es el supuesto que D2 ya hace, así que I5 no prueba las tendencias paralelas.

## I3. Holm sobre la familia confirmatoria

La familia tiene k = 20 diseños. Rechazan a α = 0,05 con Holm: 8 de 20. Un diseño sin muestra, sin fila o sin IC entra con p = 1: la familia no se achica. D7 y D9 se leen de la fila `dW` de su mart, que guarda sus resultados en la columna `resultado`. D11c se sumó después de la primera corrida, con las cifras de D11 ya conocidas: la regla de D11 le da veredicto propio, como a D4 y D12 sus dos filas (segunda aclaración de la regla, en `pipeline/inferencia.py`). E2 y D14 se sumaron después, cada uno con su regla fijada antes de calcular ninguna de sus cifras (`82d58c0` en `pipeline/stacked.py` y `5002094` en `pipeline/causal_exposicion.py`); sumarlos sube k y puede cambiar el p ajustado de los demás.

| Diseño | Fuente | Estado | Veredicto del diseño | Valor | IC 95% | p | p de Holm | ¿Rechaza? |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | --- |
| D1 | `mart_causal_veredicto:D1` | leido | no sobrevive a su placebo | -25,75 | -33,95 a -17,94 | < 0,0001 | < 0,0001 | sí |
| D13 | `mart_causal_profundo_d13:D13` | leido | general | 7,48 | 5,08 a 9,85 | < 0,0001 | < 0,0001 | sí |
| D7 | `mart_causal_profundo_d7:dW` | leido | sostiene: comunicación física causal bajo tendencias paralelas | 9,03 | 6,26 a 12,13 | < 0,0001 | < 0,0001 | sí |
| D5 | `mart_causal_profundo_veredicto:D5` | leido | persiste | 10,89 | 7,69 a 15,04 | < 0,0001 | < 0,0001 | sí |
| D2 | `mart_causal_veredicto:D2` | leido | sostiene: comunicación física causal bajo tendencias paralelas | 13,76 | 9,51 a 19,89 | < 0,0001 | < 0,0001 | sí |
| D10 | `mart_causal_exposicion_veredicto:D10` | leido | persiste | 10,49 | 6,81 a 15,41 | < 0,0001 | < 0,0001 | sí |
| D3 | `mart_causal_profundo_d3:dA_pd` | leido | entra agua en los días producidos | 19,51 | 12,84 a 29,20 | < 0,0001 | < 0,0001 | sí |
| R1 | `mart_golpes_repetidos_veredicto:R1` | leido | se repite en cada golpe | 9,61 | 3,65 a 15,01 | 0,0009 | 0,0118 | sí |
| D6 | `mart_causal_profundo_veredicto:D6` | leido | depende de un operador | 7,08 | -0,60 a 18,11 | 0,1383 | 1,0000 | no |
| D4_tamano | `mart_causal_profundo_veredicto:D4_tamano` | leido | sin gradiente | -8,60 | -18,89 a 9,37 | 0,2327 | 1,0000 | no |
| D4_distancia | `mart_causal_profundo_veredicto:D4_distancia` | leido | sin gradiente | 3,17 | -3,66 a 10,78 | 0,3892 | 1,0000 | no |
| D1b | `mart_causal_veredicto:D1b` | sin muestra | sin muestra | -6,06 | -36,10 a 17,25 | 1,0000 | 1,0000 | no |
| D9 | `mart_causal_profundo_d9:dW` | sin muestra | sin muestra | 6,73 | -0,68 a 13,40 | 1,0000 | 1,0000 | no |
| E | `mart_apilado:E` | sin muestra | sin muestra | -14,96 | -26,72 a -4,64 | 1,0000 | 1,0000 | no |
| E2 | `mart_apilado_e2:E2` | sin muestra | sin muestra | -21,93 | -30,58 a -13,45 | 1,0000 | 1,0000 | no |
| D11a | `mart_causal_exposicion_veredicto:D11a` | sin muestra | sin muestra | 13,70 | 3,45 a 25,85 | 1,0000 | 1,0000 | no |
| D11c | `mart_causal_exposicion_veredicto:D11c` | sin muestra | sin muestra | 0,60 | -4,99 a 8,07 | 1,0000 | 1,0000 | no |
| D12a | `mart_causal_exposicion_veredicto:D12a` | sin muestra | sin muestra | 14,22 | 0,61 a 21,47 | 1,0000 | 1,0000 | no |
| D12b | `mart_causal_exposicion_veredicto:D12b` | sin muestra | sin muestra | 10,96 | -0,98 a 22,89 | 1,0000 | 1,0000 | no |
| D14 | `mart_causal_d14:D14` | sin muestra | sin muestra | 13,31 | 6,20 a 23,02 | 1,0000 | 1,0000 | no |

Entraron con p = 1 por no tener su mart o su fila en este warehouse (el paso que los escribe no corrió antes que este) o por no tener muestra: D1b, D9, E, E2, D11a, D11c, D12a, D12b, D14. El p de la permutación de D2 (I4: 0,0005; I5: 0,0005; I2: 0,0005) no reemplaza al de la familia.

Rechazar acá solo dice que el valor se separa de cero después del ajuste por la familia; no cambia el veredicto de cada diseño, que sale de su propia regla. Rechaza y su veredicto no cambia: D1 («no sobrevive a su placebo»). D3 entra con el agua por día producido (`dA_pd` de `mart_causal_profundo_d3`), el estadístico con el que decide su veredicto ([causal_profundo.md](causal_profundo.md)); su estado y su veredicto salen de `mart_causal_profundo_veredicto`. Este cambio se fijó en 19415b3, después de ver el p de Holm de D3 con el volumen de agua del mes.

### Publicado sin veredicto: los intervalos de la descomposición

Son 141 intervalos (una prueba por fila de `mart_descomposicion_k`, `mart_descomposicion_aditiva` y `mart_descomposicion_distancia`; en la aditiva, el de la brecha del volumen). Sin ajuste, 90 excluyen cero. Con Holm dentro de esa familia, con la misma aproximación normal, siguen rechazando 36.

La aproximación normal usa el IC 95% publicado y no un p exacto: sirve para el orden de magnitud del ajuste, no para un valor p al cuarto decimal.
