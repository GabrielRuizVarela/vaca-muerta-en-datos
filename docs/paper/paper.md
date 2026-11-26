# La huella de una fractura nueva en los pozos vecinos de Vaca Muerta: un estudio de eventos con datos públicos

## Resumen

Medimos qué les pasa a los pozos que ya producían (los padres) cuando se fractura un pozo nuevo (el hijo) a menos de 1 km.
Usamos solo el dato público mensual de la Secretaría de Energía, en toda la cuenca: 2.094 eventos.
Primero, el padre deja de producir días: el mes de la fractura, entre 79 y 88% de la caída son días sin producir: dos maneras de contar, sin y con los meses en que el padre estuvo cerrado todo el mes.
Así se vería un cierre preventivo del operador.
Después rinde menos por día.
Un mes después de la fractura, los padres rinden entre 19 y 23 puntos menos que pozos de control a 2 a 5 km.
Cerca de la mitad de la caída del volumen ya es menos petróleo por día producido.
A los 6 meses la brecha baja a menos de 5 puntos, pero con medias de logaritmos el intervalo de la brecha del volumen todavía queda entero por debajo de cero: no está probado que el petróleo que falta llegue después.
El agua sigue arriba, a cerca de la mitad del pico: el corte de agua del padre sube 13,8 puntos porcentuales en el mayor de los meses 0 y 1 (447 padres) y sigue arriba en los meses 6 a 12.
La caída del petróleo es una huella medida, no una causa demostrada.
La suba del agua es causal con supuestos nombrados; medida mes a mes (no como el mayor de dos meses), aguanta una cota de Rambachan y Roth del tamaño del mayor salto previo, sigue cuando la serie se corta en la segunda fractura a menos de 1 km, se repite en Colorado, donde no depende de un solo operador pero no es pareja entre ellos (con los pozos de PDC, el de más tratados, no se distingue de cero; Wyoming no permite probarla), y en Vaca Muerta depende de los pozos de YPF.
El dato mensual no separa un cierre preventivo de un daño; los datos diarios y los registros de cierres de un operador sí. Una parte del estudio corre en su máquina sobre su dato mensual: la brecha del estudio de eventos, el modelo de dosis y, como lee el agua mensual opcional, el diseño del corte de agua. No parte la caída en días y caudal, y todavía no lee el diario ni los cierres.

## 1. Pregunta

Cuando se fractura un pozo nuevo (el hijo), ¿los pozos vecinos que ya producían (los padres) rinden menos que pozos parecidos más lejos? La pregunta se responde solo con datos abiertos, y el trabajo dice qué se puede afirmar con ellos y qué no.

## 2. Datos

- **Producción.** Datos abiertos de la Secretaría de Energía: 436.309 filas de producción mensual por pozo no convencional. No hay producción diaria ni cierres declarados.
- **Fracturas y ubicación.** La fecha de cada fractura y las coordenadas de superficie del pad. La trayectoria de la rama y el espaciamiento real no están en el dato principal.
- **Eventos.** 2.094 eventos de fractura de un pozo hijo.
- **Padres.** Pozos que ya producían a menos de 1 km del hijo.
- **Controles.** Pozos a 2 a 5 km de un pozo hijo.

Lo que el dato no tiene define lo que el estudio no puede decir: con datos mensuales, un cierre preventivo del operador y un daño en el pozo se ven iguales, y ninguna fuente dice por qué cambió el caudal de un pozo.

## 3. Método

**Estudio de eventos.** Cada pozo se mide contra su propio caudal previo, así que se comparan niveles relativos y no volúmenes. La brecha es la mediana del índice de los padres menos la de los controles, mes a mes, con k = 0 en el mes de la fractura. Los intervalos de 95% son bootstrap por pads hijo; el de la brecha del mes 1 es además bootstrap por bloques espaciales de 5 km, y es el que se informa.

**Pretendencia.** Se miran los meses previos a la fractura. Si los padres cercanos ya venían por debajo, la brecha del mes 1 en bruto es una cota superior contra el control de 2 a 5 km, no contra cualquiera, y no el valor.

**Placebo y permutación.** La fecha de fractura se corre medio año y un año, antes y después, y se vuelve a medir. Además, las fechas se permutan 200 veces entre hijos del mismo año. Si la brecha saliera de cómo se mide, aparecería también con fechas que no son las reales.

**Efectos plantados.** Sobre datos reales con fechas falsas se planta una caída conocida y se mira si el estimador la devuelve. Una caída plantada de 20% del caudal (unos -17,4 puntos del índice) se recupera, descontado el mundo nulo, como -17,3 puntos; se cumplen 5 de las 5 reglas fijadas de antemano, y la de falsos positivos da 2 de 30 mundos.

**Reglas fijadas antes de correr.** Cada módulo que da un veredicto tiene su regla escrita antes de calcular su propia cifra: muestra, estadístico, umbrales y veredictos posibles, con su fecha y lo que se había mirado antes. Ejemplos:

- El día de inicio como dosis: regla fijada en el commit `d370e0b`, antes de calcular ninguna cifra de ese estudio.
- La replicación por cuenca: la misma regla para cada cuenca, fijada antes de bajar o medir nada de Wyoming.
- El mecanismo por la geometría de las ramas: regla fijada en el commit `bddf1e0771`.
- El diseño causal con controles aún no tratados: regla fijada en el commit `8f52ff1`.

Hubo desvíos, y cada página los declara: dos arreglos de implementación en el commit siguiente al de la regla de `causal.md`, sin tocar constantes ni umbrales; en `causal_profundo.md`, el mínimo de dos meses base del agua por día producido se eligió al calcular, no lo fijó la regla; y una corrección de código posterior a la regla, en `operador-datos-propios.md`. Varias reglas se fijaron conociendo cifras anteriores del estudio, y lo dicen: la de `causal_profundo.md` se fijó conociendo la caída del petróleo, y por eso decide con el agua.

**Agregado después de ver resultados (marcado así).** Algunas pruebas se escribieron después de ver un resultado anterior del estudio. "Fijado después" quiere decir eso: la regla se fijó después de ver una cifra anterior y antes de calcular la cifra propia de la prueba. Salvo la cota de Rambachan y Roth y las permutaciones de D2, todas las de abajo están en la familia confirmatoria de Holm (sección I3 de [`inferencia.md`](../../wiki/hallazgos/inferencia.md)); lo de abajo dice qué se había visto antes de fijar cada regla:

- *Fijado después:* la descomposición del agua por día producido (D3, en el diseño causal), tras ver D2.
- *Fijado después:* la dosis del diseño causal (D4: distancia y agua de fractura del hijo), tras ver D2.
- *Fijado después:* la forma en el tiempo del corte de agua (D5) y su dependencia por operador (D6), tras ver D2 y D3.
- *Fijado después:* el diseño causal repetido en Colorado (D7), tras ver D2 y antes de calcular el agua de esa cuenca. La regla de Wyoming (D9) se fijó igual, tras ver D2 y D7.
- *Fijado después:* la suba del agua en Colorado sin cada uno de sus operadores (D13), tras ver D6 y D7, con la regla escrita antes de calcularla (commit `a1f1fee`).
- *Fijado después:* la serie del agua cortada en la segunda fractura a menos de 1 km (D10), tras ver D2 y D5, con la regla escrita antes de calcularla (commit `857d434`).
- *Fijado después:* el estimador apilado del petróleo (E), con su regla escrita antes de calcularlo (commit `857d434`).
- *Fijado después:* la misma pila con donantes a 2 a 10 km (E2), tras ver E sin muestra, con la regla escrita antes de calcularla (commit `82d58c0`).
- *Fijado después:* D2 con el golpe definido por la distancia entre ramas, de 2016 a 2023 (D14), tras ver D2 y D11, con la regla escrita antes de calcularla (commit `5002094`, con una aclaración en `f1b1e08`, también antes).
- *Fijado después, fuera de la familia de Holm:* la cota de Rambachan y Roth sobre D1 y D2, con su regla escrita antes de calcularla (commit `857d434`). Es un análisis de sensibilidad de esos dos diseños y no tiene prueba propia.
- *Fijado después, fuera de la familia de Holm:* la permutación dentro de las celdas de D2 (I4), tras ver la permutación por estratos, con la regla escrita antes de calcularla (commit `19415b3`).
- *Fijado después, fuera de la familia de Holm:* la permutación por pad padre dentro de las celdas de D2 (I5), tras ver I4, con la regla escrita antes de calcularla (commit `052ee98`).

Las pruebas del libro suman 193: 17 hipótesis con umbral fijo, 13 subconjuntos de robustez que se publican aunque debiliten el resultado, 141 intervalos de la descomposición, 9 intervalos descriptivos del lado del hijo y 13 intervalos por bloques que no son hipótesis. No entran en esa cuenta los diseños causales, con sus placebos y cortes, ni las escalas de bloques ni las permutaciones de D2: se cuentan aparte en [`inferencia.md`](../../wiki/hallazgos/inferencia.md). Los 19 diseños causales forman una familia ajustada con Holm: 7 rechazan cero (D1, D2, D3, D5, D7, D10 y D13; D1 igual no sobrevive a su placebo) y los 9 sin muestra entran con p = 1. De los 141 intervalos de la descomposición, 90 excluyen cero sin ajuste y 36 siguen excluyéndolo con Holm dentro de esa familia ([`inferencia.md`](../../wiki/hallazgos/inferencia.md)). D3 entra con el agua por día producido, la cifra que usa su veredicto; la familia lo leía con el agua por día calendario, y el cambio se fijó en el commit `19415b3`, después de ver ese p. La permutación de las etiquetas dentro de cada celda de D2 (I4) da p = 0,0005, el mínimo con 2.000 permutaciones; entre los percentiles 2,5 y 97,5 su distribución nula va de -2,3 a 2,4 pp, centrada en cero, contra 13,8 la real. Reemplaza como prueba a la permutación por estratos de bloque, año y edad, en la que solo se mezclaba el 8,0% de las observaciones y cuya distribución nula no estaba centrada en cero. Repartida por pad padre (I5), con los pozos de un mismo pad juntos, el p sigue en el mínimo (0,0005), pero la nula ya no está centrada en cero: entre los percentiles 2,5 y 97,5 va de 3,2 a 9,5 pp, con media 6,4, porque solo se mezcla el 38,5% de las observaciones; 13,8 queda por encima de toda esa franja. Como la permutación por estratos, es una prueba débil y se lee así.

## 4. Resultados

### 4.1 La brecha del mes 1

Un mes después de la fractura, los padres a menos de 1 km rinden entre 19 y 23 puntos menos que los controles a 2 a 5 km. El 23 es el valor en bruto (-23,0 puntos con la base de los meses -3 a -1) y una cota superior contra este control (2 a 5 km), no contra cualquiera: contra el anillo de 5 a 10 km la brecha del mes 1 es -24,6 puntos. El 19 descuenta la brecha previa. El IC 95% por bloques espaciales de 5 km (145 bloques) de la brecha de -23,0 va de -30,0 a -17,0 puntos.

Antes de la fractura ya hay una brecha: -2,5, -3,6 y -6,3 puntos en los meses -3, -2 y -1, con la base de los meses -6 a -4. Con datos mensuales no se separa un nivel distinto de los padres cercanos de un efecto anticipado.

A los 6 meses la brecha casi se cierra: -2,1 puntos en el mes 6. No está probado que la producción que falta llegue después.

Figura: [`docs/img/caso_event_study.svg`](../img/caso_event_study.svg), la brecha de petróleo por mes desde la fractura del hijo.

### 4.2 De qué está hecha la brecha

La caída del volumen del padre se parte en dos: días sin producir y menos petróleo por día producido.
Las medianas no se suman, así que la partición usa medias de logaritmos sobre los mismos eventos, con base en los meses -6 a -4.
Los puntos de estas tablas son puntos logarítmicos: 100 veces la diferencia de logaritmos naturales.
No son los puntos del índice de la sección 4.1.
La parte de los días es la brecha de los días sobre la del volumen.
Es una parte de la brecha del volumen en medias de logaritmos y no una parte de los 19 a 23 puntos.

Con los meses cerrados enteros, con los días acotados a un día de 30:

| k | Eventos cercanos | Brecha del volumen (IC 95%) | Días efectivos (IC 95%) | Caudal por día (IC 95%) | Parte de los días (IC 95%) |
| ---: | ---: | --- | --- | --- | --- |
| 0 | 2.040 | -51,0 (-60,1 a -42,6) | -45,1 (-53,2 a -37,0) | -5,9 (-11,8 a -0,9) | 88% (78% a 98%) |
| 1 | 2.037 | -72,8 (-84,6 a -61,2) | -38,1 (-47,2 a -30,3) | -34,6 (-44,1 a -25,4) | 52% (44% a 61%) |
| 2 | 2.039 | -45,2 (-57,7 a -33,6) | -14,7 (-21,6 a -8,3) | -30,6 (-40,5 a -21,1) | 32% (21% a 45%) |
| 6 | 1.944 | -9,4 (-17,9 a -1,2) | -0,2 (-5,5 a 5,9) | -9,2 (-16,1 a -2,6) | 2% (-183% a 50%) |

Sin los meses cerrados enteros:

| k | Eventos cercanos | Brecha del volumen (IC 95%) | Días efectivos (IC 95%) | Caudal por día (IC 95%) | Parte de los días (IC 95%) |
| ---: | ---: | --- | --- | --- | --- |
| 0 | 1.863 | -37,2 (-46,5 a -29,9) | -29,2 (-35,4 a -24,2) | -8,0 (-14,5 a -2,6) | 79% (67% a 92%) |
| 1 | 1.886 | -66,5 (-77,4 a -53,8) | -27,9 (-33,4 a -22,5) | -38,6 (-47,3 a -28,0) | 42% (36% a 51%) |
| 2 | 1.927 | -43,5 (-55,0 a -31,9) | -10,7 (-15,0 a -6,4) | -32,8 (-42,7 a -23,3) | 25% (17% a 33%) |
| 6 | 1.831 | -11,4 (-20,2 a -3,5) | -1,7 (-5,2 a 1,8) | -9,7 (-17,0 a -2,4) | 15% (-28% a 45%) |

El mes de la fractura, entre 79 y 88% de la caída del volumen son días sin producir: dos maneras de contar, sin y con los meses en que el padre estuvo cerrado todo el mes.
El 79% es sin los meses cerrados enteros y el 88% es con ellos.
En el mes 1 la parte baja a entre 42 y 52%, y el resto es menos petróleo por día producido.
La variante con cerrados depende del piso de un día, por eso se muestran las dos.
A los 6 meses los intervalos de la parte son muy anchos y no se leen.

Así se vería un cierre preventivo del operador.
El dato mensual no separa un cierre de un daño en el pozo.

### 4.3 El corte de agua

El corte de agua es el agua sobre el agua más el petróleo.
Se mide con el diseño causal: la primera fractura de un hijo a menos de 1 km, con controles aún no tratados.
Sube si entra agua o si cae el petróleo con el agua quieta, así que se miden los dos volúmenes por separado.
Cada fila lleva su rótulo: la regla de D2 se fijó antes de calcular ninguna cifra del agua; cada una de las otras se fijó antes de calcular su propia cifra y después de ver las que nombra el rótulo.

| Prueba | Qué mide | Cifra | IC 95% | Tratados | Rótulo |
| --- | --- | ---: | --- | ---: | --- |
| D2 | Corte de agua, el mayor de los meses 0 y 1 | 13,8 pp | 9,5 a 19,9 | 447 | regla fijada antes |
| D3 | Agua por día calendario | 4,8 puntos del líquido base | -0,1 a 12,3 | 468 | tras D2, antes de su cifra |
| D3 | Agua por día producido | 19,5 puntos del líquido base | 12,8 a 29,2 | 434 | tras D2, antes de su cifra |
| D5 | Corte de agua, media de los meses 6 a 12 | 10,9 pp | 7,7 a 15,0 | 297 | tras D2 y D3, antes de su cifra |
| D6 | Corte de agua sin los pozos de YPF | 7,1 pp | -0,6 a 18,1 | 129 de 447 | tras D2 y D3, antes de su cifra |
| D6 | Corte de agua solo con los pozos de YPF | 17,5 pp | 11,6 a 24,5 | 255 | tras D2 y D3, antes de su cifra |
| D7 | Corte de agua en Colorado | 9,0 pp | 6,3 a 12,1 | 1.247 | tras D2, antes del agua de la cuenca |
| D13 | Corte de agua en Colorado sin el operador que más lo baja | 7,5 pp | 5,1 a 9,9 | 1.140 de 1.247 | tras D6 y D7, antes de su cifra |
| D9 | Corte de agua en Wyoming, sin muestra | 6,7 pp | -0,7 a 13,4 | 38 | tras D2 y D7, antes del agua de la cuenca |
| D10 | Corte de agua, media de los meses 6 a 12, con la serie cortada en la segunda fractura a menos de 1 km | 10,5 pp | 6,8 a 15,4 | 241 | tras D5, antes de su cifra |
| D14 | Corte de agua con el golpe por distancia entre ramas (2016 a 2023), sin muestra | 13,3 pp | 6,2 a 23,0 | 114 | tras D2 y D11, antes de su cifra |

Las cifras de D2, D5, D6, D7, D9, D10, D13 y D14 son puntos porcentuales (pp) de corte de agua.
Las de D3 son puntos del líquido de la base de cada padre.

**D2 y D3.** En los días que el padre produce, sale más agua por día: entra agua.
Por día calendario la suba no alcanza a separarse de cero.
D3 se fijó después de ver las cifras de D2.

**D5.** La suba no se cura en 12 meses.
La media de los meses 6 a 12 queda sobre cero.
En la serie por mes cortada en la segunda fractura a menos de 1 km (D10), la suba es de +17,8 pp en el mes 1 y de +8,4 a +8,9 pp en los meses 10 a 12: un año después sigue arriba, a cerca de la mitad del pico.
Los intervalos de esos meses se superponen y no se corrió una prueba de la baja.
El 42% de los tratados recibe otro golpe a menos de 2 km en los meses 2 a 12.
La serie mide la primera fractura y lo que vino después, no la primera sola.

**D10.** Sin los golpes siguientes a menos de 1 km, la suba sigue.
Si la serie de cada padre se corta cuando recibe otra fractura a menos de 1 km, la media de los meses 6 a 12 sigue en 10,5 pp: el veredicto es persiste.
Salen de la serie antes del mes 12 62 de 341 tratados a 1 km y 142 a 2 km.
La censura no es al azar: los padres de zonas de relleno reciben más hijos, así que D10 mide la primera fractura sola en los que no recibieron otra a menos de 1 km. Cortada a 2 km, la serie queda con 169 tratados como mínimo, menos que los 200 que pide la regla, y se publica sin veredicto.
La regla se fijó antes de calcular D10, después de ver D5.

**D6.** La suba depende de YPF.
Sin sus pozos el IC incluye cero.
Con 129 tratados el IC es ancho: el dato no muestra la suba fuera de YPF ni la descarta.
Las reglas de D5 y D6 se fijaron antes de calcular sus cifras, pero después de ver D2 y D3.

**D7.** El diseño se repite en Colorado y da el mismo veredicto.
La prueba se agregó después de ver Vaca Muerta, y su regla se fijó antes de calcular el agua de Colorado.

**D13.** En Colorado la suba no depende de un solo operador.
La regla se fijó en el commit `a1f1fee`, después de ver D6 y D7 y antes de calcular ninguna cifra de D13: sacando de a uno los 7 operadores que tienen 50 tratados o más, el IC tiene que seguir sobre cero.
Sigue sobre cero sin cualquiera de ellos; el más bajo es sin Bonanza Creek, con 7,5 pp (IC 5,1 a 9,9, 1.140 tratados).
Con los pozos de un solo operador, el IC incluye cero en 2: PDC y Prairie.
PDC es el operador con más tratados (342) y solo da 3,6 pp (IC -0,9 a 8,1): la suba de Colorado no es pareja entre operadores.

**D9.** Wyoming no permite probarla.
El diseño queda con 38 tratados con el corte de agua medido, menos que los 300 que pide la regla, así que queda sin muestra.
Da 6,7 pp (IC -0,7 a 13,4), una cifra que no se lee como resultado.
La regla se fijó en el commit `f29014a`, después de ver D2, D7 y el petróleo de Wyoming y antes de calcular ninguna cifra de agua de Wyoming.

**D14.** Con el golpe definido por la distancia entre ramas queda sin muestra.
Un padre es tratado si la rama de un hijo pasa a menos de 250 m de la suya, de 2016 a 2023, los años con ramas medidas; un control no tiene, desde un año antes del golpe hasta seis meses después, un par medido a menos de 1.000 m ni un hijo cercano sin rama medida (antes de esa ventana puede haberlo tenido).
Quedan 114 tratados con el corte de agua medido, menos que los 300 que pide la regla.
Da 13,3 pp (IC 6,2 a 23,0), una cifra sin veredicto; D2 en esos mismos años, con el golpe por boca de pozo, da 15,1 pp (IC 10,5 a 20,3, 290 tratados).
Los dos golpes marcan sobre todo padres distintos: entre los tratados de celdas con controles, 64 lo son con las dos definiciones, 65 solo con la de ramas y 242 solo con la de boca de pozo.
Esos recuentos incluyen a los tratados que no entran a la estimación, sin el corte de agua medido o en celdas sin suficientes controles que lo tengan; por eso suman más que los tratados de arriba.
La regla se fijó en el commit `5002094`, con una aclaración en `f1b1e08`, después de ver D2 y D11 y antes de calcular ninguna cifra de D14.

**Cota de Rambachan y Roth.** Pregunta cuánto tendría que saltar el sesgo de un mes al siguiente después de la fractura, contra el mayor salto previo (Mbar), para que el efecto deje de distinguirse de cero.
El mes 1 solo (15,6 pp, 413 tratados) sigue distinto de cero en toda la grilla, hasta Mbar = 2.
La media de los meses 0 y 1 (9,7 pp, 410 tratados) deja de distinguirse de cero recién con Mbar = 1,62.
El mayor de los meses 0 y 1 de D2 no es lineal en el efecto y no lleva esta cota.
La regla se fijó antes de calcular la cota (commit `857d434`).

La causa vale bajo los supuestos del diseño causal.
Son tendencias paralelas condicionales a cohorte y edad, sin anticipación más allá de 3 meses y sin derrame sobre los controles a 2 km.
No es un hecho físico medido: el agua se ve en el volumen mensual, no entrando.

### 4.4 Placebo y permutación

- Con fechas falsas, la brecha del mes 1 va de -2,4 a 0,5 puntos y todos los intervalos incluyen el cero.
- Con 200 permutaciones, va de -8,1 a -4,9 puntos (media -6,4), contra -23,0 la real. La media no es cero, así que el valor p que sale de ahí es un piso y no una probabilidad exacta.

Pasar estas pruebas descarta una brecha que aparezca en cualquier fecha. No demuestra causalidad ni separa un daño de un cierre preventivo.

### 4.5 El día de inicio no sobrevive a su placebo

Si la fractura le cuesta al padre, un inicio el día 3 del mes debería pesar más en el mes 0 que uno el día 27. Entre padres cercanos la pendiente es de -2,7 puntos de índice por cada 0,1 del mes expuesto (IC 95% por bloques de 5 km: -4,3 a -1,6), sobre 2.044 eventos cercanos.

Pero la misma pendiente aparece donde no hay exposición. Los controles dan -0,4 (IC -0,7 a -0,1), la fecha falsa de 6 meses antes da 1,1 (IC 0,2 a 2,1), y los días sorteados dan un p bilateral de 0,005. Veredicto contra la regla fijada: **no sobrevive a su placebo**. La pendiente no se separa del calendario o de la selección y no se lee como dosis. Lo publicamos igual: un resultado que no pasa su propia regla también informa.

### 4.6 Replicación en otras cuencas

Con el mismo estimador, los mismos filtros y una regla fijada de antemano, la brecha del mes 1 **se replica en 1 de 2 cuencas**:

| Cuenca | Eventos cercanos | Brecha del mes 1 (puntos) | IC 95% por bloques de 5 km | Brecha previa, mes -1 | Lectura |
| --- | ---: | ---: | --- | ---: | --- |
| Colorado (cuenca DJ) | 3.691 | -19,9 | -27,5 a -14,8 | -6,9 | se replica |
| Wyoming | 353 | -2,5 | -5,5 a 2,2 | -11,9 | no se replica |

En Wyoming el intervalo incluye cero y la brecha previa es mayor que la del mes 1. Las cuencas no miden lo mismo: la fecha del hijo es el inicio de fractura en Colorado y la primera terminación del regulador en Wyoming. No hay promedio ni estimación conjunta: con dos cuencas, la lectura no separa una huella que depende de la cuenca de una que se mide con más ruido en una de ellas.

## 5. Qué no afirmamos

- **No afirmamos una causa para la caída del petróleo.** Es una huella medida contra un control. Con datos mensuales, un cierre preventivo del operador y un daño se ven iguales. Con controles que van a recibir un hijo más tarde, la caída del mes 1 deja de distinguirse de cero si el sesgo salta 0,20 veces el mayor salto previo (cota de Rambachan y Roth). Un estimador apilado con controles limpios da -15,0 puntos al mes 1 (IC -26,7 a -4,6; en los meses -3, -2 y -1 da +8,1, +10,2 y +7,4, con IC que incluyen cero), pero queda sin muestra: 81 eventos en 26 bloques, contra un mínimo de 300 y 30. Con donantes a 2 a 10 km (E2, regla fijada antes de calcularla) entran 210 eventos en 44 bloques, con mejor balance después del emparejamiento que E, y da -21,9 puntos (IC -30,6 a -13,4); también queda sin muestra, porque la regla pide 300 eventos, y deja de distinguirse de cero con Mbar = 0,51.
- **No damos un tamaño de efecto para un operador.** La brecha es una mediana sobre muchos eventos; el modelo de costo no predice un evento (R2 fuera de muestra de -0,18, contra -0,03 de predecir la media del área), y el riesgo de un golpe fuerte tampoco se predice con estos datos.
- **No afirmamos que la producción vuelva toda.** A los 6 meses la brecha es chica, pero no es cero. E2, sin muestra, da 11,9 puntos al mes 6 (IC 1,3 a 21,8): ahí el padre golpeado rinde más que sus controles. Como E2 no tiene muestra, esa cifra no decide nada; la damos porque arriba damos la de su primer mes.
- **No afirmamos que la huella valga fuera de Vaca Muerta.** Se replica en una cuenca de dos.
- **No afirmamos que la suba del agua sea física nueva.** Depende de los pozos de YPF: sin ellos el intervalo incluye cero.

## 6. Limitaciones

- **Brecha previa.** Los padres cercanos ya rinden menos antes de la fractura; por eso se da un rango (19 a 23) y no un número.
- **Control que no es un cero limpio.** Los pozos del anillo de 5 a 10 km rinden 2,9 puntos más que los de 2 a 5 km (con la base de los meses -6 a -4; prueba agregada después de ver resultados); contra el anillo la brecha del mes 1 es -24,6 puntos. Si el control habitual está también afectado, lo que se mide contra él queda corto.
- **Sin trayectorias en el dato principal.** La distancia es entre superficies, no entre ramas.
- **Sin producción diaria ni cierres declarados.** No se separa un golpe de un cierre dentro del mes.
- **Permutación con media distinta de cero.** El valor p de la permutación es un piso.
- **Pruebas múltiples.** Parte de los intervalos no tiene ajuste por comparaciones múltiples.
- **Dos cuencas de replicación**, que además fechan el evento de forma distinta.

## 7. Reproducibilidad

**Código:** el código y el libro de hipótesis son públicos en https://github.com/GabrielRuizVarela/vaca-muerta-en-datos, una copia de un solo commit. Cada regla fijada cita el commit en que se fijó; ese historial de trabajo no se publica y se comparte con quien lo pida; `docs/reglas-fijadas.md` conserva la fecha, el asunto y el texto de cada regla citada. Cada cifra con claim se recalcula del warehouse con `pipeline.claims`, que falla si alguna cambia; la prueba de cifras sueltas exige un claim para cada número del README, del resumen para el operador, de `limites.md`, del caso y de este paper. Las cifras de otros trabajos no se recalculan: llevan su fuente. Los datos de entrada son públicos.

## 8. Referencias internas

- [Caso de estudio, con figuras y cada cifra verificada](../caso-interferencia.md)
- [Arquitectura y reglas fijadas antes de correr](../arquitectura.md)
- [Hallazgo de interferencia, con su historial por versión de datos](../../wiki/hallazgos/interferencia.md)
- [Placebo](../../wiki/hallazgos/placebo.md)
- [Efectos plantados](../../wiki/hallazgos/inyeccion.md)
- [El día de inicio como dosis](../../wiki/hallazgos/dia_inicio.md)
- [Replicación por cuenca](../../wiki/hallazgos/replicacion_cuencas.md)
- [Mecanismo por la geometría de las ramas](../../wiki/hallazgos/mecanismo.md)
- [Diseño causal](../../wiki/hallazgos/causal.md)
- [Causal profundo: entra agua o sale petróleo](../../wiki/hallazgos/causal_profundo.md)
- [Descomposición de la brecha](../../wiki/hallazgos/descomposicion.md)
- [Libro de hipótesis](../../wiki/hallazgos/libro.md)
- [Plan del estudio del día de inicio](../plan-dia-inicio.md)
