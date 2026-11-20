# Validación por inyección

Página generada por `pipeline/inyeccion.py`. Pregunta si el estimador sin cambios recupera efectos de tamaño conocido plantados en datos reales, en fechas falsas donde la brecha real es cercana a cero. Convierte "se midió una brecha" en "el método recupera tanto, con esta dispersión". Complementa [Interferencia entre fracturas](interferencia.md), la [falsación](placebo.md), la [descomposición](descomposicion.md) y la [sincronía](sincronia.md); las reglas se fijaron antes de correr y están en el libro de hallazgos como `inyeccion_r1`, `inyeccion_r2`, `inyeccion_r3`, `inyeccion_r4a` e `inyeccion_r4b`.

## Resumen

- **R1, cifra principal: se cumple.** Con una caída plantada de 20% del caudal del mes 1, la brecha recuperada del mes 1 es -19,5 puntos en media de 30 mundos (rango del 5% al 95%: -20,7 a -18,3); la regla pedía entre -25 y -15. En puntos del índice, una caída de 20% del caudal es unos -17,4 puntos y no -20, porque el índice de los cercanos es menor que 1; lo recuperado (-19,5) suma eso y la brecha residual del mundo nulo (-2,2). Descontado el nulo, el estimador devuelve -17,3 puntos, lo plantado.
- **R2, reparto entre días y caudal: se cumple.** Con un cierre plantado la parte de los días del log de la brecha es 105%; con una caída de caudal plantada la parte del caudal por día es 103%. La regla pedía al menos 80% en los dos. Las partes son repartos del log de la brecha y pasan de 100% cuando la otra parte tiene signo contrario (el mundo nulo trae su propia composición).
- **R3, tiempo dentro del mes: se cumple.** Con una caída plantada de 40% desde el inicio de la fractura la pendiente del mes 0 recuperada es -2,8 puntos por cada 0,1 de f0 (plantado -4,0 nominal), y su IC excluye cero con el signo plantado en 100% de los mundos; la regla pedía al menos 80%. En puntos del índice lo plantado es -3,4 y, descontada la pendiente del mundo nulo (0,4), lo recuperado es -3,1.
- **R4a, falsos positivos: se cumple.** Sin nada plantado el IC de la brecha del mes 1 excluye cero en 7% de los mundos, 2 de 30; la regla del libro dice como máximo 10%. La brecha media del mundo nulo es -2,2 puntos. La tasa es la del IC por pads, no la del IC por bloques de 5 km que informa el caso, y con 30 mundos 2 de 30 es compatible con tasas de 1% a 22%.
- **R4b, brecha previa de nivel: se cumple.** Con una brecha de 5% plantada desde el mes -3 y sin efecto de fractura, restando el mundo nulo de los mismos sorteos, la pretendencia recuperada es -5,2 puntos (plantado -5,0) y la brecha neta del mes 1 es 0,5 puntos (plantado 0,0). Se filtra al mes 1 de la base limpia como -4,7 puntos y al de la base de los meses -3 a -1 como -0,5 puntos.

Se publican todas las celdas calculadas, no solo las de las reglas. Recuperar un efecto plantado dice algo del estimador, no de los pozos.

## Cómo se hizo

- Mundo nulo: la fecha de fractura de cada hijo corrida 12 meses hacia atrás, con los pares padre e hijo de la página de falsación y solo los pares ya elegibles con la fecha real. La brecha real ahí es cercana a cero.
- Mundos: 30 por celda. Cada mundo sortea el 70% de los pads hijo con una semilla fija y planta el efecto en los padres cercanos de esos pads; los controles no se tocan. El IC es el bootstrap por pads hijo de la página de falsación con 200 repeticiones. La dispersión entre mundos es muestreo de pads sobre datos reales.
- Estimadores sin cambios: la brecha del mes 1 de `pipeline/placebo.py`, la descomposición en logaritmos de `pipeline/descomposicion.py` y la pendiente de `pipeline/sincronia.py`; solo se les dan las matrices con el efecto plantado.
- S1 cierra el mes 1 (cero días y cero petróleo) en el 42,9% de los cercanos de cada mundo, la parte que da una brecha esperada de -50 puntos en el mundo nulo completo. S2 baja el caudal por día del mes 1 10, 20 y 30%. S3 lo baja 20, 40 y 60% desde el día de inicio de la fractura dentro del mes 0, de modo que la pendiente nominal es el tamaño sobre 10 en puntos por cada 0,1 de f0. S4 deja a los cercanos 3, 5 y 8% más abajo desde el mes -3 (la base de los meses -3 a -1 la incluye) sin efecto de fractura. S5 no planta nada.
- Los tamaños son nominales: un porcentaje de lo que produce cada cercano. En puntos del índice el efecto plantado es ese porcentaje por el índice de los cercanos, que es menor que 1. La columna Plantado en puntos lo mide sobre el mundo nulo completo, con el estimador del escenario aplicado al efecto plantado solo, sin ruido ni sorteo de pads; Recuperado menos nulo resta la media del mundo nulo de los mismos sorteos.

## Brecha del mes 1

Puntos del índice (base de los meses -3 a -1), cercano menos control. En S4 lo recuperado es la diferencia con S5 de los mismos sorteos, y el IC excluye cero de S4 es el del valor bruto (con la brecha residual del mundo nulo), no el de esa diferencia. Tamaño en %: S1 es el % de días del mes perdidos, S2 el % de caída, S4 el % de nivel. Las partes son la media entre mundos del reparto del log de la brecha.

| Escenario | Tamaño | Plantado (nominal) | Plantado en puntos | Recuperado (media) | Recuperado menos nulo | p05 a p95 | IC excluye cero | Parte de los días | Parte del caudal por día |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| S1 | 100 | -50,0 | -50,0 | -49,8 | -47,6 | -58,7 a -44,2 | 100% | 105% | -5% |
| S2 | 10 | -10,0 | -8,8 | -10,8 | -8,6 | -12,1 a -9,6 | 100% | -6% | 106% |
| S2 | 20 | -20,0 | -17,4 | -19,5 | -17,3 | -20,7 a -18,3 | 100% | -3% | 103% |
| S2 | 30 | -30,0 | -25,9 | -28,1 | -25,9 | -29,2 a -27,0 | 100% | -2% | 102% |
| S4 | 3 | 0,0 | -0,3 | -0,2 | -0,2 | -0,4 a 0,0 | 10% (bruto) | n/d | n/d |
| S4 | 5 | 0,0 | -0,6 | -0,5 | -0,5 | -0,8 a -0,2 | 17% (bruto) | n/d | n/d |
| S4 | 8 | 0,0 | -0,8 | -0,8 | -0,8 | -1,2 a -0,4 | 23% (bruto) | n/d | n/d |
| S5 | 0 | 0,0 | 0,0 | -2,2 | n/d | -3,6 a -0,9 | 7% | n/d | n/d |

## Pendiente del mes 0

Puntos del índice por cada 0,1 de f0 (la fracción del mes posterior al inicio de la fractura). El IC cuenta el signo plantado (negativo) salvo en S5, donde cuenta cualquier signo. La última columna es la misma pendiente en el mes -1, sin días expuestos, que debe quedar cerca de cero.

| Escenario | Tamaño | Plantado (nominal) | Plantado en puntos | Recuperada (media) | Recuperada menos nulo | p05 a p95 | IC excluye cero | Mes -1 (media) |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| S3 | 20 | -2,0 | -1,7 | -1,1 | -1,5 | -1,9 a -0,4 | 20% | -0,1 |
| S3 | 40 | -4,0 | -3,4 | -2,8 | -3,1 | -3,4 a -2,1 | 100% | -0,1 |
| S3 | 60 | -6,0 | -5,1 | -4,5 | -4,9 | -5,1 a -3,9 | 100% | -0,2 |
| S5 | 0 | 0,0 | 0,0 | 0,4 | n/d | -0,4 a 1,1 | 0% | 0,0 |

## Brecha previa de nivel

Medias entre mundos en puntos. En S4 se resta S5 de los mismos sorteos; la fila de S5 es el valor absoluto del mundo nulo, su brecha residual. Lo plantado en S4 es menos el tamaño en la pretendencia y en el mes 1 con la base limpia (meses -6 a -4), y cero en la brecha neta (el mes 1 menos la pretendencia) y en el mes 1 con la base de los meses -3 a -1. Medido en puntos del índice, con el 5% lo plantado es -5,2 en la pretendencia, -4,9 en el mes 1 con la base limpia y 0,3 en la brecha neta.

| Escenario | Tamaño | Pretendencia | Mes 1, base limpia | Mes 1 neto | Mes 1, base -3 a -1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| S5 | 0 | -3,6 | -5,0 | -1,4 | -2,2 |
| S4 | 3 | -3,1 | -2,8 | 0,4 | -0,2 |
| S4 | 5 | -5,2 | -4,7 | 0,5 | -0,5 |
| S4 | 8 | -8,3 | -7,5 | 0,8 | -0,8 |

## Límites

- Los efectos plantados son simples (multiplicativos, el mismo para todos los cercanos de un pad) e independientes de la geología, la distancia y el operador. Recuperarlos dice algo del estimador, no de los pozos.
- El cierre de S1 se mide con los días acotados a un día de 30 en la descomposición, así que un mes cerrado entero es un efecto de días casi por construcción: la parte de los días de S1 es una verificación débil. S2 es la prueba que separa.
- El mundo nulo tiene una brecha residual (los cercanos de la fecha falsa no son idénticos a los controles) y los pozos reales traen su propio ruido y sus cierres; por eso en S4 se resta el nulo.
- Un padre puede ser cercano en un evento y control en otro: un efecto plantado puede tocar un control por solapamiento de ventanas, y un cercano en dos eventos cercanos recibe el efecto dos veces. No se corrige.
- Cada mundo usa el 70% de los pads, así que el IC y la tasa de falsos positivos son los de una muestra más chica que la del resultado principal.
- La corrida con 50 mundos por celda pasó de los 8 minutos que la regla fijó como tope (unos 9 minutos), así que se bajó a 30 mundos por celda, como la regla decía. Con menos mundos las medias y los rangos son menos estables.
- La salida de esa corrida de 50 mundos se guardó en `docs/inyeccion_50_mundos.txt` y se publica acá, fuera de tope y sin cambiar los veredictos fijados. Se corrió con una versión anterior de los datos y no se repitió con la actual, así que sus cifras son de esa versión. R1: -19,6 puntos. R2: partes de 105% y 104%. R3: IC que excluye cero en 96% de los mundos. R4a: 8% (4 de 50), que con 50 mundos pasaría también el operador estricto. R4b: pretendencia -5,1 puntos y brecha neta del mes 1 0,4. El veredicto de R4a que vale es el de 30 mundos, el que fijó la regla; los 50 dicen que el borde es sensible al número de mundos.
- La pendiente plantada en puntos del índice es el tamaño por el índice del mes 0 de los cercanos, que es menor que 1: con el 40% es -3,4 y no -4,0. Descontando la pendiente del mundo nulo (0,4), lo recuperado (-3,1) queda cerca de lo plantado (92%). La columna Plantado (nominal) usa el tamaño nominal. La regla R3 usa solo el signo y el IC.
- Es una prueba del método sobre efectos plantados, no una prueba de causa.
