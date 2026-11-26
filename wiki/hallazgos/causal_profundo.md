# Causal profundo: entra agua o sale petróleo

Página generada por `pipeline/causal_profundo.py`. El diseño causal (`causal.md`) encontró que la primera fractura de un hijo a menos de 1 km sube el corte de agua del padre, y la regla le dio a eso el nombre "comunicación física". Pero el corte de agua es una proporción, agua sobre agua más petróleo: sube si entra agua o si cae el petróleo con el agua quieta. Esta página mide los dos volúmenes por separado, con el mismo diseño, los mismos controles aún no tratados y los mismos sorteos del bootstrap. El plan completo está en `docs/plan-causal-profundo.md`.

## Resumen

- ◐ **D3, agua que entra o petróleo que sale: entra agua en los días producidos.** En los días que el padre produce, sale más agua por día: entra agua. Por día calendario la suba no alcanza a separarse de cero; no se midió si es porque ese mes el padre produce menos días. El corte de agua de D2 sube porque entra agua en los días producidos, no solo porque cae el petróleo.
- Agua por día calendario: 4,8 puntos del líquido de la base (IC 95% por bloques de 5 km: -0,1 a 12,3), 468 padres tratados en 89 bloques.
- Agua por día producido: 19,5 puntos (IC 95%: 12,8 a 29,2), 434 tratados; petróleo por día producido: -3,7 (IC 95%: -10,7 a 2,3).
- Petróleo por día calendario: -23,2 puntos (IC 95%: -32,5 a -17,1).
- Qué le pasa a D2: conserva el nombre "comunicación física" con la salvedad de que el agua entra en los días producidos y el volumen del mes no alcanza a separarse de cero.
- El placebo de nunca tratados, que la regla de D2 no tenía, sobre el corte de agua de D2: 0,4 puntos porcentuales (IC 95%: -1,5 a 3,8), 520 pseudo tratados; no rompe.
- ○ **D4, dosis por distancia: sin gradiente.** El corte de agua sube 10,4 puntos porcentuales con el primer golpe a menos de 0,5 km, 16,7 entre 0,5 y 1 km y 7,2 entre 1 y 2 km; la cercana menos la lejana da 3,2 (IC 95%: -3,7 a 10,8).
- ○ **D4, dosis por tamaño del hijo (agua de fractura): sin gradiente.** Tercil alto 8,7, medio 13,5, bajo 17,3 puntos porcentuales; alto menos bajo -8,6 (IC 95%: -18,9 a 9,4).
- D8, la lectura operativa, no se escribe: la regla la pide solo si D3 da agua que entra y D4 da gradiente de distancia.
- ● **D5, forma en el tiempo: persiste.** La suba del corte de agua no se cura en 12 meses: la media de los meses 6 a 12 da 10,9 puntos porcentuales (IC 95%: 7,7 a 15,0), 297 tratados, contra 11,2 de los meses 0 y 1. El IC queda sobre cero en cada mes desde el mes 0.
- ◐ **D6, dónde se sostiene: depende de un operador: YPF.** La suba del corte de agua de D2 depende de YPF: sin los pozos de YPF da 7,1 puntos porcentuales con un IC que incluye cero (IC 95%: -0,6 a 18,1), sobre 129 tratados de 447; los de YPF solos dan 17,5 (IC 95%: 11,6 a 24,5), 255 tratados. Sin YPF quedan 129 tratados y el IC es ancho: el dato no muestra la suba fuera de YPF, ni la descarta. Sacar cualquiera de los otros operadores con el mínimo (Pluspetrol, Tecpetrol, Vista) la deja sobre cero.
- ● **D7, Colorado: se repite.** El corte de agua de D2 sostiene también en Colorado, y D3 da allí el mismo veredicto que en Vaca Muerta.
- ● **Colorado por operador (D13, [causal_profundo.md](causal_profundo.md), regla fijada antes de calcular D13): general.** En Colorado la suba se sostiene sin cada uno de sus operadores grandes (D13).
- ○ **D9, Wyoming: sin muestra.** La muestra de Wyoming no llega al mínimo de la regla: las cifras se publican pero no deciden, y Wyoming no permite probarla.

## Regla fijada antes de calcular

La regla se fijó en el commit 74e3975 de la rama `t3/causal-profundo`: la cabecera de `pipeline/causal_profundo.py`, sus constantes y las funciones de veredicto, sin ninguna cifra calculada. Al fijarla se conocían todas las cifras de `causal.md`, incluida la caída del petróleo: por eso D3 decide con el agua.

- Unidad: puntos del líquido de la base. Para cada padre, el cambio de su agua (o de su petróleo) por día entre la base (meses -6 a -4) y la media de los meses 0 y 1, dividido por su líquido por día de la base, por 100. Agua y petróleo quedan en la misma unidad y suman el cambio del líquido.
- Decide el agua por día calendario: un cierre baja los días producidos, así que no puede subirla. El agua por día producido (meses con 5 días producidos o más) es secundaria: puede inflarse por el flujo de una reapertura, y deja afuera los meses casi enteros cerrados.
- Un placebo rompe si su IC excluye cero y vale 5 puntos o más.
- Orden del veredicto: sin muestra; no sobrevive a su placebo; entra agua (IC bajo del agua por día calendario sobre cero); entra agua en los días producidos (el anterior incluye cero, el IC bajo por día producido queda sobre cero y sus placebos no rompen); el corte sube porque cae el petróleo (el agua no sube 5 puntos por ninguna de las dos vías y el petróleo cae); no firme.

## D3: volúmenes

| Cantidad | Tratados | Controles | Cambio (puntos del líquido base) | IC 95% |
| --- | ---: | ---: | ---: | --- |
| Agua por día calendario (decide) | 468 | 2.026 | 4,8 | -0,1 a 12,3 |
| Petróleo por día calendario | 468 | 2.026 | -23,2 | -32,5 a -17,1 |
| Agua por día producido | 434 | 1.877 | 19,5 | 12,8 a 29,2 |
| Petróleo por día producido | 434 | 1.877 | -3,7 | -10,7 a 2,3 |
| Líquido por día calendario (agua más petróleo) | 468 | 2.026 | -18,4 | -28,2 a -9,8 |

Puente con D2, sin veredicto: el corte de agua con la media de los meses 0 y 1 (D2 toma el mayor de los dos) da 9,5 puntos porcentuales (IC 95%: 6,0 a 14,5), contra 13,8 de D2.

Placebos de D3.

| Placebo | Tratados | Cambio (puntos) | IC 95% | Rompe |
| --- | ---: | ---: | --- | --- |
| Previo (meses -2 y -1), agua por día calendario | 468 | -0,4 | -4,5 a 5,2 | no |
| Fecha falsa (12 meses antes), agua por día calendario | 218 | 0,9 | -2,9 a 3,1 | no |
| Distancia falsa (primer hijo a 3 a 5 km), agua por día calendario | 305 | -1,5 | -5,9 a 3,3 | no |
| Nunca tratados (fechas sorteadas), agua por día calendario | 569 | -1,7 | -5,0 a 2,6 | no |
| Previo (meses -2 y -1), agua por día producido | 449 | 1,7 | -1,8 a 6,9 | no |
| Nunca tratados (fechas sorteadas), agua por día producido | 508 | 1,4 | -2,3 a 6,7 | no |

## D4: dosis

Las precisiones de D4 se fijaron en el commit df3a7d6, antes de calcular cualquier cifra de D4: los mismos sorteos que D3, la distancia del golpe más cercano del mes de la fractura, la cohorte nueva de 1 a 2 km y los terciles del hijo. Decide el corte de agua de D2; el agua por día calendario de D3 se publica al lado. "Gradiente" pide que las tres estimaciones bajen de cerca a lejos (o de grande a chico) y que el IC de la diferencia entre los extremos quede entero sobre cero; "sin gradiente", que ese IC incluya el cero.

| Distancia del primer golpe | Tratados | Corte de agua (pp) | IC 95% | Agua por día calendario (puntos) | IC 95% |
| --- | ---: | ---: | --- | ---: | --- |
| 0 a 0,5 km | 206 | 10,4 | 5,1 a 18,3 | 7,1 | 1,0 a 15,3 |
| 0,5 a 1 km | 241 | 16,7 | 9,5 a 24,2 | 2,7 | -3,9 a 11,6 |
| 1 a 2 km (cohorte nueva) | 390 | 7,2 | 1,8 a 13,0 | 0,8 | -6,9 a 8,1 |
| 3 a 5 km (placebo de distancia falsa) | 287 | -0,8 | -4,0 a 2,3 | -1,5 | -5,9 a 3,3 |
| Cercana menos lejana (0 a 0,5 menos 1 a 2) |  | 3,2 | -3,7 a 10,8 | 6,3 | -4,1 a 17,0 |

Las bandas de 0 a 0,5 y de 0,5 a 1 km parten los tratados de D2. La de 1 a 2 km es otra cohorte: padres cuyo primer golpe a menos de 2 km cae entre 1 y 2 km, sin ninguno a menos de 1 km en la ventana, con los mismos controles; un pozo fuera del universo de los sorteos toma el peso de su bloque de 5 km, y 3 quedan fuera porque su bloque no tiene ninguno. La banda de 3 a 5 km es el placebo de distancia falsa de D2, reimpreso.

Sin veredicto, visto después de la regla: la banda de 1 a 2 km también sube el corte (IC 1,8 a 13,0) y la de 3 a 5 km no se separa de cero. El efecto no se corta en 1 km, pero la regla no pidió un umbral y la banda más cercana no es la más alta.

| Agua de fractura del hijo | Tratados | Corte de agua (pp) | IC 95% | Agua por día calendario (puntos) | IC 95% |
| --- | ---: | ---: | --- | ---: | --- |
| Tercil alto | 122 | 8,7 | 0,9 a 23,3 | -4,5 | -14,8 a 12,9 |
| Tercil medio | 135 | 13,5 | 5,8 a 23,5 | 5,5 | -2,9 a 15,7 |
| Tercil bajo | 190 | 17,3 | 10,6 a 23,8 | 11,9 | 4,5 a 20,4 |
| Alto menos bajo |  | -8,6 | -18,9 a 9,4 | -16,4 | -29,1 a 2,9 |

Los cortes de los terciles salen de los 636 tratados de las celdas de D2 con el agua de fractura del hijo (100% de los que tienen corte de agua); las estimaciones usan los que quedan en celdas con controles suficientes, como D2.

Sin veredicto: el tercil de más agua da la suba más chica, al revés de una dosis; la regla no tiene veredicto para un gradiente al revés y el IC de la diferencia incluye el cero.

Longitud de rama del hijo, sin veredicto: el tercil más largo menos el más corto da -6,2 puntos porcentuales (IC 95%: -16,9 a 8,2); tiene el dato el 94% de los tratados.

## D5: forma en el tiempo

Las precisiones de D5 y D6 se fijaron en el commit cfd9039, antes de calcular cualquier cifra de D5 o de D6. D5 sigue a los tratados de D2 mes a mes, de -6 a 12 meses desde la fractura, con controles aún no tratados hasta 12 meses después. Cada mes se compara con la base de D2 (meses -6 a -4) y cuenta solo: D2 toma el mayor de dos meses seguidos, así que su cifra queda más alta que la de cualquier mes de esta tabla sin que eso sea una cura. Decide la media del corte de agua en los meses 6 a 12: "persiste" si su IC queda entero sobre cero; "se cura" si su IC incluye el cero y su extremo alto queda bajo la mitad de la suba de los meses 0 y 1.

| Mes | Tratados | Corte de agua (pp) | IC 95% | Agua por día calendario (puntos) | IC 95% | Petróleo por día calendario (puntos) | IC 95% |
| ---: | ---: | ---: | --- | ---: | --- | ---: | --- |
| -6 | 335 | -1,1 | -2,6 a 0,5 | -0,1 | -2,3 a 3,2 | 2,4 | -3,1 a 8,6 |
| -5 | 335 | 0,2 | -0,6 a 1,0 | -0,3 | -2,0 a 1,5 | -0,3 | -2,7 a 3,2 |
| -4 | 332 | 0,9 | -0,6 a 2,0 | 0,4 | -2,9 a 2,7 | -2,2 | -10,4 a 3,6 |
| -3 | 325 | 0,9 | -0,9 a 2,7 | 0,7 | -2,9 a 4,0 | -5,9 | -17,0 a 2,6 |
| -2 | 329 | 1,3 | -0,6 a 3,2 | -0,3 | -4,0 a 4,6 | -5,9 | -18,3 a 4,1 |
| -1 | 319 | 2,3 | -0,2 a 5,1 | 0,0 | -6,1 a 6,4 | -15,5 | -29,1 a -3,9 |
| 0 | 292 | 4,7 | 1,7 a 8,3 | -1,9 | -8,6 a 4,7 | -36,5 | -50,6 a -26,1 |
| 1 | 296 | 17,8 | 12,3 a 25,2 | 13,7 | 6,7 a 23,1 | -27,1 | -34,7 a -19,6 |
| 2 | 309 | 18,3 | 13,0 a 24,5 | 29,0 | 21,3 a 40,8 | -7,6 | -14,7 a 1,7 |
| 3 | 315 | 16,4 | 12,3 a 21,3 | 31,0 | 24,4 a 40,8 | 0,9 | -9,1 a 13,3 |
| 4 | 306 | 14,4 | 10,8 a 19,2 | 31,1 | 22,7 a 42,7 | 1,1 | -7,6 a 12,4 |
| 5 | 311 | 12,9 | 10,1 a 17,8 | 30,4 | 19,8 a 45,5 | 4,8 | -5,8 a 17,1 |
| 6 | 299 | 14,1 | 10,6 a 18,9 | 28,1 | 19,4 a 42,0 | 5,3 | -6,8 a 18,9 |
| 7 | 310 | 11,8 | 8,0 a 16,3 | 23,9 | 15,1 a 36,3 | 9,4 | -4,0 a 23,1 |
| 8 | 304 | 10,9 | 6,9 a 15,4 | 20,2 | 12,9 a 28,9 | 3,9 | -9,1 a 17,4 |
| 9 | 304 | 12,0 | 8,1 a 17,2 | 18,0 | 12,1 a 27,1 | 2,1 | -9,8 a 13,2 |
| 10 | 305 | 9,1 | 4,6 a 15,1 | 15,7 | 10,2 a 24,4 | 5,3 | -6,6 a 17,4 |
| 11 | 309 | 9,0 | 4,6 a 14,6 | 15,5 | 8,5 a 25,1 | 6,8 | -6,1 a 19,5 |
| 12 | 297 | 9,4 | 5,2 a 13,8 | 18,2 | 11,9 a 26,6 | 8,6 | -5,5 a 24,1 |

- Media de los meses 6 a 12: 10,9 puntos porcentuales (IC 95%: 7,7 a 15,0), con 297 tratados (el menor n de esos meses). Media de los meses 0 y 1: 11,2.
- Primer mes con el IC del corte de agua sobre cero: 0.
- 142 de 341 tratados (42%) reciben otro golpe a menos de 2 km en los meses 2 a 12: la serie mide la primera fractura y lo que vino después, no la primera sola.
- Pozos fuera de los sorteos porque su bloque de 5 km no tiene ninguno del universo: 0.
- Antes de la fractura (meses -6 a -1) el corte de agua no se separa de cero en ningún mes.
- Sin veredicto, visto después de la regla: el petróleo por día calendario ya cae en el mes -1 (-15,5 puntos, IC 95%: -29,1 a -3,9), antes de la fractura del hijo, y el corte de agua de ese mes no se separa de cero. La regla de `causal.md` admite anticipación hasta 3 meses; no se midió si es un cierre del padre.
- Sin veredicto, visto después de la regla: el agua por día calendario, que en la media de los meses 0 y 1 no alcanza a separarse de cero (D3), queda sobre cero en cada mes de 2 a 12, entre 15,5 y 31,1 puntos del líquido de la base.

## D6: dónde se sostiene

El corte de agua de D2 partido por operador (solo y sin él, con 50 tratados o más), por edad del padre, por año de la cohorte y por área (con el mismo mínimo). Se publican todos los cortes, sin ajuste por comparaciones múltiples, y ningún subgrupo tiene veredicto. Decide solo el "sin el operador": "general" si sin cada operador el IC sigue sobre cero, "depende de un operador" si no. Sacar un operador saca sus tratados y sus controles, y con ellos los tratados de las celdas que se quedan con menos de 5 controles: por eso los tratados sin un operador pueden ser menos que el total menos los suyos. Un subgrupo deja los controles de su celda.

| Corte | Grupo | Tratados | Controles | Corte de agua (pp) | IC 95% |
| --- | --- | ---: | ---: | ---: | --- |
| Todos (D2) | todos | 447 | 1.915 | 13,8 | 9,5 a 19,9 |
| Solo el operador | Pluspetrol | 30 | 134 | -0,1 | -10,3 a 19,6 |
| Sin el operador | Pluspetrol | 405 | 1.556 | 15,0 | 10,4 a 20,7 |
| Solo el operador | Tecpetrol | 53 | 285 | -1,9 | -8,8 a 7,3 |
| Sin el operador | Tecpetrol | 394 | 1.591 | 15,8 | 10,9 a 22,3 |
| Solo el operador | Vista | 41 | 180 | 13,1 | -2,5 a 46,8 |
| Sin el operador | Vista | 397 | 1.620 | 14,2 | 9,7 a 19,8 |
| Solo el operador | YPF | 255 | 1.120 | 17,5 | 11,6 a 24,5 |
| Sin el operador | YPF | 129 | 449 | 7,1 | -0,6 a 18,1 |
| Edad del padre (meses) | 6-11 | 139 | 613 | 23,0 | 14,0 a 32,7 |
| Edad del padre (meses) | 12-23 | 141 | 615 | 9,9 | 1,9 a 19,4 |
| Edad del padre (meses) | 24-47 | 147 | 598 | 9,6 | 4,0 a 18,3 |
| Edad del padre (meses) | 48+ | 20 | 89 | 7,4 | -12,5 a 25,9 |
| Año de la cohorte | hasta 2018 | 64 | 211 | 10,5 | 2,2 a 18,6 |
| Año de la cohorte | 2019-2021 | 105 | 561 | 14,5 | 7,9 a 21,1 |
| Año de la cohorte | 2022 en adelante | 278 | 1.143 | 14,2 | 9,1 a 23,1 |
| Área | FORTIN DE PIEDRA | 53 | 285 | -1,9 | -8,8 a 7,3 |
| Área | LA AMARGA CHICA | 77 | 456 | 20,7 | 6,8 a 35,9 |
| Área | LOMA CAMPANA | 125 | 470 | 16,1 | 6,7 a 22,3 |

Veredicto: depende de un operador: YPF. La suba del corte de agua de D2 depende de YPF: sin los pozos de YPF da 7,1 puntos porcentuales con un IC que incluye cero (IC 95%: -0,6 a 18,1), sobre 129 tratados de 447; los de YPF solos dan 17,5 (IC 95%: 11,6 a 24,5), 255 tratados. Sin YPF quedan 129 tratados y el IC es ancho: el dato no muestra la suba fuera de YPF, ni la descarta. Sacar cualquiera de los otros operadores con el mínimo (Pluspetrol, Tecpetrol, Vista) la deja sobre cero.

Tecpetrol y el área FORTIN DE PIEDRA son los mismos tratados: sus dos filas dan lo mismo.

## D7: Colorado

El mismo diseño de D2 y D3, con las mismas constantes, los mismos sorteos y una regla fijada antes de calcular D7, sobre el warehouse de Colorado (cuenca DJ): los pozos horizontales con coordenadas, el mes de fractura de los hijos sin fecha dudosa y la producción mensual. El warehouse de Colorado se abre solo para leer; la tabla `mart_causal_profundo_d7` se escribe en el de Vaca Muerta. La regla pide primero que el dato de agua alcance, y después compara.

- Cobertura del dato de agua: 100% de los meses base (meses -6 a -4) de los 1.495 tratados de las celdas del diseño tienen agua y días efectivos; la regla pide 70%. D2 cuenta después solo a los tratados con el corte de agua medido, por eso da menos tratados.
- D2, corte de agua: 9,0 puntos porcentuales (IC 95%: 6,3 a 12,1), con 1.247 tratados; en Vaca Muerta, 13,8 (IC 95%: 9,5 a 19,9). Veredicto en Colorado: sostiene: comunicación física causal bajo tendencias paralelas.
- Placebos de D2: de los de cohorte, ninguno de los 3 rompe. El placebo de cierre da 2,6 (IC 95%: 1,5 a 3,7): el intervalo no toca cero, pero queda debajo de 50% del corte de D2, así que con la regla de D2 no rompe.
- D3, en puntos del líquido base: agua por día calendario 2,7 (IC 95%: -1,1 a 7,7), agua por día producido 10,4 (IC 95%: 5,3 a 16,6), petróleo por día calendario -20,0 (IC 95%: -25,3 a -14,4), con 1.360 tratados.
- Placebos de D3: del agua por día calendario, ninguno de los 4 rompe; del agua por día producido, ninguno de los 2 rompe.
- D3 en Colorado: entra agua en los días producidos. En Vaca Muerta: entra agua en los días producidos.
- ● **D7, Colorado: se repite.** El corte de agua de D2 sostiene también en Colorado, y D3 da allí el mismo veredicto que en Vaca Muerta.

## D13: dónde se sostiene la suba de Colorado

El corte de agua de D7 (Colorado) partido por operador, solo y sin él, con 50 tratados o más: las mismas celdas y los mismos sorteos de D7 y los mismos cortes de D6, sin cortes de edad, período ni área porque la pregunta es el operador. Se publican todos los cortes, sin ajuste por comparaciones múltiples, y ningún subgrupo tiene veredicto. Decide solo el "sin el operador": "general" si sin cada operador el IC sigue sobre cero, "depende de un operador" si no, "sin muestra" si hay menos de 2 operadores con el mínimo o D7 no pasa su compuerta de agua. Sacar un operador saca sus tratados y sus controles, y con ellos los tratados de las celdas que se quedan con menos de 5 controles: por eso los tratados sin un operador pueden ser menos que el total menos los suyos. Un subgrupo deja los controles de su celda.

| Corte | Grupo | Tratados | Controles | Corte de agua (pp) | IC 95% |
| --- | --- | ---: | ---: | ---: | --- |
| Todos (D7) | todos | 1.247 | 17.389 | 9,0 | 6,3 a 12,1 |
| Solo el operador | BONANZA CREEK ENERGY OPERATING COMPANY LLC | 107 | 5.426 | 26,2 | 7,6 a 40,9 |
| Sin el operador | BONANZA CREEK ENERGY OPERATING COMPANY LLC | 1.140 | 15.157 | 7,5 | 5,1 a 9,9 |
| Solo el operador | CRESTONE PEAK RESOURCES OPERATING LLC | 83 | 5.989 | 6,6 | 0,6 a 17,5 |
| Sin el operador | CRESTONE PEAK RESOURCES OPERATING LLC | 1.164 | 15.185 | 9,2 | 6,3 a 12,6 |
| Solo el operador | EXTRACTION OIL & GAS INC | 146 | 2.589 | 7,4 | 2,4 a 14,4 |
| Sin el operador | EXTRACTION OIL & GAS INC | 1.101 | 15.960 | 9,5 | 6,6 a 12,7 |
| Solo el operador | KERR MCGEE OIL & GAS ONSHORE LP | 190 | 6.249 | 4,7 | 0,1 a 9,9 |
| Sin el operador | KERR MCGEE OIL & GAS ONSHORE LP | 1.052 | 12.409 | 9,4 | 6,2 a 13,2 |
| Solo el operador | NOBLE ENERGY INC | 189 | 5.412 | 12,1 | 5,7 a 19,9 |
| Sin el operador | NOBLE ENERGY INC | 1.058 | 13.101 | 8,6 | 5,5 a 11,9 |
| Solo el operador | PDC ENERGY INC | 342 | 7.323 | 3,6 | -0,9 a 8,1 |
| Sin el operador | PDC ENERGY INC | 877 | 11.564 | 11,1 | 7,5 a 15,2 |
| Solo el operador | PRAIRIE OPERATING CO LLC | 54 | 1.173 | 3,4 | -19,9 a 22,8 |
| Sin el operador | PRAIRIE OPERATING CO LLC | 1.193 | 17.186 | 9,3 | 6,4 a 12,4 |

Veredicto: general. En Colorado la suba se sostiene sin cada uno de sus operadores grandes (D13).
El valor del veredicto es el "sin el operador" de IC bajo más chico: 7,5 puntos porcentuales (IC 95%: 5,1 a 9,9), 1.247 tratados en D7.

La regla se fijó en el commit a1f1fee, antes de calcular ninguna cifra de D13. Entra en la familia de Holm de `inferencia.md`, con la fila de su veredicto.

## D9: Wyoming

El mismo diseño de D7 (D2 y D3 con las mismas constantes, los mismos sorteos y la regla de veredicto de Colorado), con una regla fijada antes de calcular ninguna cifra de agua de Wyoming, sobre el warehouse opcional de Wyoming: los pozos horizontales con coordenadas y la producción mensual. El mes 0 del hijo es el de la primera terminación (FIRSTCOMP), como en la replicación del petróleo de Wyoming, no el de la fractura: es la diferencia con Colorado y un límite de esta prueba. El warehouse de Wyoming se abre solo para leer; la tabla `mart_causal_profundo_d9` se escribe en el de Vaca Muerta. La regla pide primero que el dato de agua alcance, y después compara.

- Cobertura del dato de agua: 100% de los meses base (meses -6 a -4) de los 114 tratados de las celdas del diseño tienen agua y días efectivos; la regla pide 70%. D2 cuenta después solo a los tratados con el corte de agua medido, por eso da menos tratados.
- D2, corte de agua: 6,7 puntos porcentuales (IC 95%: -0,7 a 13,4), con 38 tratados; en Vaca Muerta, 13,8 (IC 95%: 9,5 a 19,9). Veredicto en Wyoming: sin muestra.
- Placebos de D2: de los de cohorte, ninguno de los 3 rompe. El placebo de cierre da 2,9 (IC 95%: -0,3 a 5,4): el intervalo toca cero, no rompe.
- D3, en puntos del líquido base: agua por día calendario -7,7 (IC 95%: -37,6 a 6,6), agua por día producido 6,9 (IC 95%: -3,0 a 18,7), petróleo por día calendario -12,2 (IC 95%: -37,6 a 1,1), con 43 tratados.
- Placebos de D3: del agua por día calendario, rompen previo, nunca tratados; del agua por día producido, ninguno de los 2 rompe.
- D3 en Wyoming: sin muestra. En Vaca Muerta: entra agua en los días producidos.
- ○ **D9, Wyoming: sin muestra.** La muestra de Wyoming no llega al mínimo de la regla: las cifras se publican pero no deciden, y Wyoming no permite probarla.

## Límites

- Causa bajo los supuestos de `causal.md` (tendencias paralelas condicionales a cohorte y edad, sin anticipación más allá de 3 meses, sin derrame sobre controles limpios a 2 km), no un hecho físico medido: el agua se ve en el volumen mensual, no entrando.
- El agua por día producido deja afuera a los padres sin ningún mes de 5 días producidos o más en la ventana o con menos de dos en la base (ese mínimo de dos meses no lo fijó la regla: se eligió al calcular, en el mismo commit que dio las cifras): quedan 93% de los tratados y 93% de los controles. Es una muestra que el cierre puede elegir.
- Una reapertura puede dar un flujo inicial alto; si eso explicara la suba por día producido, el petróleo por día producido también subiría.
- Solo la primera fractura a menos de 1 km de cada padre, distancia entre bocas de pozo, como en `causal.md`.
- D6 publica cada corte sin ajuste por comparaciones múltiples, y ningún subgrupo tiene veredicto: con tantos cortes, alguno puede salir alto o bajo por azar.
- Lo que lo cargaría como hecho físico sigue en la tabla de datos de `causal.md`: presión del padre, producción diaria, trazadores.

## Reproducir

```
uv run python -m pipeline.build
uv run python -m pipeline.trayectorias
uv run python -m pipeline.causal
uv run python -m pipeline.causal_profundo
uv run python -m pipeline.wiki
```
