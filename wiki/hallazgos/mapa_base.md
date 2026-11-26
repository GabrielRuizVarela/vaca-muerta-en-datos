# Mapa base de Vaca Muerta en 3D: fuentes y licencias

Lo que se ve debajo de los pozos en `site/mundo.html` (relieve, ríos, lagos y embalses, límites entre provincias, localidades y concesiones de explotación) es dato publicado por tres organismos, no una estimación de este estudio. La regla es una sola: sin fuente no hay capa. Ningún río se dibuja de memoria y ningún bloque se inventa a partir de los pozos.

Esta página la escribe `python -m pipeline.base_mapa` a partir de `data/base_mapa.json` y, para la imagen del suelo, de `data/base_foto.json`. No se edita a mano.

## Qué cubre

La hoja va de 70,5° a 67,5° de longitud oeste y de 39,6° a 36,6° de latitud sur. Tiene:

- relieve: una grilla de 540 por 675 celdas (20 por 16 segundos de arco, cerca de 500 m de lado), con cotas de 220 a 4.656 m sobre el nivel del mar;
- relieve fino del núcleo: entre los 69,25° y los 68,25° de longitud oeste y entre los 38,85° y los 38,1° de latitud sur, donde está la mayoría de los pozos, una segunda grilla fina de 900 por 675 celdas de 4 segundos de arco (cerca de 97 m hacia el este y 124 m hacia el sur), con cotas de 217 a 886 m. La página dibuja esta y la funde con la de la hoja en una franja junto a cada borde, el 4 % del lado del recorte;
- 10 ríos y arroyos con nombre, los que suman 60 km o más dentro de la hoja;
- 24 cuerpos de agua con nombre (6 embalses, 9 lagos y 9 cauces anchos) y 27 contornos sin nombre;
- 4 límites entre provincias;
- 20 localidades, de una lista fija;
- 142 concesiones de explotación de 32 empresas operadoras, con nombre y código.

## Fuentes

| Capa | Conjunto | Organismo | Licencia | Bajado |
|---|---|---|---|---|
| Relieve | SRTM de 1 segundo de arco (teselas skadi de Terrain Tiles) | NASA y USGS | dominio público; datos SRTM cortesía del U.S. Geological Survey | 19/11/2026 |
| Ríos | Corriente de agua perenne | Instituto Geográfico Nacional | uso libre y gratuito con reconocimiento de la autoría del Instituto Geográfico Nacional | 19/11/2026 |
| Lagos, embalses y cauces anchos | Embalse | Instituto Geográfico Nacional | uso libre y gratuito con reconocimiento de la autoría del Instituto Geográfico Nacional | 19/11/2026 |
| Lagos, embalses y cauces anchos | Espejo de agua perenne | Instituto Geográfico Nacional | uso libre y gratuito con reconocimiento de la autoría del Instituto Geográfico Nacional | 19/11/2026 |
| Lagos, embalses y cauces anchos | Corriente de agua (áreas) | Instituto Geográfico Nacional | uso libre y gratuito con reconocimiento de la autoría del Instituto Geográfico Nacional | 19/11/2026 |
| Límites interprovinciales | Límite interprovincial | Instituto Geográfico Nacional | uso libre y gratuito con reconocimiento de la autoría del Instituto Geográfico Nacional | 19/11/2026 |
| Localidades | Localidad (BAHRA) | Instituto Geográfico Nacional | uso libre y gratuito con reconocimiento de la autoría del Instituto Geográfico Nacional | 19/11/2026 |
| Concesiones de explotación | Producción de hidrocarburos: concesiones de explotación | Secretaría de Energía | CC-BY-4.0 | 19/11/2026 |

Dirección de descarga y huella de cada conjunto:

- SRTM de 1 segundo de arco (teselas skadi de Terrain Tiles): `https://s3.amazonaws.com/elevation-tiles-prod/skadi/S39/S39W069.hgt.gz`, sha256 `707789b98181cbe9320994c18837643203d2e6d7f4e5c5348ad1a59f4987ed2a`.
- Corriente de agua perenne: `https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&outputFormat=application/json&bbox=-70.5,-39.6,-67.5,-36.6&typeName=ign:lineas_de_aguas_continentales_perenne`, sha256 `b08ccbbcb77eaad497d275ca45d410cf1069c8d0bad0e2882c1e8ef00b17e09c`.
- Embalse: `https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&outputFormat=application/json&bbox=-70.5,-39.6,-67.5,-36.6&typeName=ign:areas_de_aguas_continentales_BH130`, sha256 `c51a96ef17a081ca71076158b0016c08ba1e946d8bdfc096f5fffbe9f1c7ec89`.
- Espejo de agua perenne: `https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&outputFormat=application/json&bbox=-70.5,-39.6,-67.5,-36.6&typeName=ign:areas_de_aguas_continentales_perenne`, sha256 `39cfcdd5e92add20eb70545c6bd69bf77533fdd3ec13b6adf534fea4e2b71568`.
- Corriente de agua (áreas): `https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&outputFormat=application/json&bbox=-70.5,-39.6,-67.5,-36.6&typeName=ign:areas_de_aguas_continentales_BH140`, sha256 `c1515c50678fcce180b393be00271bca412884e7bfd5214b5643d48c8438068d`.
- Límite interprovincial: `https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&outputFormat=application/json&bbox=-70.5,-39.6,-67.5,-36.6&typeName=ign:linea_de_limite_070111`, sha256 `b96c7cdcf19042a40de59afced4a028f2de17a1cb2826ac61a788b0c8bc8fcb7`.
- Localidad (BAHRA): `https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&outputFormat=application/json&bbox=-70.5,-39.6,-67.5,-36.6&typeName=ign:localidad_bahra`, sha256 `2a3e2f3e7c879300d82c3cac0aea1efb779437ca6459b2e8d005adb670c0e71d`.
- Producción de hidrocarburos: concesiones de explotación: `http://datos.energia.gob.ar/dataset/81cfad0a-4162-4f85-ad71-837f5a5fae57/resource/48a306a3-d5da-4f28-8ab5-7f80767ffdec/download/produccin-hidrocarburos-concesiones-de-explotacin.zip`, sha256 `5245af707af4a4f8154d7ea80908aa4992d57f3eff7f19a64a92bbee4b45e0eb`.

El relieve son 16 teselas de un grado (la dirección de arriba es una de ellas) y su huella es el sha256 de la lista de las huellas de cada tesela. La huella de las capas del Instituto Geográfico Nacional es el sha256 de una forma canónica de sus elementos (ordenados por id), porque ese servicio no devuelve dos veces los mismos bytes. La de las concesiones es el sha256 del archivo bajado. El exportador no corre si una fuente cambió: hay que mirar qué cambió y fijar la huella nueva a mano.

## Cómo se arma cada capa

- Relieve: cada celda es la media entera de 20 por 16 muestras de un segundo de arco, sin contar los vacíos de la fuente. El relieve fino del núcleo sale de las mismas teselas con bloques de 4 por 4 muestras. Cada muestra de la fuente cae sobre un segundo de arco entero, así que la media de un bloque corresponde a medio segundo al noroeste del centro que le daría la caja: la caja del relieve fino lleva ese corrimiento y la de la hoja no (ver Exactitud).
- Ríos: las líneas de agua perenne se agrupan por nombre completo, se unen los tramos que comparten un extremo y se simplifican con una tolerancia de 60 m. Quedan los nombres que suman 60 km o más.
- Agua: todos los embalses y cauces anchos, y los lagos de 1 km² o más, con una tolerancia de 40 m.
- Límites: los tramos de cada límite se unen y se simplifican con una tolerancia de 100 m.
- Localidades: la lista fija del exportador, en el orden en que la página decide qué nombre mostrar primero.
- Concesiones: los polígonos del archivo cuya caja toca la hoja, tal como se publican, con una tolerancia de 15 m.
- Todas las coordenadas se guardan en una grilla de 65.535 pasos por lado: cerca de 4 m hacia el este y 5 m hacia el sur.

## Imagen del suelo

En la lectura de suelo de `site/mundo.html` los pozos se ven sobre una imagen satelital en color real, tendida sobre el relieve de esta misma hoja. La imagen es contexto: muestra el lugar en una fecha, no mide nada, y ningún número de la página sale de ella.

- Fuente: programa Copernicus de la Unión Europea, misión Sentinel-2, producto L2A en color real (TCI), leído del catálogo abierto Earth Search de Element 84 (`https://earth-search.aws.element84.com/v1`).
- Es un mosaico de 20 escenas tomadas el 29/12/2025 y el 30/12/2025: 11 de la órbita principal y 9 de la órbita vecina, que rellena la franja que la primera no cubre.
- La hoja entera mide 3.072 por 3.072 píxeles: cada uno cubre cerca de 86 m hacia el este y 109 m hacia el sur.
- Un recorte más fino cubre el núcleo, de 69,25° a 68,25° de longitud oeste y de 38,85° a 38,1° de latitud sur. Mide 3.072 por 2.304 píxeles: cada uno cubre cerca de 28 m hacia el este y 36 m hacia el sur.
- Licencia: los datos Sentinel son de uso libre y abierto (`https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice`), con esta atribución: "Contains modified Copernicus Sentinel data 2025". Dice "modified" porque las escenas se recortan, se remuestrean, se funden en sus bordes y se comprimen.
- Bajado el 19/11/2026.

Huella de cada archivo:

- `data/base_foto_caja.webp`: 831.106 bytes, sha256 `549139789053fb87c699794247d7a2fb3fc641f77abc1313b6ec023c3d7aaad9`.
- `data/base_foto_nucleo.webp`: 886.534 bytes, sha256 `c61d3a15ad2ff314a98490324d177d75632f962c25b9f0bceb5ab4887abbb1c7`.

La lista de las escenas, con la fecha y el satélite de cada una, está en `data/base_foto.json`. El armador (`pipeline/base_foto.py`) fija la huella de cada ventana que lee de cada escena y no corre si una cambió.

## Exactitud

Qué tan bien ubica la página lo que dibuja. Lo mide `python -m pipeline.exactitud` sobre la página publicada (datos a 2026-09, 3.448 pozos) y lo guarda en `data/exactitud.json`. Cada línea dice si es una medida o un supuesto.

- medido, relieve contra su fuente: en las bocas de los 3.437 pozos que caen dentro de la hoja, la cota que dibuja la página difiere de la del modelo de un segundo de arco en 0,6 m de mediana; el 99 % queda a 8,0 m o menos y el peor caso es de 28,4 m. Con la grilla de la hoja sola, en esos mismos pozos, la mediana era de 1,2 m y el 99 % quedaba a 11,0 m o menos. En los 2.552 pozos donde rige entero el relieve fino, la mediana es de 0,5 m, el 99 % queda a 2,4 m o menos y el peor caso es de 5,5 m; en esos, con la grilla de la hoja sola eran 1,1 m y 8,8 m.
- medido, cumbres: una celda promedia el terreno que cubre, así que la página rebaja las cumbres. Volcán Auca Mahuida: 2.251 m en la fuente y 2.165 m en la página; Volcán Domuyo: 4.698 m en la fuente y 4.619 m en la página.
- medido, espejos de agua: Embalse Los Barreales: 414 m en la fuente y 414 m en la página; Embalse Mari Menuco: 414 m en la fuente y 414 m en la página; Embalse Ezequiel Ramos Mexía: 370 m en la fuente y 370 m en la página; Lago Pellegrini: 272 m en la fuente y 272 m en la página.
- medido, relieve contra un modelo independiente: en una muestra fija de 91 bocas, la fuente da 2,1 m más que el modelo Copernicus GLO-90 en la mediana, con una diferencia máxima de 8,9 m; la página da 2,1 m más, con una máxima de 10,7 m. Los valores de GLO-90 se consultaron una sola vez, el 19/11/2026, y quedaron, con su fuente y su atribución, en `data/exactitud_glo90.json`.
- medido, pozos sobre la imagen: se apilaron los recortes de la imagen centrados en 767 locaciones, las de pozos que producían al menos 6 meses antes de la imagen. La pila tiene su máximo en el píxel del centro, de 3,5 desvíos sobre el entorno, y su centro queda a 7 m al oeste y 6 m al sur de la posición publicada; un píxel mide 28 por 36 m. El 86 % de las locaciones cae sobre suelo más claro que su entorno. La misma pila corrida 1 km al este no muestra ningún máximo: llega a 0,5 desvíos. La imagen se ve blanda de cerca porque cada píxel cubre esas decenas de metros: es resolución, no un error de ubicación.
- medido, agua sobre la imagen: el contorno de Embalse Los Barreales y Embalse Mari Menuco coincide con el agua de la imagen en el 91,3 % (intersección sobre unión), y ningún corrimiento de hasta 8 píxeles lo mejora.
- supuesto, el dibujo es plano: la página dibuja cada grado de latitud como 111,32 km y cada grado de longitud como 111,32 km por el coseno de la latitud del pozo mediano. Contra el elipsoide WGS84, eso alarga las distancias norte-sur un 0,29 %. Las distancias este-oeste quedan un 0,4 % cortas en el borde norte del núcleo y un 0,6 % largas en el borde sur; en los bordes de la hoja, un 2,4 % cortas al norte y un 1,7 % largas al sur. Las distancias entre pozos del estudio no salen del dibujo: se calculan con la latitud de cada pozo.
- supuesto, registro de la grilla de la hoja: sus celdas quedan medio segundo de arco corridas respecto de las muestras que promedian, cerca de 12 m al este y 15 m al sur. El relieve fino lo corrige en el núcleo, y el efecto ya está dentro de las diferencias medidas arriba.

## Qué no es

- No es cartografía oficial y no sirve para medir un lindero: las líneas están simplificadas.
- Las concesiones son las del archivo publicado el día de la descarga. No muestran cambios posteriores de titular ni permisos de exploración.
- El relieve es el terreno. No dice nada de la profundidad de una formación: en la página la profundidad sigue siendo un esquema, y así está rotulada.
- La imagen del suelo tiene fecha y no cambia con el reloj de la página: un pozo posterior a esa fecha puede no tener todavía su locación en ella, y al mirar un mes anterior se ven locaciones que todavía no existían. La página lo dice en pantalla.

## Reproducir

```
uv run python -m pipeline.base_mapa --descargar   # baja lo que falta a data/raw/base_mapa y arma el producto
uv run python -m pipeline.base_mapa --verificar   # compara con data/base_mapa.json y con esta página
uv run python -m pipeline.base_mapa --pagina      # reescribe solo esta página, sin los archivos crudos
uv run --with pillow python -m pipeline.base_foto --descargar   # baja las ventanas que faltan y arma la imagen
uv run python -m pipeline.base_foto --verificar   # compara data/base_foto.json con los dos archivos WebP
uv run --with pillow python -m pipeline.exactitud   # mide la página armada y escribe data/exactitud.json
uv run --with pillow python -m pipeline.exactitud --verificar   # mide de nuevo y compara
```
