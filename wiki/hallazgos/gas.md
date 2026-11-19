# El padre en la ventana de gas

Página generada por `pipeline/gas.py`. Todo el estudio de eventos mide al padre en petróleo; esta página repite el diseño con padres gasíferos (`tipo_pozo` 'Gasífero') y el gas como resultado, para un operador de Vaca Muerta que también desarrolla la ventana de gas. La regla, la muestra mínima y el veredicto se fijaron en el código antes de correr. Complementa [Interferencia entre fracturas](interferencia.md) y las [pruebas de falsación](placebo.md).

## Resumen

- **Veredicto: no firme.** La brecha del mes 1 tiene la forma de "sostiene" (menor que -10 puntos con IC por bloques de 5 km bajo cero), pero no pasa la pretendencia (C2).
- Brecha del gas del mes 1 (volumen, por día calendario): -12,5 puntos de índice (IC 95% por bloques de 5 km: -27,1 a -3,6; por pads hijo: -21,6 a -7,3), con 472 eventos cercanos y 2.807 controles en 52 bloques de 5 km.
- Pretendencia: con la base de los meses -6 a -4, la brecha entre cercanos y controles ya es de -7,3 puntos en el mes -1, antes de la fractura (IC 95% por pads: -10,8 a -3,2), y llega a -17,4 en el mes 1.
- Cota superior de la caída del mes 1 compatible con el dato público: 27,1 puntos de índice.
- Mes 6: -3,5 puntos (IC 95% por bloques de 5 km: -12,0 a 4,3): se cierra a los 6 meses.
- Días o caudal: la caída del volumen está en los días producidos y no en el caudal por día. Por día efectivo la brecha del mes 1 es -3,4 puntos (IC 95% por bloques de 5 km: -8,7 a 2,9). Con datos mensuales un cierre preventivo y un daño se ven igual: esta lectura no los separa.
- Gas diferido por evento cercano en los meses 0 a 6, contra el índice mediano de los controles: mediana de 2,67 millones de m3 (469 eventos con los 7 meses). Sin descontar la pretendencia ni los solapes entre eventos del mismo padre.
- GOR de los padres petrolíferos: la brecha del índice de la relación gas petróleo es -1,4 puntos al mes 1 (IC 95% por pads: -3,9 a 0,6) y 0,2 al mes 6 (IC 95%: -4,0 a 3,5).

## Regla fijada antes de correr

Mismos eventos que el resultado principal de petróleo: el hijo más cercano fija la banda (cercano a menos de 1 km, control de 2 a 5 km), el padre tiene al menos 6 meses de producción y el índice es el caudal del mes sobre la media de los meses -3 a -1. Cambia el padre (pozos 'Gasífero', edad desde el primer mes con gas o petróleo) y la base mínima: 1,0 mil m3 de gas por día, del orden en energía del umbral de 1 m3 de petróleo por día.

- Resultado primario (V): gas del mes por día calendario. Secundario (E): gas por día efectivo, en meses con días efectivos.
- Veredicto con el IC por bloques de 5 km de V al mes 1. Sostiene: brecha menor que -10 puntos con IC bajo cero, y pasan C1 (ninguna de las cuatro fechas falsas, de -12, -6, 6 y 12 meses, da una brecha menor que -10 puntos con IC por pads bajo cero) y C2 (con base -6 a -4, la brecha del mes -1 queda a menos de 5 puntos o su IC incluye cero). No se sostiene: IC que incluye cero y brecha a menos de 5 puntos. No firme: cualquier otro caso. Sin muestra: menos de 100 cercanos, 100 controles o 30 bloques de 5 km.
- Descriptivo, sin veredicto propio: el cierre al mes 6, la lectura de días o caudal, el gas diferido y el GOR de los padres petrolíferos.

## Resultados

Brechas en puntos de índice (mediana de los cercanos menos mediana de los controles).

| Resultado | Mes | Cercanos | Controles | Índice cercano | Índice control | Brecha | IC 95% por pads | IC 95% por bloques de 5 km |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Volumen (día calendario) | 1 | 472 | 2.807 | 0,776 | 0,901 | -12,5 | -21,6 a -7,3 | -27,1 a -3,6 |
| Volumen (día calendario) | 6 | 469 | 2.772 | 0,726 | 0,761 | -3,5 | -9,8 a 3,2 | -12,0 a 4,3 |
| Caudal por día efectivo | 1 | 421 | 2.668 | 0,862 | 0,896 | -3,4 | -7,5 a 0,2 | -8,7 a 2,9 |
| Caudal por día efectivo | 6 | 435 | 2.605 | 0,730 | 0,781 | -5,1 | -9,0 a -0,8 | -10,4 a 3,5 |

Fechas falsas (C1), brecha del mes 1 del volumen con la fecha de fractura del hijo corrida:

| Desplazamiento (meses) | Eventos cercanos | Brecha | IC 95% por pads | Brecha real en los mismos eventos |
| ---: | ---: | ---: | --- | ---: |
| 0 | 472 | -12,5 | -23,2 a -7,4 | -12,5 |
| -12 | 292 | -6,2 | -10,3 a -2,4 | -17,2 |
| -6 | 358 | -5,1 | -9,1 a -0,7 | -14,5 |
| 6 | 440 | -4,4 | -10,9 a -0,1 | -11,6 |
| 12 | 402 | -1,4 | -8,9 a 4,7 | -11,9 |

Pretendencia (C2), volumen con la base de los meses -6 a -4:

| Mes | Cercanos | Controles | Brecha | IC 95% por pads |
| ---: | ---: | ---: | ---: | --- |
| -3 | 472 | 2.768 | -3,9 | -6,5 a -1,1 |
| -2 | 472 | 2.768 | -4,8 | -7,7 a -1,5 |
| -1 | 472 | 2.768 | -7,3 | -10,8 a -3,2 |
| 0 | 472 | 2.768 | -14,6 | -20,2 a -9,9 |
| 1 | 472 | 2.768 | -17,4 | -22,8 a -10,8 |
| 2 | 472 | 2.768 | -15,5 | -21,8 a -9,1 |
| 3 | 472 | 2.768 | -15,3 | -20,4 a -9,5 |

GOR de los padres petrolíferos (eventos del resultado principal de petróleo):

| Mes | Cercanos | Controles | Brecha | IC 95% por pads |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1.909 | 17.512 | -1,4 | -3,9 a 0,6 |
| 6 | 1.823 | 15.881 | 0,2 | -4,0 a 3,5 |

Las fechas falsas dan brechas de -6,2 a -1,4 puntos; como en el estudio de petróleo, una fecha falsa puede caer sobre el golpe de otro hijo cercano, así que una brecha distinta de cero en una fecha falsa tiene más de una lectura.

## Qué quiere decir para un operador

- El padre gasífero cercano produce menos gas el mes siguiente a la fractura del hijo, pero ya venía rindiendo menos que los controles antes de la fractura: con la regla fijada, el resultado no alcanza para atribuir la caída a la fractura.
- En la mediana la caída está en los días producidos, no en el caudal por día efectivo, y a los 6 meses la brecha queda a menos de 5 puntos: es compatible con cierres del padre durante la fractura del hijo, que con datos mensuales no se separan de un daño.

## Límites

- Es una huella medida contra un control, no una prueba de causa. Las coordenadas son de superficie, no de la rama.
- `tipo_pozo` es lo que declara el operador en su último mes; un pozo puede haber cambiado de ventana.
- El gas diferido no descuenta la pretendencia ni los solapes, así que no se suma a la cifra de petróleo diferido.
- Los intervalos no se ajustan por comparaciones múltiples (dos resultados, dos meses, dos unidades de remuestreo y el GOR).
