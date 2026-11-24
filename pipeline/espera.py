"""Regla de plata de la espera: cuanto cuesta recibir los barriles mas tarde.

Es un calculo de supuestos, no una medicion. Este modulo arma el diccionario de la pagina
`site/espera.html` (que escribe con `render`) y permite correr la regla sobre el warehouse
para ver una sola linea por consola.

La regla: los barriles diferidos se reciben mas tarde. Con un precio por barril
(PRECIO), una tasa anual (TASA) y una espera (MESES) se calcula el costo de recibir
los barriles tarde, no su valor:

    dinero(bbl, precio, tasa_pct, meses) = bbl * precio * (1 - (1 + tasa_pct / 100) ** (-meses / 12))

El factor es un descuento por el tiempo de espera, asi que a tasa cero el costo es
cero y el costo crece con los meses de espera. Como son supuestos, cada parametro
tiene un rango permitido (minimo, maximo, valor por defecto, paso) y un valor fuera
de rango es un error, no un recorte silencioso.

El rango del diferido se toma del warehouse: la cota inferior es la variante
neto_previa de mart_diferido_rango (la que descuenta el diferido previo) y la cota
superior es la variante original. La frase que resume la regla lo dice explicito:
"el extremo alto es un maximo; supuesto, no medicion".

Datos que usa replay.collect (mismo contrato que pipeline/replay.py):

- meta:    {meses, mes_datos, hash_datos, ...} la linea de tiempo sin cambios, salvo n_pozos,
           que pasa a contar los pozos de esta vista.
- pozos:   [{id, op, area, pad, wiki, lon, lat, mes0, frac}] los pozos que quedan
           en esta vista (los padres y los hijos de los eventos cercanos con diferido),
           en el orden original de la vista general y renumerados desde cero.
- caudal:  base64 de una matriz Uint16 pozos x meses, en bbl/d.
- agua:    base64 de una matriz Uint8 pozos x meses, corte de agua por 255.
- eventos: [{f, t: "interf", p, h, km, rumbo, clase, bbl}] solo interferencias
           cercanas (menos de 1 km) con diferido medido; p y h son indices en pozos. Se eligen por traer
           bbl (solo los eventos cercanos de mart_interferencia_diferida lo traen), no por km: replay redondea km a
           dos decimales y un evento a 0,996 km llega como 1,0. El rango y la mediana se leen de sus marts.
- rango:   {inferior_bbl, superior_bbl, eventos_inferior, eventos_superior} de
           mart_diferido_rango, sin redondear.
- mediana_24: {bbl, ic_bajo, ic_alto, eventos} de mart_diferido_operador para TODAS.
- caso:    indice en eventos del caso por defecto, elegido por una regla fija.
- supuestos: {precio, tasa, meses} los tres supuestos de la regla.
"""
from __future__ import annotations

import base64
import json
import sys
from array import array
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import duckdb

from pipeline import mundo, replay, sistema
from pipeline.ingest import DATA, ROOT

# La pagina de la espera: el caso sobre el terreno y la regla de plata.
TEMPLATE = Path(__file__).parent / "espera_template.html"
OUT = ROOT / "site" / "espera.html"
MAX_BYTES = 6 * 1024 * 1024

# La banda de la brecha: el lienzo va de 160 por 100 unidades, los meses de -3 a 12 y la banda se pega
# al borde de arriba (la linea del control). Un punto de brecha son 0,85 unidades de alto y la banda
# no pasa de 60 unidades.
MES_BANDA_MIN = -3
MES_BANDA_MAX = 12
BANDA_UNIDADES = 0.85
BANDA_MAX = 60

# Supuestos de la regla de plata, cada uno como (minimo, maximo, valor por defecto, paso).
PRECIO = (30, 100, 60, 5)  # USD por barril
TASA = (0, 20, 10, 1)  # porcentaje anual
MESES = (6, 24, 12, 1)  # meses de espera
VENTANA_CASO = 24  # meses de ventana que el caso por defecto necesita estar completos


def _en_rango(valor: float, rango: tuple, nombre: str) -> None:
    lo, hi, _, _ = rango
    if not lo <= valor <= hi:
        raise ValueError(f"{nombre} fuera de rango: {valor} (permitido {lo} a {hi})")


def numero_es(valor: float, decimales: int = 0) -> str:
    """Numero en formato argentino: punto para los miles y coma para los decimales."""
    return f"{valor:,.{decimales}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def dinero(bbl: float, precio: float, tasa_pct: float, meses: float) -> float:
    """Costo de recibir los barriles bbl mas tarde, en USD. No es su valor.

    A tasa cero el costo es cero: la espera no tiene precio cuando no hay descuento.
    """
    if bbl < 0:
        raise ValueError(f"bbl no puede ser negativo: {bbl}")
    _en_rango(precio, PRECIO, "precio")
    _en_rango(tasa_pct, TASA, "tasa")
    _en_rango(meses, MESES, "meses")
    return bbl * precio * (1 - (1 + tasa_pct / 100) ** (-meses / 12))


def _millones_redondeados(valor: float) -> int:
    """Millones de USD redondeados a entero, con redondeo a la mitad hacia arriba."""
    return int(Decimal(repr(valor / 1e6)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def frase(lo_bbl: float, hi_bbl: float, precio: float, tasa_pct: float, meses: float) -> str:
    """La frase de la regla de plata: una sola oracion en Castellano."""
    a = _millones_redondeados(dinero(lo_bbl, precio, tasa_pct, meses))
    b = _millones_redondeados(dinero(hi_bbl, precio, tasa_pct, meses))
    return (f"Con USD {numero_es(precio)} por barril, {numero_es(tasa_pct)}% anual y "
            f"{numero_es(meses)} meses de espera, esperar costó entre USD {numero_es(a)} y "
            f"{numero_es(b)} millones. El extremo alto es un máximo; es un supuesto, no una medición.")


def mes_indice(mes: str) -> int:
    """Indice lineal de un mes "AAAA-MM" (para comparar meses sin depender del calendario)."""
    ano, mes = mes.split("-")[:2]
    return int(ano) * 12 + int(mes) - 1


def ventana_ok(mes_evento: str, mes_datos: str, ventana: int = VENTANA_CASO) -> bool:
    """True cuando la ventana de `ventana` meses del evento esta completa en los datos."""
    return mes_indice(mes_evento) + ventana <= mes_indice(mes_datos)


def elegir_caso(eventos: list, mes_datos: str) -> int:
    """Indice del caso por defecto dentro de `eventos`, o -1 si no hay caso.

    Regla fija de antemano: cuentan los eventos de interferencia cercanos (menos de
    1 km; el km llega redondeado, por eso se acepta 1,0) con diferido medido cuya ventana de VENTANA_CASO meses esta completa en los
    datos. Entre ellos se toma la mediana del diferido (con cantidad par, la mediana
    inferior), ordenando por (bbl, fecha, padre). El indice devuelto es el del evento
    dentro de la lista original.
    """
    candidatos = []
    for i, ev in enumerate(eventos):
        if ev.get("t") != "interf" or ev.get("km") is None or ev["km"] > 1:
            continue
        if "bbl" not in ev:
            continue
        if not ventana_ok(ev["f"][:7], mes_datos):
            continue
        candidatos.append(i)
    if not candidatos:
        return -1
    ordenados = sorted(candidatos, key=lambda i: (eventos[i]["bbl"], eventos[i]["f"], eventos[i]["p"]))
    return ordenados[(len(ordenados) - 1) // 2]


def _recortar(matriz_b64: str, filas: list, nm: int, typecode: str) -> str:
    """Recorta las filas pedidas de una matriz base64 y la vuelve a codificar."""
    a = array(typecode)
    a.frombytes(base64.b64decode(matriz_b64, validate=True))
    if sys.byteorder == "big" and a.itemsize > 1:
        a.byteswap()
    out = array(typecode, bytes(a.itemsize * len(filas) * nm))
    for i, f in enumerate(filas):
        out[i * nm:(i + 1) * nm] = a[f * nm:(f + 1) * nm]
    return replay.b64(out)


def collect(con) -> dict:
    """Arma el diccionario de la pagina de espera (sin escribirla)."""
    datos = replay.collect(con)
    meta = dict(datos["meta"])
    meses = meta["meses"]
    nm = len(meses)

    eventos = [ev for ev in datos["eventos"]
               if ev.get("t") == "interf" and "bbl" in ev]
    wells = sorted({ev["p"] for ev in eventos} | {ev["h"] for ev in eventos})
    nuevo = {w: i for i, w in enumerate(wells)}
    pozos = [datos["pozos"][w] for w in wells]
    evs = []
    for ev in eventos:
        e = dict(ev)
        e["p"] = nuevo[ev["p"]]
        e["h"] = nuevo[ev["h"]]
        evs.append(e)
    meta["n_pozos"] = len(pozos)

    rango = {}
    for variante, clave in (("neto_previa", "inferior"), ("original", "superior")):
        fila = replay.q(con, f"select diferido_bbl, eventos from mart_diferido_rango where variante = '{variante}'")
        if not fila:
            raise SystemExit(f"falta la variante {variante} en mart_diferido_rango: correr pipeline.diferido")
        rango[f"{clave}_bbl"] = float(fila[0][0])
        rango[f"eventos_{clave}"] = int(fila[0][1])

    fila = replay.q(con, "select mediana_bbl, mediana_ic_bajo, mediana_ic_alto, eventos "
                         "from mart_diferido_operador where operador = 'TODAS'")
    if not fila:
        raise SystemExit("falta la fila TODAS en mart_diferido_operador: correr pipeline.diferido")
    mediana_24 = {"bbl": float(fila[0][0]), "ic_bajo": float(fila[0][1]),
                      "ic_alto": float(fila[0][2]), "eventos": int(fila[0][3])}

    filas = replay.q(con, "select km_desde, km_hasta, brecha from mart_descomposicion_distancia "
                          "where control = '5 a 10 km' and base = '-6 a -4' "
                          "and banda in ('0 a 1', '1 a 2', '2 a 5') order by km_desde")
    if len(filas) != 3:
        raise SystemExit("faltan las bandas de distancia en mart_descomposicion_distancia: correr pipeline.descomposicion")
    distancia = [{"km_desde": float(a), "km_hasta": float(b), "brecha": float(c)} for a, b, c in filas]

    return {"meta": meta, "pozos": pozos, "distancia": distancia,
            "caudal": _recortar(datos["caudal"], wells, nm, "H"),
            "agua": _recortar(datos["agua"], wells, nm, "B"),
            "eventos": evs, "curva": datos["curva"], "corte": datos["corte"], "base": datos["base"],
            "rango": rango, "mediana_24": mediana_24,
            "caso": elegir_caso(evs, meta["mes_datos"]),
            "supuestos": {"precio": PRECIO, "tasa": TASA, "meses": MESES},
            "foto": mundo.leer_base_foto()}


def banda_svg(curva) -> str:
    """La banda de la brecha entre el vecino y el control, en svg y en su estado final.

    Sin JavaScript la pagina tiene que mostrar la banda ya crecida, asi que el svg entra en el html
    generado. El borde de arriba es el control, siempre en 0; el borde de abajo es el vecino: la
    profundidad es la brecha en puntos por 0,85 unidades, nunca mas de 60. El ancho va de 160
    unidades para los meses de -3 a 12, los mismos de la chispa del vecino.
    """
    cerc, ctrl = {}, {}
    for punto in curva or []:
        k = int(punto["k"])
        if punto.get("banda") == "cercano":
            cerc[k] = float(punto["indice"]) * 100
        else:
            ctrl[k] = float(punto["indice"]) * 100
    # solo los meses con las dos curvas y dentro del ancho: un mes sin control no es una brecha de 100 puntos
    ks = sorted(k for k in set(cerc) & set(ctrl) if MES_BANDA_MIN <= k <= MES_BANDA_MAX)
    if not ks:
        return ""
    ancho = MES_BANDA_MAX - MES_BANDA_MIN

    def x(k: float) -> float:
        return (k - MES_BANDA_MIN) / ancho * 160

    camino = f"M {x(ks[0]):.2f},0"
    for k in ks:
        brecha = (ctrl[k] - cerc[k]) * BANDA_UNIDADES
        camino += f" L {x(k):.2f},{max(0.0, min(BANDA_MAX, brecha)):.2f}"
    camino += f" L {x(ks[-1]):.2f},0 Z"
    return (
        '<svg viewBox="0 0 160 100" preserveAspectRatio="none" class="banda" role="img" '
        'aria-label="brecha entre los pozos vecinos y el control, mes a mes">'
        f'<path d="{camino}" fill="var(--lutita)" stroke="var(--orilla)" stroke-width="1.5" '
        'vector-effect="non-scaling-stroke"></path></svg>'
    )


def render(data: dict, out: Path) -> int:
    """Escribe la pagina con los datos dentro y devuelve su tamano en bytes."""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\u0021--")
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", payload)
    html = html.replace("/*__SISTEMA__*/", sistema.sistema_css())
    html = html.replace("<!--__BANDA__-->", banda_svg(data.get("curva")))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    size = out.stat().st_size
    if size > MAX_BYTES:
        raise SystemExit(f"{out} is {size} bytes, over the {MAX_BYTES} byte budget")
    return size


def main() -> int:
    """Escribe site/espera.html y resume en consola el caso por defecto."""
    con = duckdb.connect(str(DATA / "warehouse.duckdb"), read_only=True)
    try:
        d = collect(con)
    finally:
        con.close()
    size = render(d, OUT)
    caso = d["eventos"][d["caso"]] if d["caso"] >= 0 else None
    caso_txt = f"{caso['f']} ({caso['bbl']} bbl)" if caso else "sin caso"
    lo = d["rango"].get("inferior_bbl", 0.0) / 1e6
    hi = d["rango"].get("superior_bbl", 0.0) / 1e6
    print(f"wrote {OUT} ({size / 1024 / 1024:.2f} MB)")
    print(f"espera: {len(d['pozos'])} pozos, {len(d['eventos'])} eventos, caso {caso_txt}, "
          f"rango {numero_es(lo, 1)} a {numero_es(hi, 1)} millones de bbl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
