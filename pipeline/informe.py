"""Informe para un operador (site/informe.html): una página con gráficos, armada desde los marts.

Los datos, los gráficos y el código van dentro del archivo. No pide nada a la red: las dos tipografías del sistema
Horizonte (pipeline.sistema) son archivos propios de site/fuentes.

  uv run python -m pipeline.informe                       # data/warehouse.duckdb -> site/informe.html
  uv run python -m pipeline.informe --fragmento OUT.html  # misma página sin doctype/head (para publicarla aparte)

No estima nada nuevo: lee marts ya publicados (curva del estudio de eventos, brechas por distancia y por edad,
sacar de a un operador o área, cierre a 6 meses, diferido y cota de pérdida, potencia del nulo de dosis) y los
dibuja. Las cifras del texto se formatean acá, en Python, y pipeline.claims las verifica contra el warehouse.
La calculadora de valor usa la misma fórmula que pipeline.decision.valor_indicativo; el precio y la tasa los pone
quien la usa.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from pipeline.decision import valor_indicativo
from pipeline.diferido import BBL_M3
from pipeline.ingest import DATA, ROOT, SOURCES, load_manifest
from pipeline.sistema import sistema_css
from pipeline.wiki import num

TEMPLATE = Path(__file__).parent / "informe_template.html"
SALIDA = ROOT / "site" / "informe.html"
FIN_HEAD = "<!--FIN_HEAD-->\n"
COMPLETA = "(muestra completa)"
CINCO_PUNTOS = 0.05
EDADES = (("06-11", "6 a 11 meses"), ("12-23", "12 a 23 meses"), ("24-47", "24 a 47 meses"), ("48+", "48 meses o más"))
# valores de arranque de la calculadora: entradas de ejemplo, no pronóstico ni precio observado (los padres por
# hijo arrancan en la mediana de la cuenca)
PRECIO_EJEMPLO = 60.0
TASA_EJEMPLO = 0.10
REZAGO_EJEMPLO = 12


def _filas(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _r(x: float | None, d: int = 6) -> float | None:
    return None if x is None else round(float(x), d)


def fecha_verificada(manifest: dict | None) -> str | None:
    """Día (UTC) hasta el que la copia local de las fuentes está verificada contra el servidor.

    Cada fuente guarda cuándo se bajó (loaded_at) y cuándo se comprobó por última vez que seguía igual (checked_at).
    Vale la más vieja de las fuentes, porque la página usa todas. None si falta alguna: ahí la página no dice fecha."""
    dias = [((manifest or {}).get(f) or {}).get("checked_at") or ((manifest or {}).get(f) or {}).get("loaded_at")
            for f in SOURCES]
    return min(str(x)[:10] for x in dias) if all(dias) else None


def datos(con, manifest: dict | None = None) -> dict:
    """Todo lo que la página dibuja, leído de los marts. Brechas en fracción (x100 = puntos)."""
    curva: dict[str, dict[int, float]] = {}
    for f in _filas(con, "select banda, k, indice_mediana from mart_interferencia_curva order by banda, k"):
        curva.setdefault(f["banda"], {})[int(f["k"])] = _r(f["indice_mediana"])
    edad = {f["grupo_edad"]: f for f in _filas(con, "select * from mart_decision_edad")}
    rob = _filas(con, "select eje, salida, k, n_cercanos, brecha, ic_bajo, ic_alto from mart_robustez_operador "
                      "order by eje, k, n_cercanos")
    perd = _filas(con, "select * from mart_decision_perdida")[0]
    mde = con.execute("select max(mde80_holm_desvios) from mart_potencia_dosis "
                      "where resultado = 'A' and modelo = 'conjunto'").fetchone()[0]
    mes = con.execute("select max(mes) from mart_vm_mensual").fetchone()[0]
    distintos = con.execute("select count(distinct padre) from mart_interferencia_diferida").fetchone()[0]
    padres = con.execute("select median(n) from (select count(*) n from mart_interferencia_diferida "
                         "group by hijo_cercano, mes_frac)").fetchone()[0]
    # intervalo de la brecha del mes 1 con bloques espaciales de 5 km (pipeline.bloques): el más ancho de los publicados
    ic1 = _filas(con, "select estimacion, ic_bajo_5km, ic_alto_5km from mart_bloques "
                      "where metrica = 'brecha_mes1_base_original' and k = 1")[0]
    todos = edad["todos"]
    if abs(ic1["estimacion"] - todos["brecha_mes1"]) > 1e-9:
        raise ValueError("mart_bloques y mart_decision_edad no dan la misma brecha del mes 1: el intervalo sería de otra cifra")
    return {
        "mes_dato": f"{mes.year:04d}-{mes.month:02d}",
        "verificado": fecha_verificada(manifest),
        "curva": {b: [[k, v] for k, v in sorted(curva[b].items())] for b in ("cercano", "intermedio", "control")},
        "todos": {"eventos": int(todos["eventos"]), "pads_hijo": int(todos["pads_hijo"]),
                  "brecha1": _r(todos["brecha_mes1"]), "brecha6": _r(todos["brecha_mes6"]),
                  "ic1_bajo": _r(ic1["ic_bajo_5km"]), "ic1_alto": _r(ic1["ic_alto_5km"]),
                  "dif_m3": _r(todos["diferido_medio_m3"], 1), "dif_bajo_m3": _r(todos["diferido_ic_bajo_m3"], 1),
                  "dif_alto_m3": _r(todos["diferido_ic_alto_m3"], 1)},
        "edad": [{"grupo": g, "etiqueta": e, "eventos": int(edad[g]["eventos"]),
                  "brecha1": _r(edad[g]["brecha_mes1"]), "brecha6": _r(edad[g]["brecha_mes6"])} for g, e in EDADES],
        "distancia": [{"banda": f["banda"], "n": int(f["n_banda"]), "brecha": _r(f["brecha_mes1"]),
                       "ic_bajo": _r(f["ic_bajo"]), "ic_alto": _r(f["ic_alto"]), "cercana": i < 3}
                      for i, f in enumerate(_filas(con, "select * from mart_decision_distancia order by orden"))],
        "cierre": [{"variante": f["variante"], "control": f["descripcion"], "brecha1": _r(f["brecha_mes1"]),
                    "brecha6": _r(f["brecha_mes6"]), "parte": _r(f["parte_recuperada"])}
                   for f in _filas(con, "select * from mart_decision_cierre order by variante")],
        "robustez": [{"eje": f["eje"], "salida": f["salida"], "k": int(f["k"]), "n": int(f["n_cercanos"]),
                      "brecha": _r(f["brecha"]), "ic_bajo": _r(f["ic_bajo"]), "ic_alto": _r(f["ic_alto"])}
                     for f in rob],
        "cota_m3": _r(perd["cota_m3"], 1), "cota_bbl": _r(perd["cota_bbl"], 1),
        "media24_bbl": _r(perd["media_24m_bbl"], 1), "media24_bajo_bbl": _r(perd["media_ic_bajo_bbl"], 1),
        "media24_alto_bbl": _r(perd["media_ic_alto_bbl"], 1),
        "mde": _r(mde, 3),
        "padres_mediana": int(round(padres)),
        "padres_distintos": int(distintos),
        "bbl_m3": BBL_M3,
        "ejemplo": {"precio": PRECIO_EJEMPLO, "tasa": TASA_EJEMPLO, "rezago": REZAGO_EJEMPLO,
                    "padres": int(round(padres))},
    }


def _pts(x: float) -> str:
    """Fracción a puntos con signo y coma: -0.229 -> '-22,9'."""
    return num(100 * x, 1)


def _salidas(d: dict, eje: str, k: int) -> list[dict]:
    return [f for f in d["robustez"] if f["eje"] == eje and f["k"] == k and f["salida"] != COMPLETA]


def textos(d: dict) -> dict[str, str]:
    """Cifras del texto, ya formateadas en español."""
    t = d["todos"]
    op1, ar1 = _salidas(d, "operador", 1), _salidas(d, "area", 1)
    op6, ar6 = _salidas(d, "operador", 6), _salidas(d, "area", 6)
    seis = op6 + ar6
    ej = d["ejemplo"]
    v = valor_indicativo(t["dif_m3"], ej["precio"], ej["tasa"], ej["rezago"])
    cota_valor = valor_indicativo(d["cota_m3"], ej["precio"], ej["tasa"], ej["rezago"])["valor_cota_perdida"]
    edades1 = [e["brecha1"] for e in d["edad"]]
    cierres6 = [c["brecha6"] for c in d["cierre"]]
    cerca = [f["brecha"] for f in d["distancia"] if f["cercana"]]
    lejos = {f["banda"]: f["brecha"] for f in d["distancia"] if not f["cercana"]}
    fuera = [e for e in d["edad"] if abs(e["brecha6"]) > CINCO_PUNTOS]
    if len(fuera) == 1:
        frase_viejos = (f"Con {fuera[0]['etiqueta']} el mes 6 queda en {_pts(fuera[0]['brecha6'])} puntos: es el único "
                        "grupo de edad fuera de los 5 puntos del control.")
    elif fuera:
        frase_viejos = (f"{len(fuera)} grupos de edad quedan en el mes 6 fuera de los 5 puntos del control: "
                        + ", ".join(f"{e['etiqueta']} ({_pts(e['brecha6'])})" for e in fuera) + ".")
    else:
        frase_viejos = "En el mes 6 todos los grupos de edad quedan dentro de los 5 puntos del control."
    return {
        "mes_dato": d["mes_dato"],
        "frase_verificado": f" (copia verificada contra la fuente el {d['verificado']})" if d.get("verificado") else "",
        "dist_cerca_min": _pts(max(cerca)),
        "dist_cerca_max": _pts(min(cerca)),
        "dist_12": _pts(lejos["1 a 2"]),
        "dist_25": _pts(lejos["2 a 5"]),
        "frase_viejos": frase_viejos,
        "padres_mediana": num(d["padres_mediana"]),
        "padres_distintos": num(d["padres_distintos"]),
        "gap1": _pts(t["brecha1"]),
        "gap1_ic_bajo": _pts(t["ic1_bajo"]),
        "gap1_ic_alto": _pts(t["ic1_alto"]),
        "gap6": _pts(t["brecha6"]),
        "eventos": num(t["eventos"]),
        "pads_hijo": num(t["pads_hijo"]),
        "dif_m3": num(t["dif_m3"]),
        "dif_bajo_m3": num(t["dif_bajo_m3"]),
        "dif_alto_m3": num(t["dif_alto_m3"]),
        "dif_bbl": num(t["dif_m3"] * BBL_M3),
        "cota_bbl": num(d["cota_bbl"]),
        "cota_m3": num(d["cota_m3"]),
        "media24_bbl": num(d["media24_bbl"]),
        "media24_bajo_bbl": num(d["media24_bajo_bbl"]),
        "media24_alto_bbl": num(d["media24_alto_bbl"]),
        "edad_menos": _pts(max(edades1)),
        "edad_mas": _pts(min(edades1)),
        "cierre_peor": _pts(min(cierres6)),
        "op_n": num(len(op1)),
        "ar_n": num(len(ar1)),
        "op_min": _pts(max(f["brecha"] for f in op1)),
        "op_max": _pts(min(f["brecha"] for f in op1)),
        "ar_min": _pts(max(f["brecha"] for f in ar1)),
        "ar_max": _pts(min(f["brecha"] for f in ar1)),
        "ic_alto_max": _pts(max(f["ic_alto"] for f in op1 + ar1)),
        "seis_min": _pts(max(f["brecha"] for f in seis)),
        "seis_max": _pts(min(f["brecha"] for f in seis)),
        "mde": num(d["mde"], 2),
        "ej_precio": num(ej["precio"]),
        "ej_tasa": num(100 * ej["tasa"]),
        "ej_rezago": num(ej["rezago"]),
        "ej_padres": num(ej["padres"]),
        "ej_costo": num(ej["padres"] * v["costo_de_diferir"]),
        "ej_cota": num(ej["padres"] * cota_valor),
    }


def render(d: dict, documento: bool = True) -> str:
    """Rellena la plantilla. documento=False deja la página sin doctype ni head (para un visor que la envuelve)."""
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__SISTEMA__*/", sistema_css())
    for clave, valor in textos(d).items():
        html = html.replace("{{" + clave + "}}", valor)
    html = html.replace("/*__DATOS__*/null", json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    if "{{" in html or "__DATOS__" in html:
        raise ValueError("quedó un marcador sin reemplazar en la plantilla del informe")
    cabeza, cuerpo = html.split(FIN_HEAD)
    if not documento:
        return cabeza + cuerpo
    return ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + cabeza + '</head>\n<body>' + cuerpo + '</body>\n</html>\n')


def main(path=DATA / "warehouse.duckdb", out: Path = SALIDA, fragmento: Path | None = None) -> None:
    con = duckdb.connect(str(path), read_only=True)
    d = datos(con, load_manifest())
    con.close()
    Path(out).write_text(render(d), encoding="utf-8")
    print(f"[informe] {out}")
    if fragmento:
        Path(fragmento).write_text(render(d, documento=False), encoding="utf-8")
        print(f"[informe] fragmento {fragmento}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(DATA / "warehouse.duckdb"))
    ap.add_argument("--out", default=str(SALIDA))
    ap.add_argument("--fragmento", default=None)
    a = ap.parse_args()
    main(a.db, Path(a.out), Path(a.fragmento) if a.fragmento else None)
