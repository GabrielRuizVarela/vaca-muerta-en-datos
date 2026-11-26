# Dosis y respuesta mes a mes: caudal por día, k = 1 a 4

Página generada por `pipeline/dosis_meses.py`. Pregunta si la caída del caudal por día del padre crece con el 
trabajo del hijo y la depleción en cada mes k = 1 a 4, porque un golpe que se note con retraso no aparece 
en el mes 1. Mismo modelo conjunto de pipeline.dosis (resultado B) en cada mes, con Holm sobre 16 celdas.
Prueba agregada después de ver los resultados de pipeline.dosis: la regla se fijó antes de correr, pero la pregunta nació de ese resultado.

## Veredicto

**tampoco con respuesta tardia**: tampoco aparece una respuesta en los meses 2 a 4: ninguna de las 16 celdas cumple tras Holm.

Reproducción de pipeline.dosis en k = 1: reproduce pipeline.dosis (diferencia máxima 0,0000).

### Mes 1 (n = 1.402, pads = 248)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena por etapa | 0,021 | -0,186 a 0,149 | 1,000 | no |
| arena por metro de rama | -0,029 | -0,198 a 0,107 | 1,000 | no |
| presión máxima de tratamiento | 0,052 | -0,221 a 0,175 | 1,000 | no |
| depleción del padre | 0,095 | -0,102 a 0,290 | 1,000 | no |

### Mes 2 (n = 1.429, pads = 251)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena por etapa | -0,014 | -0,199 a 0,142 | 1,000 | no |
| arena por metro de rama | 0,071 | -0,140 a 0,273 | 1,000 | no |
| presión máxima de tratamiento | 0,016 | -0,172 a 0,149 | 1,000 | no |
| depleción del padre | 0,133 | -0,099 a 0,362 | 1,000 | no |

### Mes 3 (n = 1.426, pads = 249)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena por etapa | 0,038 | -0,032 a 0,193 | 1,000 | no |
| arena por metro de rama | 0,044 | -0,068 a 0,140 | 1,000 | no |
| presión máxima de tratamiento | 0,022 | -0,151 a 0,136 | 1,000 | no |
| depleción del padre | 0,146 | -0,053 a 0,323 | 1,000 | no |

### Mes 4 (n = 1.412, pads = 249)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena por etapa | 0,037 | -0,033 a 0,152 | 1,000 | no |
| arena por metro de rama | -0,002 | -0,100 a 0,074 | 1,000 | no |
| presión máxima de tratamiento | 0,001 | -0,117 a 0,162 | 1,000 | no |
| depleción del padre | 0,227 | 0,052 a 0,359 | 0,224 | no |

## Qué no prueba

- Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real y la geometría 
no están en el dato público.
- A mayor k la muestra y la potencia bajan: menos eventos con caudal por día positivo y más dependencia 
con el ciclo del pozo.
- Los intervalos son por pads hijo; los eventos de un mismo padre en meses distintos no son independientes 
entre sí.
