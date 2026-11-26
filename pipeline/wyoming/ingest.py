"""Baja los datos publicos de Wyoming a data/wyoming/raw (git-ignorado), con manifiesto de sha256.

    uv run python -m pipeline.wyoming.ingest

Fuentes (las dos del menu de descargas de WOGCC, por URL directa, una vez por archivo):
  * Encabezados de pozos (APINO, LON y LAT de superficie, FIRSTCOMP, TD, MD): un zip con el DBF de pozos
    (110326WH.DBF) y el de pozos taponados (110326PA.DBF, que NO se usa).
  * Produccion mensual por pozo y anio: un zip con cuatro XLSX por rangos de condados, una fila por pozo y anio
    con doce columnas por mes (OIL, GAS, WATER, DAYS).

Los archivos bajados son datos no confiables: no se ejecuta nada de ellos; se leen con zipfile, struct y xml.
Idempotente: un archivo ya presente y registrado con el mismo sha256 no se baja otra vez; uno presente pero sin
registro (por ejemplo, copiado de una descarga previa) se valida contra la fuente (tamano del zip) y se registra.
Sin recorrer paginas, formularios de consulta ni consultas por pozo; un solo reintento ante un error de red.
Uso de la fuente (nuestra lectura de los terminos del menu de descargas de WOGCC, no una licencia): la ingesta baja
solo los archivos del menu por URL directa y nada de Wyoming se redistribuye crudo.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from pipeline.colorado.ingest import leer_dbf  # noqa: F401  (el mismo lector de DBF que Colorado)
from pipeline.ingest import DATA

RAW = DATA / "wyoming" / "raw"
MANIFEST = RAW / "manifest.json"
UA = "vaca-muerta-data/0.1"

WOGCC = "https://pipeline.wyo.gov/downloads"
URL_POZOS = WOGCC + "/110326WH.zip"
URL_PRODUCCION = WOGCC + "/TTLProd_110426.zip"

RUTA_POZOS = "110326WH.zip"
RUTA_PRODUCCION = "TTLProd_110426.zip"

MESES = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
TIPOS_MES = ["OIL", "GAS", "WATER", "DAYS"]
COLUMNAS_MES = [f"{m}_{t}" for m in MESES for t in TIPOS_MES]

# ---------------------------------------------------------------- red

def _pedido(url: str, metodo: str = "GET"):
    return urllib.request.urlopen(urllib.request.Request(url, method=metodo, headers={"User-Agent": UA}), timeout=600)


def tamano_remoto(url: str) -> int:
    with _pedido(url, metodo="HEAD") as r:
        return int(r.headers["Content-Length"])


def _descargar(url: str, destino: Path) -> dict:
    """Baja a un temporal junto al destino y lo mueve al final (un corte nunca deja un archivo a medias)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".part")
    sha = hashlib.sha256()
    n = 0
    with _pedido(url) as r, tmp.open("wb") as out:
        meta = {"etag": r.headers.get("ETag"), "last_modified": r.headers.get("Last-Modified")}
        while chunk := r.read(1 << 20):
            sha.update(chunk)
            n += len(chunk)
            out.write(chunk)
    if n == 0:
        tmp.unlink()
        raise RuntimeError(f"{url}: descarga vacia")
    tmp.replace(destino)
    return {**meta, "bytes": n, "sha256": sha.hexdigest()}


def descargar(url: str, destino: Path) -> dict:
    """Una descarga con un unico reintento ante un error de red (nada mas)."""
    try:
        return _descargar(url, destino)
    except (urllib.error.URLError, OSError) as err:
        print(f"reintento unico tras error de red ({url}): {err}", file=sys.stderr)
        return _descargar(url, destino)


# ---------------------------------------------------------------- lector de XLSX con la biblioteca estandar

def _local(tag: str) -> str:
    return tag.rpartition("}")[2]


def _col_a_indice(ref: str) -> int:
    """Referencia 'BC12' a indice 0-based de columna (55)."""
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
    if not n:
        raise ValueError(f"referencia de celda sin columna: {ref!r}")
    return n - 1


def _leer_shared_strings(fh) -> list[str]:
    it = ET.iterparse(fh, events=("start", "end"))
    _, raiz = next(it)
    out = []
    for evento, elem in it:
        if evento == "end" and _local(elem.tag) == "si":
            out.append("".join(t.text or "" for t in elem.iter() if _local(t.tag) == "t"))
            raiz.clear()
    return out


def _valor_celda(c, ss: list[str]) -> str:
    t = c.get("t", "n")
    v = None
    for h in c:
        nombre = _local(h.tag)
        if nombre == "v":
            v = h.text
        elif nombre == "is":
            v = "".join(x.text or "" for x in h.iter() if _local(x.tag) == "t")
    if v is None or v == "":
        return ""
    if t == "s":
        try:
            return ss[int(v)]
        except (ValueError, IndexError):
            return ""
    if t in ("str", "inlineStr"):
        return v
    if t == "b":
        return "1" if v == "1" else "0"
    if t == "e":
        return ""
    try:
        f = float(v)
    except ValueError:
        return v
    return str(int(f)) if f.is_integer() else repr(f)


def _leer_hoja(fh, ss: list[str]):
    """Filas de una hoja XLSX como listas de texto, con memoria acotada (iterparse y limpieza por fila)."""
    it = ET.iterparse(fh, events=("start", "end"))
    _, raiz = next(it)
    primera, ncols, emitidas = True, 0, 0
    for evento, elem in it:
        if evento != "end" or _local(elem.tag) != "row":
            continue
        celdas: dict[int, str] = {}
        for c in elem:
            if _local(c.tag) != "c":
                continue
            try:
                celdas[_col_a_indice(c.get("r", ""))] = _valor_celda(c, ss)
            except ValueError:
                continue
        if primera:
            ncols = (max(celdas) + 1) if celdas else 0
            primera = False
        try:
            n = int(elem.get("r", emitidas + 1))
        except ValueError:
            n = emitidas + 1
        while emitidas < n - 1:  # filas salteadas en el XML: se emiten vacias para no desalinear
            yield [""] * ncols
            emitidas += 1
        yield [celdas.get(i, "") for i in range(ncols)]
        emitidas += 1
        raiz.clear()


def _filas_xlsx(zf: zipfile.ZipFile):
    try:
        with zf.open("xl/sharedStrings.xml") as fh:
            ss = _leer_shared_strings(fh)
    except KeyError:
        ss = []
    try:
        fh = zf.open("xl/worksheets/sheet1.xml")
    except KeyError:
        nombres = [i.filename for i in zf.infolist()]
        raise ValueError(f"el XLSX no trae xl/worksheets/sheet1.xml (trae: {', '.join(nombres)})")
    with fh:
        yield from _leer_hoja(fh, ss)


def filas_xlsx(path: Path):
    """Filas de la primera hoja de un XLSX como listas de texto (la primera es el encabezado)."""
    with zipfile.ZipFile(path) as zf:
        yield from _filas_xlsx(zf)


def filas_xlsx_bytes(datos: bytes):
    """Lo mismo desde los bytes de un XLSX (para leerlo dentro del zip de produccion sin extraerlo)."""
    import io

    with zipfile.ZipFile(io.BytesIO(datos)) as zf:
        yield from _filas_xlsx(zf)


def canonizar_columna(nombre: str) -> str:
    """Encabezado del XLSX de WOGCC a nombre canonico (JAN_OIL, APINO, YR, COMPANY, FIELD)."""
    e = re.sub(r"\s+", "_", nombre.strip().upper()).replace("-", "_")
    m = re.fullmatch(r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)_?(OIL|GAS|WATER|DAYS)", e)
    if m:
        return f"{m.group(1)}_{m.group(2)}"
    if e in ("APINO", "API", "API_NO", "APINUMBER", "API_NUMBER"):
        return "APINO"
    if e in ("YR", "YEAR", "YYYY", "ANO", "ANIO"):
        return "YR"
    if e in ("COMPANY", "OPERATOR", "OPNAME", "OPERADOR", "COMPANY_NAME"):
        return "COMPANY"
    if "FIELD" in e:
        return "FIELD"
    return e


def xlsx_a_csv(fuente: Path | bytes, destino: Path) -> list[str]:
    """La primera hoja de un XLSX a un CSV de texto con encabezados canonicos. Devuelve los originales.

    Las filas del todo vacias (relleno de la hoja) no se escriben. COMPANY y FIELD ausentes se agregan vacias;
    APINO, YR o alguna columna de mes ausente frenan con un error que las nombra.
    """
    filas = filas_xlsx_bytes(fuente) if isinstance(fuente, bytes) else filas_xlsx(fuente)
    original = next(filas)
    canon = [canonizar_columna(h) for h in original]
    if len(set(canon)) != len(canon):
        repetidas = sorted({c for c in canon if canon.count(c) > 1})
        raise ValueError(f"columnas canonicas repetidas: {', '.join(repetidas)}")
    faltan = [c for c in ["APINO", "YR", *COLUMNAS_MES] if c not in canon]
    if faltan:
        raise ValueError(f"columnas ausentes en el XLSX: {', '.join(faltan)}")
    for opt in ("COMPANY", "FIELD"):
        if opt not in canon:
            canon.append(opt)
    idx = {c: canon.index(c) for c in canon}
    n = len(original)
    with destino.open("w", newline="", encoding="utf-8") as out:
        w = csv.writer(out, lineterminator="\n")
        w.writerow(canon)
        for fila in filas:
            if not any(c.strip() for c in fila):
                continue
            fila += [""] * (n - len(fila))
            w.writerow([fila[idx[c]] if idx[c] < n else "" for c in canon])
    return original


# ---------------------------------------------------------------- miembros de los zips

def miembro_encabezados(zip_path: Path) -> str:
    """El DBF de pozos dentro del zip de encabezados (el WH; el PA de taponados no se usa)."""
    with zipfile.ZipFile(zip_path) as z:
        candidatos = [i.filename for i in z.infolist() if i.filename.upper().endswith("WH.DBF")]
    if len(candidatos) != 1:
        raise ValueError(f"{zip_path.name}: esperaba un DBF de pozos (WH) y hay {len(candidatos)}")
    return candidatos[0]


def miembros_produccion(zip_path: Path) -> list[str]:
    """Los XLSX dentro del zip de produccion, ordenados por nombre."""
    with zipfile.ZipFile(zip_path) as z:
        return sorted(i.filename for i in z.infolist() if i.filename.lower().endswith(".xlsx"))


def pozos_a_csv(zip_path: Path, destino: Path) -> int:
    """El DBF de pozos del zip de encabezados a un CSV de texto en `destino`. Devuelve las filas de datos."""
    n = 0
    with zipfile.ZipFile(zip_path) as z, z.open(miembro_encabezados(zip_path)) as fh, destino.open(
        "w", newline="", encoding="utf-8"
    ) as out:
        w = csv.writer(out, lineterminator="\n")
        for i, fila in enumerate(leer_dbf(fh)):
            w.writerow(fila)
            n += i > 0
    return n


# ---------------------------------------------------------------- manifiesto

def cargar_manifiesto(path: Path = MANIFEST) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def guardar_manifiesto(m: dict, path: Path = MANIFEST) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(m, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def sha256_archivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _zip_valido(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None
    except (zipfile.BadZipFile, OSError):
        return False


def asegurar_zip(nombre: str, url: str, ruta: str, manifiesto: dict, raw: Path = RAW) -> str:
    """Un zip de WOGCC: presente y registrado con su sha256 no se baja; presente sin registro se valida contra el tamano remoto."""
    destino = raw / ruta
    e = manifiesto.get(nombre)
    if destino.exists() and e and e.get("sha256") == sha256_archivo(destino):
        return "sin cambios"
    if destino.exists():
        try:
            ok = _zip_valido(destino) and destino.stat().st_size == tamano_remoto(url)
        except OSError:
            ok = False
        if ok:
            manifiesto[nombre] = {"url": url, "ruta": ruta, "bytes": destino.stat().st_size,
                                  "sha256": sha256_archivo(destino), "origen": "copia validada", "registrado": _ahora()}
            return "registrado (copia validada contra la fuente)"
    meta = descargar(url, destino)
    manifiesto[nombre] = {"url": url, "ruta": ruta, **meta, "origen": "descarga", "registrado": _ahora()}
    return "descargado"


def main(argv: list[str] | None = None) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    m = cargar_manifiesto()
    print(f"pozos: {asegurar_zip('pozos', URL_POZOS, RUTA_POZOS, m)}")
    guardar_manifiesto(m)
    print(f"produccion: {asegurar_zip('produccion', URL_PRODUCCION, RUTA_PRODUCCION, m)}")
    guardar_manifiesto(m)
    print(f"manifiesto: {MANIFEST} ({len(m)} fuentes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
