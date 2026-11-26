# Wyoming: datos y conteos de la replicación

Esta página la escribe el código (`uv run python -m pipeline.wyoming.build`) a partir del warehouse de Wyoming, separado de `data/warehouse.duckdb`. Solo cuenta filas, pozos, hijos, padres cercanos y controles con las reglas fijadas antes de correr (`pipeline/wyoming/__init__.py`). No calcula brecha ni rendimiento: eso es el tramo siguiente, y no se afirma nada causal.

## Fuentes

Datos públicos de WOGCC (Wyoming Oil and Gas Conservation Commission): encabezados de pozos y producción mensual por pozo y año, bajados del menú de descargas del regulador por URL directa, una vez por archivo. Se usan con atribución a la fuente y sujetos a los términos de uso del sitio, que dicen textualmente (menú principal y pie de datos de WOGCC, `pipeline.wyo.gov`):

> No Warranty is made by the Wyoming Oil and Gas Conservation Commission for the use of this data. Those making use of, or relying on, this information assume all risks and liability arising from such use or reliance.
>
> Scraping of website data is not allowed.

Los términos no traen prohibición de usar ni publicar cifras derivadas de los archivos que el menú ofrece para descargar; esta es nuestra lectura de los términos, no una licencia. Por la segunda línea, la ingesta baja solo los archivos de ese menú, por URL directa, una vez por archivo, sin recorrer páginas ni usar formularios de consulta ni consultas por pozo. Nada de Wyoming se redistribuye crudo: solo se publican cifras derivadas. La producción cubre de 1978-01-01 a 2026-09-01, el último mes con producción reportada: los meses que faltan del año en curso llegan en cero por el formato de una fila por pozo y año.

| Archivo | Bytes | sha256 |
|---|---:|---|
| `pozos` | 18.742.744 | `604dc5a61092` |
| `produccion` | 430.521.456 | `1af576ea1be9` |

Unidades: el petróleo se toma como barriles y pasa a m3 (x 0,158987); el gas se toma como Mcf y pasa a miles de m3 (x 0,0283168); el agua se toma como barriles y pasa a m3. Son la convención del regulador: el archivo no las escribe. TD se toma como profundidad vertical total y MD como profundidad medida; que TD sea vertical no se pudo confirmar.

Encabezados exactos de cada XLSX de producción, leídos del archivo:

- `Counties01-05_110426.csv`: APINO | COMPANY | Field | YR | JAN_OIL | JAN_GAS | JAN_WATER | JAN_DAYS | FEB_OIL | FEB_GAS | FEB_WATER | FEB_DAYS | MAR_OIL | MAR_GAS | MAR_WATER | MAR_DAYS | APR_OIL | APR_GAS | APR_WATER | APR_DAYS | MAY_OIL | MAY_GAS | MAY_WATER | MAY_DAYS | JUN_OIL | JUN_GAS | JUN_WATER | JUN_DAYS | JUL_OIL | JUL_GAS | JUL_WATER | JUL_DAYS | AUG_OIL | AUG_GAS | AUG_WATER | AUG_DAYS | SEP_OIL | SEP_GAS | SEP_WATER | SEP_DAYS | OCT_OIL | OCT_GAS | OCT_WATER | OCT_DAYS | NOV_OIL | NOV_GAS | NOV_WATER | NOV_DAYS | DEC_OIL | DEC_GAS | DEC_WATER | DEC_DAYS | API_RES | ResCode | Reservoir
- `Counties07-17_110426.csv`: APINO | COMPANY | Field | YR | JAN_OIL | JAN_GAS | JAN_WATER | JAN_DAYS | FEB_OIL | FEB_GAS | FEB_WATER | FEB_DAYS | MAR_OIL | MAR_GAS | MAR_WATER | MAR_DAYS | APR_OIL | APR_GAS | APR_WATER | APR_DAYS | MAY_OIL | MAY_GAS | MAY_WATER | MAY_DAYS | JUN_OIL | JUN_GAS | JUN_WATER | JUN_DAYS | JUL_OIL | JUL_GAS | JUL_WATER | JUL_DAYS | AUG_OIL | AUG_GAS | AUG_WATER | AUG_DAYS | SEP_OIL | SEP_GAS | SEP_WATER | SEP_DAYS | OCT_OIL | OCT_GAS | OCT_WATER | OCT_DAYS | NOV_OIL | NOV_GAS | NOV_WATER | NOV_DAYS | DEC_OIL | DEC_GAS | DEC_WATER | DEC_DAYS | API_RES | ResCode | Reservoir
- `Counties19-33_110426.csv`: APINO | COMPANY | Field | YR | JAN_OIL | JAN_GAS | JAN_WATER | JAN_DAYS | FEB_OIL | FEB_GAS | FEB_WATER | FEB_DAYS | MAR_OIL | MAR_GAS | MAR_WATER | MAR_DAYS | APR_OIL | APR_GAS | APR_WATER | APR_DAYS | MAY_OIL | MAY_GAS | MAY_WATER | MAY_DAYS | JUN_OIL | JUN_GAS | JUN_WATER | JUN_DAYS | JUL_OIL | JUL_GAS | JUL_WATER | JUL_DAYS | AUG_OIL | AUG_GAS | AUG_WATER | AUG_DAYS | SEP_OIL | SEP_GAS | SEP_WATER | SEP_DAYS | OCT_OIL | OCT_GAS | OCT_WATER | OCT_DAYS | NOV_OIL | NOV_GAS | NOV_WATER | NOV_DAYS | DEC_OIL | DEC_GAS | DEC_WATER | DEC_DAYS | API_RES | ResCode | Reservoir
- `Counties35-45_110426.csv`: APINO | COMPANY | Field | YR | JAN_OIL | JAN_GAS | JAN_WATER | JAN_DAYS | FEB_OIL | FEB_GAS | FEB_WATER | FEB_DAYS | MAR_OIL | MAR_GAS | MAR_WATER | MAR_DAYS | APR_OIL | APR_GAS | APR_WATER | APR_DAYS | MAY_OIL | MAY_GAS | MAY_WATER | MAY_DAYS | JUN_OIL | JUN_GAS | JUN_WATER | JUN_DAYS | JUL_OIL | JUL_GAS | JUL_WATER | JUL_DAYS | AUG_OIL | AUG_GAS | AUG_WATER | AUG_DAYS | SEP_OIL | SEP_GAS | SEP_WATER | SEP_DAYS | OCT_OIL | OCT_GAS | OCT_WATER | OCT_DAYS | NOV_OIL | NOV_GAS | NOV_WATER | NOV_DAYS | DEC_OIL | DEC_GAS | DEC_WATER | DEC_DAYS | API_RES | ResCode | Reservoir

## Filas por etapa

| Etapa | Filas |
|---|---:|
| Filas de producción en la fuente (una por pozo, año y reservorio) | 1.738.212 |
| Sin pozo o sin año válido | 0 |
| Pozo-año distintos | 1.653.497 |
| Pozo-mes (años abiertos en doce meses, filas repetidas sumadas) | 19.841.964 |
| Pozos con producción | 80.241 |
| Pozo-año con más de una fila en la fuente | 77.168 |
| Pozo-mes con más de una fila aportante | 926.016 |
| Pozo-mes con cero días producidos | 5.854.499 |
| Pozo-mes sin días válidos | 762.051 |
| Pozo-mes con petróleo | 8.886.525 |

## Pozos

| Conjunto | Pozos |
|---|---:|
| Encabezados de WOGCC | 143.555 |
| Encabezados con coordenadas | 143.554 |
| Pozos con producción que están en los encabezados | 49.052 |
| Pozos con producción que no están en los encabezados | 31.189 |
| Pozos con producción y coordenadas | 49.052 |
| Pozos con producción horizontales | 1.741 |
| Pozos con algún mes de petróleo | 44.684 |
| Pozos con primer petróleo censurado (primer mes descargado) | 9.336 |
| Pads (ubicaciones a menos de 50 m) | 67.840 |
| Pozos en pads de 3 o más | 78.610 |

Horizontal: profundidad vertical (TD) mayor que 1.000 ft y profundidad medida (MD) menos vertical mayor que 1.500 ft; la columna de dirección del encabezado no se usa. Sin alguno de los dos datos, no es horizontal.

## De las terminaciones a los hijos

| Paso | Pozos |
|---|---:|
| Pozos con fecha de primera terminación (FIRSTCOMP) | 51.044 |
| FIRSTCOMP vacío | 92.489 |
| FIRSTCOMP que no se lee como fecha válida | 22 |
| De esos, de siete dígitos que se leen como fecha válida de dos maneras (ambiguos) | 21 |
| Pozos con fecha y con producción | 48.476 |
| Primera terminación entre 2018-07 y 2024-06 | 2.418 |
| En la ventana, en los encabezados y con coordenadas | 2.418 |
| De esos, horizontales | 1.191 |
| De esos, con fecha dudosa (más de 30 días después del primer petróleo) | 20 |
| En la ventana con coordenadas pero verticales o sin dato de profundidad | 1.227 |
| En la ventana, horizontales y con coordenadas, pero sin petróleo (excluidos) | 8 |
| Hijos (regla fijada) | 1.163 |
| Hijos sin producción | 0 |

La fecha del hijo es FIRSTCOMP, la fecha de primera terminación del regulador: no es una fecha de fractura, y un refrac no se distingue de un hijo nuevo porque hay una sola fecha por pozo. FIRSTCOMP viene como AAAAMMDD o AAAAMDD (mes sin cero a la izquierda); un valor de siete dígitos que también se lee como AAAAMMD es ambiguo y el pozo queda afuera.

Entre los 1.163 hijos, el mes de FIRSTCOMP es el del primer petróleo en 876, el primer petróleo es posterior en 279 y anterior en 8. Una fecha de terminación que cae más tarde que el inicio de la fractura corre el mes 0 hacia adelante: si pasa en Wyoming, la base de los meses -3 a -1 incluye meses posteriores a la fractura y el mes 1 queda más lejos de ella. Eso se publica como límite y no como explicación: no se probó cuánto del resultado sale de ahí, y la lectura no separa "no hay huella" de "el mes 0 está corrido".

## Hijos, padres cercanos y controles

Eventos = (padre, mes de terminación) con caudal base mayor que 1 m3/d. Cercano: a menos de 1 km del hijo más cercano; control: de 2 a 5 km.

| Conteo | Hijos | Eventos cercanos | Controles |
|---|---:|---:|---:|
| Regla fijada, solo padres horizontales (corte principal) | 1.163 | 353 | 2.286 |
| Regla fijada, todos los padres | 1.163 | 936 | 9.220 |

Eventos intermedios (de 1 a 2 km, fuera de la brecha), regla fijada: 475 con padres horizontales y 1.616 con todos. Hijos con al menos un padre cercano con base válida: 231 (padres horizontales) y 598 (todos).

## Por año de la terminación

Eventos por año del mes de terminación, regla fijada.

| Año | Cercanos, horizontales | Controles, horizontales | Cercanos, todos | Controles, todos |
|---|---:|---:|---:|---:|
| 2018 | 0 | 1 | 20 | 193 |
| 2019 | 0 | 16 | 103 | 857 |
| 2020 | 9 | 75 | 125 | 1.353 |
| 2021 | 45 | 310 | 148 | 1.800 |
| 2022 | 83 | 483 | 189 | 1.761 |
| 2023 | 153 | 1.007 | 265 | 2.497 |
| 2024 | 63 | 394 | 86 | 759 |

## Límites

- No hay fecha de fractura: se usa FIRSTCOMP, la primera terminación del regulador; un refrac no se distingue de un hijo nuevo.
- Los bloques espaciales de 5 km usan la proyección de `pipeline/bloques.py`, centrada en la latitud de Vaca Muerta: a las latitudes de Wyoming (41 a 45 grados norte) un bloque es algo más angosto que 5 km de este a oeste y mide 5 km de norte a sur. No se midió cuánto cambia el intervalo.
- No hay etapas ni arena de la fractura; el largo de rama es un proxy (profundidad medida menos vertical).
- El primer petróleo está censurado en el primer mes descargado, cuando empieza la producción.
- La fuente trae una fila por pozo y año con doce columnas por mes: se abre en doce meses, se suma al pozo y mes, y los días son el máximo de las filas.
- Los días fuera del rango 0 a 31 (casi siempre 99 en la fuente, un código y no un conteo) se toman como desconocidos: 762.051 pozo-mes. El máximo válido se topa en el largo del mes.
- El petróleo NULL del mes es 0; el gas se toma como Mcf y el agua como barriles, convención del regulador no escrita en el archivo.
- TD se toma como profundidad vertical sin confirmación; la columna de dirección del encabezado no se usa.
- El corte principal usa solo padres horizontales; el corte con todos los padres se publica al lado.
- El corte con todos los padres de esta página y el de la página de replicación salen de dos armados distintos y sus conteos no coinciden del todo; la diferencia no se reconcilió. El corte principal coincide en las dos páginas.
- La auditoría de fuentes anotó una discrepancia para el pozo 720921: el encabezado trae FIRSTCOMP 2024-06-15 y la producción empieza en 1984-02, 14.745 días antes. Es consistente con una terminación nueva de un pozo viejo (no se pudo confirmar): cae en la ventana, no es horizontal y queda marcado como fecha dudosa, así que no entra entre los hijos. La regla de fecha dudosa existe para estos casos.
- 31.189 pozos con producción no están en los encabezados: no tienen coordenadas ni FIRSTCOMP y no entran como hijos, padres ni controles. Pueden estar en el archivo de pozos taponados y abandonados, que no se usa; no se midió cuánto cambiaría una cifra si entraran.
