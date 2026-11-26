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
| -6 | 2.043 | 17.755 | 1,2 (-3,4 a 5,6) | 0,7 (-2,4 a 3,9) | 0,4 (-2,6 a 3,4) | 63% (-379% a 699%) |
| -5 | 2.040 | 17.772 | 0,4 (-2,7 a 3,4) | 1,5 (-0,5 a 3,4) | -1,1 (-3,1 a 0,9) | 359% (-1.594% a 1.073%) |
| -4 | 2.048 | 17.788 | 2,7 (-1,4 a 6,0) | 1,8 (-2,1 a 4,4) | 1,0 (-1,1 a 3,0) | 65% (-82% a 255%) |
| -3 | 2.048 | 17.785 | -0,6 (-5,5 a 3,9) | -0,5 (-3,7 a 2,5) | -0,1 (-3,4 a 3,4) | 82% (-559% a 375%) |
| -2 | 2.046 | 17.770 | -5,0 (-11,3 a 0,6) | -3,8 (-8,7 a 0,3) | -1,2 (-5,4 a 2,7) | 75% (-126% a 237%) |
| -1 | 2.040 | 17.740 | -11,2 (-17,5 a -4,2) | -9,2 (-15,0 a -3,3) | -2,0 (-5,7 a 2,3) | 83% (50% a 141%) |
| 0 | 2.040 | 17.781 | -51,0 (-60,1 a -42,6) | -45,1 (-53,2 a -37,0) | -5,9 (-11,8 a -0,9) | 88% (78% a 98%) |
| 1 | 2.037 | 17.730 | -72,8 (-84,6 a -61,2) | -38,1 (-47,2 a -30,3) | -34,6 (-44,1 a -25,4) | 52% (44% a 61%) |
| 2 | 2.039 | 17.730 | -45,2 (-57,7 a -33,6) | -14,7 (-21,6 a -8,3) | -30,6 (-40,5 a -21,1) | 32% (21% a 45%) |
| 3 | 2.028 | 17.571 | -24,0 (-33,8 a -14,5) | -6,5 (-12,6 a -0,8) | -17,6 (-25,1 a -9,7) | 27% (4% a 47%) |
| 4 | 2.005 | 17.491 | -13,6 (-22,1 a -4,9) | -2,6 (-8,7 a 3,1) | -11,0 (-18,0 a -4,8) | 19% (-47% a 51%) |
| 5 | 1.991 | 17.266 | -12,4 (-22,7 a -4,0) | -1,7 (-7,8 a 3,5) | -10,7 (-17,5 a -3,4) | 14% (-57% a 55%) |
| 6 | 1.944 | 16.916 | -9,4 (-17,9 a -1,2) | -0,2 (-5,5 a 5,9) | -9,2 (-16,1 a -2,6) | 2% (-183% a 50%) |
| 7 | 1.894 | 16.522 | -7,4 (-15,9 a 1,7) | 1,0 (-5,6 a 7,8) | -8,4 (-15,1 a -1,1) | -13% (-438% a 406%) |
| 8 | 1.856 | 16.250 | -3,7 (-13,3 a 4,6) | 3,4 (-2,1 a 8,6) | -7,1 (-14,1 a 0,3) | -93% (-1.388% a 1.255%) |
| 9 | 1.810 | 15.939 | -0,9 (-9,7 a 7,7) | 4,8 (-2,2 a 10,1) | -5,8 (-12,0 a 0,6) | -512% (-1.816% a 1.395%) |
| 10 | 1.776 | 15.649 | -4,7 (-13,0 a 4,2) | 0,4 (-6,4 a 7,1) | -5,2 (-12,4 a 2,2) | -9% (-560% a 876%) |
| 11 | 1.752 | 15.418 | -3,3 (-11,7 a 4,6) | 2,3 (-4,0 a 8,8) | -5,6 (-12,6 a 0,5) | -71% (-749% a 685%) |
| 12 | 1.733 | 15.091 | -4,6 (-15,9 a 4,6) | 0,8 (-7,3 a 7,3) | -5,4 (-12,6 a 1,2) | -18% (-547% a 621%) |

### Sin los meses cerrados enteros

| k | Eventos cercanos | Eventos control | Brecha del volumen (IC 95%) | Días efectivos (IC 95%) | Caudal por día (IC 95%) | Parte de los días (IC 95%) |
| ---: | ---: | ---: | --- | --- | --- | --- |
| -6 | 2.013 | 17.399 | 0,1 (-4,0 a 4,1) | -0,4 (-2,6 a 2,1) | 0,5 (-2,4 a 3,4) | -800% (-301% a 1.582%) |
| -5 | 2.014 | 17.497 | -0,2 (-2,8 a 2,5) | 0,9 (-0,3 a 2,3) | -1,1 (-3,3 a 1,4) | -544% (-837% a 1.425%) |
| -4 | 2.032 | 17.517 | 1,2 (-1,4 a 3,9) | 0,2 (-1,3 a 1,9) | 1,0 (-0,9 a 3,1) | 16% (-393% a 347%) |
| -3 | 2.027 | 17.528 | -1,5 (-5,7 a 3,0) | -1,5 (-3,9 a 0,8) | -0,1 (-3,3 a 3,7) | 96% (-357% a 701%) |
| -2 | 1.999 | 17.478 | -3,1 (-8,3 a 2,1) | -1,8 (-4,8 a 1,6) | -1,4 (-5,6 a 2,5) | 56% (-340% a 316%) |
| -1 | 1.963 | 17.334 | -6,7 (-12,6 a -0,7) | -4,4 (-8,0 a -1,1) | -2,3 (-7,1 a 2,3) | 65% (20% a 224%) |
| 0 | 1.863 | 17.243 | -37,2 (-46,5 a -29,9) | -29,2 (-35,4 a -24,2) | -8,0 (-14,5 a -2,6) | 79% (67% a 92%) |
| 1 | 1.886 | 17.072 | -66,5 (-77,4 a -53,8) | -27,9 (-33,4 a -22,5) | -38,6 (-47,3 a -28,0) | 42% (36% a 51%) |
| 2 | 1.927 | 16.996 | -43,5 (-55,0 a -31,9) | -10,7 (-15,0 a -6,4) | -32,8 (-42,7 a -23,3) | 25% (17% a 33%) |
| 3 | 1.923 | 16.719 | -24,6 (-33,3 a -16,2) | -6,0 (-10,1 a -1,7) | -18,6 (-26,0 a -11,2) | 24% (9% a 38%) |
| 4 | 1.899 | 16.575 | -14,5 (-23,7 a -6,9) | -2,9 (-6,3 a 0,3) | -11,6 (-19,2 a -4,6) | 20% (-3% a 45%) |
| 5 | 1.885 | 16.282 | -14,5 (-23,5 a -6,0) | -3,4 (-7,6 a 0,2) | -11,1 (-18,8 a -3,5) | 24% (-1% a 53%) |
| 6 | 1.831 | 15.879 | -11,4 (-20,2 a -3,5) | -1,7 (-5,2 a 1,8) | -9,7 (-17,0 a -2,4) | 15% (-28% a 45%) |
| 7 | 1.779 | 15.427 | -9,6 (-18,3 a -1,7) | -0,9 (-3,9 a 2,7) | -8,7 (-15,7 a -1,5) | 10% (-82% a 49%) |
| 8 | 1.757 | 15.161 | -7,9 (-16,0 a 0,4) | -1,2 (-4,6 a 2,1) | -6,7 (-14,6 a 0,2) | 15% (-76% a 87%) |
| 9 | 1.710 | 14.791 | -6,0 (-13,1 a 2,0) | -0,8 (-4,1 a 2,9) | -5,2 (-11,4 a 1,9) | 13% (-178% a 139%) |
| 10 | 1.657 | 14.502 | -6,9 (-14,8 a 1,7) | -1,8 (-5,6 a 2,1) | -5,2 (-12,4 a 2,0) | 25% (-89% a 186%) |
| 11 | 1.653 | 14.241 | -8,9 (-16,4 a -1,9) | -4,1 (-7,6 a 0,5) | -4,8 (-12,2 a 1,5) | 47% (-10% a 135%) |
| 12 | 1.609 | 13.904 | -6,5 (-14,1 a 1,2) | -1,1 (-4,9 a 3,4) | -5,4 (-11,6 a 1,3) | 17% (-121% a 241%) |

## Cierres al mes 1

Parte de los eventos con el índice de días por debajo de 0,9 (más de 10% de los días perdidos respecto de su base) y parte cerrados todo el mes, cercanos contra control (mismos eventos que el panel de días).

| Grupo | Eventos | Índice de días menor a 0,9 | Cerrados todo el mes |
| --- | ---: | ---: | ---: |
| Cercanos | 2.048 | 45,5% | 7,4% |
| Controles | 17.757 | 19,9% | 3,7% |

## Paneles por mes (medianas, descriptivos)

Brecha de las medianas por panel. Describen cada panel por separado y no se usan para partir la brecha.

### Panel 1: Petróleo (caudal por día calendario)

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | --- |
| -6 | 2.044 | 17.759 | 0,9 | -0,5 a 2,0 |
| -5 | 2.041 | 17.778 | -0,1 | -0,8 a 0,7 |
| -4 | 2.048 | 17.790 | -1,6 | -2,7 a -0,1 |
| -3 | 2.048 | 17.788 | -2,5 | -4,8 a -0,6 |
| -2 | 2.048 | 17.778 | -3,6 | -6,0 a -1,3 |
| -1 | 2.040 | 17.744 | -6,3 | -9,7 a -3,5 |
| 0 | 2.044 | 17.792 | -21,0 | -25,6 a -17,5 |
| 1 | 2.048 | 17.757 | -25,6 | -31,3 a -21,2 |
| 2 | 2.048 | 17.753 | -17,0 | -21,5 a -12,9 |
| 3 | 2.034 | 17.595 | -11,6 | -16,2 a -6,9 |
| 4 | 2.009 | 17.509 | -8,6 | -13,1 a -4,8 |
| 5 | 1.999 | 17.283 | -5,7 | -10,6 a -2,4 |
| 6 | 1.950 | 16.935 | -4,3 | -8,9 a 0,3 |
| 7 | 1.902 | 16.538 | -4,3 | -8,3 a -0,6 |
| 8 | 1.859 | 16.269 | -3,5 | -7,6 a 0,9 |
| 9 | 1.821 | 15.956 | -3,8 | -7,4 a 0,8 |
| 10 | 1.786 | 15.672 | -4,4 | -8,7 a -0,7 |
| 11 | 1.756 | 15.438 | -5,3 | -8,9 a -1,4 |
| 12 | 1.737 | 15.117 | -5,4 | -9,0 a -0,6 |

### Panel 2: Días efectivos (fracción del mes producida)

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | --- |
| -6 | 2.044 | 17.759 | 0,0 | -0,1 a 0,1 |
| -5 | 2.041 | 17.778 | 0,1 | 0,0 a 0,2 |
| -4 | 2.048 | 17.790 | 0,0 | -0,1 a 0,1 |
| -3 | 2.048 | 17.788 | -0,1 | -0,3 a 0,1 |
| -2 | 2.048 | 17.778 | -0,2 | -0,4 a 0,0 |
| -1 | 2.040 | 17.744 | -0,5 | -0,6 a -0,3 |
| 0 | 2.044 | 17.792 | -5,6 | -8,8 a -2,2 |
| 1 | 2.048 | 17.757 | -4,7 | -10,1 a -1,8 |
| 2 | 2.048 | 17.753 | -0,3 | -0,8 a -0,2 |
| 3 | 2.034 | 17.595 | -0,2 | -0,3 a 0,0 |
| 4 | 2.009 | 17.509 | -0,2 | -0,3 a 0,0 |
| 5 | 1.999 | 17.283 | -0,1 | -0,3 a 0,1 |
| 6 | 1.950 | 16.935 | -0,1 | -0,3 a 0,1 |
| 7 | 1.902 | 16.538 | -0,1 | -0,3 a 0,1 |
| 8 | 1.859 | 16.269 | 0,0 | -0,2 a 0,2 |
| 9 | 1.821 | 15.956 | -0,1 | -0,2 a 0,2 |
| 10 | 1.786 | 15.672 | -0,1 | -0,2 a 0,1 |
| 11 | 1.756 | 15.438 | -0,1 | -0,2 a 0,1 |
| 12 | 1.737 | 15.117 | -0,1 | -0,2 a 0,1 |

### Panel 3: Petróleo por día efectivo

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | --- |
| -6 | 2.014 | 17.403 | 1,2 | 0,1 a 2,4 |
| -5 | 2.015 | 17.503 | -0,3 | -0,7 a 0,2 |
| -4 | 2.032 | 17.519 | -1,1 | -2,2 a 0,2 |
| -3 | 2.027 | 17.531 | -1,7 | -3,4 a 0,1 |
| -2 | 2.001 | 17.486 | -2,5 | -4,9 a -0,1 |
| -1 | 1.963 | 17.338 | -3,9 | -6,8 a -0,7 |
| 0 | 1.867 | 17.254 | -6,4 | -9,6 a -3,5 |
| 1 | 1.897 | 17.099 | -13,8 | -17,4 a -10,4 |
| 2 | 1.936 | 17.019 | -10,9 | -15,3 a -6,8 |
| 3 | 1.929 | 16.743 | -8,5 | -12,6 a -4,1 |
| 4 | 1.903 | 16.593 | -7,8 | -10,7 a -4,3 |
| 5 | 1.893 | 16.299 | -5,5 | -8,7 a -1,9 |
| 6 | 1.837 | 15.898 | -4,1 | -7,9 a -0,1 |
| 7 | 1.787 | 15.443 | -4,8 | -8,4 a -0,9 |
| 8 | 1.760 | 15.180 | -4,2 | -8,0 a -0,6 |
| 9 | 1.721 | 14.808 | -4,1 | -7,9 a -0,9 |
| 10 | 1.667 | 14.525 | -4,1 | -7,9 a -1,1 |
| 11 | 1.657 | 14.261 | -4,9 | -9,0 a -1,8 |
| 12 | 1.613 | 13.930 | -5,5 | -8,4 a -2,4 |

### Panel 4: Corte de agua

| k (meses desde la fractura) | Eventos cercanos | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| ---: | ---: | ---: | ---: | --- |
| -6 | 2.014 | 17.403 | 0,3 | 0,0 a 0,7 |
| -5 | 2.016 | 17.503 | -0,1 | -0,3 a 0,0 |
| -4 | 2.033 | 17.519 | -0,3 | -0,6 a 0,0 |
| -3 | 2.027 | 17.532 | -0,7 | -1,3 a -0,4 |
| -2 | 2.001 | 17.487 | -1,0 | -1,8 a -0,4 |
| -1 | 1.963 | 17.340 | -1,1 | -1,9 a -0,3 |
| 0 | 1.865 | 17.256 | -0,6 | -1,5 a 0,3 |
| 1 | 1.896 | 17.102 | 2,3 | 1,1 a 3,8 |
| 2 | 1.934 | 17.020 | 4,1 | 2,3 a 5,7 |
| 3 | 1.928 | 16.740 | 3,7 | 2,2 a 5,4 |
| 4 | 1.903 | 16.597 | 2,5 | 1,1 a 4,0 |
| 5 | 1.893 | 16.296 | 1,9 | 0,8 a 3,7 |
| 6 | 1.837 | 15.891 | 2,1 | 0,7 a 3,4 |
| 7 | 1.781 | 15.438 | 1,3 | 0,8 a 3,1 |
| 8 | 1.760 | 15.175 | 1,2 | 0,7 a 2,5 |
| 9 | 1.716 | 14.806 | 1,1 | 0,3 a 1,7 |
| 10 | 1.662 | 14.516 | 1,1 | 0,3 a 1,8 |
| 11 | 1.657 | 14.255 | 1,2 | 0,5 a 1,9 |
| 12 | 1.612 | 13.919 | 1,1 | 0,4 a 2,2 |

De referencia, con la base del resultado principal (meses -3 a -1) la brecha del petróleo al mes 1 es -23,0 puntos (IC -27,3 a -18,2) con 2.094 eventos cercanos y 18.291 controles.

## Gradiente por distancia

Brecha del petróleo al mes 1 por banda de distancia al hijo más cercano, contra un anillo lejano: padres cuyo hijo más cercano está a 5 a 10 km, sin otro hijo a menos de 1 km en los meses -6 a +3 del evento. Las bandas de 1 km o más llevan la misma restricción que el anillo. La fila de 5 a 10 contra 2 a 5 km compara el anillo con 2 a 5 km (mismas restricciones): una brecha ahí es un gradiente entre zonas, y no se separa de la interferencia que llegue más allá de 5 km. La fila de 0 a 1 km reúne a todos los padres a menos de 1 km contra el anillo, con la base limpia y con la base original (meses -3 a -1, la del resultado principal).

| Banda (km) | Control (km) | Base (meses) | Eventos banda | Eventos control | Brecha (puntos) | IC 95% (puntos) |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 0 a 0,3 | 5 a 10 km | -6 a -4 | 332 | 25.789 | -28,1 | -36,8 a -22,2 |
| 0 a 1 | 5 a 10 km | -6 a -4 | 2.048 | 25.789 | -29,6 | -34,9 a -25,5 |
| 0,3 a 0,6 | 5 a 10 km | -6 a -4 | 623 | 25.789 | -32,1 | -42,0 a -23,0 |
| 0,6 a 1 | 5 a 10 km | -6 a -4 | 1.093 | 25.789 | -29,0 | -35,1 a -24,8 |
| 1 a 2 | 5 a 10 km | -6 a -4 | 2.654 | 25.789 | -10,8 | -13,9 a -7,0 |
| 2 a 5 | 5 a 10 km | -6 a -4 | 14.269 | 25.789 | -2,9 | -4,5 a -1,2 |
| 5 a 10 | 2 a 5 km | -6 a -4 | 25.789 | 14.269 | 2,9 | 1,2 a 4,5 |
| 0 a 1 | 5 a 10 km | -3 a -1 | 2.094 | 26.756 | -24,6 | -28,8 a -20,4 |

Las tres bandas de menos de 1 km suman 2.048 eventos, los mismos 2.048 cercanos del panel de petróleo en k = 1.

La banda de 2 a 5 km (14.269 eventos) y el control de 2 a 5 km de la fila del anillo (14.269 eventos) usan la misma regla: padres sin un hijo a menos de 1 km en los meses -6 a +3.

## Qué se concluye

- Resultado principal reproducido: con la base de los meses -3 a -1 la brecha del petróleo al mes 1 es -23,0 puntos (IC -27,3 a -18,2). Con la base limpia de -6 a -4 de estos paneles es -25,6 puntos (IC -31,3 a -21,2); la diferencia es en parte la brecha previa que la base de -3 a -1 absorbe.
- Contra el anillo de 5 a 10 km la brecha del mes 1 es -24,6 puntos, más negativa que los -23,0 contra 2 a 5 km.
- Mes 1, descomposición aditiva (media de los logaritmos, puntos logarítmicos, 2.037 eventos cercanos y 17.730 controles con días y caudal por día): la brecha del volumen es -72,8 (IC -84,6 a -61,2), la de los días efectivos -38,1 (IC -47,2 a -30,3) y la del caudal por día efectivo -34,6 (IC -44,1 a -25,4). La parte de los días es 52% (IC 44% a 61%) y la del caudal por día es 48%. Las medianas no se suman; la parte de cada panel sale de la media de los logaritmos sobre los mismos eventos.
- Misma descomposición sin los meses cerrados enteros (1.886 eventos cercanos y 17.072 controles): la parte de los días es 42% y la del caudal por día 58%. Los meses cerrados enteros no tienen logaritmo de los días: la variante principal los acota a un día de 30 y los deja sin cambio en el caudal por día; esta variante los deja fuera, y por eso resta peso a los días.
- Cierres al mes 1: el 45% de los padres cercanos tiene un índice de días menor a 0,9 contra el 20% de los controles, y el 7% de los cercanos estuvo cerrado todo el mes contra el 4% de los controles.
- Lectura que sostienen los datos: mixta: ninguna de las dos partes lleva sola la mayor parte de la brecha del volumen (días 52% y caudal por día 48%).
- Las lecturas al mes 1. Cierres o días perdidos: no. Golpe de fractura (menos caudal por día): no. Mezcla de ambos: sí. La diferencia entre zonas se mira en el anillo lejano más abajo.
- Pretendencia por panel, en medianas (k = -3 a -1, base de -6 a -4): petróleo -6,3 puntos en k = -1 (IC -9,7 a -3,5), días efectivos -0,5 puntos en k = -1 (IC -0,6 a -0,3), petróleo por día efectivo -3,9 puntos en k = -1 (IC -6,8 a -0,7), corte de agua -1,1 puntos en k = -1 (IC -1,9 a -0,3); en los paneles de días o caudal por día el IC excluye cero en k = -2, -1, así que parte de la diferencia ya estaba antes de la fractura.
- Mayor brecha entre k = 0 y 12, en medianas: petróleo -25,6 puntos en k = 1; días efectivos -5,6 puntos en k = 0; petróleo por día efectivo -13,8 puntos en k = 1.
- Corte de agua al mes 1: 2,3 puntos de corte (IC 1,1 a 3,8); el IC excluye cero.
- Anillo lejano (5 a 10 km contra 2 a 5 km, al mes 1): 2,9 puntos (IC 1,2 a 4,5, 25.789 eventos contra 14.269). El IC excluye cero: los padres de 5 a 10 km rinden 2,9 puntos más que los de 2 a 5 km. El control de 2 a 5 km no es un cero limpio; con estos datos no se separa si es interferencia que llega más allá de 5 km o una diferencia entre zonas con y sin actividad cercana (edad, desarrollo, declinación).
- Gradiente por distancia (contra el anillo lejano de 5 a 10 km), no un alcance: 0 a 0,3 km: -28,1, 0,3 a 0,6 km: -32,1, 0,6 a 1 km: -29,0, 1 a 2 km: -10,8, 2 a 5 km: -2,9 puntos. 5 de 5 bandas tienen un IC que excluye cero (0 a 0,3, 0,3 a 0,6, 0,6 a 1, 1 a 2, 2 a 5 km); la brecha cambia de forma gradual con la distancia y no corta en un punto, y como el control de 2 a 5 km tampoco es un cero limpio, esto no fija hasta dónde llega la interferencia.

## Límites

- Con datos mensuales no se distingue un cierre de un golpe dentro del mes: un pozo que produce menos horas por día y uno cerrado unos días dan el mismo mes. La descomposición separa días de caudal por día, no el motivo del cambio.
- Un cierre protector del operador y un golpe de la fractura se ven igual; el lenguaje de esta página es de brecha medida, no de causa.
- La parte de los días depende de cómo se tratan los meses cerrados enteros (sin logaritmo): por eso se muestran la variante con el piso de un día y la que los deja fuera.
- Un efecto parejo hasta 10 km no se ve: solo se ve un gradiente entre 2 a 5 km y 5 a 10 km.
- Los intervalos son bootstrap por pads hijo y no se ajustan por comparaciones múltiples; la página tiene 141 intervalos, así que alguno puede quedar fuera de cero por azar.
