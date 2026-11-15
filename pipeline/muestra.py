"""Genera la muestra de datos (data/muestra/) a partir de la capa raw real.

  uv run python -m pipeline.muestra                 # lee data/raw (o VM_RAW_DIR), escribe data/muestra
  uv run python -m pipeline.muestra --destino DIR   # escribe en otro directorio

La muestra es un subconjunto determinista de los dos CSV que lee pipeline.build: se quedan las filas de unas
pocas áreas (las que pasan de la lista AREAS) y, de fracturas, las de los pozos que quedaron. Solo se
conservan las columnas que lee el staging SQL. Filas ordenadas, gzip con mtime=0: dos corridas dan los mismos bytes.
Escribe también manifest.json (mismo formato que data/manifest.json, con el SHA-256 del archivo fuente) y README.md.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import sys
from pathlib import Path

from pipeline import checks
from pipeline.ingest import DATA, ROOT, load_manifest

DESTINO = DATA / "muestra"

# Áreas que se conservan: Loma Campana y vecinas con muchos eventos de interferencia (el nombre se compara
# sin espacios sobrantes y en mayúsculas).
AREAS = ["LOMA CAMPANA", "BANDURRIA SUR", "LA AMARGA CHICA", "BANDURRIA CENTRO"]
NOMBRES = ("produccion_no_convencional", "fractura_adjunto_iv")
# Columna de cada archivo por la que se ordena (anio, mes, idpozo) o (idpozo, fecha, id).
ORDEN = {"produccion_no_convencional": ("anio", "mes", "idpozo"),
         "fractura_adjunto_iv": ("idpozo", "fecha_inicio_fractura", "id_base_fractura_adjiv")}


def _clave(valor: str):
    try:
        return (0, int(valor), "")
    except ValueError:
        return (1, 0, valor)


def columnas_usadas(dataset: str) -> set[str]:
    return set(checks.COLUMNAS_ESPERADAS[dataset])


def _leer(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f)
        cabecera = [c.strip() for c in next(r)]
        return cabecera, [fila for fila in r if fila]


def _gzip(texto: str) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, compresslevel=9, mtime=0) as g:
        g.write(texto.encode("utf-8"))
    return buf.getvalue()


def _csv_texto(cabecera: list[str], filas: list[list[str]]) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(cabecera)
    w.writerows(filas)
    return out.getvalue()


def _proyectar(cabecera: list[str], filas: list[list[str]], dataset: str) -> tuple[list[str], list[list[str]]]:
    usadas = columnas_usadas(dataset)
    idx = [i for i, c in enumerate(cabecera) if c.lower() in usadas]
    return [cabecera[i] for i in idx], [[f[i] if i < len(f) else "" for i in idx] for f in filas]


def _ordenar(cabecera: list[str], filas: list[list[str]], dataset: str) -> list[list[str]]:
    pos = [cabecera.index(c) for c in ORDEN[dataset] if c in cabecera]
    return sorted(filas, key=lambda f: ([_clave(f[i]) for i in pos], f))


def seleccionar(raw: dict[str, Path], areas: list[str] = AREAS) -> dict[str, tuple[list[str], list[list[str]]]]:
    """Filas elegidas de cada dataset, ya proyectadas a las columnas usadas y ordenadas."""
    areas_n = {a.strip().upper() for a in areas}
    cab, filas = _leer(raw["produccion_no_convencional"])
    i_area, i_pozo = cab.index("areapermisoconcesion"), cab.index("idpozo")
    prod = [f for f in filas if f[i_area].strip().upper() in areas_n]
    pozos = {f[i_pozo] for f in prod}
    cab_f, filas_f = _leer(raw["fractura_adjunto_iv"])
    j_pozo = cab_f.index("idpozo")
    frac = [f for f in filas_f if f[j_pozo] in pozos]
    out = {}
    for dataset, (c, fs) in (("produccion_no_convencional", (cab, prod)), ("fractura_adjunto_iv", (cab_f, frac))):
        c2, fs2 = _proyectar(c, fs, dataset)
        out[dataset] = (c2, _ordenar(c2, fs2, dataset))
    return out


def readme(manifest_fuente: dict, filas: dict[str, int], areas: list[str]) -> str:
    fuentes = "\n".join(f"- `{n}`: SHA-256 `{manifest_fuente[n]['sha256']}` ({manifest_fuente[n]['bytes']} bytes)"
                        for n in NOMBRES)
    return f"""# Muestra de datos

Subconjunto pequeño de los datos abiertos de la Secretaría de Energía de la Nación (datos.energia.gob.ar),
pensado para que `make demo` corra sin descargar los 150 MB originales.

**Esta muestra no reproduce las cifras de la cuenca.** Sirve para ver el pipeline y la página funcionando,
no para sacar conclusiones. Las cifras de la cuenca salen de la capa raw completa (`make full`).

## Fuentes

- Producción de pozos de gas y petróleo no convencional (Capítulo IV), `produccion_no_convencional`.
- Datos de fractura de pozos de hidrocarburos (Adjunto IV), `fractura_adjunto_iv`.

SHA-256 de los archivos fuente completos, tomados de `data/manifest.json` en el momento de generar la muestra:

{fuentes}

## Regla de selección

- Producción: todas las filas (todos los meses) de las áreas {", ".join(f"`{a}`" for a in areas)}
  ({filas['produccion_no_convencional']} filas).
- Fracturas: las filas de los pozos que quedaron en la muestra de producción ({filas['fractura_adjunto_iv']} filas).
- Solo se conservan las columnas que lee el staging (`pipeline/sql/01_staging.sql`); el resto se descarta.
- Filas ordenadas y gzip con mtime=0: `uv run python -m pipeline.muestra` da siempre los mismos bytes.
- `manifest.json` de esta carpeta tiene el mismo formato que `data/manifest.json`; sus `sha256` y `bytes` son los de
  los archivos de la muestra.

## Atribución

Datos: Secretaría de Energía de la Nación, datos abiertos (datos.energia.gob.ar). Recorte y procesamiento: este repositorio.
"""


def generar(raw: dict[str, Path], manifest_fuente: dict, destino: Path = DESTINO, areas: list[str] = AREAS) -> dict[str, Path]:
    """Escribe la muestra en `destino`. Devuelve los archivos escritos."""
    import hashlib
    destino.mkdir(parents=True, exist_ok=True)
    sel = seleccionar(raw, areas)
    manifest, escritos, filas = {}, {}, {}
    for dataset in NOMBRES:
        cab, fs = sel[dataset]
        datos = _gzip(_csv_texto(cab, fs))
        ruta = destino / f"{dataset}.csv.gz"
        ruta.write_bytes(datos)
        escritos[dataset] = ruta
        filas[dataset] = f"{len(fs):,}".replace(",", ".")
        fuente = manifest_fuente[dataset]
        manifest[dataset] = {"url": fuente.get("url"), "bytes": len(datos), "sha256": hashlib.sha256(datos).hexdigest(),
                             "path": ruta.name, "sha256_fuente": fuente["sha256"], "bytes_fuente": fuente["bytes"]}
    (destino / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (destino / "README.md").write_text(readme(manifest_fuente, filas, areas), encoding="utf-8")
    return escritos


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.muestra", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--destino", type=Path, default=DESTINO, help="directorio de salida (por defecto data/muestra)")
    a = ap.parse_args(argv)
    from pipeline.build import raw_inputs
    manifest = load_manifest()
    raw_dir = Path(os.environ.get("VM_RAW_DIR") or DATA / "raw")
    raw = raw_inputs(manifest, raw_dir)
    escritos = generar(raw, manifest, a.destino)
    for dataset, ruta in escritos.items():
        print(f"{dataset}: {ruta.relative_to(ROOT) if ruta.is_relative_to(ROOT) else ruta} ({ruta.stat().st_size / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
