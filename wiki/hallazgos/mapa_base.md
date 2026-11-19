# Mapa base del mundo 4D: fuentes y licencias

Lo que se ve debajo de los pozos en `site/mundo.html` (relieve, ríos, lagos y embalses, límites entre provincias, localidades y concesiones de explotación) es dato publicado por tres organismos, no una estimación de este estudio. La regla es una sola: sin fuente no hay capa. Ningún río se dibuja de memoria y ningún bloque se inventa a partir de los pozos.

Esta página la escribe `python -m pipeline.base_mapa` a partir de `data/base_mapa.json`. No se edita a mano.

## Qué cubre

La hoja va de 70,5° a 67,5° de longitud oeste y de 39,6° a 36,6° de latitud sur. Tiene:

- relieve: una grilla de 540 por 675 celdas (20 por 16 segundos de arco, cerca de 500 m de lado), con cotas de 220 a 4.656 m sobre el nivel del mar;
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

- Relieve: cada celda es la media entera de 20 por 16 muestras de un segundo de arco, sin contar los vacíos de la fuente.
- Ríos: las líneas de agua perenne se agrupan por nombre completo, se unen los tramos que comparten un extremo y se simplifican con una tolerancia de 60 m. Quedan los nombres que suman 60 km o más.
- Agua: todos los embalses y cauces anchos, y los lagos de 1 km² o más, con una tolerancia de 40 m.
- Límites: los tramos de cada límite se unen y se simplifican con una tolerancia de 100 m.
- Localidades: la lista fija del exportador, en el orden en que la página decide qué nombre mostrar primero.
- Concesiones: los polígonos del archivo cuya caja toca la hoja, tal como se publican, con una tolerancia de 15 m.
- Todas las coordenadas se guardan en una grilla de 65.535 pasos por lado: cerca de 4 m hacia el este y 5 m hacia el sur.

## Qué no es

- No es cartografía oficial y no sirve para medir un lindero: las líneas están simplificadas.
- Las concesiones son las del archivo publicado el día de la descarga. No muestran cambios posteriores de titular ni permisos de exploración.
- El relieve es el terreno. No dice nada de la profundidad de una formación: en la página la profundidad sigue siendo un esquema, y así está rotulada.

## Reproducir

```
uv run python -m pipeline.base_mapa --descargar   # baja lo que falta a data/raw/base_mapa y arma el producto
uv run python -m pipeline.base_mapa --verificar   # compara con data/base_mapa.json y con esta página
uv run python -m pipeline.base_mapa --pagina      # reescribe solo esta página, sin los archivos crudos
```
