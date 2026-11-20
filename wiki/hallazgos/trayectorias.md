# Trayectorias de pozo: la rama en planta frente a la distancia de superficie

Hasta acá, la distancia entre un hijo y un padre es la de sus bocas en superficie. Dos pozos del mismo pad están a menos de 50 m en superficie y sus ramas pueden ir en direcciones opuestas; dos pads a 2 km pueden tener las ramas lado a lado. La Secretaría de Energía publica las trayectorias de los pozos horizontales y dirigidos de Vaca Muerta. Esta página dice cuántos pozos y pares cubre y cuánto cambia la distancia cuando se mide entre ramas. Es descriptiva: no estima ningún efecto de interferencia y no cambia ninguna cifra del estudio, que sigue usando la distancia de superficie.

Esta página la escribe `python -m pipeline.wiki` con `pipeline.trayectorias.pagina_trayectorias`. No se edita a mano.

## Lectura

- La fuente trae 2.017 pozos en 2.363 filas. 1.693 de los 3.498 pozos shale de Vaca Muerta del estudio tienen la rama medida.
- Tienen la rama medida 1.662 de los 2.698 hijos horizontales (62%) y 3.798 de los 8.446 pares a menos de 1 km en superficie (45%). Los otros 429 hijos (dirigidos y verticales, por su sigla) casi no están en la fuente; con la rama medida: 1.
- La fuente todavía no publica la mayoría de los pozos recientes. De los hijos horizontales fracturados antes de 2024, 1.528 de 1.634 están en la fuente (94%); de los fracturados desde 2024, 334 de 1.064 (31%).
- En el mismo pad (bocas a menos de 50 m) la mediana de la menor distancia entre ramas es 511 m, pero la separación mediana a lo largo de la rama del hijo es 1.742 m: muchas ramas de un pad salen hacia lados opuestos.
- De los pares cercanos en superficie (menos de 1 km), el 23% tiene las ramas a 1 km o más. De los pares de control (2 a 5 km), el 8% tiene las ramas a menos de 1 km; de los intermedios (1 a 2 km), el 28%.
- La correlación de rangos entre la distancia de superficie y la menor distancia entre ramas es 0,73 (43.981 pares con las dos ramas medidas).

## Fuente

| Conjunto | Organismo | Licencia | Publicado | Bajado | Huella sha256 |
| --- | --- | --- | --- | --- | --- |
| Trayectorias de Pozo Vaca Muerta | Secretaría de Energía (Subsecretaría de Eficiencia e Información Energética) | CC-BY-4.0 | Sun, 15 Nov 2026 05:00:16 GMT | 2026-11-20 | `83093dc4b7bad3b7ab54449bbfb074264f3b6cb17d675c9494a2336403db3034` |

Paquete: http://datos.energia.gob.ar/dataset/f5c0b5a5-b402-44d7-8fe0-f9e4fcb78b8d. Archivo: `http://datos.energia.gob.ar/dataset/f5c0b5a5-b402-44d7-8fe0-f9e4fcb78b8d/resource/94741ac7-4f46-4efe-b112-d3f82a4ef7c5/download/trayectorias-de-pozo-vaca-muerta.csv`. Diccionario de campos y códigos de unidad: Resolución 319/93, Planos Base, instructivo de carga de información geográfica, objeto 4.1.4.10. La copia cruda queda en data/raw y no se redistribuye: el repositorio publica solo las tablas derivadas de esta página, con la fuente citada.

## Cobertura

- Filas publicadas: 2.363; filas repetidas idénticas: 277; pozos: 2.017 (115 sin idpo, identificados por sigla; 67 con más de una versión).
- Unidos al warehouse: 1.899 por idpo y 18 por sigla.
- Con la rama medida: 1.693. Mediana de la distancia entre el inicio del trazado y la ubicación del pozo en el warehouse: 0,1 m.

| Motivo por el que un pozo de la fuente no tiene rama medida | Pozos |
| --- | ---: |
| sin pozo en el warehouse | 15 |
| pozo repetido | 85 |
| fuera del estudio | 4 |
| boca lejos de la ubicación | 12 |
| trazado más largo que el pozo | 3 |
| sin largo de rama | 200 |
| rama más larga que el trazado | 5 |

Por año de fractura del hijo. Horizontales: por la sigla del pozo. En la fuente: unidos a un pozo de la fuente, tenga o no la rama medida.

| Año | Hijos | Horizontales | En la fuente | Con rama | Parte | Pares a menos de 1 km | Con las dos ramas | Parte | Pares a menos de 2 km | Con las dos ramas | Parte |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2011 | 1 | 1 | 0 | 0 | 0% | 1 | 0 | 0% | 1 | 0 | 0% |
| 2012 | 22 | 4 | 1 | 1 | 25% | 13 | 0 | 0% | 51 | 0 | 0% |
| 2013 | 105 | 8 | 7 | 5 | 62% | 36 | 0 | 0% | 185 | 2 | 1% |
| 2014 | 167 | 15 | 15 | 10 | 67% | 294 | 0 | 0% | 1.029 | 0 | 0% |
| 2015 | 173 | 45 | 45 | 38 | 84% | 532 | 7 | 1% | 2.669 | 28 | 1% |
| 2016 | 116 | 104 | 104 | 98 | 94% | 262 | 60 | 23% | 843 | 175 | 21% |
| 2017 | 140 | 133 | 131 | 121 | 91% | 252 | 133 | 53% | 484 | 270 | 56% |
| 2018 | 176 | 170 | 159 | 134 | 79% | 213 | 155 | 73% | 577 | 410 | 71% |
| 2019 | 183 | 180 | 156 | 142 | 79% | 261 | 219 | 84% | 787 | 666 | 85% |
| 2020 | 87 | 86 | 84 | 84 | 98% | 154 | 88 | 57% | 550 | 425 | 77% |
| 2021 | 261 | 261 | 252 | 246 | 94% | 582 | 503 | 86% | 1.546 | 1.259 | 81% |
| 2022 | 296 | 293 | 272 | 260 | 89% | 1.035 | 930 | 90% | 2.537 | 2.196 | 87% |
| 2023 | 334 | 334 | 302 | 255 | 76% | 956 | 758 | 79% | 2.496 | 1.978 | 79% |
| 2024 | 355 | 354 | 172 | 138 | 39% | 1.145 | 554 | 48% | 3.629 | 1.330 | 37% |
| 2025 | 457 | 456 | 147 | 115 | 25% | 1.554 | 295 | 19% | 4.175 | 679 | 16% |
| 2026 | 254 | 254 | 15 | 15 | 6% | 1.156 | 96 | 8% | 3.587 | 156 | 4% |
| Total | 3.127 | 2.698 | 1.862 | 1.662 | 62% | 8.446 | 3.798 | 45% | 25.146 | 9.574 | 38% |

## Las ramas

Pozos con la rama medida. Largo de la rama (m), cuantiles 5, 25, 50, 75 y 95%: 1.391, 2.014, 2.496, 2.850 y 3.389. Profundidad vertical del inicio de la navegación (m): 2.689, 2.875, 2.998, 3.092 y 3.242. Perforados entre 2011 y 2025.

| Unidad donde navega la rama | Pozos | Parte |
| --- | ---: | ---: |
| U1, Vaca Muerta inferior | 794 | 47% |
| U2, Vaca Muerta media | 838 | 49% |
| U3, Vaca Muerta media | 30 | 2% |
| U4, Vaca Muerta superior | 15 | 1% |
| U5, Vaca Muerta superior | 16 | 1% |
| U6, Vaca Muerta superior | 0 | 0% |

## Distancia entre ramas por banda de superficie

Pares hijo y padre de int_par_padre_hijo (padre con petróleo desde al menos 6 meses antes de la fractura del hijo, bocas a menos de 5 km). Menor distancia: la menor entre las dos ramas en planta. Separación mediana: la mediana de la distancia de cada punto de la rama del hijo a la rama del padre.

| Distancia de superficie | Pares | Con las dos ramas | Menor distancia, mediana (m) | Cuartiles (m) | Separación mediana (m) | Ramas a menos de 1 km | Misma unidad | Diferencia de profundidad vertical, mediana (m) |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| menos de 50 m (mismo pad) | 152 | 51 | 511 | 379 a 661 | 1.742 | 98% | 59% | 20 |
| 50 a 500 m | 2.828 | 1.508 | 595 | 404 a 784 | 1.519 | 89% | 50% | 41 |
| 500 m a 1 km | 5.466 | 2.239 | 802 | 565 a 1.082 | 1.026 | 68% | 50% | 38 |
| 1 a 2 km | 16.700 | 5.776 | 1.375 | 935 a 1.795 | 1.637 | 28% | 52% | 40 |
| 2 a 5 km | 101.563 | 34.407 | 3.002 | 2.122 a 3.919 | 3.495 | 8% | 52% | 55 |

## Cómo se reparten los pares al medir entre ramas

Pares con las dos ramas medidas. Filas: la banda de superficie del estudio. Columnas: la menor distancia entre ramas.

| Superficie | menos de 250 m | 250 m a 1 km | 1 a 2 km | 2 km o más | Pares |
| --- | ---: | ---: | ---: | ---: | ---: |
| cercano (menos de 1 km) | 260 (7%) | 2.664 (70%) | 869 (23%) | 5 (0%) | 3.798 |
| intermedio (1 a 2 km) | 100 (2%) | 1.515 (26%) | 3.253 (56%) | 908 (16%) | 5.776 |
| control (2 a 5 km) | 235 (1%) | 2.497 (7%) | 4.913 (14%) | 26.762 (78%) | 34.407 |

## Dónde queda el padre respecto de la rama del hijo

El eje de cada rama en planta es su primera componente principal. Con el eje del hijo, el padre queda de costado cuando su rama solapa el 30% o más de la rama del hijo, de punta cuando no solapa nada y mixto en el resto. Es descriptivo: no cambia ninguna cifra del estudio.

Pares con las dos ramas medidas. Filas: la banda de superficie del estudio. Columnas: la posición del padre respecto de la rama del hijo. El porcentaje es sobre los pares de la fila.

| Superficie | costado | punta | mixto | Pares |
| --- | ---: | ---: | ---: | ---: |
| cercano (menos de 1 km) | 2.017 (53%) | 1.716 (45%) | 65 (2%) | 3.798 |
| intermedio (1 a 2 km) | 2.903 (50%) | 2.221 (38%) | 652 (11%) | 5.776 |
| control (2 a 5 km) | 10.162 (30%) | 19.892 (58%) | 4.353 (13%) | 34.407 |

## Cómo se mide

- Duplicados: se quitan las filas idénticas. Un pozo es su idpo, o su sigla cuando el idpo es 0. Si quedan varias versiones, vale la que tiene un inicio de navegación válido; entre ellas, la más profunda.
- Unión: idpo igual a pozo_id del warehouse; con idpo 0, la sigla exacta cuando es única.
- Rama: el tramo final del trazado en planta con el largo declarado de la rama (o profundidad final menos el inicio de la navegación, si falta), simplificado a 2 m. En la rama el pozo va casi horizontal: su largo medido y su largo en planta coinciden.
- Un pozo se descarta si su trazado sale a más de 200 m de su ubicación en el warehouse o si el trazado en planta es más largo que el pozo.
- Las distancias usan la misma escala que la distancia de superficie del estudio: 111,32 km por grado y el coseno de la latitud del hijo.
- Posición del padre: el eje de cada rama en planta es su primera componente principal; con el eje del hijo, el solape a lo largo de ese eje da la posición (costado, punta o mixto) y el desvío perpendicular es la mediana de la distancia al eje del hijo sobre la parte que se solapa.

## Qué no es

- Es la rama en planta. La fuente no publica la cota de cada punto: la profundidad entra solo como la diferencia del inicio de la navegación entre los dos pozos y como la unidad donde navega cada uno.
- No es un espaciamiento declarado por el operador ni dice dónde se fracturó cada etapa.
- La cobertura cae en los pozos recientes, así que una comparación por año mezcla años bien cubiertos con años que todavía no lo están. Los pozos verticales no tienen trayectoria: el instructivo la pide para los horizontales, dirigidos y sidetrack.
- No mide interferencia: el estudio de eventos sigue con la distancia de superficie. Cambiarla por la distancia entre ramas es una corrida aparte, con su regla fijada antes.

## Reproducir

- `uv run python -m pipeline.ingest` baja la fuente con las otras dos y registra su huella en data/manifest.json.
- `uv run python -m pipeline.trayectorias` arma los marts (mart_trayectoria_pozo, mart_trayectoria_par, mart_par_rama y los de esta página); `uv run python -m pipeline.wiki` reescribe la página y `uv run python -m pipeline.claims` verifica sus cifras contra el warehouse.
