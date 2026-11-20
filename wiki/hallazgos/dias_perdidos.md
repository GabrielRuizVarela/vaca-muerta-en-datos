# Días que pierde un padre cuando fracturan a un hijo

Alrededor de la fractura de un hijo, un pozo padre pasa días sin producir: lo cierran para protegerlo o queda fuera de servicio por el golpe. Esta página cuenta esos días (meses -1 a 2 contra la base de los meses -6 a -4), los abre por operador del padre y prueba dos cosas: si la diferencia entre operadores se mantiene en el tiempo y si más días parados se asocian con mejor caudal después. La regla se fijó antes de calcular; más abajo dice qué se había mirado antes. En Colorado la misma regla se corrió después, como prueba confirmatoria (sección al final).

## Lectura

- Un padre a menos de 1 km pierde 14,4 días más que un control (IC 95% 11,6 a 16,8; 2.036 eventos cercanos). Es una medida descriptiva: se había mirado antes de fijar la regla.
- Prueba B (regla informada): Los días que pierde un padre dependen de su operador, y la diferencia se mantuvo en el tiempo. Diferencia entre el grupo alto y el bajo en la segunda mitad: 15,2 días (IC 95% 10,2 a 25,1; 4 operadores; veredicto: sostiene). La regla es informada (se fijó conociendo la dispersión entre operadores de toda la muestra), y en Colorado, donde la prueba es confirmatoria, no se confirmó (veredicto: no firme).
- Prueba C (regla informada): Dentro de un mismo operador no se ve relación entre los días parados y el caudal posterior. Pendiente: -1,4 puntos logarítmicos por cada 10 días (IC 95% -3,6 a 0,3; 1.939 eventos; veredicto: no se ve relación). El mayor beneficio compatible con el dato es 0,3 puntos por cada 10 días. No prueba que cerrar no proteja: un golpe más fuerte da a la vez más días parados y peor caudal después, y eso sesga la pendiente hacia abajo.
- Los días de más equivalen a 636 m3 de petróleo por evento cercano (IC 95% 459 a 812), valuados al caudal que el pozo traía. Es volumen diferido: el dato no dice que ese petróleo se pierda.
- Colorado, prueba confirmatoria con la misma regla: brecha de días, sostiene (19,8 días, IC 95% 15,0 a 24,3); prueba B, no firme; prueba C, no se ve relación. El detalle está en la sección de Colorado, al final.

## Cuántos días, por distancia al hijo

| Banda | Eventos | Sin ventana completa | Exceso medio (días) | Exceso mediano (días) | Brecha contra el control (días) | IC 95% | Volumen de la brecha (m3 por evento) | IC 95% |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| Cercano (menos de 1 km) | 2.036 | 12 | 17,2 | 10,8 | 14,4 | 11,6 a 16,8 | 636 | 459 a 812 |
| 1 a 2 km | 3.507 | 15 | 6,8 | 1,3 | 3,9 | 2,3 a 5,6 | 152 | 52 a 229 |
| Control (2 a 5 km) | 17.684 | 111 | 2,8 | 0,3 |  |  |  |  |

## Por operador del padre

Operadores con al menos 50 eventos cercanos. La brecha de cada uno es contra sus propios controles, para quitar lo que cada operador informa distinto siempre. Es descriptiva: las medias por operador, sin intervalos, se habían mirado antes de fijar la regla.

| Operador | Cercanos | Controles | Brecha (días) | IC 95% | Volumen de la brecha (m3 por evento) | IC 95% | Caudal de base (m3/d) |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| Tecpetrol | 150 | 996 | 24,5 | 14,7 a 35,9 | 358 | 216 a 564 | 15,1 |
| Chevron | 57 | 86 | 22,2 | 12,4 a 33,6 | 987 | 464 a 1.302 | 69,4 |
| Shell | 58 | 776 | 18,1 | 6,1 a 32,4 | 773 | 221 a 1.437 | 51,9 |
| YPF | 1.306 | 13.350 | 16,3 | 13,2 a 19,4 | 743 | 567 a 940 | 47,4 |
| Pluspetrol | 119 | 591 | 8,4 | -3,6 a 19,2 | 1.144 | 405 a 2.004 | 90,7 |
| Pan American Energy | 121 | 402 | 5,5 | 2,7 a 10,7 | 253 | 154 a 421 | 75,9 |
| Vista | 180 | 1.214 | 1,9 | -13,3 a 12,7 | -152 | -1.195 a 541 | 85,1 |

## Prueba B: si la diferencia entre operadores se mantiene en el tiempo

Corte: 2023-06, la mediana del mes de los eventos cercanos. Los operadores se ordenan por su brecha de la primera mitad (grupo bajo y grupo alto) y se mira si el grupo alto sigue por encima en la segunda. Entran los que tienen al menos 30 cercanos y 30 controles en cada mitad.

| Operador | Grupo | Cercanos, 1.ª mitad | Controles, 1.ª mitad | Brecha, 1.ª mitad (días) | Cercanos, 2.ª mitad | Controles, 2.ª mitad | Brecha, 2.ª mitad (días) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Chevron | no entra | 5 | 7 | 23,7 | 52 | 79 | 21,9 |
| Pan American Energy | bajo | 30 | 133 | 13,9 | 91 | 269 | 2,4 |
| Pluspetrol | no entra | 13 | 132 | 10,2 | 106 | 459 | 8,7 |
| Shell | no entra | 23 | 305 | 19,4 | 35 | 471 | 17,2 |
| Tecpetrol | alto | 92 | 602 | 24,4 | 58 | 394 | 24,9 |
| Vista | bajo | 40 | 254 | -14,4 | 140 | 960 | 6,5 |
| YPF | alto | 810 | 7.630 | 17,4 | 496 | 5.720 | 14,4 |

Veredicto: sostiene. Correlación de Spearman entre las dos mitades: 0,80 (descriptiva). Repeticiones descartadas porque a un operador le faltó un lado: 0 de 400.

## Prueba C: si más días parados van con mejor caudal después

Mínimos cuadrados del logaritmo del caudal por día efectivo de los meses 4 a 6 sobre el de la base, contra el exceso de días dividido por 10, solo en los cercanos, con efectos fijos de operador, de grupo de edad del padre y de año, más la distancia al hijo y el logaritmo del caudal de base. Error de la pendiente: 1,0 puntos; efecto mínimo detectable: 2,8 puntos por cada 10 días. Esta prueba no cambia ninguna recomendación. Lo que la resolvería es un ensayo con el tamaño de abajo, o los registros de cierre y la presión del padre de un operador.

## Cuánto vale

El volumen de la brecha por evento, por los 340 eventos cercanos de los últimos 12 meses con ventana completa, da 216.174 m3 por año (1.359.692 barriles). En promedio, cada día de la brecha son 44,2 m3 por evento. La tabla da el costo de diferir ese volumen (el valor tiempo de cobrarlo más tarde), en millones de dólares por año, según cuánto tarde en recuperarse. Precio y tasa son entradas de quien lo usa, no resultados.

| Precio (USD/bbl) | Tasa anual | Se recupera en 6 meses | Se recupera en 12 meses | Se recupera en 24 meses |
| ---: | ---: | ---: | ---: | ---: |
| 40 | 10% | 2,5 | 4,9 | 9,4 |
| 40 | 15% | 3,7 | 7,1 | 13,3 |
| 60 | 10% | 3,8 | 7,4 | 14,2 |
| 60 | 15% | 5,5 | 10,6 | 19,9 |
| 80 | 10% | 5,1 | 9,9 | 18,9 |
| 80 | 15% | 7,3 | 14,2 | 26,5 |

## Tamaño de un ensayo

Para ver una diferencia de caudal posterior de 5, 10 y 20 puntos logarítmicos entre dos formas de cerrar (80% de potencia, 5% a dos colas, desvío de los residuos 0,78) hacen falta 3.812, 953 y 239 eventos por rama, en ese orden. Es un piso: no cuenta la correlación dentro del pad.

## Estado declarado de los meses cerrados

El 16,9% de los eventos cercanos tiene al menos un mes de la ventana con cero días efectivos, contra el 7,6% de los controles. El estado que declara el operador en esos meses (estados con al menos 1% de los meses):

| Banda | Estado declarado | Meses | Parte |
| --- | --- | ---: | ---: |
| Cercano (menos de 1 km) | Parado Transitoriamente | 445 | 86,1% |
| Cercano (menos de 1 km) | Extracción Efectiva | 59 | 11,4% |
| Control (2 a 5 km) | Parado Transitoriamente | 2.016 | 86,7% |
| Control (2 a 5 km) | Extracción Efectiva | 236 | 10,2% |
| Control (2 a 5 km) | En Estudio | 24 | 1,0% |

## Colorado: la prueba confirmatoria

En Colorado (cuenca DJ) no se había mirado nada de este módulo antes de fijar la regla, así que ahí la brecha de días (A), la prueba B y la prueba C son confirmatorias. Se corrió con la misma regla, sin cambiarla, sobre el corte principal de la [replicación en Colorado](replicacion.md): padres horizontales, hijos con la fecha de fractura de FracFocus y producción de 2018-01 a 2024-12. Lo que el dato de Colorado obligó a decidir se escribió antes de correr, en un commit propio, al pie del encabezado de `pipeline/dias_perdidos.py`: el operador es el del último mes informado a ECMC, con el nombre que usa ECMC (un pozo que cambió de manos cuenta con su operador actual); en C, un padre con el primer petróleo censurado en 2018-01 y menos de 48 meses contados desde ahí va a un grupo de edad propio; el estado declarado no se mira; los IC son por pads hijo, como en Vaca Muerta.

- Brecha de días (A, confirmatoria): Los padres cercanos pierden más días que los controles, y la brecha pasa el umbral de 5 días. En Colorado la brecha es de 19,8 días (IC 95% 15,0 a 24,3; 3.524 eventos cercanos; veredicto: sostiene), contra 14,4 días en Vaca Muerta.
- Prueba B (confirmatoria): Las diferencias entre operadores no se separan del ruido de un período: el intervalo no alcanza para decidir. En Colorado la diferencia entre el grupo alto y el bajo en la segunda mitad es de -4,4 días (IC 95% -15,9 a 10,1; 7 operadores; veredicto: no firme).
- Prueba C (confirmatoria): Dentro de un mismo operador no se ve relación entre los días parados y el caudal posterior. En Colorado la pendiente es de -1,1 puntos logarítmicos por cada 10 días (IC 95% -2,8 a 0,2; 3.306 eventos; veredicto: no se ve relación). El mayor beneficio compatible con el dato es 0,2 puntos por cada 10 días. No prueba que cerrar no proteja: un golpe más fuerte da a la vez más días parados y peor caudal después, y eso sesga la pendiente hacia abajo.
- En Colorado los días de más equivalen a 215 m3 de petróleo por evento cercano (IC 95% 156 a 282), valuados al caudal que el pozo traía. Es volumen diferido: el dato no dice que ese petróleo se pierda.

| Banda | Eventos | Sin ventana completa | Exceso medio (días) | Exceso mediano (días) | Brecha contra el control (días) | IC 95% | Volumen de la brecha (m3 por evento) | IC 95% |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| Cercano (menos de 1 km) | 3.524 | 7 | 23,4 | 8,0 | 19,8 | 15,0 a 24,3 | 215 | 156 a 282 |
| 1 a 2 km | 7.578 | 8 | 12,5 | 1,0 | 9,0 | 7,2 a 10,9 | 76 | 45 a 110 |
| Control (2 a 5 km) | 50.600 | 63 | 3,5 | 0,0 |  |  |  |  |

Por operador del padre, con al menos 50 eventos cercanos y la brecha contra sus propios controles (descriptiva). Con la prueba B no firme en Colorado, estas diferencias no se separan del ruido de un período.

| Operador | Cercanos | Controles | Brecha (días) | IC 95% | Volumen de la brecha (m3 por evento) | IC 95% | Caudal de base (m3/d) |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| CRESTONE PEAK RESOURCES OPERATING LLC | 267 | 4.304 | 28,5 | 20,7 a 35,2 | 498 | 171 a 820 | 18,4 |
| KERR MCGEE OIL & GAS ONSHORE LP | 506 | 11.491 | 24,8 | 16,8 a 33,4 | 131 | 63 a 200 | 13,2 |
| PDC ENERGY INC | 1.125 | 13.779 | 24,6 | 15,6 a 34,0 | 298 | 151 a 459 | 16,5 |
| BONANZA CREEK ENERGY OPERATING COMPANY LLC | 218 | 3.151 | 22,4 | 14,0 a 32,6 | 39 | 5 a 73 | 4,2 |
| PRAIRIE OPERATING CO LLC | 132 | 1.189 | 20,3 | -1,6 a 41,5 | 301 | -61 a 732 | 19,4 |
| HIGHPOINT OPERATING CORPORATION | 79 | 2.093 | 18,1 | 3,8 a 33,7 | 92 | 9 a 185 | 5,8 |
| NOBLE ENERGY INC | 482 | 5.782 | 12,2 | 2,9 a 20,9 | 169 | 71 a 291 | 32,2 |
| VERDAD RESOURCES LLC | 91 | 979 | 8,9 | -17,5 a 30,5 | 85 | -434 a 441 | 32,2 |
| EXTRACTION OIL & GAS INC | 436 | 5.252 | 4,5 | -3,9 a 21,5 | -8 | -125 a 197 | 21,2 |

Prueba B en Colorado: corte en 2021-05, la mediana del mes de los eventos cercanos; entran los operadores con al menos 30 cercanos y 30 controles en cada mitad.

| Operador | Grupo | Cercanos, 1.ª mitad | Controles, 1.ª mitad | Brecha, 1.ª mitad (días) | Cercanos, 2.ª mitad | Controles, 2.ª mitad | Brecha, 2.ª mitad (días) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BONANZA CREEK ENERGY OPERATING COMPANY LLC | alto | 150 | 1.961 | 26,3 | 68 | 1.190 | 14,8 |
| CIVITAS NORTH LLC | no entra | 0 | 54 | n/d | 31 | 227 | 9,9 |
| CRESTONE PEAK RESOURCES OPERATING LLC | bajo | 120 | 2.617 | 18,6 | 147 | 1.687 | 35,9 |
| EXTRACTION OIL & GAS INC | bajo | 298 | 2.776 | 2,1 | 138 | 2.476 | 10,3 |
| FUNDARE RESOURCES OPERATING COMPANY LLC | no entra | 31 | 254 | 5,0 | 0 | 201 | n/d |
| HIGHPOINT OPERATING CORPORATION | no entra | 53 | 1.091 | 19,9 | 26 | 1.002 | 17,7 |
| KERR MCGEE OIL & GAS ONSHORE LP | alto | 380 | 7.342 | 27,6 | 126 | 4.149 | 15,8 |
| NOBLE ENERGY INC | bajo | 232 | 2.982 | 21,4 | 250 | 2.800 | 3,6 |
| PDC ENERGY INC | bajo | 475 | 6.659 | 12,1 | 650 | 7.120 | 33,5 |
| PRAIRIE OPERATING CO LLC | alto | 35 | 442 | 25,8 | 97 | 747 | 18,6 |
| PROVIDENCE OPERATING LLC DBA POCO OPERATING | no entra | 4 | 56 | 14,7 | 26 | 208 | -1,9 |
| VERDAD RESOURCES LLC | no entra | 10 | 265 | 0,0 | 81 | 714 | 9,9 |

Correlación de Spearman entre las dos mitades: -0,07 (descriptiva). Repeticiones descartadas porque a un operador le faltó un lado: 3 de 400.

Tamaño de un ensayo en Colorado, con el desvío de sus residuos de C (0,74): para ver 5, 10 y 20 puntos logarítmicos de caudal posterior entre dos formas de cerrar se necesitan 3.411, 853 y 214 eventos por rama, en ese orden (un piso, igual que arriba).

Qué cambia con Colorado, según la regla:

- A: la brecha de días aparece también en otra cuenca, con otro regulador y otra convención de reporte.
- B: no firme en Colorado, así que la lectura de Vaca Muerta conserva la salvedad de regla informada: allí la diferencia entre operadores se mantuvo en el tiempo, pero no se confirmó en otra cuenca.
- C: no cambia ninguna recomendación en ninguna de las dos cuencas. Lo que la resolvería es un ensayo con el tamaño de arriba, o los registros de cierre y la presión del padre de un operador.

## Regla fijada antes de correr

- La regla está en el encabezado de `pipeline/dias_perdidos.py`, en un commit anterior a cualquier cálculo de este módulo.
- Brecha de la cuenca y prueba B: sostiene si el IC 95% queda por encima de cero y el valor es de al menos 5 días; no se sostiene si el límite alto queda por debajo de 5 días; no firme en otro caso.
- Prueba C: el veredicto sale del signo del IC 95% de la pendiente.
- Los IC son de percentiles, por pads hijo, y comparan medias: unos pocos cierres largos pesan en el volumen y la mediana no los ve.
- Qué se había mirado antes en Vaca Muerta: la descomposición ya publicada, y una consulta exploratoria sin intervalos con las medias del exceso por banda, por operador y por distancia, y el caudal posterior por cuartil de exceso. Por eso la brecha y la tabla por operador son descriptivas, y las pruebas B y C son de regla informada.
- Colorado: se corrió después, con la misma regla y sin cambiarla; ahí las tres medidas son confirmatorias. Lo que el dato de Colorado obligó a decidir está al pie del encabezado, en un commit anterior a la corrida de Colorado.

## Qué no prueba

- Con dato mensual, un cierre preventivo y un pozo que queda fuera de servicio por el golpe se ven igual: los días parados no son todos una decisión.
- La comparación entre operadores no es entre iguales: cambian la roca, el fluido, la edad de los pozos y cómo informa cada uno sus días efectivos. Restar el control propio corrige solo lo último.
- El volumen de los días es volumen diferido valuado al caudal que el pozo traía: no dice que ese petróleo se pierda.
- Los IC conservan la dependencia por pad hijo, pero no la de un mismo padre en varios eventos.
