# Diseño causal: qué puede sostener como causa el dato público

Página generada por `pipeline/causal.py`. Todo lo demás del estudio es descriptivo: compara padres cercanos con controles a 2 a 5 km de la misma edad, y los cercanos ya rendían menos antes de la fractura. Esta página cambia el control por un padre que también va a recibir un hijo a menos de 1 km, pero más tarde (aún no tratado), y fija antes de calcular qué resultado se lee como causa. El plan completo está en `docs/plan-causal.md`.

## Resumen

- ○ **D1, caudal de petróleo al mes 1: no sobrevive a su placebo.** Un placebo da un efecto donde no debería haberlo: el diseño no separa la fractura de la selección. ATT(1) = -25,8 puntos (IC 95% por bloques de 5 km: -33,9 a -17,9), 468 padres tratados en 89 bloques.
- ○ **D1b, persistencia en los meses 7 a 24: sin muestra.** La muestra no alcanza el mínimo que fijó la regla; el valor se publica pero no decide nada. 43 tratados (la regla pide 200); diferencia -6,1 puntos (IC 95%: -36,1 a 17,3).
- ● **D2, corte de agua: sostiene: comunicación física causal bajo tendencias paralelas.** Ningún placebo rompe, el cierre solo no explica el salto y el IC queda entero sobre 2 puntos. Mide la proporción de agua, no su volumen: el corte también sube si el petróleo cae con el agua constante, y D2 no separa las dos cosas; el nombre del veredicto es el de la regla fijada. ATT_W = 13,8 puntos porcentuales (IC 95%: 9,5 a 19,9), 447 tratados.
- ◐ **Debajo del corte de agua (D3, [causal_profundo.md](causal_profundo.md), regla fijada tras ver D2, antes de su cifra): entra agua en los días producidos.** En los días que el padre produce, su agua por día sube 19,5 puntos del líquido de la base (IC 95%: 12,8 a 29,2) y su petróleo por día no se separa de cero (-3,7, IC -10,7 a 2,3); el volumen de agua del mes no alcanza a separarse de cero (4,8, IC -0,1 a 12,3), y no se midió si es porque ese mes el padre produce menos días. El nombre "comunicación física" se conserva con esa salvedad. El placebo de nunca tratados sobre el corte de agua, que la regla de D2 no tenía, da 0,4 puntos porcentuales (IC 95%: -1,5 a 3,8): no rompe.
- ○ **Dosis (D4, [causal_profundo.md](causal_profundo.md), regla fijada tras ver D2, antes de su cifra): sin gradiente.** El corte de agua no sube más cuando el primer golpe está más cerca (la cercana menos la lejana da 3,2 puntos porcentuales, IC 95%: -3,7 a 10,8) ni cuando el hijo usa más agua de fractura (el tercil alto menos el bajo da -8,6, IC 95%: -18,9 a 9,4). El dato no muestra una distancia ni un tamaño de hijo que concentre el efecto, así que la lectura operativa que lo pedía no se escribe.
- ● **Forma en el tiempo (D5, [causal_profundo.md](causal_profundo.md), regla fijada tras ver D2, antes de su cifra): persiste.** La suba del corte de agua no se cura en 12 meses: la media de los meses 6 a 12 da 10,9 puntos porcentuales (IC 95%: 7,7 a 15,0), 297 tratados, contra 11,2 de los meses 0 y 1. El IC queda sobre cero en cada mes desde el mes 0.
- ◐ **Dónde se sostiene (D6, [causal_profundo.md](causal_profundo.md), regla fijada tras ver D2, antes de su cifra): depende de un operador: YPF.** La suba del corte de agua de D2 depende de YPF: sin los pozos de YPF da 7,1 puntos porcentuales con un IC que incluye cero (IC 95%: -0,6 a 18,1), sobre 129 tratados de 447; los de YPF solos dan 17,5 (IC 95%: 11,6 a 24,5), 255 tratados. Sin YPF quedan 129 tratados y el IC es ancho: el dato no muestra la suba fuera de YPF, ni la descarta. Sacar cualquiera de los otros operadores con el mínimo (Pluspetrol, Tecpetrol, Vista) la deja sobre cero.
- ● **Otra cuenca (D7, Colorado, [causal_profundo.md](causal_profundo.md), regla fijada tras ver D2, antes de calcular el agua de la cuenca): se repite.** El corte de agua de D2 sostiene también en Colorado, y D3 da allí el mismo veredicto que en Vaca Muerta. En Colorado el corte de agua sube 9,0 puntos porcentuales (IC 95%: 6,3 a 12,1), 1.247 tratados.
- ● **Colorado por operador (D13, [causal_profundo.md](causal_profundo.md), regla fijada antes de calcular D13): general.** En Colorado la suba se sostiene sin cada uno de sus operadores grandes (D13).

Lectura: el dato público carga una sola afirmación causal, y bajo supuestos nombrados. La primera fractura de un hijo a menos de 1 km sube el corte de agua del padre (la proporción, no el volumen de agua) en el mes de la fractura o el siguiente, frente a un padre de la misma zona de relleno que todavía no la recibió; un cierre de más de medio mes sin hijo cerca lo sube 3,6 puntos porcentuales, menos de la mitad. Esa suba, con reglas fijadas tras ver D2 y antes de sus cifras en `causal_profundo.md`, no se cura en los 12 meses siguientes (D5) y depende de YPF (D6): sin YPF da 7,1 puntos porcentuales con un IC que incluye cero (-0,6 a 18,1), sobre 129 tratados, así que el dato no la muestra fuera de YPF. La caída del caudal de petróleo, en cambio, no sobrevive como causa con estos controles: el placebo de nunca tratados da -8,0 puntos con un IC que excluye cero, y M* = 0,62 queda bajo 1. La brecha del mes 1 sigue medida y publicada como descripción; lo que no se sostiene es leerla como el efecto de la fractura.

## Regla fijada antes de calcular

La regla se fijó en el commit 8f52ff1 de la rama `t3/causal-diseno`: la cabecera de `pipeline/causal.py`, sus constantes y las funciones de veredicto, sin ninguna cifra calculada con estos diseños. Al fijarla se conocían las cifras ya publicadas del estudio (brecha del mes 1, pretendencia, salto de corte de agua). El commit siguiente declara dos arreglos de implementación hechos sin cambiar ninguna constante ni ningún umbral.

- Cohorte de un padre: primer mes con un hijo fracturado a menos de 1 km. Tratado: 6 meses de edad o más en ese mes, ningún hijo a menos de 2 km en los 12 meses previos, y base (meses -6 a -4) con más de 1 m3/d de petróleo.
- Índice: petróleo por día calendario sobre la base, recortado en 3. Control: padre del mismo grupo de edad en el mismo mes, con base válida, sin hijo a menos de 2 km desde 12 meses antes hasta el horizonte, y con su propio primer hijo a menos de 1 km después del horizonte (aún no tratado). Celda con al menos 1 tratado y 5 controles.
- ATT por celda de mes y grupo de edad, promediado por tratados (estilo Callaway y Sant'Anna). IC 95%: bootstrap de percentiles por bloques de 5 km, 400 repeticiones, semilla fija. M* es una versión simplificada de la cota de magnitudes relativas de Rambachan y Roth.
- Un placebo rompe si su IC excluye cero y vale 5 puntos o más (2 puntos porcentuales en D2).
- D1 sostiene si no rompe ningún placebo, el IC de ATT(1) queda entero bajo -10 puntos, M* es 1 o más y sin cada operador con 50 tratados o más el IC sigue bajo cero.
- D2 sostiene si no rompe ningún placebo, el placebo de cierre no llega a la mitad del ATT_W con un IC que excluye cero, y el IC de ATT_W queda entero sobre 2 puntos porcentuales.

## D1: caudal de petróleo

Diferencia entre tratados y controles aún no tratados del índice de cada mes relativo a la fractura, en puntos. S1 suma los padres nunca tratados al control y no decide nada.

| Mes | Tratados | Controles | ATT (puntos) | IC 95% | S1: ATT | S1: IC 95% |
| ---: | ---: | ---: | ---: | --- | ---: | --- |
| -3 | 468 | 2.018 | -6,1 | -17,3 a 1,8 | -4,0 | -11,2 a 2,8 |
| -2 | 468 | 2.026 | -3,6 | -15,4 a 3,9 | -1,5 | -8,0 a 4,9 |
| -1 | 467 | 2.026 | -10,0 | -21,3 a -1,4 | -8,3 | -13,8 a -2,2 |
| 0 | 461 | 2.019 | -30,4 | -42,0 a -22,9 | -26,0 | -31,3 a -20,3 |
| 1 | 468 | 2.026 | -25,8 | -33,9 a -17,9 | -28,4 | -34,5 a -22,6 |
| 2 | 468 | 2.023 | -5,9 | -15,1 a 1,9 | -10,8 | -18,9 a -3,3 |
| 3 | 467 | 2.005 | 0,1 | -7,1 a 10,5 | -3,6 | -11,0 a 3,5 |
| 4 | 468 | 2.025 | 0,5 | -7,4 a 11,5 | -1,8 | -8,9 a 5,5 |
| 5 | 468 | 2.014 | 5,6 | -2,5 a 13,9 | 2,6 | -3,9 a 8,8 |
| 6 | 468 | 2.012 | 6,3 | -1,7 a 15,5 | 3,0 | -3,8 a 9,5 |

Placebos de D1, en el mes 1.

| Placebo | Tratados | ATT (puntos) | IC 95% | Rompe |
| --- | ---: | ---: | --- | --- |
| Fecha falsa (la fecha de cada tratado corrida 12 meses hacia atrás) | 218 | 3,9 | -4,6 a 11,7 | no |
| Distancia falsa (primer hijo a 3 a 5 km, ninguno a menos de 2 km) | 302 | 0,9 | -9,3 a 10,9 | no |
| Nunca tratados (padres sin hijo a menos de 1 km, fechas sorteadas) | 567 | -8,0 | -15,2 a -0,5 | sí |

Tendencias no paralelas: el mayor paso previo es 6,4 puntos (con la serie de los meses -3 a -1: -6,1, -3,6 y -10,0). M* = 0,62: si cada paso posterior a la fractura pudiera desviarse 0,62 veces ese paso, el IC robusto ya tocaría cero. Es el M* simplificado, que queda como registro; la cota de Rambachan y Roth (`cota_rr.md`) lo reemplaza en el texto. La pendiente previa que se detectaría con 80% de potencia es 6,2 puntos por mes.

Dejar un operador afuera (operadores con 50 tratados o más), ATT(1).

| Sin el operador | Tratados restantes | ATT (puntos) | IC 95% |
| --- | ---: | ---: | --- |
| Pluspetrol | 424 | -27,5 | -37,3 a -19,6 |
| Tecpetrol | 413 | -25,0 | -33,8 a -18,0 |
| Vista | 416 | -26,0 | -36,0 a -17,3 |
| YPF | 132 | -29,4 | -42,1 a -16,7 |

## D1b: persistencia en los meses 7 a 24

Media del índice de los meses 7 a 24 (al menos 15 meses con dato), tratados y controles sin otro hijo a menos de 2 km en los meses 1 a 24: 43 tratados en 59 bloques, diferencia -6,1 puntos (IC 95%: -36,1 a 17,3). La regla pide 200 tratados: la exigencia de 24 meses sin otro hijo cerca deja muy pocos padres en zona de relleno, así que la pregunta de pérdida o diferido queda abierta. Suma de los meses 0 a 23, sin veredicto: -178,6 puntos-mes (IC 95%: -814,0 a 348,0).

## D2: corte de agua

ΔW: el mayor corte de agua del mes de la fractura y el siguiente, menos la media de los meses -6 a -4, en puntos porcentuales (W = agua sobre agua más petróleo). Mismas celdas y controles que D1.

- ATT_W = 13,8 puntos porcentuales (IC 95%: 9,5 a 19,9), 447 tratados, 89 bloques.
- Es una suba de corto plazo: ΔW toma el mayor de dos meses y promedia por celda. La brecha descriptiva del corte de agua (`descomposicion.md`, panel 4) es otra cantidad, una mediana mes a mes, más chica, que a los 12 meses sigue sobre cero (su IC lo excluye); D2 no mide si su propia suba persiste.
- Qué es nuevo: que el padre responda a la fractura de un hijo cercano ya lo trata como señal de interferencia la literatura de golpes de fractura (frac hits) de Vaca Muerta y de cuencas de Estados Unidos (referencias en `docs/revision-independiente.md`). Min y coautores, "Data-driven Analysis for Causality of Parent-child Interactions in the Bakken" (URTeC), tienen causalidad en el título; de ese trabajo leímos el resumen y una nota de JPT, que no describen el diseño ([literatura.md](literatura.md)). Lo que agrega este trabajo, hasta donde leímos, es el diseño sobre dato mensual público de toda la cuenca, no el hecho físico.
- Placebo de cierre: meses de padres sin hijo a menos de 2 km desde 12 meses antes hasta el mes siguiente, con menos de medio mes producido y base de 0,8 o más, contra meses sin cierre del mismo mes calendario y grupo de edad: 3,6 puntos porcentuales (IC 95%: 2,3 a 7,1), 2.900 meses cerrados. El cierre sube el corte de agua menos de la mitad del efecto (el umbral es 6,9).

| Placebo | Tratados | ΔW (pp) | IC 95% | Rompe |
| --- | ---: | ---: | --- | --- |
| Previo (ΔW en los meses -2 y -1) | 451 | 1,1 | -1,3 a 4,7 | no |
| Fecha falsa (la fecha de cada tratado corrida 12 meses hacia atrás) | 214 | -0,4 | -2,5 a 1,0 | no |
| Distancia falsa (primer hijo a 3 a 5 km, ninguno a menos de 2 km) | 287 | -0,8 | -4,0 a 2,3 | no |

## Sin veredicto

Por posición del padre respecto de la rama del hijo de la cohorte (de `mart_par_rama`). NOTA DE MUESTRA: solo entran los tratados con las dos ramas medidas; las ramas medidas cubren de 76 a 97% de los hijos fracturados de 2016 a 2023 pero solo 39% de los de 2024 y 25% de los de 2025, así que estas filas son sobre todo de 2016 a 2023. La posición la decide el diseño del pad, no se asigna al azar.

| Posición | D1: tratados | D1: ATT(1) (puntos) | IC 95% | D2: tratados | D2: ATT_W (pp) | IC 95% |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| costado | 182 | -35,6 | -48,3 a -21,7 | 170 | 16,2 | 10,3 a 24,4 |
| punta | 135 | -6,2 | -25,1 a 8,2 | 130 | 8,5 | 1,7 a 14,3 |

Esta partición de D1 y D2 por posición no tiene veredicto propio; el contraste entre costado y punta con su regla fijada está en [mecanismo.md](mecanismo.md), donde sostiene.

Cotas de Lee del caudal por día producido en el mes 1 (meses con 0,9 del mes producido o más): de -47,1 a 12,8 puntos. Producen el mes entero 43% de los tratados y 82% de los controles; con esa diferencia el recorte es grande y la cota no separa un efecto sobre el caudal de los días que se dejan de producir. Supone monotonía: la fractura solo baja la chance de producir el mes entero.

## Límites

- Causa bajo supuestos nombrados, no un hecho físico medido: tendencias paralelas condicionales a cohorte y edad, que no se pueden probar después de la fractura, y la exclusión del placebo de cierre.
- El corte de agua es una proporción: sube si entra agua o si el petróleo cae más que el agua. Las dos lecturas son físicas y ninguna es el cierre del operador (el placebo de cierre acota ese canal), pero D2 no dice cuál de las dos domina; lo mide D3, con su regla fijada tras ver D2, en `causal_profundo.md`.
- La pretendencia de D1 no es plana: el mes -1 vale -10,0 puntos (IC 95%: -21,3 a -1,4). Los cercanos que se tratan antes ya venían cayendo respecto de los que se tratan después.
- Solo cuenta la primera fractura a menos de 1 km de cada padre: los golpes siguientes no se miden acá.
- La elección del control importa para el petróleo: con aún no tratados ATT(1) = -25,8, sumando los nunca tratados -28,4, y los nunca tratados con fechas sorteadas ya dan -8,0 puntos sin ninguna fractura cerca.
- Un hijo sin fecha de fractura cargada no cuenta como golpe: un control puede tener uno cerca sin que se vea.
- La regla fijada no le asigna a D2 el placebo de nunca tratados, el que rompe D1. Se corrió después, fuera de la regla, sobre el corte de agua, y no rompe (renglón de D3 del resumen y `causal_profundo.md`): es una prueba aparte, no parte del veredicto de D2.
- Tratado y control se definen por la distancia entre bocas de pozo, no entre ramas: según `trayectorias.md`, parte de los pares cercanos tiene las ramas a 1 km o más y parte de los pares de control las tiene a menos de 1 km. Ese error de clasificación lleva sobre todo hacia cero, pero el placebo de distancia falsa también se mide entre bocas.
- Los IC no tienen ajuste por comparaciones múltiples; el veredicto sale de una sola cantidad por diseño, fijada antes.

## Qué datos cambiarían la conclusión

| Dato | Para qué | Dónde estaría |
| --- | --- | --- |
| Presión de boca o de fondo del padre durante la fractura del hijo | Prueba física directa de comunicación; D2 dejaría de depender del agua | Operadoras (no es público) |
| Producción diaria y motivo de cada parada | Separa un cierre preventivo de un golpe dentro del mes | Operadoras; la Secretaría publica el mes y el estado |
| Cronograma de etapas de la fractura del hijo | Fija el tratamiento al día y la dosis por etapa | Carga de fractura detallada |
| Trayectorias 2024 y 2025 | La lectura por posición cubre sobre todo 2016 a 2023 | Secretaría (carga pendiente) |
| Trazadores químicos o análisis de agua producida | Confirma qué agua viene de la fractura del hijo | Operadoras |
| Producción hasta el abandono, o más años de datos | EUR real en lugar del sustituto de 24 meses; muestra para D1b | Tiempo |

## Reproducir

```
uv run python -m pipeline.build
uv run python -m pipeline.trayectorias
uv run python -m pipeline.causal
uv run python -m pipeline.wiki
```
