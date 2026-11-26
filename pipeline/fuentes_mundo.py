"""Auditoria de fuentes del mundo: que publica cada regulador, verificado bajando la fuente el 2026-11-19.

    uv run python -m pipeline.fuentes_mundo      # data/fuentes_mundo.json -> wiki/hallazgos/fuentes_mundo.md

El archivo `data/fuentes_mundo.json` es una lista de registros, uno por jurisdiccion, con los campos de CAMPOS. Cada dato sale
de un pedido hecho ese dia (la lista de pedidos va en el registro). Esta pagina no calcula ninguna brecha ni rendimiento.

REGLA DE ELEGIBILIDAD (fijada antes de mirar ninguna fuente). Una fuente entra al estudio solo si cumple las cuatro:
  1. descarga directa o API documentada, sin login ni pago;
  2. terminos que no impiden descargar y publicar cifras derivadas con atribucion: una licencia que lo permite ("si") o una
     descarga que el regulador ofrece sin ninguna restriccion de uso ("sin_restriccion"). Una prohibicion expresa de reproducir o
     redistribuir, o una pagina de terminos que no se pudo leer, la deja afuera ("no" o "no_claro");
  3. petroleo reportado por pozo y por mes (no por lease, campo, instalacion ni empresa);
  4. una fecha de fractura o terminacion por pozo, del regulador o de un registro publico que une por el id del pozo.
Una condicion que falla o que no se pudo verificar deja la fuente afuera, y el motivo queda escrito.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FUENTES = ROOT / "data" / "fuentes_mundo.json"
PAGINA = ROOT / "wiki" / "hallazgos" / "fuentes_mundo.md"

CAMPOS = ("id", "pais", "jurisdiccion", "organismo", "cuenca_o_formacion_principal", "nivel", "que_publica", "url_datos",
          "formato", "tamano_bytes", "campos", "unidades_petroleo", "anios_cubiertos", "muestra", "acceso", "url_terminos",
          "terminos_cita", "permiten_derivadas", "fecha_verificada", "pedidos_hechos", "entra_al_estudio", "motivo", "notas")

# Orden de lectura de la tabla: de lo mas medible a lo menos.
NIVELES = {
    "por_pozo_con_fractura": "por pozo, con fecha de fractura o terminacion",
    "por_pozo_sin_fractura": "por pozo, sin esa fecha",
    "por_lease_o_campo": "por lease, campo o instalacion",
    "solo_totales": "solo totales",
    "nada_publico": "nada publico o de pago",
    "registro_de_fractura": "registro de fracturas, sin petroleo",
    "no_verificado": "no se pudo verificar",
}


def cargar(path: Path = FUENTES) -> list[dict]:
    regs = json.loads(path.read_text(encoding="utf-8"))
    ids = [r.get("id") for r in regs]
    if len(set(ids)) != len(ids):
        raise SystemExit("fuentes_mundo: ids repetidos")
    for r in regs:
        falta = [k for k in CAMPOS if k not in r]
        if falta:
            raise SystemExit(f"fuentes_mundo: {r.get('id')} sin los campos {falta}")
        if r["nivel"] not in NIVELES:
            raise SystemExit(f"fuentes_mundo: {r['id']} con nivel desconocido {r['nivel']!r}")
        if r["entra_al_estudio"] and r["nivel"] != "por_pozo_con_fractura":
            raise SystemExit(f"fuentes_mundo: {r['id']} entra sin ser por pozo con fractura")
    return sorted(regs, key=lambda r: (not r["entra_al_estudio"], list(NIVELES).index(r["nivel"]), r["pais"], r["jurisdiccion"]))


def recuentos(regs: list[dict]) -> dict:
    por = Counter(r["nivel"] for r in regs)
    return {"total": len(regs), "entran": sum(1 for r in regs if r["entra_al_estudio"]),
            "por_pozo_con_fractura": por["por_pozo_con_fractura"], "por_pozo_sin_fractura": por["por_pozo_sin_fractura"],
            "por_lease_o_campo": por["por_lease_o_campo"], "solo_totales": por["solo_totales"],
            "nada_publico": por["nada_publico"], "registro_de_fractura": por["registro_de_fractura"],
            "no_verificado": por["no_verificado"]}


def _celda(s) -> str:
    return str(s).replace("|", "/").replace("\n", " ")


def _v(x) -> str:
    return "no se pudo verificar" if x is None else str(x)


def pagina(regs: list[dict]) -> str:
    n = recuentos(regs)
    L = [
        "# Fuentes del mundo: quien publica petroleo por pozo",
        "",
        "Auditoria hecha el 2026-11-19 bajando cada fuente (encabezado y unas filas, nunca una bajada masiva) y leyendo sus terminos. "
        "Los datos de cada fila salen de pedidos reales que se listan en `data/fuentes_mundo.json`; lo que no se pudo ver figura como "
        "\"no se pudo verificar\", no como \"no publica\".",
        "",
        "## Regla de elegibilidad (fijada antes de mirar las fuentes)",
        "",
        "Una fuente entra al estudio de otra cuenca solo si cumple las cuatro condiciones:",
        "",
        "1. descarga directa o API documentada, sin login ni pago;",
        "2. terminos que no impiden descargar y publicar cifras derivadas con atribucion: una licencia que lo permite, o una descarga "
        "que el regulador ofrece sin ninguna restriccion de uso. Una prohibicion expresa de reproducir o redistribuir, o una pagina de "
        "terminos que no se pudo leer, la deja afuera;",
        "3. petroleo reportado por pozo y por mes (no por lease, campo, instalacion ni empresa);",
        "4. una fecha de fractura o terminacion por pozo, del regulador o de un registro publico que une por el id del pozo "
        "(se verifica con dos pozos reales que el id coincide).",
        "",
        "Una condicion que falla, o que no se pudo verificar, deja la fuente afuera.",
        "",
        "## Resultado",
        "",
        f"Se auditaron {n['total']} jurisdicciones. {n['entran']} entran al estudio. Por nivel: {n['por_pozo_con_fractura']} publican "
        f"produccion por pozo con fecha de fractura o terminacion, {n['por_pozo_sin_fractura']} por pozo sin esa fecha, {n['por_lease_o_campo']} por lease, "
        f"campo o instalacion, {n['solo_totales']} solo totales, {n['nada_publico']} nada publico o de pago, {n['registro_de_fractura']} es un registro de "
        f"fracturas sin petroleo y {n['no_verificado']} no se pudieron verificar.",
        "",
        "| Jurisdiccion | Organismo | Nivel | Entra | Motivo |",
        "|---|---|---|---|---|",
    ]
    for r in regs:
        L.append(f"| {_celda(r['pais'])}, {_celda(r['jurisdiccion'])} | {_celda(r['organismo'])} | {NIVELES[r['nivel']]} | "
                 f"{'si' if r['entra_al_estudio'] else 'no'} | {_celda(r['motivo'])} |")
    L += ["", "## Detalle por fuente", ""]
    for r in regs:
        c = r["campos"] or {}
        L += [f"### {r['pais']}, {r['jurisdiccion']}", "",
              f"- Que publica: {r['que_publica']}",
              f"- Acceso: {r['acceso']}. Archivo o API: {r['url_datos']} ({r['formato']}" + (f", {r['tamano_bytes']:,} bytes".replace(",", ".") if r["tamano_bytes"] else "") + ").",
              f"- Id del pozo: {_v(c.get('id_pozo'))}. Ubicacion: {_v(c.get('ubicacion'))}.",
              f"- Petroleo mensual por pozo: {_v(c.get('petroleo_mensual_por_pozo'))} (unidad: {_v(r['unidades_petroleo'])}). Anios: {_v(r['anios_cubiertos'])}.",
              f"- Fecha de fractura o terminacion: {_v(c.get('fecha_fractura_o_terminacion'))}.",
              f"- Terminos ({r['url_terminos']}): {r['terminos_cita']} Permiten derivadas con atribucion: {r['permiten_derivadas']}.",
              f"- Notas: {r['notas']}", ""]
    L += [
        "## Que NO es",
        "",
        "- No es una medicion de nada: ninguna cifra de esta pagina es una brecha, un rendimiento ni una afirmacion causal.",
        "- \"No entra\" no dice que la jurisdiccion no produzca ni que no publique nada: dice que esta auditoria no encontro, "
        "verificando hoy, las cuatro condiciones juntas. Una fuente marcada \"no se pudo verificar\" quedo sin leer, y su estado puede cambiar.",
        "- Un permiso no claro cuenta como no permitido hasta que el regulador lo aclare; no se rodea ningun login, pago ni termino de uso. "
        "\"Sin restriccion\" quiere decir que la pagina no prohibe usar ni publicar cifras derivadas de los archivos que ofrece; no es una licencia.",
        "- La auditoria lee encabezados y unas filas. Que una fuente entre no garantiza que sus datos alcancen para medir: eso lo dice el estudio de cada cuenca.",
        "",
    ]
    return "\n".join(L)


def main(path: Path = FUENTES, salida: Path = PAGINA) -> str:
    texto = pagina(cargar(path))
    salida.write_text(texto, encoding="utf-8")
    return texto


if __name__ == "__main__":
    main()
