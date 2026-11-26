# Colorado (cuenca DJ): datos y conteos de la replicación

Esta página la escribe el código (`uv run python -m pipeline.colorado.build`) a partir del warehouse del Colorado, separado de `data/warehouse.duckdb`. Solo cuenta filas, pozos, hijos, padres cercanos y controles con las reglas fijadas antes de correr (`pipeline/colorado/__init__.py`). No calcula brecha ni rendimiento: eso es el tramo siguiente, y no se afirma nada causal.

## Fuentes

Datos públicos de ECMC (producción mensual 2018 a 2024 y archivo de pozos) y de FracFocus (lista de divulgaciones). Se usan con atribución a las fuentes y sujetos a los términos de uso de cada sitio. La producción cubre de 2018-01-01 a 2024-12-01.

| Archivo | Bytes | sha256 |
|---|---:|---|
| `fracfocus_disclosure_list` | 61.878.602 | `84c7b50d2bf4` |
| `pozos` | 15.766.245 | `d40a9bdcea4c` |
| `produccion_2018` | 11.783.526 | `34f2184149f3` |
| `produccion_2019` | 11.597.497 | `14dae3c30fc7` |
| `produccion_2020` | 10.898.454 | `3656df463515` |
| `produccion_2021` | 10.684.524 | `37a348ba04f2` |
| `produccion_2022` | 10.458.751 | `4304f871f6a5` |
| `produccion_2023` | 10.202.320 | `156098457e3f` |
| `produccion_2024` | 9.995.505 | `c95967bd4d5d` |

## Filas por etapa

| Etapa | Filas |
|---|---:|
| Filas de producción en la fuente (una por formación y mes) | 4.879.945 |
| Sin pozo o sin mes válido | 0 |
| Tras quedarse con la última revisión de cada fila | 4.879.945 |
| Pozo-mes (formaciones y sidetracks sumados) | 4.137.737 |
| Pozos con producción | 59.421 |
| Pozos con más de un sidetrack | 209 |
| Pozo-mes con más de una fila en la fuente | 550.495 |
| Pozo-mes con cero días producidos | 1.062.166 |
| Pozo-mes con petróleo | 1.874.326 |

## Pozos

| Conjunto | Pozos |
|---|---:|
| Archivo de pozos de ECMC | 124.462 |
| Archivo de pozos con coordenadas | 124.462 |
| Pozos con producción que están en el archivo | 59.421 |
| Pozos con producción que no están en el archivo | 0 |
| Pozos con producción y coordenadas | 59.421 |
| Pozos con producción horizontales | 12.559 |
| Pozos con algún mes de petróleo | 37.547 |
| Pozos con primer petróleo censurado (enero de 2018) | 23.938 |
| Pads (ubicaciones a menos de 50 m) | 79.197 |
| Pozos en pads de 3 o más | 46.442 |

Horizontal: profundidad vertical mayor que 1.000 ft y profundidad medida menos vertical mayor que 1.500 ft. Sin alguno de los dos datos, no es horizontal.

## De las divulgaciones a los hijos

| Paso | Pozos |
|---|---:|
| Divulgaciones de FracFocus en Colorado | 22.346 |
| Con clave de API inválida | 0 |
| Pozos distintos | 21.443 |
| Pozos que están en el archivo de pozos | 21.439 |
| Pozos con producción | 20.342 |
| Pozos con fecha de primera divulgación | 21.443 |
| Primera divulgación entre 2018-07 y 2024-06 | 5.990 |
| En la ventana, en el archivo y con coordenadas | 5.987 |
| De esos, horizontales | 4.798 |
| De esos, con fecha dudosa (más de 30 días después del primer petróleo) | 9 |
| En la ventana con coordenadas pero verticales o sin dato de profundidad | 1.189 |
| Hijos (regla fijada) | 4.789 |
| Hijos sin producción | 12 |
| Hijos con ubicación marcada como planificada | 2 |

## Conteo frente a la estimación de la memoria

Eventos = (padre, mes de fractura) con caudal base mayor que 1 m3/d. Cercano: a menos de 1 km del hijo más cercano; control: de 2 a 5 km.

| Conteo | Hijos | Eventos cercanos | Controles |
|---|---:|---:|---:|
| Estimación de la memoria | 4.817 | 3.866 | 58.139 |
| Regla fijada, solo padres horizontales (corte principal) | 4.789 | 3.692 | 53.339 |
| Regla fijada, todos los padres | 4.789 | 3.708 | 53.675 |
| Método de la memoria, solo padres horizontales | 4.818 | 3.750 | 56.836 |
| Método de la memoria, todos los padres | 4.818 | 3.766 | 57.190 |

Diferencia de la regla fijada, todos los padres, frente a la estimación: -28 hijos, -158 eventos cercanos, -4.464 controles.

Eventos intermedios (de 1 a 2 km, fuera de la brecha), regla fijada: 7.990 con padres horizontales y 8.028 con todos. Hijos con al menos un padre cercano con base válida: 2.546 (padres horizontales) y 2.575 (todos).

## Por año de la fractura

Eventos por año del mes de fractura, regla fijada.

| Año | Cercanos, horizontales | Controles, horizontales | Cercanos, todos | Controles, todos |
|---|---:|---:|---:|---:|
| 2018 | 429 | 5.373 | 433 | 5.445 |
| 2019 | 695 | 12.936 | 704 | 13.033 |
| 2020 | 533 | 6.363 | 533 | 6.411 |
| 2021 | 719 | 9.495 | 719 | 9.531 |
| 2022 | 519 | 7.742 | 520 | 7.757 |
| 2023 | 473 | 7.253 | 474 | 7.315 |
| 2024 | 324 | 4.177 | 325 | 4.183 |

## Por qué difieren

La memoria toma la divulgación más antigua dentro de la ventana; la regla fijada toma la primera de cada pozo de cualquier año, porque un refrac no es un hijo nuevo, y excluye los pozos con fecha dudosa (9 pozos horizontales en la ventana). Con el método de la memoria salen 4.818 hijos. Además, 6.019 pozos tienen divulgación en la ventana y coordenadas antes de pedir que sean horizontales. La diferencia restante con la estimación no se explica con estos datos.

## Límites

- No hay etapas ni arena de la fractura; el largo de rama es un proxy (profundidad medida menos vertical).
- El primer petróleo está censurado en enero de 2018, cuando empieza la producción descargada.
- La fecha de la fractura viene de un formulario de divulgación, no de un mes de reporte; se la contrasta con el primer petróleo.
- La fuente trae una fila por formación y mes: se suman al pozo y mes, y los días son el máximo de las filas.
- Algunos hijos tienen la ubicación marcada como planificada y no medida; la cifra está en la tabla de hijos.
- El corte principal usa solo padres horizontales; el corte con todos los padres se publica al lado.
