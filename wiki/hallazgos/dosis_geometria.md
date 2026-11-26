# Dosis con la geometría de las ramas, detrás de una puerta de potencia

La regla se fijó antes de calcular cualquier número, en el commit 59b3a26, y no se cambia después de ver resultados. Se publican todos los modelos que se calculen, favorables o no. Esta página la genera `python -m pipeline.wiki` y no se edita a mano.

## Lectura

- Muestra, resultado A: 2.094 eventos de dosis, 921 con el par (hijo, padre) medido entre ramas, 493 cercanos entre ramas (m_min menor que 600 m), 464 de caso completo y 134 pads hijo.
- Muestra, resultado B: 2.094 eventos de dosis, 921 con el par (hijo, padre) medido entre ramas, 493 cercanos entre ramas (m_min menor que 600 m), 395 de caso completo y 122 pads hijo.
- Puerta: **la geometría no da más potencia**: el menor MDE80 de Holm del resultado A es de 0,34 desvíos de la caída por desvío de la dosis: medir los padres cercanos entre ramas no baja el efecto mínimo detectable por debajo de 0,22 desvíos de la caída por desvío de la dosis. Esto no dice que no haya dosis y respuesta ni golpes de fractura: la potencia dice qué tamaño de efecto hace falta para verse.
- Comparación: el menor MDE80 de Holm del resultado A es de 0,34 desvíos de la caída por desvío de la dosis y el mayor es de 0,52, contra la referencia de 0,22 (el mejor MDE80 de Holm de hoy). Hoy (pipeline.potencia_dosis, modelo conjunto A) los cuatro MDE80 de Holm van de 0,22 a 0,31. La muestra de hoy tiene 1.551 eventos y 263 pads hijo; la de esta página es la parte con las dos ramas medidas y cercana entre ramas.
- Simulación de planta y recupera: la potencia empírica no valida la cuenta analítica; la puerta sigue siendo la analítica.
- Modelo de dosis sobre esta muestra: no se corrió, la puerta no pasó.

## La puerta de potencia

MDE80: efecto mínimo con 80% de potencia a dos colas con alfa 0,05, desde el ancho del intervalo de percentiles del bootstrap por pads hijo. La versión con Holm es la conservadora (paso más exigente sobre 4 pruebas). De la puerta no se lee ni se publica ningún coeficiente.

### Resultado A (n = 464, pads = 134)

| Variable | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: |
| arena por etapa | 0,137 | 0,384 | 0,458 |
| arena por metro de rama | 0,116 | 0,325 | 0,387 |
| presión máxima de tratamiento | 0,100 | 0,281 | 0,335 |
| depleción del padre | 0,156 | 0,438 | 0,522 |

### Resultado B (n = 395, pads = 122)

| Variable | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: |
| arena por etapa | 0,164 | 0,460 | 0,548 |
| arena por metro de rama | 0,127 | 0,356 | 0,424 |
| presión máxima de tratamiento | 0,114 | 0,318 | 0,379 |
| depleción del padre | 0,131 | 0,366 | 0,436 |

## Pads y eventos para ver 0,1 y 0,2 desvíos

Pads y eventos necesarios para que el MDE80 con Holm llegue a cada objetivo. Si el número necesario es menor que el actual (factor menor que 1), la muestra actual ya alcanza para ese objetivo. La cuenta supone eventos por pad constantes: el error baja como 1 sobre la raíz del número de pads.

### Resultado A (actual: n = 464, pads = 134)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,2 | Eventos 0,2 |
| --- | ---: | ---: | ---: | ---: |
| arena por etapa | 2.809 | 9.728 | 702 | 2.432 |
| arena por metro de rama | 2.008 | 6.953 | 502 | 1.738 |
| presión máxima de tratamiento | 1.504 | 5.209 | 376 | 1.302 |
| depleción del padre | 3.652 | 12.646 | 913 | 3.162 |

## Simulación de planta y recupera

Se ajusta el modelo conjunto A sobre la muestra, se le quita a la caída el efecto estimado de las cuatro variables, se planta un efecto delta por variable y se reajusta con bootstrap por pads. La tabla da la potencia empírica con su error de Monte Carlo.

| Variable | Nivel | Delta (desvíos) | Regla | Potencia | Error | Aciertos | Corridas |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| arena por etapa | sin efecto | 0,000 | Holm | 0,005 | 0,005 | 1 | 200 |
| arena por etapa | sin efecto | 0,000 | sin ajustar | 0,045 | 0,015 | 9 | 200 |
| arena por metro de rama | sin efecto | 0,000 | Holm | 0,005 | 0,005 | 1 | 200 |
| arena por metro de rama | sin efecto | 0,000 | sin ajustar | 0,015 | 0,009 | 3 | 200 |
| presión máxima de tratamiento | sin efecto | 0,000 | Holm | 0,005 | 0,005 | 1 | 200 |
| presión máxima de tratamiento | sin efecto | 0,000 | sin ajustar | 0,040 | 0,014 | 8 | 200 |
| depleción del padre | sin efecto | 0,000 | Holm | 0,000 | 0,000 | 0 | 200 |
| depleción del padre | sin efecto | 0,000 | sin ajustar | 0,005 | 0,005 | 1 | 200 |
| arena por etapa | 0,1 | 0,100 | Holm | 0,020 | 0,010 | 4 | 200 |
| arena por etapa | 0,1 | 0,100 | sin ajustar | 0,110 | 0,022 | 22 | 200 |
| arena por metro de rama | 0,1 | 0,100 | Holm | 0,030 | 0,012 | 6 | 200 |
| arena por metro de rama | 0,1 | 0,100 | sin ajustar | 0,150 | 0,025 | 30 | 200 |
| presión máxima de tratamiento | 0,1 | 0,100 | Holm | 0,205 | 0,029 | 41 | 200 |
| presión máxima de tratamiento | 0,1 | 0,100 | sin ajustar | 0,540 | 0,035 | 108 | 200 |
| depleción del padre | 0,1 | 0,100 | Holm | 0,000 | 0,000 | 0 | 200 |
| depleción del padre | 0,1 | 0,100 | sin ajustar | 0,040 | 0,014 | 8 | 200 |
| arena por etapa | 0,2 | 0,200 | Holm | 0,095 | 0,021 | 19 | 200 |
| arena por etapa | 0,2 | 0,200 | sin ajustar | 0,295 | 0,032 | 59 | 200 |
| arena por metro de rama | 0,2 | 0,200 | Holm | 0,125 | 0,023 | 25 | 200 |
| arena por metro de rama | 0,2 | 0,200 | sin ajustar | 0,340 | 0,033 | 68 | 200 |
| presión máxima de tratamiento | 0,2 | 0,200 | Holm | 0,425 | 0,035 | 85 | 200 |
| presión máxima de tratamiento | 0,2 | 0,200 | sin ajustar | 0,770 | 0,030 | 154 | 200 |
| depleción del padre | 0,2 | 0,200 | Holm | 0,025 | 0,011 | 5 | 200 |
| depleción del padre | 0,2 | 0,200 | sin ajustar | 0,135 | 0,024 | 27 | 200 |
| arena por etapa | 0,22 (referencia) | 0,220 | Holm | 0,090 | 0,020 | 18 | 200 |
| arena por etapa | 0,22 (referencia) | 0,220 | sin ajustar | 0,355 | 0,034 | 71 | 200 |
| arena por metro de rama | 0,22 (referencia) | 0,220 | Holm | 0,145 | 0,025 | 29 | 200 |
| arena por metro de rama | 0,22 (referencia) | 0,220 | sin ajustar | 0,360 | 0,034 | 72 | 200 |
| presión máxima de tratamiento | 0,22 (referencia) | 0,220 | Holm | 0,465 | 0,035 | 93 | 200 |
| presión máxima de tratamiento | 0,22 (referencia) | 0,220 | sin ajustar | 0,790 | 0,029 | 158 | 200 |
| depleción del padre | 0,22 (referencia) | 0,220 | Holm | 0,040 | 0,014 | 8 | 200 |
| depleción del padre | 0,22 (referencia) | 0,220 | sin ajustar | 0,180 | 0,027 | 36 | 200 |
| arena por etapa | MDE80 sin ajustar | 0,384 | Holm | 0,445 | 0,035 | 89 | 200 |
| arena por etapa | MDE80 sin ajustar | 0,384 | sin ajustar | 0,750 | 0,031 | 150 | 200 |
| arena por metro de rama | MDE80 sin ajustar | 0,325 | Holm | 0,315 | 0,033 | 63 | 200 |
| arena por metro de rama | MDE80 sin ajustar | 0,325 | sin ajustar | 0,670 | 0,033 | 134 | 200 |
| presión máxima de tratamiento | MDE80 sin ajustar | 0,281 | Holm | 0,595 | 0,035 | 119 | 200 |
| presión máxima de tratamiento | MDE80 sin ajustar | 0,281 | sin ajustar | 0,900 | 0,021 | 180 | 200 |
| depleción del padre | MDE80 sin ajustar | 0,438 | Holm | 0,380 | 0,034 | 76 | 200 |
| depleción del padre | MDE80 sin ajustar | 0,438 | sin ajustar | 0,760 | 0,030 | 152 | 200 |
| arena por etapa | MDE80 de Holm | 0,458 | Holm | 0,585 | 0,035 | 117 | 200 |
| arena por etapa | MDE80 de Holm | 0,458 | sin ajustar | 0,875 | 0,023 | 175 | 200 |
| arena por metro de rama | MDE80 de Holm | 0,387 | Holm | 0,480 | 0,035 | 96 | 200 |
| arena por metro de rama | MDE80 de Holm | 0,387 | sin ajustar | 0,805 | 0,028 | 161 | 200 |
| presión máxima de tratamiento | MDE80 de Holm | 0,335 | Holm | 0,720 | 0,032 | 144 | 200 |
| presión máxima de tratamiento | MDE80 de Holm | 0,335 | sin ajustar | 0,935 | 0,017 | 187 | 200 |
| depleción del padre | MDE80 de Holm | 0,522 | Holm | 0,600 | 0,035 | 120 | 200 |
| depleción del padre | MDE80 de Holm | 0,522 | sin ajustar | 0,925 | 0,019 | 185 | 200 |

Tamaño (sin efecto plantado): la fracción que se ve va de 0,005 a 0,045 con la regla sin ajustar y de 0,000 a 0,005 con Holm, entre las cuatro variables.

La simulación no valida la cuenta analítica: la potencia empírica en algún MDE80 (con su regla) queda fuera de 0,70 a 0,90, así que la cuenta analítica es optimista. La puerta sigue siendo la analítica.

Agregado después de ver los resultados (no cambia la puerta): parte de la diferencia puede venir de la resolución del bootstrap de la simulación. Con B = 300 el p mínimo posible es 2 sobre 301, y con Holm sobre cuatro pruebas la variable de menor p solo pasa si ningún sorteo cae del lado contrario, un umbral más exigente que el normal de la cuenta analítica.

## Cómo se mide

- Muestra: los eventos de pipeline.dosis (los eventos cercano de int_interferencia_evento) cuyo par (hijo, padre) está en mart_trayectoria_par y cuya distancia entre ramas en planta `m_min` es menor que 600 m. El caso completo, los controles, las dummies de terminación, las celdas de efectos fijos y la estandarización se rehacen dentro del subconjunto con las mismas funciones de pipeline.dosis.
- Puerta: el menor de los cuatro MDE80 de Holm del resultado A se compara con la referencia de 0,22 desvíos de la caída por desvío de la dosis. Pasa si es menor. La regla se fijó antes de calcular cualquier número y no se cambia después de ver resultados.
- Decide la regla, no el resultado: si la puerta no pasa, la unidad termina y no se publica ningún coeficiente de dosis sobre esta muestra.
- El resultado A (caída del índice al mes 1) decide; el resultado B (caudal por día) se informa aparte y no cambia ningún veredicto.

## Qué no es

- La potencia es sobre el efecto lineal de la dosis estandarizada con la forma del modelo; no dice nada de efectos no lineales, de umbrales ni de interacciones. El error estándar sale de un intervalo de percentiles y la simulación lo contrasta solo para el modelo conjunto A.
- La muestra es la parte de los eventos de dosis con las dos ramas medidas y cercana entre ramas. Las trayectorias laterales cubren el 76 a 98% de los hijos fracturados de 2016 a 2023 (86% en conjunto) pero solo el 39% de los de 2024 y el 25% de los de 2025, así que la muestra es sobre todo de 2016 a 2023.
- Un padre con la rama a menos de 600 m de la del hijo pero con la boca a 1 km o más no está en la muestra de dosis (los eventos de dosis son los de menos de 1 km en superficie): esta página no lo corrige.
- "La geometría no da más potencia" dice que este dato, con esta definición de cercano, no alcanza para ver un efecto menor que 0,22 desvíos de la caída; no dice que no haya dosis y respuesta ni golpes de fractura.
- Medir entre ramas no mide el espaciamiento real ni la geometría de la fractura: es la distancia en planta de las ramas.
- La definición de cercano usa el hijo de pipeline.dosis (el más cercano en superficie); un padre golpeado por otro hijo del pad queda clasificado por el hijo más cercano en superficie.

## Reproducir

1. `uv run python -m pipeline.dosis_geometria` (necesita pipeline.trayectorias y pipeline.potencia_dosis antes)
2. `uv run python -m pipeline.wiki`
3. `uv run python -m pipeline.claims`
