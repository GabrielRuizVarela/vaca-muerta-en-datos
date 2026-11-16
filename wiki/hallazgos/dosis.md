# Dosis y respuesta: trabajos más grandes, ¿más caída?

Página generada por `pipeline/dosis.py`. Pregunta si la caída del padre al mes 1 crece con el tamaño del trabajo del hijo (arena por etapa, arena por metro de rama, presión máxima) y con la depleción del padre: eso es lo que predice la física de los golpes de fractura. Resultado A, caída del índice al mes 1 (principal, decide el veredicto). Resultado B, caída del caudal por día efectivo (se informa aparte y no cambia el veredicto de A).

## Veredicto (resultado A)

**sin dosis y respuesta**: el dato público no muestra dosis y respuesta: ninguna variable cumple en el modelo conjunto y ninguna tiene orden en los quintiles, lo que es compatible con cierre preventivo o con variables no observadas (espaciamiento real); el semiancho mayor de los IC sin ajustar por Holm es de 0,19 desvíos de la caída, que es cuanto efecto queda descartado. Esto es falsar el mecanismo con datos públicos: no dice que no haya golpes de fractura.

Regla fijada antes de correr: dos o más variables cumplen (signo positivo y p ajustado por Holm sobre las cuatro menor que 0,05) con el modelo conjunto, controles y efectos fijos de área por año, e inferencia por bootstrap de pads hijo (B = 2.000). Resultado B: **sin dosis y respuesta**: el dato público no muestra dosis y respuesta: ninguna variable cumple en el modelo conjunto y ninguna tiene orden en los quintiles, lo que es compatible con cierre preventivo o con variables no observadas (espaciamiento real); el semiancho mayor de los IC sin ajustar por Holm es de 0,15 desvíos de la caída, que es cuanto efecto queda descartado. Esto es falsar el mecanismo con datos públicos: no dice que no haya golpes de fractura.

## Modelo conjunto (las cuatro variables a la vez)

### Resultado A, caída del índice (n = 1.544, pads = 262)

| Variable | Coef por desvío | IC 95% | p Holm | FIV | Cumple |
| --- | ---: | --- | ---: | ---: | --- |
| arena por etapa | 0,007 | -0,079 a 0,055 | 1,000 | 1,1 | no |
| arena por metro de rama | -0,020 | -0,091 a 0,044 | 1,000 | 1,1 | no |
| presión máxima de tratamiento | 0,021 | -0,031 a 0,099 | 1,000 | 1,0 | no |
| depleción del padre | 0,025 | -0,077 a 0,115 | 1,000 | 2,2 | no |

### Resultado B, caída del caudal por día (n = 1.395, pads = 247)

| Variable | Coef por desvío | IC 95% | p Holm | FIV | Cumple |
| --- | ---: | --- | ---: | ---: | --- |
| arena por etapa | 0,015 | -0,183 a 0,143 | 1,000 | 1,1 | no |
| arena por metro de rama | -0,033 | -0,216 a 0,105 | 1,000 | 1,1 | no |
| presión máxima de tratamiento | 0,053 | -0,209 a 0,175 | 1,000 | 1,0 | no |
| depleción del padre | 0,096 | -0,112 a 0,292 | 1,000 | 2,6 | no |

## Quintiles de cada variable (caída ajustada media por quintil)

La caída ajustada es el residuo de la caída contra los controles y efectos fijos más la media general.

### Resultado A

| Variable | Q1 | Q2 | Q3 | Q4 | Q5 | n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arena por etapa | 0,210 | 0,200 | 0,195 | 0,251 | 0,156 | 2.077 |
| arena por metro de rama | 0,265 | 0,208 | 0,211 | 0,284 | 0,197 | 1.820 |
| presión máxima de tratamiento | 0,211 | 0,200 | 0,200 | 0,162 | 0,241 | 2.069 |
| depleción del padre | 0,276 | 0,196 | 0,250 | 0,220 | 0,268 | 1.592 |

### Resultado B

| Variable | Q1 | Q2 | Q3 | Q4 | Q5 | n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arena por etapa | 0,664 | 0,710 | 0,574 | 0,738 | 0,701 | 1.869 |
| arena por metro de rama | 0,715 | 0,751 | 0,638 | 0,878 | 0,587 | 1.631 |
| presión máxima de tratamiento | 0,682 | 0,679 | 0,709 | 0,625 | 0,699 | 1.864 |
| depleción del padre | 0,704 | 0,718 | 0,852 | 0,595 | 0,821 | 1.432 |

## Orden en los quintiles

| Resultado | Variable | Spearman | Q5 menos Q1 (IC 95%) | p Holm | Orden |
| --- | --- | ---: | --- | ---: | --- |
| A | arena por etapa | -0,40 | -0,054 (-0,132 a 0,023) | 0,537 | no |
| A | arena por metro de rama | -0,30 | -0,067 (-0,145 a 0,012) | 0,364 | no |
| A | presión máxima de tratamiento | 0,00 | 0,030 (-0,042 a 0,105) | 0,802 | no |
| A | depleción del padre | -0,10 | -0,007 (-0,110 a 0,090) | 0,875 | no |
| B | arena por etapa | 0,30 | 0,037 (-0,159 a 0,250) | 1,000 | no |
| B | arena por metro de rama | -0,30 | -0,128 (-0,299 a 0,043) | 0,572 | no |
| B | presión máxima de tratamiento | 0,10 | 0,017 (-0,172 a 0,221) | 1,000 | no |
| B | depleción del padre | 0,20 | 0,117 (-0,086 a 0,334) | 0,924 | no |

Hay "orden" si el Spearman de las cinco medias con el número de quintil es al menos 0,7 y Q5 menos Q1 es positiva con p Holm menor que 0,05.

## Sensibilidades (se informan, no entran en el veredicto)

Modelo conjunto con cambios (B = 1.000 remuestreos): sin las dummies de terminación, solo terminación Tapón disparo, las cuatro variables como rangos percentil, y cada variable sola con los controles.

| Resultado | Sensibilidad | Variable | Coef por desvío | IC 95% | n |
| --- | --- | --- | ---: | --- | ---: |
| A | variables como rangos percentil | arena por etapa | 0,013 | -0,051 a 0,062 | 1.544 |
| A | variables como rangos percentil | arena por metro de rama | -0,001 | -0,069 a 0,064 | 1.544 |
| A | variables como rangos percentil | depleción del padre | 0,001 | -0,089 a 0,075 | 1.544 |
| A | variables como rangos percentil | presión máxima de tratamiento | 0,019 | -0,031 a 0,078 | 1.544 |
| A | sin dummies de terminación | arena por etapa | 0,008 | -0,072 a 0,051 | 1.544 |
| A | sin dummies de terminación | arena por metro de rama | -0,020 | -0,085 a 0,044 | 1.544 |
| A | sin dummies de terminación | depleción del padre | 0,024 | -0,080 a 0,112 | 1.544 |
| A | sin dummies de terminación | presión máxima de tratamiento | 0,020 | -0,029 a 0,092 | 1.544 |
| A | cada variable sola | arena por etapa | 0,006 | -0,077 a 0,054 | 1.544 |
| A | cada variable sola | arena por metro de rama | -0,016 | -0,086 a 0,038 | 1.544 |
| A | cada variable sola | depleción del padre | 0,022 | -0,083 a 0,104 | 1.544 |
| A | cada variable sola | presión máxima de tratamiento | 0,019 | -0,033 a 0,100 | 1.544 |
| A | solo Tapón disparo | arena por etapa | 0,014 | -0,071 a 0,064 | 1.244 |
| A | solo Tapón disparo | arena por metro de rama | -0,035 | -0,106 a 0,032 | 1.244 |
| A | solo Tapón disparo | depleción del padre | 0,046 | -0,077 a 0,149 | 1.244 |
| A | solo Tapón disparo | presión máxima de tratamiento | 0,035 | -0,011 a 0,086 | 1.244 |
| B | variables como rangos percentil | arena por etapa | 0,041 | -0,113 a 0,174 | 1.395 |
| B | variables como rangos percentil | arena por metro de rama | -0,012 | -0,212 a 0,156 | 1.395 |
| B | variables como rangos percentil | depleción del padre | 0,043 | -0,143 a 0,215 | 1.395 |
| B | variables como rangos percentil | presión máxima de tratamiento | -0,013 | -0,180 a 0,166 | 1.395 |
| B | sin dummies de terminación | arena por etapa | 0,020 | -0,179 a 0,132 | 1.395 |
| B | sin dummies de terminación | arena por metro de rama | -0,047 | -0,203 a 0,104 | 1.395 |
| B | sin dummies de terminación | depleción del padre | 0,095 | -0,112 a 0,293 | 1.395 |
| B | sin dummies de terminación | presión máxima de tratamiento | 0,051 | -0,221 a 0,170 | 1.395 |
| B | cada variable sola | arena por etapa | 0,018 | -0,177 a 0,140 | 1.395 |
| B | cada variable sola | arena por metro de rama | -0,025 | -0,197 a 0,099 | 1.395 |
| B | cada variable sola | depleción del padre | 0,095 | -0,109 a 0,294 | 1.395 |
| B | cada variable sola | presión máxima de tratamiento | 0,050 | -0,215 a 0,174 | 1.395 |
| B | solo Tapón disparo | arena por etapa | 0,028 | -0,164 a 0,135 | 1.124 |
| B | solo Tapón disparo | arena por metro de rama | -0,080 | -0,254 a 0,075 | 1.124 |
| B | solo Tapón disparo | depleción del padre | 0,169 | -0,064 a 0,404 | 1.124 |
| B | solo Tapón disparo | presión máxima de tratamiento | -0,017 | -0,159 a 0,122 | 1.124 |

## Qué no prueba

- Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real y la geometría de la fractura no están en el dato público, y el hijo más cercano puede no ser el que golpeó al padre.
- Un coeficiente positivo no separa el golpe de un cierre preventivo más largo cuanto más grande es el trabajo: la dosis puede mover la decisión del operador. Si hubiera una respuesta que crece con la dosis, crecería bajo las dos lecturas.
- Los eventos de un mismo hijo comparten pad y calendario; el bootstrap por pads cubre eso, no la dependencia entre pads.
- Los datos de presión de la base pública tienen ceros y valores atípicos: los ceros cuentan como faltantes y solo entran presiones entre 0 y 20.000 psi.
