# Muestra de datos

Subconjunto pequeño de los datos abiertos de la Secretaría de Energía de la Nación (datos.energia.gob.ar),
pensado para que `make demo` corra sin descargar los 150 MB originales.

**Esta muestra no reproduce las cifras de la cuenca.** Sirve para ver el pipeline y la página funcionando,
no para sacar conclusiones. Las cifras de la cuenca salen de la capa raw completa (`make full`).

## Fuentes

- Producción de pozos de gas y petróleo no convencional (Capítulo IV), `produccion_no_convencional`.
- Datos de fractura de pozos de hidrocarburos (Adjunto IV), `fractura_adjunto_iv`.

SHA-256 de los archivos fuente completos, tomados de `data/manifest.json` en el momento de generar la muestra:

- `produccion_no_convencional`: SHA-256 `61cecc31c8dd81fd474c4094f2605b2b01b5a5d157e2089db7f3c548c410deae` (148923474 bytes)
- `fractura_adjunto_iv`: SHA-256 `ff95734bf485b1a27ecb75e3a44dda3035e5496805cf3970a28d19802bf03026` (1271920 bytes)

## Regla de selección

- Producción: todas las filas (todos los meses) de las áreas `LOMA CAMPANA`, `BANDURRIA SUR`, `LA AMARGA CHICA`, `BANDURRIA CENTRO`
  (125.668 filas).
- Fracturas: las filas de los pozos que quedaron en la muestra de producción (1.393 filas).
- Solo se conservan las columnas que lee el staging (`pipeline/sql/01_staging.sql`); el resto se descarta.
- Filas ordenadas y gzip con mtime=0: `uv run python -m pipeline.muestra` da siempre los mismos bytes.
- `manifest.json` de esta carpeta tiene el mismo formato que `data/manifest.json`; sus `sha256` y `bytes` son los de
  los archivos de la muestra.

## Atribución

Datos: Secretaría de Energía de la Nación, datos abiertos (datos.energia.gob.ar). Recorte y procesamiento: este repositorio.
