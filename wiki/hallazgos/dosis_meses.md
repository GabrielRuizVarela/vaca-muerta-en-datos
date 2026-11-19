# Dosis y respuesta mes a mes: caudal por día, k = 1 a 4

Página generada por `pipeline/dosis_meses.py`. Pregunta si la caída del caudal por día del padre crece con el 
trabajo del hijo y la depleción en cada mes k = 1 a 4, porque un golpe que se note con retraso no aparece 
en el mes 1. Mismo modelo conjunto de pipeline.dosis (resultado B) en cada mes, con Holm sobre 16 celdas.
Prueba agregada después de ver los resultados de pipeline.dosis: la regla se fijó antes de correr, pero la pregunta nació de ese resultado.

## Veredicto

**tampoco con respuesta tardia**: tampoco aparece una respuesta en los meses 2 a 4: ninguna de las 16 celdas cumple tras Holm.

Reproducción de pipeline.dosis en k = 1: reproduce pipeline.dosis (diferencia máxima 0,0000).

### Mes 1 (n = 1.395, pads = 247)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena por etapa | 0,015 | -0,196 a 0,139 | 1,000 | no |
| arena por metro de rama | -0,033 | -0,201 a 0,106 | 1,000 | no |
| presión máxima de tratamiento | 0,053 | -0,210 a 0,178 | 1,000 | no |
| depleción del padre | 0,096 | -0,104 a 0,292 | 1,000 | no |

### Mes 2 (n = 1.415, pads = 249)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena por etapa | -0,012 | -0,203 a 0,136 | 1,000 | no |
| arena por metro de rama | 0,061 | -0,139 a 0,259 | 1,000 | no |
| presión máxima de tratamiento | 0,017 | -0,176 a 0,150 | 1,000 | no |
| depleción del padre | 0,147 | -0,080 a 0,363 | 1,000 | no |

### Mes 3 (n = 1.410, pads = 247)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena por etapa | 0,037 | -0,034 a 0,183 | 1,000 | no |
| arena por metro de rama | 0,043 | -0,071 a 0,140 | 1,000 | no |
| presión máxima de tratamiento | 0,023 | -0,159 a 0,126 | 1,000 | no |
| depleción del padre | 0,144 | -0,056 a 0,318 | 1,000 | no |

### Mes 4 (n = 1.406, pads = 248)

| Variable | Coef por desvío | IC 95% | p Holm | Cumple |
| --- | ---: | --- | ---: | --- |
| arena por etapa | 0,037 | -0,038 a 0,154 | 1,000 | no |
| arena por metro de rama | -0,002 | -0,100 a 0,070 | 1,000 | no |
| presión máxima de tratamiento | 0,003 | -0,111 a 0,173 | 1,000 | no |
| depleción del padre | 0,222 | 0,044 a 0,360 | 0,256 | no |

## Qué no prueba

- Un coeficiente nulo no dice que no haya golpes de fractura: el espaciamiento real y la geometría 
no están en el dato público.
- A mayor k la muestra y la potencia bajan: menos eventos con caudal por día positivo y más dependencia 
con el ciclo del pozo.
- Los intervalos son por pads hijo; los eventos de un mismo padre en meses distintos no son independientes 
entre sí.
