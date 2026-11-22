# Dosis y respuesta: trabajos más grandes, ¿más caída?

Página generada por `pipeline/dosis.py`. Pregunta si la caída del padre al mes 1 crece con el tamaño del trabajo del hijo (arena por etapa, arena por metro de rama, presión máxima) y con la depleción del padre: eso es lo que predice la física de los golpes de fractura. Resultado A, caída del índice al mes 1 (principal, decide el veredicto). Resultado B, caída del caudal por día efectivo (se informa aparte y no cambia el veredicto de A).

## Veredicto (resultado A)

**sin dosis y respuesta**: el dato público no muestra dosis y respuesta: ninguna variable cumple en el modelo conjunto y ninguna tiene orden en los quintiles, lo que es compatible con cierre preventivo o con variables no observadas (espaciamiento real); la cota superior mayor de los IC sin ajustar por Holm es de 0,23 desvíos de la caída: el efecto positivo compatible con los datos llega, como mucho, a eso (el semiancho mayor, 0,18, mide la precisión y no el efecto descartado). No se detectó dosis y respuesta con datos públicos; eso no dice que no haya golpes de fractura.

Regla fijada antes de correr: dos o más variables cumplen (signo positivo y p ajustado por Holm sobre las cuatro menor que 0,05) con el modelo conjunto, controles y efectos fijos de área por año, e inferencia por bootstrap de pads hijo (B = 2.000). Resultado B: **sin dosis y respuesta**: el dato público no muestra dosis y respuesta: ninguna variable cumple en el modelo conjunto y ninguna tiene orden en los quintiles, lo que es compatible con cierre preventivo o con variables no observadas (espaciamiento real); la cota superior mayor de los IC sin ajustar por Holm es de 0,22 desvíos de la caída: el efecto positivo compatible con los datos llega, como mucho, a eso (el semiancho mayor, 0,15, mide la precisión y no el efecto descartado). No se detectó dosis y respuesta con datos públicos; eso no dice que no haya golpes de fractura.

## Modelo conjunto (las cuatro variables a la vez)

### Resultado A, caída del índice (n = 1.551, pads = 263)

| Variable | Coef por desvío | IC 95% | p Holm | FIV | Cumple |
| --- | ---: | --- | ---: | ---: | --- |
| arena por etapa | 0,006 | -0,081 a 0,054 | 1,000 | 1,2 | no |
| arena por metro de rama | -0,021 | -0,092 a 0,045 | 1,000 | 1,1 | no |
| presión máxima de tratamiento | 0,021 | -0,030 a 0,101 | 1,000 | 1,0 | no |
| depleción del padre | 0,027 | -0,070 a 0,115 | 1,000 | 2,2 | no |

### Resultado B, caída del caudal por día (n = 1.402, pads = 248)

| Variable | Coef por desvío | IC 95% | p Holm | FIV | Cumple |
| --- | ---: | --- | ---: | ---: | --- |
| arena por etapa | 0,021 | -0,188 a 0,148 | 1,000 | 1,1 | no |
| arena por metro de rama | -0,029 | -0,197 a 0,110 | 1,000 | 1,1 | no |
| presión máxima de tratamiento | 0,052 | -0,195 a 0,173 | 1,000 | 1,0 | no |
| depleción del padre | 0,095 | -0,101 a 0,290 | 1,000 | 2,6 | no |

## Quintiles de cada variable (caída ajustada media por quintil)

La caída ajustada es el residuo de la caída contra los controles y efectos fijos más la media general.

### Resultado A

| Variable | Q1 | Q2 | Q3 | Q4 | Q5 | n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arena por etapa | 0,199 | 0,208 | 0,200 | 0,255 | 0,157 | 2.094 |
| arena por metro de rama | 0,267 | 0,204 | 0,214 | 0,287 | 0,198 | 1.837 |
| presión máxima de tratamiento | 0,210 | 0,203 | 0,198 | 0,167 | 0,243 | 2.086 |
| depleción del padre | 0,274 | 0,200 | 0,254 | 0,212 | 0,272 | 1.599 |

### Resultado B

| Variable | Q1 | Q2 | Q3 | Q4 | Q5 | n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arena por etapa | 0,650 | 0,727 | 0,557 | 0,770 | 0,701 | 1.886 |
| arena por metro de rama | 0,717 | 0,756 | 0,630 | 0,888 | 0,596 | 1.648 |
| presión máxima de tratamiento | 0,675 | 0,689 | 0,718 | 0,628 | 0,702 | 1.881 |
| depleción del padre | 0,701 | 0,728 | 0,850 | 0,585 | 0,829 | 1.439 |

## Orden en los quintiles

| Resultado | Variable | Spearman | Q5 menos Q1 (IC 95%) | p Holm | Orden |
| --- | --- | ---: | --- | ---: | --- |
| A | arena por etapa | -0,10 | -0,042 (-0,119 a 0,036) | 0,864 | no |
| A | arena por metro de rama | -0,30 | -0,069 (-0,145 a 0,014) | 0,392 | no |
| A | presión máxima de tratamiento | 0,00 | 0,033 (-0,038 a 0,112) | 0,864 | no |
| A | depleción del padre | -0,10 | -0,003 (-0,107 a 0,091) | 0,927 | no |
| B | arena por etapa | 0,30 | 0,051 (-0,146 a 0,276) | 1,000 | no |
| B | arena por metro de rama | -0,30 | -0,121 (-0,298 a 0,051) | 0,688 | no |
| B | presión máxima de tratamiento | 0,20 | 0,028 (-0,152 a 0,237) | 1,000 | no |
| B | depleción del padre | 0,20 | 0,128 (-0,076 a 0,347) | 0,693 | no |

Hay "orden" si el Spearman de las cinco medias con el número de quintil es al menos 0,7 y Q5 menos Q1 es positiva con p Holm menor que 0,05.

## Sensibilidades (se informan, no entran en el veredicto)

Modelo conjunto con cambios (B = 1.000 remuestreos): sin las dummies de terminación, solo terminación Tapón disparo, las cuatro variables como rangos percentil, y cada variable sola con los controles.

| Resultado | Sensibilidad | Variable | Coef por desvío | IC 95% | n |
| --- | --- | --- | ---: | --- | ---: |
| A | variables como rangos percentil | arena por etapa | 0,013 | -0,049 a 0,068 | 1.551 |
| A | variables como rangos percentil | arena por metro de rama | -0,001 | -0,071 a 0,067 | 1.551 |
| A | variables como rangos percentil | depleción del padre | 0,003 | -0,082 a 0,077 | 1.551 |
| A | variables como rangos percentil | presión máxima de tratamiento | 0,018 | -0,034 a 0,079 | 1.551 |
| A | sin dummies de terminación | arena por etapa | 0,006 | -0,074 a 0,052 | 1.551 |
| A | sin dummies de terminación | arena por metro de rama | -0,021 | -0,082 a 0,042 | 1.551 |
| A | sin dummies de terminación | depleción del padre | 0,027 | -0,073 a 0,115 | 1.551 |
| A | sin dummies de terminación | presión máxima de tratamiento | 0,020 | -0,032 a 0,097 | 1.551 |
| A | cada variable sola | arena por etapa | 0,004 | -0,075 a 0,050 | 1.551 |
| A | cada variable sola | arena por metro de rama | -0,017 | -0,085 a 0,037 | 1.551 |
| A | cada variable sola | depleción del padre | 0,024 | -0,074 a 0,115 | 1.551 |
| A | cada variable sola | presión máxima de tratamiento | 0,019 | -0,034 a 0,102 | 1.551 |
| A | solo Tapón disparo | arena por etapa | 0,014 | -0,071 a 0,064 | 1.244 |
| A | solo Tapón disparo | arena por metro de rama | -0,035 | -0,106 a 0,032 | 1.244 |
| A | solo Tapón disparo | depleción del padre | 0,046 | -0,077 a 0,149 | 1.244 |
| A | solo Tapón disparo | presión máxima de tratamiento | 0,035 | -0,011 a 0,086 | 1.244 |
| B | variables como rangos percentil | arena por etapa | 0,043 | -0,122 a 0,188 | 1.402 |
| B | variables como rangos percentil | arena por metro de rama | -0,009 | -0,208 a 0,153 | 1.402 |
| B | variables como rangos percentil | depleción del padre | 0,045 | -0,163 a 0,198 | 1.402 |
| B | variables como rangos percentil | presión máxima de tratamiento | -0,014 | -0,178 a 0,150 | 1.402 |
| B | sin dummies de terminación | arena por etapa | 0,026 | -0,156 a 0,153 | 1.402 |
| B | sin dummies de terminación | arena por metro de rama | -0,043 | -0,207 a 0,100 | 1.402 |
| B | sin dummies de terminación | depleción del padre | 0,094 | -0,102 a 0,273 | 1.402 |
| B | sin dummies de terminación | presión máxima de tratamiento | 0,050 | -0,213 a 0,171 | 1.402 |
| B | cada variable sola | arena por etapa | 0,024 | -0,200 a 0,136 | 1.402 |
| B | cada variable sola | arena por metro de rama | -0,019 | -0,196 a 0,105 | 1.402 |
| B | cada variable sola | depleción del padre | 0,095 | -0,107 a 0,298 | 1.402 |
| B | cada variable sola | presión máxima de tratamiento | 0,050 | -0,228 a 0,170 | 1.402 |
| B | solo Tapón disparo | arena por etapa | 0,028 | -0,164 a 0,135 | 1.124 |
| B | solo Tapón disparo | arena por metro de rama | -0,080 | -0,254 a 0,075 | 1.124 |
| B | solo Tapón disparo | depleción del padre | 0,169 | -0,064 a 0,404 | 1.124 |
| B | solo Tapón disparo | presión máxima de tratamiento | -0,017 | -0,159 a 0,122 | 1.124 |

## Qué no prueba

- Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real y la geometría de la fractura no están en el dato público, y el hijo más cercano puede no ser el que golpeó al padre.
- Un coeficiente positivo no separa el golpe de un cierre preventivo más largo cuanto más grande es el trabajo: la dosis puede mover la decisión del operador.
- Los eventos de un mismo hijo comparten pad y calendario; el bootstrap por pads cubre eso, no la dependencia entre pads.
- Los datos de presión de la base pública tienen ceros y valores atípicos: los ceros cuentan como faltantes y solo entran presiones entre 0 y 20.000 psi.
