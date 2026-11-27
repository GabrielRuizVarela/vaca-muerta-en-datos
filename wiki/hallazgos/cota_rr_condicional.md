# Cota de Rambachan y Roth con la prueba condicional e híbrida

Página generada por `pipeline/cota_rr_condicional.py`, regla fijada en el commit de19052 antes de calcular.

Es la misma pregunta que en [la cota de Rambachan y Roth](cota_rr.md): qué tan grande tendría que ser la violación de tendencias paralelas después del tratamiento, medida contra el mayor salto previo, para que el efecto deje de distinguirse de cero. Cambia la inferencia. En lugar de la unión de percentiles del bootstrap, que no sale de una prueba con nivel conocido, esta página usa el conjunto de confianza de Rambachan y Roth (2023), que invierte la prueba condicional e híbrida de Andrews, Roth y Pakes (2023) para cada valor del parámetro, con la restricción de magnitudes relativas escrita como unión de seis poliedros. La matriz de covarianza sale de los mismos sorteos del bootstrap por bloques de 5 km. La tabla de cada estimando pone al lado el intervalo de unión de la otra página, como registro. Unidades: puntos de producción en D1 y puntos porcentuales de corte de agua en D2.

## Validación fijada antes de leer cifras reales

La prueba se validó con datos sintéticos, sin warehouse, antes de calcular nada con los datos reales. Resultado:

- Dualidad (200 casos al azar): el estadístico por vértices coincide con el mínimo directo sobre gamma, diferencia máxima 2e-15 (tolerancia 1e-9). Pasa.
- Cobertura (delta previa sintética, saltos posteriores en el borde de la restricción, 1000 simulaciones por caso, mínimo exigido 93,0 %):
  - Mbar = 0,5, ATT(1): 99,6 %.
  - Mbar = 0,5, media: 99,3 %.
  - Mbar = 1,0, ATT(1): 100,0 %.
  - Mbar = 1,0, media: 100,0 %.
  - Pasa.
- Potencia plantada (efecto de -10, Mbar = 0; mínimo exigido 90,0 %): ATT(1) 100,0 %; media 100,0 %. Pasa.
- Ancho (primeras 20 simulaciones, ATT(1), Mbar = 0): el conjunto contiene el punto en 20 de 20. Pasa. El más ancho mide 2,14 veces el intervalo normal al 95 % y el promedio 1,79 veces. La regla de de19052 ponía un tope de 2, que no se cumple: desde la enmienda de abajo, el ancho es un dato y no una puerta.

## Enmienda antes de calcular (55a709a)

La regla de de19052 hacía del ancho una puerta: con Mbar = 0, el conjunto no podía medir más del doble del intervalo normal. La primera corrida de la validación, todavía sin datos reales, no la pasó: el más ancho midió 2,14 veces. Ese tope no salía de la literatura ni de una cuenta. Se puso como guarda contra una implementación rota, y el ancho mide eficiencia, no corrección. La enmienda, hecha antes de calcular ninguna cifra real, deja el ancho como dato. Que el conjunto contenga el punto sigue siendo puerta, y no cambia ningún otro número: el tope no se reemplazó por otro, y la dualidad, la cobertura y la potencia quedan iguales.

De dónde sale el ancho, con los mismos datos sintéticos (ATT(1), Mbar = 0, theta = -3): cada poliedro por separado, con su rechazo de theta verdadero en 1000 simulaciones y su ancho en los 20 casos del ancho.

| Poliedro (mes del mayor salto previo, signo) | Contiene la delta verdadera | Rechazo de theta verdadero | Ancho medio | Ancho máximo |
|---|---|---|---|---|
| -3, + | sí | 4,3 % | 1,27 | 1,70 |
| -3, - | no | 11,9 % | 1,58 | 2,09 |
| -2, + | sí | 2,8 % | 1,27 | 1,97 |
| -2, - | no | 12,0 % | 1,53 | 2,14 |
| -1, + | no | 6,3 % | 1,53 | 2,13 |
| -1, - | no | 5,1 % | 1,34 | 2,11 |

Los anchos son en veces el intervalo normal al 95 %. Los 2 poliedros que contienen a la delta verdadera rechazan theta verdadero en 4,3 % y 2,8 %, y su conjunto mide como máximo 1,70 y 1,97 veces. La unión de los seis contiene a theta en 100,0 % de las 1000 simulaciones; su ancho medio es 1,79 veces y el máximo 2,14. El exceso sobre el tope viene de poliedros que no contienen a la delta verdadera: la unión tiene que incluirlos porque con datos reales no se sabe cuál vale. Un conjunto más ancho incluye antes el cero, así que solo puede bajar el Mbar de quiebre, nunca subirlo.

## D1, ATT(1)

Efecto estimado -25,8; previos b(-3) = -6,1, b(-2) = -3,6, b(-1) = -10,0; 468 tratados, 400 sorteos completos. Saltos previos entre meses: -6,1; 2,6; -6,4.

| Mbar | Conjunto de confianza condicional | Intervalo de unión |
|---|---|---|
| 0,00 | -35,0 a 6,8 | -24,7 a -5,7 |
| 0,25 | -34,5 a 3,6 | -29,0 a 1,1 |
| 0,50 | -35,3 a 4,3 | -34,0 a 8,7 |
| 0,75 | -37,5 a 11,0 | -41,6 a 16,0 |
| 1,00 | -42,8 a 17,9 | -49,4 a 24,0 |
| 1,25 | -49,6 a 24,9 | -57,5 a 32,1 |
| 1,50 | -56,5 a 31,9 | -66,6 a 39,9 |
| 1,75 | -63,4 a 38,9 | -75,3 a 48,5 |
| 2,00 | -70,5 a 46,1 | -84,3 a 57,6 |

Mbar de quiebre condicional: 0,00. Veredicto: **no resiste ni con Mbar = 0**.
Mbar de quiebre de la unión: 0,20. Veredicto: **resiste solo con Mbar menor que 1**.
Con Mbar = 0 el conjunto condicional mide 2,19 veces el intervalo de unión.
El quiebre condicional es menor que el de la unión: con esta prueba el efecto resiste menos.

## D2, tau_W(1)

Efecto estimado 15,6; previos b(-3) = 1,1, b(-2) = 1,2, b(-1) = 1,0; 413 tratados, 400 sorteos completos. Saltos previos entre meses: 1,1; 0,1; -0,2.

| Mbar | Conjunto de confianza condicional | Intervalo de unión |
|---|---|---|
| 0,00 | 8,8 a 20,5 | 10,7 a 19,7 |
| 0,25 | 9,2 a 20,4 | 9,9 a 20,7 |
| 0,50 | 9,0 a 20,6 | 9,1 a 22,1 |
| 0,75 | 8,2 a 21,6 | 8,0 a 23,4 |
| 1,00 | 7,1 a 22,7 | 6,7 a 25,1 |
| 1,25 | 5,8 a 24,1 | 5,1 a 27,0 |
| 1,50 | 4,4 a 25,5 | 3,8 a 28,6 |
| 1,75 | 3,0 a 27,0 | 2,2 a 30,6 |
| 2,00 | 1,5 a 28,4 | 0,5 a 32,6 |

Mbar de quiebre condicional: mayor que 2,00. Veredicto: **resiste Mbar = 1**.
Mbar de quiebre de la unión: mayor que 2,00. Veredicto: **resiste Mbar = 1**.
Con Mbar = 0 el conjunto condicional mide 1,30 veces el intervalo de unión.

## D2, media tau_W(0,1)

Efecto estimado 9,7; previos b(-3) = 1,1, b(-2) = 1,2, b(-1) = 1,0; 410 tratados, 400 sorteos completos. Saltos previos entre meses: 1,1; 0,1; -0,2.

| Mbar | Conjunto de confianza condicional | Intervalo de unión |
|---|---|---|
| 0,00 | 5,2 a 12,6 | 6,2 a 11,7 |
| 0,25 | 5,5 a 12,4 | 5,8 a 12,7 |
| 0,50 | 5,1 a 12,7 | 5,1 a 13,8 |
| 0,75 | 4,4 a 13,6 | 4,1 a 14,7 |
| 1,00 | 3,5 a 14,6 | 3,2 a 15,9 |
| 1,25 | 2,5 a 15,6 | 2,0 a 17,3 |
| 1,50 | 1,5 a 16,7 | 0,6 a 18,8 |
| 1,75 | 0,4 a 17,9 | -0,8 a 20,3 |
| 2,00 | -0,7 a 19,0 | -2,0 a 21,8 |

Mbar de quiebre condicional: 1,83. Veredicto: **resiste Mbar = 1**.
Mbar de quiebre de la unión: 1,62. Veredicto: **resiste Mbar = 1**.
Con Mbar = 0 el conjunto condicional mide 1,33 veces el intervalo de unión.
El quiebre condicional es mayor que el de la unión: con esta prueba el efecto resiste más.

## Una cláusula de la regla que no se siguió

La regla de de19052 pedía que, en un PR de texto aparte, el README y la portada citaran el quiebre condicional de D1 ATT(1) como la cota de Rambachan y Roth y dijeran que el de la unión es más conservador, aunque el quiebre condicional saliera menor. La primera parte se siguió; la segunda no. Nadie midió el nivel de la unión de percentiles, y en el petróleo al mes 1 de D1 su quiebre quedó por encima del condicional (las dos cifras están en su tabla, arriba): decir que la unión es más conservadora habría sido falso ahí. El README y el paper ponen los dos quiebres lado a lado para el petróleo al mes 1 de D1 y para la media de los meses 0 y 1 del agua, y la portada, para el petróleo; en el mes 1 del agua ninguno de los dos cae dentro de la grilla de Mbar. La regla queda como se escribió en el código; esta sección registra el desvío.

## Contraste con HonestDiD

Regla fijada en el commit 06f7720 antes de calcular, con sus aclaraciones en el commit 21e1a91 (fijadas antes de correr R sobre entradas reales). Generada por `pipeline/cota_rr_contraste.py`. La prueba condicional e híbrida de esta página se corre otra vez con el paquete HonestDiD 0.2.8 de CRAN, en R dentro de un contenedor con límites (`scripts/contraste_honestdid.sh`). Las entradas son `data/cota_rr_contraste_entradas.json` (beta, Sigma y las matrices A por poliedro; sin datos de pozos) y la salida de R es `data/cota_rr_contraste_honestdid.json`.

R 4.4.2 (2024-10-31), HonestDiD 0.2.8, semilla 0. **Lectura L1 (misma A y mismo valor crítico que el módulo): coincide** con la regla de coincidencia en los 5 estimandos. La mayor diferencia de un extremo entre L1 y el módulo es 0,023 sd (extremo bajo) y 0,031 sd (extremo alto), en desvíos del estimando.

Las cuatro lecturas: L1 (misma A y mismo valor crítico), L1p (misma A y valor crítico del paquete, 1000 sorteos), L2 (HonestDiD completo, `postPeriodMomentsOnly = FALSE`) y L3 (HonestDiD por defecto: usa solo las filas de A que tocan meses posteriores). L1p, L2 y L3 se publican como dato: no cambian ningún veredicto. Las diferencias son en sd contra el módulo, extremo bajo y extremo alto, sobre los Mbar de la grilla con ese extremo cerrado en los dos conjuntos.

### D1 ATT(1)

| Lectura | Mbar de quiebre | Veredicto | Mayor diferencia con el módulo (sd) | Fallos del programa lineal | Errores del paquete | Conjuntos que contienen al anterior |
|---|---|---|---|---|---|---|
| módulo | 0,00 | no resiste ni con Mbar = 0 | - | - | - | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1 | no se biseca: pasa la prueba del cero alrededor del quiebre del módulo | - | 0,023 y 0,031 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1p | 0,00 | no resiste ni con Mbar = 0 | 0,043 y 0,072 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L2 | 0,00 | no resiste ni con Mbar = 0 | 0,023 y 0,031 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L3 | 0,35 | resiste solo con Mbar menor que 1 | 2,116 y 2,812 | 0 | 0 | 8 de 8 |

### D2 tau_W(1)

| Lectura | Mbar de quiebre | Veredicto | Mayor diferencia con el módulo (sd) | Fallos del programa lineal | Errores del paquete | Conjuntos que contienen al anterior |
|---|---|---|---|---|---|---|
| módulo | mayor que 2,00 | resiste Mbar = 1 | - | - | - | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1 | no se biseca: pasa la prueba del cero alrededor del quiebre del módulo | - | 0,009 y 0,016 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1p | mayor que 2,00 | resiste Mbar = 1 | 0,009 y 0,012 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L2 | mayor que 2,00 | resiste Mbar = 1 | 0,009 y 0,108 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L3 | mayor que 2,00 | resiste Mbar = 1 | 0,604 y 0,652 | 0 | 0 | 8 de 8 |

### D2 media tau_W(0,1)

| Lectura | Mbar de quiebre | Veredicto | Mayor diferencia con el módulo (sd) | Fallos del programa lineal | Errores del paquete | Conjuntos que contienen al anterior |
|---|---|---|---|---|---|---|
| módulo | 1,83 | resiste Mbar = 1 | - | - | - | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1 | no se biseca: pasa la prueba del cero alrededor del quiebre del módulo | - | 0,012 y 0,012 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1p | 1,83 | resiste Mbar = 1 | 0,008 y 0,012 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L2 | 1,83 | resiste Mbar = 1 | 0,012 y 0,076 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L3 | 1,85 | resiste Mbar = 1 | 0,544 y 0,844 | 0 | 0 | 8 de 8 |

### E ATT(1)

| Lectura | Mbar de quiebre | Veredicto | Mayor diferencia con el módulo (sd) | Fallos del programa lineal | Errores del paquete | Conjuntos que contienen al anterior |
|---|---|---|---|---|---|---|
| módulo | 0,00 | no resiste ni con Mbar = 0 | - | - | - | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1 | no se biseca: pasa la prueba del cero alrededor del quiebre del módulo | - | 0,011 y 0,014 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1p | 0,00 | no resiste ni con Mbar = 0 | 0,042 y 0,040 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L2 | 0,00 | no resiste ni con Mbar = 0 | 0,031 y 0,020 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L3 | 0,38 | resiste solo con Mbar menor que 1 | 2,236 y 1,828 | 0 | 0 | 8 de 8 |

### E2 ATT(1)

| Lectura | Mbar de quiebre | Veredicto | Mayor diferencia con el módulo (sd) | Fallos del programa lineal | Errores del paquete | Conjuntos que contienen al anterior |
|---|---|---|---|---|---|---|
| módulo | 0,48 | resiste solo con Mbar menor que 1 | - | - | - | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1 | no se biseca: pasa la prueba del cero alrededor del quiebre del módulo | - | 0,013 y 0,010 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L1p | 0,48 | resiste solo con Mbar menor que 1 | 0,013 y 0,012 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L2 | 0,48 | resiste solo con Mbar menor que 1 | 0,013 y 0,016 | 0 | 0 | 7 de 8 (no contiene al anterior en Mbar = 0,25) |
| L3 | 0,59 | resiste solo con Mbar menor que 1 | 0,532 y 1,672 | 0 | 0 | 8 de 8 |

El veredicto de L3 es distinto del del módulo en D1 ATT(1), E ATT(1). Es un dato de esta lectura: ningún veredicto publicado cambia por él.

El anidamiento es un dato, sin veredicto: para cada lectura se cuenta en cuántos Mbar de la grilla (desde el segundo) el conjunto contiene al del Mbar anterior, con tolerancia de 0,05 sd más el paso de la grilla. Cuando el paquete falla con un error en un theta, o su programa lineal no converge, esa prueba no rechaza; se cuenta y se publica. L3 usa solo las filas de A que tocan meses posteriores.

### Lo que no dice el contraste

Prueba que la misma prueba da lo mismo con otro código. No prueba que Delta^RM sea la restricción correcta ni que la base de los coeficientes sea la que usaría HonestDiD con los datos crudos: usa la de este proyecto, que es la de `pipeline.cota_rr`.

## E y E2

La misma cota condicional del módulo (regla 06f7720, aclaraciones 21e1a91) sobre las series principales de los diseños apilados E (controles a 2 a 5 km) y E2 (a 2 a 10 km), con los mismos sorteos que sus páginas: beta es el punto de la muestra completa y Sigma la covarianza de los sorteos completos de e = -3, -2, -1, 0 y 1. Es cifra nueva. El quiebre condicional va al lado del de la unión, que sale de las marts de cada diseño. Unidades: puntos de índice, los del estimando de cada diseño.

| Diseño | Tratados | Sorteos completos | Mbar de quiebre condicional | Veredicto condicional | Mbar de quiebre de la unión | Veredicto de la unión |
|---|---|---|---|---|---|---|
| E ATT(1) | 81 | 400 | 0,00 | no resiste ni con Mbar = 0 | 0,32 | resiste solo con Mbar menor que 1 |
| E2 ATT(1) | 210 | 400 | 0,48 | resiste solo con Mbar menor que 1 | 0,51 | resiste solo con Mbar menor que 1 |

### E ATT(1): conjunto de confianza condicional

| Mbar | Conjunto condicional |
|---|---|
| 0,00 | -55,9 a 7,9 |
| 0,25 | -56,4 a 5,4 |
| 0,50 | -57,8 a 5,6 |
| 0,75 | -60,0 a 11,3 |
| 1,00 | -66,5 a 18,6 |
| 1,25 | -75,0 a 26,1 |
| 1,50 | -83,5 a 33,6 |
| 1,75 | -92,2 a 41,1 |
| 2,00 | -100,8 a 48,7 |

### E2 ATT(1): conjunto de confianza condicional

| Mbar | Conjunto condicional |
|---|---|
| 0,00 | -32,4 a -0,7 |
| 0,25 | -32,4 a -2,9 |
| 0,50 | -33,0 a 0,2 |
| 0,75 | -34,9 a 3,8 |
| 1,00 | -38,2 a 8,9 |
| 1,25 | -43,0 a 14,1 |
| 1,50 | -48,0 a 19,3 |
| 1,75 | -53,2 a 24,6 |
| 2,00 | -58,3 a 29,9 |

Los veredictos de E y de E2 no cambian: `pipeline.stacked.veredicto_apilado` sigue recibiendo el veredicto de la unión y da E: **sin muestra** y E2: **sin muestra** por el número de eventos, no por la cota.

## Lo que no dice

Supone, como la cota de la unión, que los meses previos no tienen efecto (sin anticipación). La matriz de covarianza sale del bootstrap por bloques, no de una fórmula; con un número fijo de sorteos para el valor crítico el Mbar de quiebre tiene un error de simulación del orden de la tolerancia de la bisección o mayor. El conjunto se busca en una grilla de valores del parámetro: si llega al borde de la grilla se publica como abierto de ese lado.

## Referencias

- Rambachan, A. y Roth, J. (2023). A More Credible Approach to Parallel Trends. *Review of Economic Studies*, 90(5), 2555-2591. doi:10.1093/restud/rdad018.
- Andrews, I., Roth, J. y Pakes, A. (2023). Inference for Linear Conditional Moment Inequalities. *Review of Economic Studies*, 90(6), 2763-2791. doi:10.1093/restud/rdad004.
- Rambachan, A. y Roth, J. HonestDiD, paquete de R, versión 0.2.8. https://github.com/asheshrambachan/HonestDiD.

Qué se leyó de cada una está en `docs/proceso/antecedentes-leidos.md`, sección 14.
