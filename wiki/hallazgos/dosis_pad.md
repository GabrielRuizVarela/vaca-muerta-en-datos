# Dosis del pad y cercanía

Página generada por `pipeline/dosis_pad.py`. Pregunta si la caída del padre crece con la dosis de todo 
el pad del hijo y con la interacción de padre depletado e hijo muy cerca.
Prueba agregada después de ver los resultados de pipeline.dosis y pipeline.dosis_meses, con la lectura 
más favorable a la física para que un nulo pese más.

## Veredicto

Resultado A: **sigue sin dosis y respuesta**: ninguna de las cuatro del pad cumple en la muestra completa y ninguna de las cinco cumple en la cercanía: tampoco con la dosis del pad ni en la cercanía aparece respuesta; la cota superior mayor de los IC sin ajustar es de 0,29 desvíos de la caída en la muestra completa y 0,41 en la cercanía: el efecto positivo compatible con los datos llega, como mucho, a eso.
Resultado B: **sigue sin dosis y respuesta**: ninguna de las cuatro del pad cumple en la muestra completa y ninguna de las cinco cumple en la cercanía: tampoco con la dosis del pad ni en la cercanía aparece respuesta; la cota superior mayor de los IC sin ajustar es de 0,24 desvíos de la caída en la muestra completa y 0,52 en la cercanía: el efecto positivo compatible con los datos llega, como mucho, a eso.

### Resultado A, caída del índice, muestra completa (n = 1.559, pads = 265)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | 0,047 | -0,038 a 0,148 | 0,663 | no |
| arena por metro de rama del pad | -0,067 | -0,165 a 0,006 | 0,320 | no |
| presión máxima del pad | 0,032 | -0,023 a 0,095 | 0,663 | no |
| depleción del padre | 0,039 | -0,054 a 0,125 | 0,663 | no |

### Resultado A, caída del índice, cercanía km menor que 0,5 (n = 662, pads = 151)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | -0,024 | -0,154 a 0,067 | 1,000 | no |
| arena por metro de rama del pad | 0,005 | -0,127 a 0,122 | 1,000 | no |
| presión máxima del pad | 0,021 | -0,051 a 0,190 | 1,000 | no |
| depleción del padre | 0,048 | -0,117 a 0,207 | 1,000 | no |
| interacción depleción por cercanía | -0,026 | -0,091 a 0,063 | 1,000 | no |

### Resultado B, caída del caudal por día, muestra completa (n = 1.407, pads = 249)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | 0,068 | -0,159 a 0,323 | 1,000 | no |
| arena por metro de rama del pad | -0,058 | -0,338 a 0,115 | 1,000 | no |
| presión máxima del pad | -0,032 | -0,206 a 0,103 | 1,000 | no |
| depleción del padre | 0,096 | -0,105 a 0,291 | 1,000 | no |

### Resultado B, caída del caudal por día, cercanía km menor que 0,5 (n = 587, pads = 140)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | -0,030 | -0,296 a 0,232 | 1,000 | no |
| arena por metro de rama del pad | 0,049 | -0,173 a 0,277 | 1,000 | no |
| presión máxima del pad | -0,037 | -0,246 a 0,194 | 1,000 | no |
| depleción del padre | 0,137 | -0,130 a 0,580 | 1,000 | no |
| interacción depleción por cercanía | 0,070 | -0,137 a 0,222 | 1,000 | no |

## Sensibilidad (mismo mes)

Modelo de muestra completa con la ventana de mismo mes (se informa, no entra en el veredicto).

### Resultado A (n = 1.559, pads = 265)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | 0,035 | -0,086 a 0,126 | 1,000 | no |
| arena por metro de rama del pad | -0,040 | -0,125 a 0,041 | 1,000 | no |
| presión máxima del pad | 0,034 | -0,022 a 0,095 | 0,943 | no |
| depleción del padre | 0,037 | -0,063 a 0,118 | 1,000 | no |

### Resultado B (n = 1.407, pads = 249)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | -0,117 | -0,544 a 0,135 | 1,000 | no |
| arena por metro de rama del pad | 0,007 | -0,190 a 0,195 | 1,000 | no |
| presión máxima del pad | -0,045 | -0,210 a 0,074 | 1,000 | no |
| depleción del padre | 0,090 | -0,095 a 0,295 | 1,000 | no |

## Cada variable sola (agregado después de ver los resultados)

Diagnóstico agregado después de ver los resultados, a pedido de una revisión: cada variable del pad sola con los controles, y el FIV en el modelo conjunto. No entra en el veredicto.

| Resultado | Variable | Coef por desvío (IC 95%) | FIV conjunto |
| --- | --- | --- | ---: |
| A | arena total del pad | 0,035 (-0,038 a 0,123) | 1,5 |
| A | arena por metro de rama del pad | -0,050 (-0,147 a 0,021) | 1,2 |
| A | presión máxima del pad | 0,037 (-0,012 a 0,102) | 1,1 |
| A | depleción del padre | 0,026 (-0,071 a 0,123) | 2,2 |
| B | arena total del pad | 0,045 (-0,193 a 0,281) | 1,5 |
| B | arena por metro de rama del pad | -0,036 (-0,321 a 0,125) | 1,2 |
| B | presión máxima del pad | -0,028 (-0,194 a 0,105) | 1,1 |
| B | depleción del padre | 0,096 (-0,106 a 0,286) | 2,6 |

## Qué no prueba

- Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real, la geometría de la 
fractura y el hijo que de verdad golpeó al padre no están en el dato público; la dosis del pad suma pozos 
que pueden estar lejos del padre.
- Un coeficiente positivo no separaría el golpe de un cierre preventivo más largo cuanto más grande es el trabajo.
- El subconjunto km menor que 0,5 es chico (cientos de eventos) y el IC de la interacción puede ser ancho; 
el semiancho se publica.
- Los eventos de un mismo pad hijo comparten calendario; el bootstrap por pads cubre eso, no la dependencia entre pads.
