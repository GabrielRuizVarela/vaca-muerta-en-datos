# Descomposición de la brecha de interferencia

Página generada por `pipeline/descomposicion.py`. Responde lo primero que pregunta un ingeniero de reservorio sobre el resultado de interferencia: si la brecha es un golpe de fractura (baja el caudal por día producido) o son cierres (bajan los días producidos), y cómo cambia con la distancia.

## Qué se mide

Los eventos son los del estudio de eventos de interferencia (mismos padres elegibles a menos de 1 km del hijo y controles de 2 a 5 km, mismo hijo más cercano, misma edad mínima y misma base positiva). La base de cada padre son los meses -6 a -4 (la base limpia de la página de falsación), para que la pretendencia se vea y no quede absorbida. k = 0 es el mes de la fractura del hijo. Los IC 95% son bootstrap por pads hijo (400 repeticiones, con la semilla de la página de falsación para el mismo k, así que la misma brecha tiene el mismo intervalo en las dos páginas).

- Petróleo: caudal por día calendario del mes sobre su base (el índice principal).
- Días efectivos: días producidos del mes sobre días del mes, sobre su base.
- Petróleo por día efectivo: volumen del mes sobre los días producidos, sobre su base. Los meses sin días producidos no tienen caudal por día y quedan fuera de ese panel (un mes cerrado entero baja los días y el volumen, no este panel).
- Corte de agua: agua sobre agua más petróleo; la brecha es el cambio del corte respecto de su base, en puntos de corte.

## Descomposición aditiva

Las medianas no se suman: la mediana del volumen no es la de los días más la del caudal por día, y con los días agrupados en 1 (muchos padres producen todos los días) la mediana de los días casi no se mueve aunque una parte de los padres pierda días. Por eso la partición de la brecha se hace con medias de logaritmos sobre los mismos eventos: el volumen es días por caudal por día efectivo, así que el logaritmo de su índice es la suma de los otros dos (se usa esa suma como índice de volumen de esta sección, que difiere del índice principal porque cada base es la media de su propia serie). La brecha es la media de los cercanos menos la de los controles, en puntos logarítmicos (100 veces la diferencia de logaritmos naturales), y la parte de cada panel es su brecha sobre la del volumen.

Los ceros se tratan así. Un mes con cero días efectivos (cerrado entero) no tiene logaritmo de los días ni caudal por día: en la variante con cerrados sus días se acotan a un día de 30 (0,033 del mes) y su caudal por día queda sin cambio; en la variante sin cerrados esos eventos se dejan fuera. Un mes con días positivos y petróleo cero queda fuera en las dos. Los eventos sin dato de volumen, días o base positiva en el mes k también quedan fuera. La variante con cerrados depende del piso de un día (un piso menor da más peso a los días), así que se muestran las dos.

### Con los meses cerrados enteros (días acotados a un día de 30)

| k | Eventos cercanos | Eventos control | Brecha del volumen (IC 95%) | Días efectivos (IC 95%) | Caudal por día (IC 95%) | Parte de los días (IC 95%) |
| ---: | ---: | ---: | --- | --- | --- | --- |
| -6 | 2.026 | 17.723 | 1,1 (-3,1 a 5,7) | 0,7 (-2,3 a 3,4) | 0,4 (-2,7 a 3,5) | 61% (-435% a 428%) |
| -5 | 2.023 | 17.740 | 0,4 (-2,6 a 3,3) | 1,5 (-0,8 a 3,2) | -1,1 (-3,2 a 1,1) | 399% (-685% a 1.378%) |
| -4 | 2.031 | 17.756 | 2,6 (-1,2 a 5,8) | 1,7 (-1,3 a 4,3) | 0,9 (-1,1 a 3,0) | 67% (-105% a 373%) |
| -3 | 2.031 | 17.753 | -0,7 (-5,4 a 4,3) | -0,5 (-3,8 a 2,3) | -0,1 (-3,2 a 3,6) | 81% (-844% a 914%) |
| -2 | 2.029 | 17.738 | -4,9 (-12,1 a 1,6) | -3,8 (-9,3 a 1,0) | -1,1 (-5,7 a 2,8) | 78% (-342% a 281%) |
| -1 | 2.023 | 17.708 | -11,1 (-18,3 a -4,4) | -9,4 (-15,3 a -4,0) | -1,7 (-6,0 a 2,6) | 85% (55% a 147%) |
| 0 | 2.023 | 17.749 | -51,0 (-60,9 a -40,5) | -45,4 (-54,6 a -37,1) | -5,6 (-11,6 a -0,1) | 89% (79% a 100%) |
| 1 | 2.020 | 17.705 | -72,5 (-85,0 a -60,6) | -38,3 (-47,5 a -30,3) | -34,2 (-43,2 a -25,7) | 53% (45% a 62%) |
| 2 | 2.009 | 17.568 | -45,1 (-57,7 a -31,2) | -14,9 (-21,7 a -8,2) | -30,2 (-41,4 a -21,1) | 33% (21% a 45%) |
| 3 | 2.002 | 17.483 | -23,7 (-34,2 a -13,1) | -6,6 (-13,3 a -0,1) | -17,1 (-25,0 a -10,3) | 28% (1% a 46%) |
| 4 | 1.999 | 17.277 | -13,7 (-23,2 a -5,3) | -2,6 (-9,0 a 2,6) | -11,1 (-18,6 a -4,6) | 19% (-41% a 52%) |
| 5 | 1.938 | 16.940 | -11,2 (-21,2 a -1,8) | -1,2 (-7,3 a 4,3) | -10,0 (-17,4 a -2,4) | 11% (-111% a 64%) |
| 6 | 1.896 | 16.490 | -10,0 (-19,1 a -2,2) | -0,4 (-6,7 a 5,2) | -9,6 (-16,8 a -3,3) | 4% (-165% a 53%) |
| 7 | 1.857 | 16.253 | -6,3 (-15,9 a 2,1) | 2,2 (-3,5 a 7,9) | -8,5 (-16,1 a -1,8) | -36% (-786% a 513%) |
| 8 | 1.818 | 15.937 | -3,2 (-12,9 a 5,5) | 4,1 (-2,4 a 10,3) | -7,2 (-15,3 a -0,5) | -129% (-1.626% a 1.850%) |
| 9 | 1.784 | 15.673 | 0,7 (-7,4 a 8,1) | 5,1 (-1,4 a 11,1) | -4,3 (-10,6 a 2,2) | 695% (-1.378% a 1.629%) |
| 10 | 1.751 | 15.432 | -3,6 (-13,0 a 4,6) | 0,5 (-6,7 a 7,5) | -4,1 (-11,2 a 1,2) | -13% (-535% a 616%) |
| 11 | 1.733 | 15.104 | -3,8 (-12,3 a 4,4) | 1,9 (-5,5 a 8,3) | -5,7 (-12,7 a 1,3) | -50% (-899% a 923%) |
| 12 | 1.712 | 14.866 | -4,0 (-13,5 a 4,8) | 1,3 (-6,2 a 8,4) | -5,3 (-12,4 a 1,8) | -33% (-822% a 573%) |

### Sin los meses cerrados enteros

| k | Eventos cercanos | Eventos control | Brecha del volumen (IC 95%) | Días efectivos (IC 95%) | Caudal por día (IC 95%) | Parte de los días (IC 95%) |
| ---: | ---: | ---: | --- | --- | --- | --- |
| -6 | 1.996 | 17.368 | 0,0 (-4,4 a 4,0) | -0,4 (-2,8 a 2,1) | 0,5 (-3,1 a 3,3) | -1.030% (-709% a 674%) |
| -5 | 1.997 | 17.465 | -0,2 (-2,8 a 2,5) | 0,9 (-0,5 a 2,2) | -1,1 (-3,8 a 1,1) | -449% (-891% a 966%) |
| -4 | 2.015 | 17.485 | 1,1 (-1,3 a 3,5) | 0,2 (-1,3 a 1,6) | 0,9 (-1,1 a 2,8) | 17% (-282% a 343%) |
| -3 | 2.010 | 17.497 | -1,6 (-6,1 a 3,3) | -1,5 (-3,8 a 0,8) | -0,1 (-3,4 a 3,8) | 95% (-582% a 642%) |
| -2 | 1.982 | 17.446 | -3,0 (-9,7 a 2,4) | -1,8 (-5,1 a 1,3) | -1,2 (-5,9 a 2,6) | 59% (-189% a 457%) |
| -1 | 1.946 | 17.302 | -6,5 (-12,7 a -0,2) | -4,4 (-7,6 a -1,0) | -2,1 (-6,4 a 2,6) | 68% (16% a 407%) |
| 0 | 1.846 | 17.214 | -37,1 (-46,2 a -28,7) | -29,3 (-35,3 a -23,7) | -7,7 (-14,7 a -1,5) | 79% (66% a 95%) |
| 1 | 1.869 | 17.048 | -66,1 (-78,1 a -53,9) | -27,9 (-34,3 a -21,7) | -38,2 (-47,9 a -28,3) | 42% (35% a 50%) |
| 2 | 1.897 | 16.840 | -43,2 (-55,3 a -32,1) | -10,7 (-15,1 a -6,5) | -32,5 (-42,6 a -22,1) | 25% (16% a 35%) |
| 3 | 1.897 | 16.635 | -24,2 (-33,0 a -14,7) | -6,0 (-10,5 a -2,2) | -18,2 (-25,1 a -10,5) | 25% (10% a 39%) |
| 4 | 1.893 | 16.370 | -14,6 (-23,6 a -6,2) | -2,9 (-6,2 a 0,4) | -11,7 (-19,8 a -5,1) | 20% (-4% a 42%) |
| 5 | 1.835 | 15.963 | -13,5 (-22,5 a -4,7) | -3,2 (-7,1 a 0,4) | -10,4 (-18,0 a -3,0) | 23% (-5% a 55%) |
| 6 | 1.786 | 15.470 | -12,1 (-21,0 a -3,7) | -2,1 (-5,5 a 1,1) | -10,0 (-16,9 a -2,2) | 17% (-15% a 52%) |
| 7 | 1.750 | 15.167 | -9,3 (-17,2 a 0,1) | -0,8 (-3,9 a 3,1) | -8,6 (-15,7 a -1,1) | 8% (-100% a 62%) |
| 8 | 1.722 | 14.861 | -7,7 (-15,8 a 0,6) | -0,8 (-4,5 a 3,1) | -6,8 (-13,6 a -0,1) | 11% (-105% a 192%) |
| 9 | 1.685 | 14.540 | -4,2 (-11,1 a 3,4) | -0,6 (-3,9 a 2,7) | -3,7 (-10,6 a 2,8) | 13% (-164% a 426%) |
| 10 | 1.633 | 14.294 | -5,8 (-14,2 a 2,3) | -1,8 (-6,1 a 1,9) | -4,0 (-11,6 a 2,7) | 30% (-83% a 188%) |
| 11 | 1.634 | 13.945 | -9,3 (-16,2 a -1,5) | -4,5 (-8,5 a -0,4) | -4,8 (-11,6 a 1,5) | 48% (1% a 127%) |
| 12 | 1.591 | 13.690 | -6,3 (-13,6 a 2,2) | -1,1 (-5,3 a 2,8) | -5,1 (-12,0 a 2,5) | 18% (-193% a 300%) |

## Cierres al mes 1

Parte de los eventos con el índice de días por debajo de 0,9 (más de 10% de los días perdidos respecto de su base) y parte cerrados todo el mes, cercanos contra control (mismos eventos que el panel de días).

| Grupo | Eventos | Índice de días menor a 0,9 | Cerrados todo el mes |
| --- | ---: | ---: | ---: |
| Cercanos | 2.031 | 45,4% | 7,4% |
| Controles | 17.732 | 20,0% | 3,7% |

## Paneles por mes (medianas, descriptivos)

Brecha de las medianas por panel. Describen cada panel por separado y no se usan para partir la brecha.

### Panel 1: Petróleo (caudal por día calendario)

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | --- |
| -6 | 2.027 | 17.727 | 0,9 | -0,6 a 2,2 |
| -5 | 2.024 | 17.746 | -0,1 | -0,7 a 0,7 |
| -4 | 2.031 | 17.758 | -1,7 | -2,9 a -0,1 |
| -3 | 2.031 | 17.756 | -2,5 | -4,9 a -0,7 |
| -2 | 2.031 | 17.746 | -3,5 | -6,0 a -1,1 |
| -1 | 2.023 | 17.712 | -6,3 | -9,7 a -3,2 |
| 0 | 2.027 | 17.760 | -20,9 | -25,4 a -16,9 |
| 1 | 2.031 | 17.732 | -25,5 | -30,6 a -21,2 |
| 2 | 2.018 | 17.591 | -16,7 | -21,1 a -12,3 |
| 3 | 2.008 | 17.503 | -11,1 | -16,1 a -6,7 |
| 4 | 2.003 | 17.295 | -8,5 | -13,1 a -4,8 |
| 5 | 1.946 | 16.957 | -5,4 | -9,9 a -1,2 |
| 6 | 1.902 | 16.509 | -4,3 | -8,6 a -0,8 |
| 7 | 1.859 | 16.269 | -4,1 | -8,1 a -0,6 |
| 8 | 1.821 | 15.955 | -3,5 | -7,5 a 1,0 |
| 9 | 1.790 | 15.689 | -3,2 | -7,1 a 1,2 |
| 10 | 1.756 | 15.454 | -4,2 | -8,1 a 0,0 |
| 11 | 1.737 | 15.124 | -5,7 | -9,5 a -1,6 |
| 12 | 1.715 | 14.887 | -4,9 | -9,3 a -0,3 |

### Panel 2: Días efectivos (fracción del mes producida)

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | --- |
| -6 | 2.027 | 17.727 | 0,0 | -0,1 a 0,0 |
| -5 | 2.024 | 17.746 | 0,1 | -0,1 a 0,2 |
| -4 | 2.031 | 17.758 | 0,0 | -0,1 a 0,1 |
| -3 | 2.031 | 17.756 | -0,1 | -0,3 a 0,1 |
| -2 | 2.031 | 17.746 | -0,2 | -0,4 a 0,0 |
| -1 | 2.023 | 17.712 | -0,5 | -0,5 a -0,3 |
| 0 | 2.027 | 17.760 | -5,6 | -10,2 a -2,2 |
| 1 | 2.031 | 17.732 | -4,5 | -9,8 a -1,8 |
| 2 | 2.018 | 17.591 | -0,3 | -0,7 a -0,2 |
| 3 | 2.008 | 17.503 | -0,2 | -0,3 a 0,0 |
| 4 | 2.003 | 17.295 | -0,2 | -0,3 a 0,0 |
| 5 | 1.946 | 16.957 | -0,2 | -0,3 a 0,0 |
| 6 | 1.902 | 16.509 | -0,1 | -0,3 a 0,1 |
| 7 | 1.859 | 16.269 | -0,1 | -0,2 a 0,1 |
| 8 | 1.821 | 15.955 | 0,1 | -0,1 a 0,2 |
| 9 | 1.790 | 15.689 | -0,1 | -0,2 a 0,2 |
| 10 | 1.756 | 15.454 | -0,1 | -0,2 a 0,1 |
| 11 | 1.737 | 15.124 | -0,1 | -0,2 a 0,1 |
| 12 | 1.715 | 14.887 | -0,1 | -0,2 a 0,2 |

### Panel 3: Petróleo por día efectivo

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | --- |
| -6 | 1.997 | 17.372 | 1,2 | 0,1 a 2,4 |
| -5 | 1.998 | 17.471 | -0,3 | -0,7 a 0,2 |
| -4 | 2.015 | 17.487 | -1,2 | -2,3 a 0,1 |
| -3 | 2.010 | 17.500 | -1,7 | -3,6 a 0,3 |
| -2 | 1.984 | 17.454 | -2,4 | -5,0 a -0,2 |
| -1 | 1.946 | 17.306 | -3,8 | -6,6 a -1,0 |
| 0 | 1.850 | 17.225 | -6,1 | -9,4 a -3,7 |
| 1 | 1.880 | 17.075 | -13,7 | -17,3 a -10,0 |
| 2 | 1.906 | 16.863 | -10,6 | -15,3 a -6,9 |
| 3 | 1.903 | 16.655 | -7,9 | -12,2 a -3,7 |
| 4 | 1.897 | 16.388 | -7,8 | -10,7 a -4,1 |
| 5 | 1.843 | 15.980 | -5,2 | -8,6 a -1,3 |
| 6 | 1.792 | 15.489 | -4,1 | -8,3 a -0,1 |
| 7 | 1.752 | 15.183 | -4,6 | -7,7 a -1,2 |
| 8 | 1.725 | 14.879 | -4,4 | -9,0 a -1,2 |
| 9 | 1.691 | 14.556 | -3,8 | -8,0 a -0,6 |
| 10 | 1.638 | 14.316 | -3,8 | -7,5 a -0,4 |
| 11 | 1.638 | 13.965 | -5,1 | -9,3 a -1,9 |
| 12 | 1.594 | 13.711 | -5,4 | -8,9 a -1,6 |

### Panel 4: Corte de agua

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | --- |
| -6 | 1.997 | 17.372 | 0,3 | 0,0 a 0,6 |
| -5 | 1.999 | 17.471 | -0,1 | -0,2 a 0,0 |
| -4 | 2.016 | 17.487 | -0,3 | -0,6 a 0,0 |
| -3 | 2.010 | 17.501 | -0,7 | -1,2 a -0,3 |
| -2 | 1.984 | 17.455 | -1,0 | -1,7 a -0,3 |
| -1 | 1.946 | 17.308 | -1,1 | -1,9 a -0,3 |
| 0 | 1.848 | 17.227 | -0,5 | -1,5 a 0,3 |
| 1 | 1.879 | 17.078 | 2,4 | 1,2 a 3,7 |
| 2 | 1.904 | 16.864 | 4,1 | 2,5 a 5,7 |
| 3 | 1.902 | 16.656 | 3,7 | 2,0 a 5,5 |
| 4 | 1.897 | 16.392 | 2,5 | 1,2 a 4,0 |
| 5 | 1.843 | 15.977 | 1,9 | 0,8 a 3,7 |
| 6 | 1.792 | 15.482 | 2,2 | 0,9 a 3,7 |
| 7 | 1.752 | 15.178 | 1,4 | 0,8 a 2,9 |
| 8 | 1.725 | 14.875 | 1,2 | 0,7 a 2,4 |
| 9 | 1.691 | 14.555 | 1,1 | 0,3 a 1,8 |
| 10 | 1.638 | 14.308 | 1,0 | 0,3 a 1,7 |
| 11 | 1.638 | 13.959 | 1,2 | 0,5 a 2,1 |
| 12 | 1.594 | 13.705 | 1,1 | 0,3 a 2,2 |

De referencia, con la base del resultado principal (meses -3 a -1) la brecha del petróleo al mes 1 es -22,9 puntos (IC -27,4 a -18,1) con 2.077 eventos cercanos y 18.262 controles.

## Gradiente por distancia

Brecha del petróleo al mes 1 por banda de distancia al hijo más cercano, contra un anillo lejano: padres cuyo hijo más cercano está a 5 a 10 km, sin otro hijo a menos de 1 km en los meses -6 a +3 del evento. Las bandas de 1 km o más llevan la misma restricción que el anillo. La fila de 5 a 10 contra 2 a 5 km compara el anillo con 2 a 5 km (mismas restricciones): una brecha ahí es un gradiente entre zonas, y no se separa de la interferencia que llegue más allá de 5 km. La fila de 0 a 1 km reúne a todos los padres a menos de 1 km contra el anillo, con la base limpia y con la base original (meses -3 a -1, la del resultado principal).

| Banda (km) | Control (km) | Base (meses) | Eventos banda | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 0 a 0,3 | 5 a 10 km | -6 a -4 | 332 | 25.786 | -28,0 | -36,9 a -21,6 |
| 0 a 1 | 5 a 10 km | -6 a -4 | 2.031 | 25.786 | -29,4 | -34,6 a -24,9 |
| 0,3 a 0,6 | 5 a 10 km | -6 a -4 | 617 | 25.786 | -31,9 | -40,9 a -23,0 |
| 0,6 a 1 | 5 a 10 km | -6 a -4 | 1.082 | 25.786 | -28,8 | -34,2 a -23,9 |
| 1 a 2 | 5 a 10 km | -6 a -4 | 2.648 | 25.786 | -10,6 | -14,1 a -7,1 |
| 2 a 5 | 5 a 10 km | -6 a -4 | 14.253 | 25.786 | -2,8 | -4,5 a -1,1 |
| 5 a 10 | 2 a 5 km | -6 a -4 | 25.786 | 14.253 | 2,8 | 1,1 a 4,5 |
| 0 a 1 | 5 a 10 km | -3 a -1 | 2.077 | 26.753 | -24,5 | -28,9 a -19,9 |

Las tres bandas de menos de 1 km suman 2.031 eventos, los mismos 2.031 cercanos del panel de petróleo en k = 1.

La banda de 2 a 5 km (14.253 eventos) y el control de 2 a 5 km de la fila del anillo (14.253 eventos) usan la misma regla: padres sin un hijo a menos de 1 km en los meses -6 a +3.

## Qué se concluye

- Resultado principal reproducido: con la base de los meses -3 a -1 la brecha del petróleo al mes 1 es -22,9 puntos (IC -27,4 a -18,1). Con la base limpia de -6 a -4 de estos paneles es -25,5 puntos (IC -30,6 a -21,2); la diferencia es en parte la brecha previa que la base de -3 a -1 absorbe.
- Contra el anillo de 5 a 10 km la brecha del mes 1 es -24,5 puntos, más negativa que los -22,9 contra 2 a 5 km.
- Mes 1, descomposición aditiva (media de los logaritmos, puntos logarítmicos, 2.020 eventos cercanos y 17.705 controles con días y caudal por día): la brecha del volumen es -72,5 (IC -85,0 a -60,6), la de los días efectivos -38,3 (IC -47,5 a -30,3) y la del caudal por día efectivo -34,2 (IC -43,2 a -25,7). La parte de los días es 53% (IC 45% a 62%) y la del caudal por día es 47%. Las medianas no se suman; la parte de cada panel sale de la media de los logaritmos sobre los mismos eventos.
- Misma descomposición sin los meses cerrados enteros (1.869 eventos cercanos y 17.048 controles): la parte de los días es 42% y la del caudal por día 58%. Los meses cerrados enteros no tienen logaritmo de los días: la variante principal los acota a un día de 30 y los deja sin cambio en el caudal por día; esta variante los deja fuera, y por eso resta peso a los días.
- Cierres al mes 1: el 45% de los padres cercanos tiene un índice de días menor a 0,9 contra el 20% de los controles, y el 7% de los cercanos estuvo cerrado todo el mes contra el 4% de los controles.
- Lectura que sostienen los datos: mixta: ninguna de las dos partes lleva sola la mayor parte de la brecha del volumen (días 53% y caudal por día 47%).
- Las lecturas al mes 1. Cierres o días perdidos: no. Golpe de fractura (menos caudal por día): no. Mezcla de ambos: sí. La diferencia entre zonas se mira en el anillo lejano más abajo.
- Pretendencia por panel, en medianas (k = -3 a -1, base de -6 a -4): petróleo -6,3 puntos en k = -1 (IC -9,7 a -3,2), días efectivos -0,5 puntos en k = -1 (IC -0,5 a -0,3), petróleo por día efectivo -3,8 puntos en k = -1 (IC -6,6 a -1,0), corte de agua -1,1 puntos en k = -1 (IC -1,9 a -0,3); en los paneles de días o caudal por día el IC excluye cero en k = -2, -1, así que parte de la diferencia ya estaba antes de la fractura.
- Mayor brecha entre k = 0 y 12, en medianas: petróleo -25,5 puntos en k = 1; días efectivos -5,6 puntos en k = 0; petróleo por día efectivo -13,7 puntos en k = 1.
- Corte de agua al mes 1: 2,4 puntos de corte (IC 1,2 a 3,7); el IC excluye cero.
- Anillo lejano (5 a 10 km contra 2 a 5 km, al mes 1): 2,8 puntos (IC 1,1 a 4,5, 25.786 eventos contra 14.253). El IC excluye cero: los padres de 5 a 10 km rinden 2,8 puntos más que los de 2 a 5 km. El control de 2 a 5 km no es un cero limpio; con estos datos no se separa si es interferencia que llega más allá de 5 km o una diferencia entre zonas con y sin actividad cercana (edad, desarrollo, declinación).
- Gradiente por distancia (contra el anillo lejano de 5 a 10 km), no un alcance: 0 a 0,3 km: -28,0, 0,3 a 0,6 km: -31,9, 0,6 a 1 km: -28,8, 1 a 2 km: -10,6, 2 a 5 km: -2,8 puntos. 5 de 5 bandas tienen un IC que excluye cero (0 a 0,3, 0,3 a 0,6, 0,6 a 1, 1 a 2, 2 a 5 km); la brecha cambia de forma gradual con la distancia y no corta en un punto, y como el control de 2 a 5 km tampoco es un cero limpio, esto no fija hasta dónde llega la interferencia.

## Límites

- Con datos mensuales no se distingue un cierre de un golpe dentro del mes: un pozo que produce menos horas por día y uno cerrado unos días dan el mismo mes. La descomposición separa días de caudal por día, no el motivo del cambio.
- Un cierre protector del operador y un golpe de la fractura se ven igual; el lenguaje de esta página es de brecha medida, no de causa.
- La parte de los días depende de cómo se tratan los meses cerrados enteros (sin logaritmo): por eso se muestran la variante con el piso de un día y la que los deja fuera.
- Un efecto parejo hasta 10 km no se ve: solo se ve un gradiente entre 2 a 5 km y 5 a 10 km.
- Los intervalos son bootstrap por pads hijo y no se ajustan por comparaciones múltiples; la página tiene 141 intervalos, así que alguno puede quedar fuera de cero por azar.
