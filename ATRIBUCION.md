# Licencia y atribución de los datos

El código y los textos de este repositorio se publican con la licencia MIT ([LICENSE](LICENSE)). Esa licencia cubre
solo lo que escribe este proyecto. Los datos de terceros conservan los términos de su fuente: si reusás un archivo de
abajo o una cifra que sale de él, citá su fuente con la atribución que pide.

## Fuentes

| Fuente | Qué se usa | Dónde está en el repositorio | Términos y atribución |
|---|---|---|---|
| Secretaría de Energía de la Nación (datos.energia.gob.ar, datos.gob.ar) | Producción por pozo, fracturas, trayectorias de pozo y concesiones de explotación | `data/muestra/` (un recorte), `data/base_mapa.json` (concesiones), las cifras del wiki y del sitio y, como archivos completos, la [release datos-crudos-2026-11-23](https://github.com/GabrielRuizVarela/vaca-muerta-en-datos/releases/tag/datos-crudos-2026-11-23) del repositorio público (los tres archivos crudos del manifest, con su sha256) | CC BY 4.0. Atribución: "Datos: Secretaría de Energía de la Nación". |
| Programa Copernicus de la Unión Europea, misión Sentinel-2 | Imagen satelital del mapa 3D | `data/base_foto_caja.webp`, `data/base_foto_nucleo.webp`, `data/base_foto.json` | Uso libre y abierto ([aviso legal](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice)). Atribución: "Contains modified Copernicus Sentinel data 2025". |
| NASA y USGS, SRTM de 1 segundo de arco | Relieve del mapa 3D | `data/base_mapa.json`, `data/base_relieve_nucleo.json` | Dominio público. Atribución: datos SRTM cortesía del U.S. Geological Survey. |
| Copernicus DEM GLO-90, leído con la API de elevación de Open-Meteo | Control de exactitud del relieve | `data/exactitud_glo90.json` | Atribución: "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved". |
| Instituto Geográfico Nacional | Ríos, lagos y embalses, límites interprovinciales y localidades | `data/base_mapa.json` | Uso libre y gratuito con reconocimiento de la autoría del Instituto Geográfico Nacional. |
| Archivo (The Archivo Project Authors) y Faustina (The Faustina Project Authors) | Tipografías de las páginas del sitio | `site/fuentes/archivo/` y `site/fuentes/faustina/`, cada una con su texto de licencia (`OFL.txt`) | SIL Open Font License 1.1, no se vende la fuente sola. Atribución: © 2020 The Archivo Project Authors y © 2016 The Faustina Project Authors. |
| Natural Earth | Contornos de los países y de las provincias o estados del globo | `data/globo_geometria.json` | Dominio público. |
| ECMC (Colorado) y FracFocus | Réplica del estudio en Colorado | Solo cifras derivadas; los archivos de la fuente no están en el repositorio | Términos de uso de cada sitio. Atribución: ECMC (Energy and Carbon Management Commission de Colorado) y FracFocus. |
| WOGCC (Wyoming) | Réplica del estudio en Wyoming | Solo cifras derivadas; los archivos de la fuente no están en el repositorio | Términos de uso del regulador; se publican solo cifras derivadas. Atribución: WOGCC (Wyoming Oil and Gas Conservation Commission). |
| Reguladores de otras cuencas (relevamiento de fuentes) | Términos de uso citados y filas de muestra cortas, para decidir qué fuentes entran al estudio | `data/fuentes_mundo.json` y `wiki/hallazgos/fuentes_mundo.md` | Los de cada fuente, citados en el archivo. Solo entran al estudio las fuentes cuyos términos permiten publicar cifras derivadas. |

## Detalle

- Mapa 3D (relieve, agua, límites, localidades, concesiones e imagen): la dirección de descarga, la fecha y la huella
  sha256 de cada capa están en [mapa_base.md](wiki/hallazgos/mapa_base.md).
- Trayectorias de pozo: lo mismo en [trayectorias.md](wiki/hallazgos/trayectorias.md).
- Natural Earth y Copernicus DEM GLO-90: la dirección, la fecha y la huella están en `data/globo_geometria.json` y en
  `data/exactitud_glo90.json`.
- Colorado y Wyoming: la huella de cada archivo está en [colorado_datos.md](wiki/hallazgos/colorado_datos.md) y en
  [wyoming_datos.md](wiki/hallazgos/wyoming_datos.md); las direcciones de descarga, en `pipeline/colorado/ingest.py` y
  en `pipeline/wyoming/ingest.py`.
- Cómo se eligieron las fuentes de otras cuencas y qué dicen sus términos: [fuentes_mundo.md](wiki/hallazgos/fuentes_mundo.md).

Los archivos crudos completos de la Secretaría de Energía no se suben al repositorio: `pipeline` los baja de la fuente y
`data/manifest.json` guarda su huella. `data/muestra/` tiene solo un recorte, con filas copiadas tal como vienen de la
fuente.
