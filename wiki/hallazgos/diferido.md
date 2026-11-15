# Barriles diferidos: un rango y una cifra por evento

Página generada por `pipeline/diferido.py`. El total de barriles diferidos del estudio de interferencia se citaba como una sola cifra. Un revisor puede objetar que esa cifra cuenta dos veces los meses de un padre al que le fracturaron varios hijos seguidos, y que no descuenta que los padres cercanos ya rendían por debajo del control antes de la fractura. Acá se responde con un rango y con cifras por evento.

## Qué se cuenta

Para cada evento cercano (un padre a menos de 1 km de un hijo recién fracturado) y cada mes desde la fractura, el diferido del mes es el caudal que habría tenido el padre al ritmo del control de la misma edad, menos el caudal observado, por los días del mes, en barriles. Es diferido contra el control de la misma edad: producción que se atrasa, medida contra un control, sin precio y sin una causa atribuida.

## Los tres totales (meses 0 a 6)

| Variante | Barriles diferidos | Eventos | Meses de padre | Barriles por evento |
|---|---|---|---|---|
| Original (cota superior) | 10.723.754 | 2.077 | 14.257 | 5.163 |
| Sin duplicar | 8.024.400 | 2.073 | 11.750 | 3.871 |
| Sin duplicar y descontando la brecha previa (cota inferior) | 5.812.431 | 2.073 | 11.750 | 2.804 |

- Original: 10.723.754 barriles. Suma los meses 0 a 6 de cada evento; un mismo mes de un padre con varios hijos puede entrar más de una vez.
- Sin duplicar: 8.024.400 barriles. Cada mes de calendario de un padre se atribuye una sola vez, al evento más cercano en el tiempo entre los que lo preceden (el de la fecha de fractura más reciente que no pasa del mes).
- Sin duplicar y descontando la brecha previa: 5.812.431 barriles. A cada mes se le resta la brecha previa a la fractura, 4,1 puntos del nivel de la base de cada padre (el promedio de la brecha cercano menos control de los meses -3 a -1 en la base limpia de la página de falsación), constante y cortada en cero para que la resta no vuelva negativo un mes con diferido positivo.

El diferido de los meses 0 a 6 va de 5,8 a 10,7 millones de barriles. No se da un punto medio: el rango dice qué tanto depende la cifra de cómo se cuente, no cuál es la verdadera.

## Por evento, a 24 meses

El acumulado de los meses 0 a 24 desde la fractura del hijo, por evento y contra el control de la misma edad, sin las correcciones de arriba (es lo que ese padre difiere en la ventana, aunque otro hijo le haya pegado en el medio). Entran los eventos con la ventana completa dentro de los datos.

| Eventos | P25 (bbl) | Mediana (bbl) | P75 (bbl) | Media (bbl) | Con diferido positivo |
|---|---|---|---|---|---|
| 1.408 | -16.080 | -1.200 | 12.353 | -2.830 | 47% |

Intervalo de 95% de la mediana: -2.550 a 4 barriles; de la media: -6.503 a 1.337 barriles (bootstrap por pads hijo, 400 repeticiones).

La mediana por evento a 24 meses (-1.200 barriles) queda por debajo de cero: a los 24 meses el padre típico no acumula diferido contra su control, y el intervalo de 95% de la mediana incluye el cero (no se distingue de un padre sin diferido a esa altura). Es otro horizonte que el de los totales de arriba (meses 0 a 6): el diferido del primer tramo y el acumulado a 24 meses no se suman ni se restan.

## Por operadora del padre, por evento

| Operadora | Eventos | Mediana por evento (bbl, IC 95%) | Media por evento (bbl, IC 95%) | Con diferido positivo |
|---|---|---|---|---|
| Toda la cuenca | 1.408 | -1.200 (-2.550 a 4) | -2.830 (-6.503 a 1.337) | 47% |
| YPF | 983 | -767 (-2.169 a 325) | -3.672 (-8.029 a 1.243) | 47% |
| Tecpetrol | 127 | -4.961 (-7.655 a -1.590) | -3.764 (-7.100 a 530) | 35% |
| Vista | 109 | 5.205 (-9.641 a 10.329) | -1.770 (-16.314 a 9.402) | 57% |
| Pan American Energy | 96 | -6.322 (-19.511 a 13.530) | -1.227 (-9.798 a 12.188) | 44% |
| Shell | 48 | 2.033 (-16.587 a 15.181) | 4.513 (-11.847 a 25.514) | 52% |
| Otras (menos de 30 eventos) | 45 | 893 (-5.013 a 9.020) | 4.357 (-9.701 a 23.771) | 53% |

El reparto por operadora no es una comparación de desempeño: cambian el tipo de pozo, la edad y las prácticas de declaración. Los intervalos son bootstrap de percentiles por conglomerados de pads hijo, sin ajuste por comparaciones múltiples.

## Límites

- Los datos son mensuales: un cierre y un golpe dentro del mes se ven igual.
- El control de la misma edad a 2 a 5 km no es un cero limpio: puede estar también afectado por las fracturas cercanas (la página de descomposición mira el anillo de 5 a 10 km). Si lo está, el diferido medido contra él queda corto.
- La brecha previa se mide en la base de los meses -6 a -4 y se aplica sobre la base de los meses -3 a -1; la corrección es una aproximación y por eso se publica como cota y no como valor.
- A 24 meses el control de la misma edad también declina con la edad y su mediana no es la media: el acumulado largo se lee por su signo y su intervalo, no como un nivel.
- Un mes sin fila de producción no suma ni resta.
- Es una huella medida, no una causa demostrada.

## Cómo se reproduce

`uv run python -m pipeline.diferido` (después de `pipeline.placebo`) escribe `mart_diferido_rango` y `mart_diferido_operador`; esta página sale de esas dos tablas.
