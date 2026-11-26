"""Baja los datos publicos del Colorado a data/colorado/raw (git-ignorado), con manifiesto de sha256.

    uv run python -m pipeline.colorado.ingest

Fuentes (todas publicas):
  * Produccion mensual por pozo y formacion, ECMC, un zip por ano 2018 a 2024.
  * Archivo de pozos de ECMC (WELLS_SHP.ZIP): ubicacion de superficie, profundidades, operador. Se lee solo Wells.dbf, con un
    lector propio de DBF; no se usa la capa de lineas direccionales (no hay lector de shapefile entre las dependencias), asi que
    el largo de rama es el proxy MD menos TVD.
  * FracFocus: SOLO DisclosureList_1.csv, sacado de FracFocusCSV.zip (444 MB) con pedidos HTTP de rango (el directorio central
    del zip y el flujo comprimido de ese miembro). El zip entero nunca se baja; si el servidor no atiende rangos, se frena.

Los archivos bajados son datos no confiables: no se ejecuta nada de ellos; se leen con zipfile, struct, zlib y DuckDB read_csv.
Idempotente: un archivo ya presente y registrado con el mismo sha256 no se baja otra vez; uno presente pero sin registro (por
ejemplo, copiado de una descarga previa) se valida contra la fuente (tamano del zip o CRC del miembro) y se registra.
Condiciones de uso de FracFocus: se aceptan al bajar; los datos se pueden agregar o combinar pero no alterar, y no hay garantia.
ECMC: sin restricciones de uso, con descargo de responsabilidad.
"""
from __future__ import annotations

import csv
import hashlib
import json
import struct
import sys
import urllib.request
import zipfile
import zlib
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path

from pipeline.colorado import ANIOS_PRODUCCION
from pipeline.ingest import DATA

RAW = DATA / "colorado" / "raw"
MANIFEST = RAW / "manifest.json"
UA = "vaca-muerta-data/0.1"

ECMC = "https://ecmc.state.co.us/documents/data/downloads"
URL_PRODUCCION = ECMC + "/production/{anio}_prod_reports.zip"
URL_POZOS = ECMC + "/gis/WELLS_SHP.ZIP"
URL_FRACFOCUS_ZIP = "https://www.fracfocusdata.org/digitaldownload/FracFocusCSV.zip"
MIEMBRO_FRACFOCUS = "DisclosureList_1.csv"

RUTA_POZOS = "WELLS_SHP.ZIP"
RUTA_FRACFOCUS = MIEMBRO_FRACFOCUS
MIEMBRO_POZOS = "Wells.dbf"


def ruta_produccion(anio: int) -> str:
    return f"prod/{anio}_prod_reports.zip"


class ErrorRango(RuntimeError):
    """El servidor no atiende pedidos de rango o devolvio algo inesperado: se frena en vez de bajar el zip entero."""


# ---------------------------------------------------------------- red

def _pedido(url: str, rango: tuple[int, int] | None = None, metodo: str = "GET"):
    req = urllib.request.Request(url, method=metodo, headers={"User-Agent": UA})
    if rango is not None:
        req.add_header("Range", f"bytes={rango[0]}-{rango[1]}")
    return urllib.request.urlopen(req, timeout=600)


def tamano_remoto(url: str) -> int:
    with _pedido(url, metodo="HEAD") as r:
        return int(r.headers["Content-Length"])


def leer_rango_http(url: str) -> Callable[[int, int], bytes]:
    """Funcion (inicio, fin inclusive) -> bytes que exige una respuesta 206 con exactamente esos bytes."""
    def leer(ini: int, fin: int) -> bytes:
        with _pedido(url, (ini, fin)) as r:
            if r.status != 206:
                raise ErrorRango(f"{url}: pedi bytes {ini}-{fin} y el servidor respondio {r.status} (no atiende rangos)")
            datos = r.read()
        if len(datos) != fin - ini + 1:
            raise ErrorRango(f"{url}: pedi {fin - ini + 1} bytes y llegaron {len(datos)}")
        return datos
    return leer


def descargar(url: str, destino: Path) -> dict:
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


# ---------------------------------------------------------------- un miembro de un zip por pedidos de rango

def directorio_central(leer: Callable[[int, int], bytes], total: int) -> list[dict]:
    """Entradas del directorio central de un zip leyendo solo su cola. Sin zip64 (el zip de FracFocus mide menos de 4 GB)."""
    cola_ini = max(0, total - 65536 - 22)
    cola = leer(cola_ini, total - 1)
    i = cola.rfind(b"PK\x05\x06")
    if i < 0:
        raise ErrorRango("no encuentro el fin del directorio central del zip")
    n, tam, off = struct.unpack("<HII", cola[i + 10:i + 20])
    if n == 0xFFFF or 0xFFFFFFFF in (tam, off):
        raise ErrorRango("zip64: no soportado")
    cd = cola[off - cola_ini:off - cola_ini + tam] if off >= cola_ini else leer(off, off + tam - 1)
    entradas, p = [], 0
    for _ in range(n):
        if cd[p:p + 4] != b"PK\x01\x02":
            raise ErrorRango("directorio central malformado")
        metodo, = struct.unpack("<H", cd[p + 10:p + 12])
        crc, csz, usz, nl, el, cl = struct.unpack("<IIIHHH", cd[p + 16:p + 34])
        off_local, = struct.unpack("<I", cd[p + 42:p + 46])
        nombre = cd[p + 46:p + 46 + nl].decode("utf-8", "replace")
        entradas.append({"nombre": nombre, "metodo": metodo, "crc32": crc, "comprimido": csz, "tamano": usz, "offset": off_local})
        p += 46 + nl + el + cl
    return entradas


def entrada(leer, total: int, nombre: str) -> dict:
    for e in directorio_central(leer, total):
        if e["nombre"] == nombre:
            return e
    raise ErrorRango(f"el zip no tiene {nombre}")


def extraer_miembro(leer: Callable[[int, int], bytes], total: int, nombre: str) -> Iterator[bytes]:
    """Bytes descomprimidos de un miembro, por pedidos de rango (directorio central, cabecera local y flujo), con CRC y tamano
    verificados al final. Un miembro stored o deflate; cualquier otro metodo se rechaza."""
    e = entrada(leer, total, nombre)
    cab = leer(e["offset"], e["offset"] + 29)
    if cab[:4] != b"PK\x03\x04":
        raise ErrorRango("cabecera local malformada")
    nl, el = struct.unpack("<HH", cab[26:30])
    ini = e["offset"] + 30 + nl + el
    if e["metodo"] not in (0, 8):
        raise ErrorRango(f"metodo de compresion {e['metodo']} no soportado")
    des = zlib.decompressobj(-15) if e["metodo"] == 8 else None
    crc, n, paso = 0, 0, 4 << 20
    for a in range(0, e["comprimido"], paso):
        b = min(a + paso, e["comprimido"])
        trozo = leer(ini + a, ini + b - 1)
        datos = des.decompress(trozo) if des else trozo
        crc = zlib.crc32(datos, crc)
        n += len(datos)
        yield datos
    if des:
        datos = des.flush()
        crc = zlib.crc32(datos, crc)
        n += len(datos)
        yield datos
    if (crc & 0xFFFFFFFF) != e["crc32"] or n != e["tamano"]:
        raise ErrorRango(f"{nombre}: el CRC o el tamano no coinciden con el directorio central")


def crc32_archivo(path: Path) -> tuple[int, int]:
    crc, n = 0, 0
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            crc = zlib.crc32(chunk, crc)
            n += len(chunk)
    return crc & 0xFFFFFFFF, n


# ---------------------------------------------------------------- lector de DBF (dBase III/IV), solo struct

def leer_dbf(fh) -> Iterator[list[str]]:
    """Filas de un DBF como listas de texto (la primera es el encabezado). Solo campos de texto: se descartan los
    borrados. Lee del archivo abierto en binario `fh`; no ejecuta nada del contenido."""
    cab = fh.read(32)
    if len(cab) < 32:
        raise ValueError("DBF truncado")
    n, largo_cab, largo_reg = struct.unpack("<IHH", cab[4:12])
    campos = []
    while True:
        d = fh.read(32)
        if not d or d[0] == 0x0D:
            break
        campos.append((d[:11].split(b"\0")[0].decode("ascii", "replace"), d[16]))
    if sum(w for _, w in campos) + 1 != largo_reg:
        raise ValueError("el largo de registro no coincide con los campos")
    fh.seek(largo_cab)
    yield [c for c, _ in campos]
    for _ in range(n):
        r = fh.read(largo_reg)
        if len(r) < largo_reg:
            raise ValueError("DBF truncado en los registros")
        if r[:1] == b"*":
            continue
        p, fila = 1, []
        for _, w in campos:
            fila.append(r[p:p + w].decode("latin1").strip())
            p += w
        yield fila


def pozos_a_csv(zip_path: Path, destino: Path) -> int:
    """Wells.dbf de WELLS_SHP.ZIP a un CSV de texto en `destino`. Devuelve la cantidad de filas de datos."""
    n = 0
    with zipfile.ZipFile(zip_path) as z, z.open(MIEMBRO_POZOS) as fh, destino.open("w", newline="", encoding="utf-8") as out:
        w = csv.writer(out, lineterminator="\n")
        for i, fila in enumerate(leer_dbf(fh)):
            w.writerow(fila)
            n += i > 0
    return n


def produccion_a_csv(zip_path: Path, destino: Path) -> None:
    """El unico CSV de un zip de produccion de ECMC, extraido a `destino` en bloques."""
    with zipfile.ZipFile(zip_path) as z:
        nombres = [i.filename for i in z.infolist() if i.filename.lower().endswith(".csv")]
        if len(nombres) != 1:
            raise ValueError(f"{zip_path.name}: esperaba un CSV y hay {len(nombres)}")
        with z.open(nombres[0]) as src, destino.open("wb") as out:
            while chunk := src.read(1 << 20):
                out.write(chunk)


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
    """Un zip de ECMC: presente y registrado con su sha256 no se baja; presente sin registro se valida contra el tamano remoto."""
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


def asegurar_fracfocus(manifiesto: dict, raw: Path = RAW, url: str = URL_FRACFOCUS_ZIP, leer=None, total: int | None = None) -> str:
    """DisclosureList_1.csv por pedidos de rango. Presente: se valida su CRC y tamano contra el directorio central."""
    leer = leer or leer_rango_http(url)
    total = tamano_remoto(url) if total is None else total
    e = entrada(leer, total, MIEMBRO_FRACFOCUS)
    destino = raw / RUTA_FRACFOCUS
    previo = manifiesto.get("fracfocus_disclosure_list")
    if destino.exists() and crc32_archivo(destino) == (e["crc32"], e["tamano"]):
        if previo and previo.get("sha256") == sha256_archivo(destino):
            return "sin cambios"
        origen = "copia validada"
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_name(destino.name + ".part")
        with tmp.open("wb") as out:
            for datos in extraer_miembro(leer, total, MIEMBRO_FRACFOCUS):
                out.write(datos)
        tmp.replace(destino)
        origen = "descarga por rango"
    manifiesto["fracfocus_disclosure_list"] = {
        "url": url, "miembro": MIEMBRO_FRACFOCUS, "ruta": RUTA_FRACFOCUS, "bytes": destino.stat().st_size,
        "sha256": sha256_archivo(destino), "crc32": f"{e['crc32']:08x}", "bytes_zip_remoto": total,
        "origen": origen, "registrado": _ahora()}
    return f"registrado ({origen})"


def main(argv: list[str] | None = None) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    m = cargar_manifiesto()
    try:
        for anio in ANIOS_PRODUCCION:
            print(f"produccion_{anio}: {asegurar_zip(f'produccion_{anio}', URL_PRODUCCION.format(anio=anio), ruta_produccion(anio), m)}")
            guardar_manifiesto(m)
        print(f"pozos: {asegurar_zip('pozos', URL_POZOS, RUTA_POZOS, m)}")
        guardar_manifiesto(m)
        print(f"fracfocus_disclosure_list: {asegurar_fracfocus(m)}")
        guardar_manifiesto(m)
    except ErrorRango as err:
        guardar_manifiesto(m)
        print(f"FRENADO: {err}", file=sys.stderr)
        return 1
    print(f"manifiesto: {MANIFEST} ({len(m)} fuentes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
