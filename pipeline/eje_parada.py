"""Regla de parada del eje de merma: junta las cuatro patas y dice si el eje se sigue presentando como hallazgo.

Se corre despues de pipeline.potencia, pipeline.eje_controles y pipeline.eje_exposicion:  uv run python -m pipeline.eje_parada

La regla se fijo antes de correr nada (docs/proceso/investigacion-fase3.md, seccion 4; reglas de cada prueba en el encabezado de su
modulo, commit "Fase 5: reglas ... fijadas antes de correr"). El proyecto deja de presentar un eje de interferencia si se cumple
CUALQUIERA de:
  1. la potencia pide mas de 2 veces los eventos actuales para separar 93 de 67,5 grados (pipeline.potencia);
  2. la ventana previa da un eje definido a menos de 30 grados de 93 (pipeline.eje_controles);
  3. el eje de merma no se separa del eje de exposicion de los pads, o la reponderacion lo deja indefinido (pipeline.eje_exposicion);
  4. con bloques espaciales de 5 km el eje de la cuenca deja de estar definido (pipeline.eje_controles).

Este modulo no calcula ninguna prueba nueva: lee los marts de los otros tres y aplica la regla. Si falta algun mart, esa pata queda
"sin correr" y no cuenta como que dispare.
"""
from __future__ import annotations

import duckdb

from pipeline.costo import _escribir
from pipeline.ingest import DATA
from pipeline.placebo import _g

NOMBRE_PATA3 = "Exposición: el eje de merma no se separa del eje de exposición, o la reponderación lo deja indefinido"
COLS = [("pata", "integer"), ("nombre", "varchar"), ("estado", "varchar"), ("dispara", "boolean"), ("detalle", "varchar")]

FRASE = ("La caída de los padres cercanos no es igual en todas las direcciones de superficie en la muestra completa (con "
         "intervalos por pads), pero con datos públicos esa dirección no se separa del SHmax publicado ni de la forma en que se "
         "disponen los pads; la geometría de las ramas se probó con otra prueba (costado contra punta, mecanismo.md). No es un hallazgo "
         "sobre esfuerzos ni sobre la fractura.")


def _existe(con, tabla: str) -> bool:
    return con.execute("select count(*) from information_schema.tables where table_name = ?", [tabla]).fetchone()[0] > 0


def _fila_o_none(con, sql: str):
    try:
        return con.execute(sql).fetchone()
    except duckdb.Error:
        return None


def patas(con) -> list[dict]:
    """Las cuatro patas: estado 'dispara', 'no dispara' o 'sin correr', con un detalle en texto."""
    out = []
    # 1. potencia
    if _existe(con, "mart_potencia_resumen"):
        r = _fila_o_none(con, "select m80, m80_texto, veredicto, n_requerido_analitico, anios_hasta_m80 "
                              "from mart_potencia_resumen where escenario = 'principal'")
        pot = con.execute("select potencia from mart_potencia_eje where escenario = 'principal' and multiplo = 2.0").fetchall() if _existe(con, "mart_potencia_eje") else []
        p2 = sum(x[0] for x in pot) / len(pot) if pot else None
        if r:
            dispara = r[2] == "no separable"
            det = (f"M80 = {r[1]} los eventos actuales (el múltiplo que da 80% de potencia); veredicto de la regla: {r[2]}."
                   + (f" Con el doble de eventos la potencia es de {_g(100 * p2)}%." if p2 is not None else "")
                   + (f" Cuenta analítica: unos {_g(r[3])} eventos." if r[3] is not None else "")
                   + (f" Al ritmo actual, unos {_g(r[4], 1)} años hasta M80." if r[4] is not None else ""))
            out.append({"pata": 1, "nombre": "Potencia: más de 2 veces los eventos actuales", "estado": "dispara" if dispara else "no dispara",
                        "dispara": dispara, "detalle": det})
    if not any(p["pata"] == 1 for p in out):
        out.append({"pata": 1, "nombre": "Potencia: más de 2 veces los eventos actuales", "estado": "sin correr", "dispara": False,
                    "detalle": "falta mart_potencia_resumen"})
    # 2 y 4. controles
    ver, d = {}, {}
    if _existe(con, "mart_eje_controles_veredicto") and _existe(con, "mart_eje_controles"):
        ver = {r[0]: (r[1], r[2]) for r in con.execute("select prueba, veredicto, dispara_regla_parada from mart_eje_controles_veredicto").fetchall()}
        d = {r[0]: r for r in con.execute("select prueba, eje, ic_bajo, ic_alto, ancho_ic, p_perm, dist_93, amplitud from mart_eje_controles").fetchall()}
    for pata, clave, nombre in ((2, "eje_previo_k-1", "Ventana previa: eje definido a menos de 30 grados de 93"),
                                (4, "bloques_5km", "Bloques de 5 km: el eje de la cuenca deja de estar definido")):
        if clave not in ver or clave not in d:
            out.append({"pata": pata, "nombre": nombre, "estado": "sin correr", "dispara": False, "detalle": "falta mart_eje_controles"})
            continue
        v, disp = ver[clave]
        r = d[clave]
        det = (f"{v}: eje {_g(r[1])} grados, IC {_g(r[2])} a {_g(r[3])} (ancho {_g(r[4])}), p de permutación {_g(r[5], 3)}"
               + (f", a {_g(r[6], 1)} grados de 93." if clave == "eje_previo_k-1" else "."))
        if clave == "bloques_5km" and _existe(con, "mart_eje_controles_rotacion"):
            rot = con.execute("select unidades, eventos_en_bloques_de_tamano_unico, p_rotacion from mart_eje_controles_rotacion "
                              "where unidad = 'bloques de 5 km'").fetchone()
            if rot:
                det += (f" Diagnóstico agregado después de ver los resultados: el p de la regla intercambia solo bloques del mismo "
                        f"tamaño y {_g(rot[1])} eventos están en bloques de tamaño único (hay {_g(rot[0])} bloques), que no se mueven; "
                        f"con una permutación que rota los rumbos de cada bloque el p es {_g(rot[2], 3)}. La regla, tal como se fijó, "
                        f"dispara; el diagnóstico dice que esta pata es la menos sólida de las cuatro.")
        out.append({"pata": pata, "nombre": nombre, "estado": "dispara" if disp else "no dispara", "dispara": bool(disp), "detalle": det})
    # 3. exposicion
    filas = con.execute("select condicion, cumple, detalle from mart_eje_exposicion_veredicto").fetchall() if _existe(con, "mart_eje_exposicion_veredicto") else []
    if filas:
        disp = any(bool(f[1]) for f in filas)
        det = " ".join(f"{f[0]}: {'se cumple' if f[1] else 'no se cumple'} ({f[2].rstrip('.')})." for f in filas if f[0] != "veredicto")
        det += " La pieza 3 (modelo de ramas del eje) no se hizo dentro de esta pata y sigue sin hacerse; con las trayectorias publicadas se hizo una prueba distinta (costado contra punta) en mecanismo.md."
        out.append({"pata": 3, "nombre": NOMBRE_PATA3,
                    "estado": "dispara" if disp else "no dispara", "dispara": disp, "detalle": det})
    else:
        out.append({"pata": 3, "nombre": NOMBRE_PATA3,
                    "estado": "sin correr", "dispara": False, "detalle": "falta mart_eje_exposicion_veredicto"})
    return sorted(out, key=lambda p: p["pata"])


def se_cumple(con) -> bool | None:
    """True si alguna pata dispara; None si ninguna pata se corrio (no se puede juzgar)."""
    ps = patas(con)
    if all(p["estado"] == "sin correr" for p in ps):
        return None
    return any(p["dispara"] for p in ps)


def aviso_anisotropia(con) -> list[str]:
    """Aviso al tope de la pagina si la regla de parada del eje (pipeline.eje_parada) se cumplio; vacio si no hay mart o no dispara."""
    existe = con.execute("select count(*) from information_schema.tables where table_name = 'mart_eje_parada'").fetchone()[0]
    if not existe or not con.execute("select count(*) from mart_eje_parada where dispara").fetchone()[0]:
        return []
    return ["> **Regla de parada cumplida** ([eje_parada.md](eje_parada.md)). El eje de abajo es una descripción de la muestra, "
            "no un hallazgo. " + FRASE, ""]


def pagina_eje_parada(con) -> str:
    ps = patas(con)
    cumple = se_cumple(con)
    n_disp = sum(p["dispara"] for p in ps)
    L = ["# Regla de parada del eje de merma", "",
         "Página generada por `pipeline/eje_parada.py`. Junta las cuatro patas de la regla de parada del plan de investigación "
         "(sección 4), fijada antes de correr, y dice si el eje de mayor merma se sigue presentando como hallazgo. No calcula nada "
         "nuevo: lee [la potencia](potencia.md), [los controles](eje_controles.md) y [la exposición](eje_exposicion.md).", "",
         "## Veredicto", ""]
    if cumple:
        L += [f"**La regla de parada se cumple** ({n_disp} de {len(ps)} patas disparan, y alcanza con una). El proyecto deja de "
              "presentar un eje de interferencia. Texto de reemplazo, el único que se usa:", "", f"> {FRASE}", "",
              "El hallazgo `anisotropia` del libro se renombra `asimetria_de_superficie` y queda no firme. El eje se conserva como "
              "descripción de la muestra (el número sigue en [anisotropia.md](anisotropia.md)), no como medición de esfuerzos ni de "
              "mecanismo.", ""]
    elif cumple is None:
        L += ["No se corrió ninguna pata.", ""]
    elif any(p["estado"] == "sin correr" for p in ps):
        L += ["Ninguna pata de las que se corrieron dispara, pero faltan patas por correr: la regla queda incompleta.", ""]
    else:
        L += ["La regla de parada no se cumple: ninguna pata dispara.", ""]
    L += ["## Las cuatro patas", "", "| Pata | Prueba | Estado |", "| ---: | --- | --- |"]
    for p in ps:
        L.append(f"| {p['pata']} | {p['nombre']} | {p['estado']} |")
    L.append("")
    for p in ps:
        L += [f"### Pata {p['pata']}: {p['estado']}", "", p["detalle"], ""]
    if _existe(con, "mart_mecanismo_veredicto"):
        r = con.execute("select * from mart_mecanismo_veredicto").fetchone()
        if r:
            v, c1, ic_b, ic_a, pl, pl_b, pl_a = r[0], r[4], r[5], r[6], r[7], r[8], r[9]
            if v == "sostiene":
                res = (f"Resultado: {v}. Al mes 1 el costado rinde {_g(-100 * c1, 1)} puntos menos que la punta "
                       f"(IC 95% por bloques de 5 km: {_g(100 * ic_b, 1)} a {_g(100 * ic_a, 1)}) y el mismo contraste en el mes -1 es de "
                       f"{_g(100 * pl, 1)} puntos (IC {_g(100 * pl_b, 1)} a {_g(100 * pl_a, 1)}), que incluye cero. Es un resultado nuevo "
                       "y distinto: no revive el eje de la brújula, que sigue retirado, y sigue siendo una huella medida, no una "
                       "medición de esfuerzos.")
            elif v == "ubicación":
                res = ("Resultado: ubicación. La diferencia del mes 1 ya se separaba de cero antes de la fractura: viene de "
                       "dónde están los pozos. Ni con la geometría de las ramas se separa un mecanismo.")
            elif v == "no firme":
                res = ("Resultado: no firme. Ni con la geometría de las ramas se sostiene un mecanismo direccional. El eje de la "
                       "brújula sigue retirado.")
            else:
                res = ("Resultado: sin muestra. No hubo eventos suficientes en el costado y la punta para decidir. El eje de la "
                       "brújula sigue retirado.")
            L += ["## La geometría de las ramas, probada aparte", "",
                  "La pata 3 decía que el modelo de ramas del eje no se podía hacer, y sigue sin hacerse. Con las trayectorias publicadas "
                  "se hizo otra cosa en [mecanismo.md](mecanismo.md), una prueba nueva con su regla fijada antes de correr (no es una repetición del "
                  "eje): el contraste entre el padre al costado de la rama del hijo y el de la punta.", "", res, ""]
    L += ["## Qué no cambia", "",
          "- La brecha del mes 1, su cierre a los 6 meses, la sincronía, la descomposición entre días y caudal por día, la validación "
          "por inyección y la replicación en Colorado no dependen del eje y no se tocan.",
          "- La regla de parada es sobre la dirección. No dice que la caída sea falsa ni que el eje sea cero: dice que con datos "
          "públicos no se puede afirmar que la dirección sea propia de la fractura.",
          "- Lo que haría falta para reabrirla: azimut de rama y coordenadas de fondo (para el modelo de ramas del eje), o unas 2 veces "
          "los eventos actuales con un desarrollo distinto del de Loma Campana. La prueba de costado contra punta de mecanismo.md no "
          "reemplaza ese modelo.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    ps = patas(con)
    _escribir(con, "mart_eje_parada", COLS, [(p["pata"], p["nombre"], p["estado"], p["dispara"], p["detalle"]) for p in ps])
    for p in ps:
        print(f"[eje_parada] pata {p['pata']}: {p['estado']:<10} {p['nombre']}")
    c = se_cumple(con)
    print(f"[eje_parada] regla de parada: {'se cumple' if c else ('sin correr' if c is None else 'no se cumple')}")
    con.close()


if __name__ == "__main__":
    main()
