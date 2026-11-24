# Plan: el día del mes en que empieza la fractura como dosis

Fecha: 2026-11-23. Rama `t3/study-a-daily-dose`, que sale de `origin/main` en f7a3746. La regla es el primer commit de la rama:
esta página y `pipeline/dia_inicio.py` (cabecera, constantes y funciones de veredicto sin datos) con sus pruebas sobre números
inventados, sin ninguna cifra calculada del estudio nuevo. Después de ese commit no se cambia: toda desviación va en su propia
sección fechada al final de esta página y en la del hallazgo.

## De dónde sale

El resultado principal del estudio dice que un mes después de la fractura de un hijo, los padres a menos de 1 km rinden 19 a 23
puntos menos de su caudal previo que los controles a 2 a 5 km. Toda la lectura depende de que los controles lejanos sean el
contrafactual de los cercanos, y esa duda aparece de cuatro formas distintas (brecha previa, medianas sin emparejar, fechas
permutadas, nunca tratados). Esta prueba usa una sola cosa que el diseño no necesita lejos: **cuánto del mes del padre expone la
fractura**. Una fractura que empieza el día 3 expone casi todo el mes 0 del padre; una que empieza el día 27 casi nada; y nadie
elige el día pensando en la cifra mensual del padre. Se compara entonces cada padre cercano con padres cercanos, por esa fracción
del mes. Una caída causada por la fractura crece con la fracción; una brecha que ya estaba (selección, pozos distintos) no.

Qué se sabía al fijar esta regla (regla informada): `pipeline/sincronia.py` ya corrió, con regla fijada el 2026-11-15, la pendiente
de la brecha cercano menos control sobre la misma fracción del mes: -2,1 puntos por cada 0,1 (IC por pads -3,3 a -0,8), -0,7
(IC -1,9 a 0,6) el mes anterior y terciles de brecha -14,5, -22,1 y -32,4 puntos. Lo que esta regla agrega, y no estaba:
(a) el estimador usa solo padres cercanos, sin ningún control lejano en la pendiente; (b) el IC es por bloques de 5 km como el
titular; (c) el equilibrio del día de inicio frente a operador, edad del padre y caudal base; (d) tres pruebas negativas
(pozos de control, fechas falsas, días sorteados); (e) el tercio monótono; (f) la lectura del intercepto; (g) un umbral de
magnitud que el de `sincronia` (2 puntos entre el primer y el último día) no tiene; (h) Colorado. La corrida del estudio nuevo
no se vio antes de fijar esta regla: nadie calculó la pendiente solo de cercanos ni ninguna de las pruebas (b) a (h).

## Variable de exposición

- Cada hijo tiene su primera fecha de inicio de fractura en el mes 0 (`stg_fractura.fecha_inicio`, la misma que fija
  `int_frac_hijo.mes_frac`) y su fecha de fin (`fecha_fin`).
- **f0 = (días del mes - día de inicio + 1) / días del mes**, con los días reales del mes (28, 29, 30 o 31). Cuenta el día de
  inicio como expuesto. Un inicio el día 1 da f0 = 1; el último día da 1 / días del mes. Es la misma definición que
  `pipeline.sincronia.fraccion_mes0`, y se reusa esa función.
- Sensibilidad sin veredicto: **fd** = días del mes entre el día de inicio y el menor entre el día de fin y el último día del mes,
  contados los dos extremos, sobre los días del mes (la exposición mientras dura la fractura). Solo con hijos cuya fecha de fin
  es posterior o igual a la de inicio. Se publica su pendiente y su IC; no entra en el veredicto.
- Cada evento (padre, mes 0) hereda la f0 del hijo más cercano, el mismo que fija su banda.

## Muestra

- Eventos de `pipeline.placebo.marco` con la base limpia (meses -6 a -4, la de `sincronia`), con los mismos filtros del titular:
  padre con al menos 6 meses de producción al mes de la fractura, base original (meses -3 a -1) y base limpia mayores que 1 m3/d.
- **Cercanos: menos de 1 km del hijo más cercano.** Esos son la muestra de la prueba. Los controles (2 a 5 km) no entran en la
  pendiente; solo en la prueba negativa de pozos de control y en la lectura del intercepto.
- Resultado de un evento: índice de petróleo del mes 0 (caudal por día sobre la media de su base), acotado a [0, 2].

## Estimador

- Regresión de mínimos cuadrados del índice del mes 0 sobre f0, con efectos fijos de área y de año de fractura (los mismos de
  `sincronia`), solo con eventos cercanos. El coeficiente de f0 es la pendiente, en índice por unidad de f0 (de 0 a 1). Se
  publica en puntos por cada 0,1 de f0 (diez veces la pendiente por unidad, en puntos) y el cambio entre un inicio el último
  día y uno el primer día (cien veces la pendiente por unidad, en puntos).
- IC 95%: bootstrap de percentiles (2,5 y 97,5) de 400 repeticiones (`REPS_BOOT`), remuestreando **bloques de 5 km** completos con
  reemplazo (`pipeline.bloques.clave_bloque` sobre el promedio de lat y lon del pad hijo). Semilla del titular para k = 0:
  SEMILLA_PLACEBO + 100 + posición de 0 en KS_PRE. Una remuestra con menos de 5 eventos cercanos se descarta.
- Una dosis en el tiempo es una pendiente **negativa**: más caída cuanto mayor es f0.

## Chequeos de equilibrio (sobre los eventos cercanos de la muestra)

El supuesto que la prueba necesita es que el día del mes en que empieza la fractura no está relacionado con la tendencia del padre.
No se puede observar la tendencia sin la fractura; sí se puede mirar lo observable.

1. **Operador del hijo:** eta cuadrado de f0 contra el operador del hijo (suma de cuadrados entre grupos sobre la total). Los
   operadores con menos de 50 eventos cercanos se juntan en "otros". Equilibrado si eta cuadrado < 0,10 (`MAX_ETA2`).
2. **Edad del padre al mes 0** (meses desde su primer petróleo): correlación de Spearman con f0. Equilibrada si el valor absoluto
   es < 0,10 (`MAX_RHO`).
3. **Caudal base del padre** (media de los meses -6 a -4, en logaritmo): correlación de Spearman con f0. Equilibrada si el valor
   absoluto es < 0,10.
4. Se publica además, sin veredicto propio, la tabla de f0 media y la parte de eventos con f0 mayor que 0,9 (inicio los tres primeros
   días del mes) por operador con 50 eventos o más.
5. **Pendiente ajustada (especificación C):** la regresión principal más efectos fijos del operador del hijo, grupo de edad del
   padre (menos de 12, 12 a 24, 24 a 48, 48 meses o más) y el logaritmo del caudal base. Mismo IC por bloques. Condición del veredicto:
   su límite superior es menor que 0.
6. **Sin cada operador grande:** la pendiente principal sin los eventos de cada operador del hijo con 10% o más de los eventos
   cercanos. Condición del veredicto: en cada una el límite superior del IC es menor que 0.

## Chequeos negativos

Los dos deben dar cero; si no, la pendiente del mes 0 no se lee como dosis.

1. **Pozos de control:** la misma regresión (misma especificación, mismos efectos fijos, mismo IC por bloques de 5 km) con los
   eventos de control (2 a 5 km) y la f0 de su hijo más cercano. Un control no está expuesto: su pendiente tiene que ser cero.
2. **Fecha falsa:** la fecha de fractura de todos los hijos corrida -12 y -6 meses (`placebo.marco` con `solo_reales=True`, como
   `tabla_fechas`), el índice en el mes 0 de esa fecha falsa y f0 con el día de inicio real y los días del mes falso (el día se
   ajusta al último del mes si no existe). Los corrimientos hacia adelante (+6 y +12) **no** se usan: su base (meses -6 a -4 de la
   fecha falsa) cae en los meses 0 a 2 reales, que dependen de f0, y fabricarían una pendiente que no es calendario.
3. **Días sorteados:** 200 permutaciones (`N_PERM`, semilla SEMILLA_PLACEBO + 900) de f0 entre hijos con el mismo mes de fractura
   (el evento hereda la f0 sorteada de su hijo); se recalcula la pendiente principal en cada una. Se publican la media, el
   percentil 2,5 y el 97,5, y el p bilateral = (1 + cantidad de pendientes sorteadas con valor absoluto mayor o igual que la
   real) / 201.
- **Rompe** un chequeo de los puntos 1 y 2 si su IC excluye cero y el valor absoluto de la pendiente es al menos
  `RUPTURA_PLACEBO` = 0,025 por unidad de f0 (2,5 puntos entre el primer y el último día, la mitad del umbral de dosis). El de
  días sorteados rompe si el valor absoluto de la media de las pendientes sorteadas es al menos 0,0125 (la mitad de eso: el
  estimador estaría sesgado). Una fecha falsa con menos de 300 eventos cercanos queda "sin muestra" y no rompe.

## Tercio monótono

- Cortes: los terciles de f0 de los eventos cercanos. Grupo 1: f0 hasta el primer corte (inicio tarde, poca exposición); grupo 3:
  f0 mayor que el segundo corte (inicio temprano, mucha exposición).
- Por grupo: mediana del índice del mes 0 de los eventos cercanos y su n. Dosis monótona si mediana(1) > mediana(2) > mediana(3) y el
  IC de mediana(3) - mediana(1) (bootstrap por bloques de 5 km, semilla SEMILLA_PLACEBO + 800) tiene el límite superior menor que 0.

## Intercepto a exposición cero

- Se ajusta la misma regresión principal por separado a los cercanos y a los controles; el intercepto de cada grupo es el promedio
  de su predicción con f0 puesta en 0 sobre sus eventos (así los efectos fijos no dependen de la categoría base). **Brecha a
  exposición cero** = intercepto cercano menos intercepto control, IC por bloques de 5 km con los dos grupos remuestreados juntos
  (semilla SEMILLA_PLACEBO + 810).
- **Brecha previa de referencia:** el coeficiente de "cercano" en la regresión del índice del mes -1 (base limpia) sobre cercano,
  con los mismos efectos fijos, sobre los eventos de `sincronia.eventos(D, -1)`, con IC por bloques de 5 km. Es la brecha que el
  estudio mide antes de la fractura.
- Lectura, sin veredicto: la brecha a exposición cero **coincide con la previa** si los dos IC se superponen; es **más negativa
  que la previa** si el IC del intercepto queda entero por debajo del de la previa; **menos negativa** si queda entero por
  encima. Si coincide, la brecha previa es lo que hay en el mes 0 sin exposición y la parte que crece con f0 es lo que agrega la
  fractura. Si es más negativa, parte del cambio del mes 0 no depende del día de inicio.

## Colorado

- Mismo diseño, mismas constantes y mismas semillas sobre el warehouse opcional de Colorado (`pipeline.cuencas.COLORADO`,
  `pipeline.replicacion.preparar`): padres horizontales a menos de 1 km de un hijo de `co_hijo` sin fecha dudosa; la fecha es la
  de inicio de trabajo de la primera divulgación de FracFocus, que trae el día completo. Efectos fijos: condado (el área) y año
  de fractura. Sin fd (no hay fecha de fin en la tabla base) y sin la tabla de operador del hijo si el warehouse no lo trae.
- Se corren la pendiente principal, la de controles y los días sorteados. Fecha falsa y tercio monótono también.
- **Se repite** si el límite superior del IC de la pendiente de los cercanos es menor que 0 y los pozos de control no rompen.
  **No se repite** si el IC incluye cero o es positivo. **Sin muestra** si hay menos de `MIN_CERCANOS`, `MIN_BLOQUES` o `MIN_TERCIO`.
  **No corrido** si el warehouse de Colorado no se pudo armar con los datos públicos; se dice por qué y no se reemplaza.

## Tamaños mínimos

- Vaca Muerta y Colorado: 1.000 eventos cercanos (`MIN_CERCANOS`), 30 bloques de 5 km con eventos cercanos (`MIN_BLOQUES`, el
  mismo mínimo de `pipeline.bloques`), 300 eventos cercanos por tercio (`MIN_TERCIO`) y 3.000 eventos de control (`MIN_CONTROLES`).
  Para memoria: `sincronia` tenía 2.044 cercanos y 17.792 controles en 745 pads.
- Si no se llega, el veredicto es "sin muestra" y no se calcula ningún otro.

## Veredicto (Vaca Muerta, en este orden)

Umbral de dosis `UMBRAL_DOSIS` = -0,05 por unidad de f0 (5 puntos de índice entre el primer y el último día del mes; informado por
`sincronia`, que mide -21 con otro estimador, y mucho más exigente que su umbral de 2).

1. **sin muestra**: algún mínimo de arriba no se cumple.
2. **opuesta**: el límite inferior del IC de la pendiente es mayor que 0. **plana**: el IC incluye cero.
3. **no equilibrado**: falla alguno de los tres chequeos de equilibrio (eta cuadrado, Spearman de edad, Spearman de caudal base).
4. **no sobrevive a su placebo**: rompe el chequeo de pozos de control, o alguna fecha falsa, o el estimador de días sorteados.
5. **no firme**: el límite superior del IC de la pendiente está entre -0,05 y 0; o el p de días sorteados es 0,05 o más; o el tercio
   no es monótono o su IC de grupo 3 menos grupo 1 no queda bajo cero; o la pendiente ajustada (C) no queda con límite superior
   bajo 0; o alguna pendiente sin un operador grande no queda con límite superior bajo 0. Se imprime cuál condición falla.
6. **con dosis**: ninguna de las anteriores.

Lectura conjunta con Colorado (una sola línea, sin promediar): "dosis en las dos cuencas" si VM es "con dosis" y Colorado "se
repite"; "dosis en Vaca Muerta, Colorado <estado>" si VM es "con dosis" y Colorado es otra cosa; en otro caso, el veredicto de Vaca
Muerta y el estado de Colorado, separados. Se publican todos los números calculados; no se elige el mejor.

## Qué dice el estudio según el veredicto

Las frases se fijan ahora; los números de cada una salen de la corrida, nunca de esta página.

| Veredicto de Vaca Muerta | Frase del estudio |
| --- | --- |
| con dosis | Entre los padres a menos de 1 km, la caída del mes de la fractura crece cuanto más temprano en el mes empieza la fractura del hijo (pendiente e IC de la página), con el día de inicio equilibrado frente a operador, edad y caudal base, sin pendiente en pozos de control ni en fechas falsas. Bajo un supuesto que se puede revisar (el día de inicio no se relaciona con la tendencia del padre), es una dosis en el tiempo, sin ningún pozo lejano en la comparación. No separa cierre de daño: los dos empiezan con la fractura. |
| plana | El día del mes en que empieza la fractura no explica la caída del mes 0 entre padres cercanos: la brecha de 19 a 23 puntos queda como asociación y no se atribuye a la fractura. La pendiente de sincronía de la página anterior, medida contra controles, no se sostiene con este estimador y se lee como resultado de la comparación con los controles, no de la dosis. |
| opuesta | Los padres cercanos caen menos cuanto antes empieza la fractura: no hay dosis en el tiempo y el vínculo temporal con la fractura queda debilitado. |
| no equilibrado | El día de inicio no es independiente de [operador, edad o caudal base, el que falle]: la pendiente se informa y no se lee como dosis. |
| no sobrevive a su placebo | La misma pendiente aparece donde no hay exposición (controles, fechas falsas, días sorteados): la huella no se separa del calendario o de la selección y no se lee como dosis. |
| no firme | La pendiente es negativa pero no pasa todas las condiciones fijadas: se dice cuál no, y la huella no se promueve a dosis. |
| sin muestra | No hay eventos suficientes para decidir; no se calcula veredicto. |

Si el veredicto no es "con dosis", el README y el sitio no ganan ninguna frase nueva; la fila "Sincronía dentro del mes" (hoy
"sostiene") se vuelve a leer a la luz de esta y la lista de líneas afectadas va al responsable del estudio, no se edita acá.

## Qué no va a poder decir ningún resultado

- Es una pendiente de un caudal mensual contra un día: el mes 0 mezcla días antes y después del inicio, así que la dosis está
  atenuada y la prueba lee signo y orden, no magnitud por día.
- No separa un cierre preventivo del operador de un daño del pozo: los dos empiezan con la fractura y los dos crecen con los días
  expuestos.
- "El día de inicio no se relaciona con la tendencia del padre" no se puede comprobar; el equilibrio y los placebos la hacen creíble
  y no la prueban. Un operador que programa la fractura al empezar el mes y a la vez recorta el padre al empezar el mes rompería el
  supuesto sin dejar rastro en los chequeos observables.
- Los controles heredan la f0 de su propio hijo más cercano; la prueba de controles mide que esa f0 no mueve a un pozo lejano, no
  que no haya derrame a 2 km.
- Bootstrap por bloques de 5 km sin ajuste por comparaciones múltiples. Es una huella medida, no una prueba de causa.

## Desviaciones

Ninguna al fijar esta regla.

2026-11-23, después de la corrida (commit de la implementación 6629dc3): ninguna desviación de la regla (constantes, estimador,
muestra y funciones de veredicto sin cambios desde d370e0b). La corrida de 6629dc3 ya traía, y publicó, una lectura posterior
fuera del veredicto (rotulada así en la página del hallazgo) sobre de dónde sale el sesgo de los días sorteados: la constante
`OFFSET_SEMILLA_DIAGNOSTICO` y las filas `diagnostico` de `mart_dia_inicio`. No cambia ninguna condición del veredicto.

2026-11-23, corrección de esa lectura posterior (commit 30bae37, a raíz de la revisión): la rotación "sin f0 de un hijo del mismo
pad" podía dejar a un pad con su propia f0 (la permutación rotada tenía puntos fijos). Se reescribió como un ciclo aleatorio entre
pads. El valor publicado de esa fila pasó de -0,4 a -0,2 puntos por 0,1 (media de los sorteos -0,0444 a -0,0162 por unidad de f0,
con rango 2,5 a 97,5 de -1,3 a 0,5 a -1,1 a 0,7 puntos por 0,1); sigue por encima del límite de sesgo de 0,0125 y ninguna
condición del veredicto cambia. Alcance de las dos rotaciones de esa lectura: no rotan los meses con un solo hijo ni con un solo
pad; en Vaca Muerta eso toca 1 de 2.044 eventos cercanos (0,05 %), comprobado el 2026-11-23.
