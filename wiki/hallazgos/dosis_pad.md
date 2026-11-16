# Dosis del pad y cercanía

Página generada por `pipeline/dosis_pad.py`. Pregunta si la caída del padre crece con la dosis de todo 
el pad del hijo y con la interacción de padre depletado e hijo muy cerca.
Prueba agregada después de ver los resultados de pipeline.dosis y pipeline.dosis_meses, con la lectura 
más favorable a la física para que un nulo pese más.

## Veredicto

Resultado A: **sigue sin dosis y respuesta**: ninguna de las cuatro del pad cumple en la muestra completa y ninguna de las cinco cumple en la cercanía: tampoco con la dosis del pad ni en la cercanía aparece respuesta; el semiancho mayor de los IC sin ajustar es de 0,19 desvíos de la caída en la muestra completa y 0,33 en la cercanía, que es cuanto efecto queda descartado.
Resultado B: **sigue sin dosis y respuesta**: ninguna de las cuatro del pad cumple en la muestra completa y ninguna de las cinco cumple en la cercanía: tampoco con la dosis del pad ni en la cercanía aparece respuesta; el semiancho mayor de los IC sin ajustar es de 0,19 desvíos de la caída en la muestra completa y 0,32 en la cercanía, que es cuanto efecto queda descartado.

### Resultado A, caída del índice, muestra completa (n = 1.552, pads = 264)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | 0,047 | -0,042 a 0,146 | 0,636 | no |
| arena por metro de rama del pad | -0,064 | -0,166 a 0,012 | 0,412 | no |
| presión máxima del pad | 0,032 | -0,021 a 0,095 | 0,636 | no |
| depleción del padre | 0,037 | -0,065 a 0,120 | 0,636 | no |

### Resultado A, caída del índice, cercanía km menor que 0,5 (n = 658, pads = 150)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | -0,026 | -0,162 a 0,061 | 1,000 | no |
| arena por metro de rama del pad | 0,011 | -0,123 a 0,118 | 1,000 | no |
| presión máxima del pad | 0,022 | -0,054 a 0,191 | 1,000 | no |
| depleción del padre | 0,059 | -0,112 a 0,216 | 1,000 | no |
| interacción depleción por cercanía | -0,029 | -0,093 a 0,057 | 1,000 | no |

### Resultado B, caída del caudal por día, muestra completa (n = 1.400, pads = 248)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | 0,071 | -0,163 a 0,328 | 1,000 | no |
| arena por metro de rama del pad | -0,064 | -0,353 a 0,096 | 1,000 | no |
| presión máxima del pad | -0,033 | -0,210 a 0,095 | 1,000 | no |
| depleción del padre | 0,097 | -0,098 a 0,290 | 1,000 | no |

### Resultado B, caída del caudal por día, cercanía km menor que 0,5 (n = 583, pads = 139)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | -0,031 | -0,291 a 0,237 | 1,000 | no |
| arena por metro de rama del pad | 0,052 | -0,161 a 0,289 | 1,000 | no |
| presión máxima del pad | -0,037 | -0,243 a 0,199 | 1,000 | no |
| depleción del padre | 0,155 | -0,114 a 0,599 | 0,905 | no |
| interacción depleción por cercanía | 0,061 | -0,127 a 0,206 | 1,000 | no |

## Sensibilidad (mismo mes)

Modelo de muestra completa con la ventana de mismo mes (se informa, no entra en el veredicto).

### Resultado A (n = 1.552, pads = 264)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | 0,037 | -0,087 a 0,132 | 1,000 | no |
| arena por metro de rama del pad | -0,038 | -0,129 a 0,043 | 1,000 | no |
| presión máxima del pad | 0,033 | -0,023 a 0,092 | 0,871 | no |
| depleción del padre | 0,035 | -0,067 a 0,123 | 1,000 | no |

### Resultado B (n = 1.400, pads = 248)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena total del pad | -0,116 | -0,546 a 0,141 | 1,000 | no |
| arena por metro de rama del pad | 0,003 | -0,209 a 0,197 | 1,000 | no |
| presión máxima del pad | -0,044 | -0,204 a 0,056 | 1,000 | no |
| depleción del padre | 0,092 | -0,098 a 0,304 | 1,000 | no |

## Qué no prueba

- Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real, la geometría de la 
fractura y el hijo que de verdad golpeó al padre no están en el dato público; la dosis del pad suma pozos 
que pueden estar lejos del padre.
- Un coeficiente positivo no separaría el golpe de un cierre preventivo más largo cuanto más grande es el trabajo.
- El subconjunto km menor que 0,5 es chico (cientos de eventos) y el IC de la interacción puede ser ancho; 
el semiancho se publica.
- Los eventos de un mismo pad hijo comparten calendario; el bootstrap por pads cubre eso, no la dependencia entre pads.
