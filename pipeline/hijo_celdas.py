"""El lado del hijo dentro de celdas de 2 km: comparar hijos del mismo lugar fracturados antes y despues de que sus vecinos produjeran.

Se corre despues de pipeline.hijo:  uv run python -m pipeline.hijo_celdas

REGLA FIJADA ANTES DE CORRER (2026-11-17). Este diseno se escribio DESPUES de ver el resultado de pipeline.hijo (veredicto "no
firme": el grupo muy depletado da -0,2 bbl por metro con IC de -12,8 a 12,4, y el control negativo da 8,9 con IC de 2,1 a 15,7, no
nulo). Responde a ese control negativo y no cambia el veredicto registrado de `hijo_depletado`. Antes de fijar esta regla no se
calculo ninguna cifra de resultado con este diseno (ni coeficientes, ni equilibrio, ni conteos de celdas).

Pregunta: entre hijos de un mismo cuadrado de 2 km de lado, del mismo ano de primer petroleo y de igual diseno y densidad final de
pozos alrededor, el que se fracturo cuando sus vecinos ya habian producido mucho rinde menos petroleo por metro a 12 meses que el que
se fracturo en zona virgen?

Por que: en pipeline.hijo el control negativo no es nulo. Los hijos con mas pozos POSTERIORES alrededor rinden mas, o sea que el
desarrollo denso sigue a la roca buena, y las celdas de area por cohorte (areas de decenas de km) no alcanzan para sacar la ubicacion.
Aca la ubicacion se absorbe con un cuadrado de 2 km y la densidad final (pozos alrededor en cualquier fecha) entra como control: lo
que queda para comparar es CUANDO se fracturo cada hijo dentro del desarrollo de su lugar.

Muestra, exposicion, grupos y resultado: los de pipeline.hijo, sin cambios (hijo.cargar, hijo.pares, hijo.exposicion_real,
hijo.exposicion_control, hijo.cortes y hijo.grupos sobre la muestra completa). Grupo 1 virgen, 2 poco depletado, 3 muy depletado;
resultado: petroleo de 12 meses por metro de rama.

Celda espacial: cuadrado de LADO_KM = 2 km en una grilla fija. x = 111,32 * cos(LAT_REF) * longitud, y = 111,32 * latitud, con
LAT_REF = -38,5 grados; celda = (piso(x / 2), piso(y / 2)).

Densidad final: numero de pozos de int_pozo_mop (los expositores de pipeline.hijo) a menos de 1 km de superficie del hijo, distintos
del hijo, sin mirar fechas.

Modelo principal: minimos cuadrados con efectos fijos de celda (absorbidos centrando), indicadores del ano de primer petroleo
(cohorte), controles rama horizontal, arena por metro, etapas, operador (los mismos de hijo.controles) y densidad final; indicadores
de los grupos 2 y 3 con el grupo 1 de referencia. Errores robustos agrupados por CELDA (CR1, normal, IC 95%), no por pad: los pads de
una celda comparten roca. Coeficiente primario: el del grupo 3 contra el 1, en bbl por metro y en porcentaje de la mediana del
rendimiento del grupo 1 en la muestra del modelo.

Control negativo: la exposicion de control de pipeline.hijo (pozos que empiezan a producir despues de la ventana de 12 meses del
hijo), sus grupos, y el mismo modelo con las mismas celdas y controles. Es NULO si el IC 95% del coeficiente de su grupo 3 incluye cero.

Minimos (si no se cumplen: "sin muestra", sin veredicto): los de pipeline.hijo (50 hijos y 20 pads en el grupo 1 y en el grupo 3,
100 pads en la muestra) y ademas MIN_CELDAS_INFORMATIVAS = 30 celdas con al menos un hijo del grupo 1 y uno del grupo 3 de la
exposicion real.

VEREDICTO: la misma regla de pipeline.hijo (hijo.veredicto), aplicada al modelo principal y al control negativo de aca:
  * no se sostiene: IC del grupo 3 incluye cero, |punto| menor que 5% del virgen y control negativo nulo;
  * sostiene: IC del grupo 3 por debajo de cero y control negativo nulo;
  * ubicacion: IC por debajo de cero y control negativo no nulo;
  * no firme: cualquier otro caso.
Cota: si el control negativo es nulo, se publica el limite bajo del IC del grupo 3, en bbl por metro y en % del virgen, como la mayor
perdida del hijo muy depletado compatible con el dato ("cota superior de la perdida"). Con el control negativo no nulo no hay cota.

Filas descriptivas, sin veredicto propio: el mismo modelo con cuadrados de 1 km y de 5 km; el modelo principal sin el control de
densidad final; el modelo principal con errores agrupados por pad; la exposicion continua (real y de control) con el modelo principal.
Equilibrio dentro de celdas (descriptivo): para rama, etapas, arena por metro, cohorte y densidad final, la media por grupo y el p de
Wald conjunto de los grupos 2 y 3 dentro de las celdas de 2 km.

Que NO prueba: lo mismo que pipeline.hijo (distancia de superficie, espaciamiento no observado, asociacion y no causa, pozos recientes
fuera). Ademas: dentro de una celda, el hijo depletado es en general el que se fracturo despues; la cohorte se controla por ano, pero
cambios de practica dentro del ano o propios de un lugar se confunden con la depleccion. Las celdas sin hijos virgenes y depletados a la
vez no aportan a la comparacion.
"""
from __future__ import annotations

import math

import duckdb
import numpy as np

from pipeline import hijo
from pipeline.costo import _escribir
from pipeline.ingest import DATA

LADO_KM = 2.0
LADOS_DESCRIPTIVOS = (1.0, 5.0)
LAT_REF = -38.5
KM_GRADO = 111.32
MIN_CELDAS_INFORMATIVAS = 30

COLS_COEF = hijo.COLS_COEF + [("celdas_fe", "integer")]
COLS_RESUMEN = [("veredicto", "varchar"), ("hijos", "integer"), ("pads", "integer"), ("celdas", "integer"),
                ("celdas_informativas", "integer"), ("hijos_en_informativas", "integer"), ("virgen_mediana_bbl_m", "double"),
                ("cota_bbl_m", "double"), ("cota_pct", "double")]
COLS_EQUILIBRIO = [("variable", "varchar"), ("grupo1", "double"), ("grupo2", "double"), ("grupo3", "double"), ("p", "double")]


def celdas(lat: np.ndarray, lon: np.ndarray, lado_km: float = LADO_KM) -> np.ndarray:
    """Cuadrado de `lado_km` de una grilla fija (x escalada por el coseno de LAT_REF)."""
    x = np.floor(KM_GRADO * math.cos(math.radians(LAT_REF)) * lon / lado_km).astype(int)
    y = np.floor(KM_GRADO * lat / lado_km).astype(int)
    return np.array([f"{a}|{b}" for a, b in zip(x, y)])


def controles_celda(H: dict, densidad: np.ndarray, con_densidad: bool = True) -> np.ndarray:
    """Controles de hijo.controles, indicadores de cohorte (el primer ano es la referencia) y la densidad final."""
    coh = H["cohorte"]
    cols = [hijo.controles(H)] + [(coh == a).astype(float)[:, None] for a in sorted(set(coh.tolist()))[1:]]
    if con_densidad:
        cols.append(densidad.astype(float)[:, None])
    return np.column_stack(cols)


def modelo_grupos(y, g, celda, cluster, C, nombre: str) -> tuple[list[tuple], float]:
    """Indicadores de los grupos 2 y 3 (referencia 1) con efectos fijos de `celda` y errores por `cluster`."""
    T = np.column_stack([(g == 2).astype(float), (g == 3).astype(float)])
    r = hijo.ajustar(y, T, C, celda, cluster)
    vm = float(np.median(y[g == 1])) if (g == 1).any() else float("nan")
    return [hijo._fila_coef(nombre, hijo.TERMINOS[k + 2], r["b"][k], r["e"][k], r["n"], r["pads"], vm) + (int(r["celdas"]),)
            for k in (0, 1)], vm


def modelo_continuo(y, expo_m, celda, cluster, C, nombre: str, vm: float) -> tuple:
    r = hijo.ajustar(y, (expo_m / hijo.ESCALA_CONTINUA)[:, None], C, celda, cluster)
    return hijo._fila_coef(nombre, hijo.TERMINO_CONTINUA, r["b"][0], r["e"][0], r["n"], r["pads"], vm) + (int(r["celdas"]),)


def informativas(celda: np.ndarray, g: np.ndarray) -> tuple[int, int]:
    """Celdas con al menos un hijo del grupo 1 y uno del grupo 3, y cuantos hijos tienen."""
    con1, con3 = set(celda[g == 1].tolist()), set(celda[g == 3].tolist())
    ambas = con1 & con3
    return len(ambas), int(np.isin(celda, list(ambas)).sum())


def calcular(D: dict) -> dict:
    H, P = D["H"], D["P"]
    i, j = hijo.pares(H, P)
    expo, expo_c = hijo.exposicion_real(H, P, i, j), hijo.exposicion_control(H, P, i, j)
    em, emc = expo / H["rama"], expo_c / H["rama"]
    g, gc = hijo.grupos(em, hijo.cortes(em)), hijo.grupos(emc, hijo.cortes(emc))
    y = H["y_bbl"] / H["rama"]
    dens = np.bincount(i, minlength=len(y)).astype(float)
    cel = celdas(H["lat"], H["lon"])
    C = controles_celda(H, dens)
    prin, vm = modelo_grupos(y, g, cel, cel, C, "principal")
    ctrl, _ = modelo_grupos(y, gc, cel, cel, C, "control_negativo")

    def pads_de(s):
        return int(len(np.unique(H["pad"][s])))
    n_inf, h_inf = informativas(cel, g)
    v = hijo.veredicto(prin[1], ctrl[1], int((g == 1).sum()), pads_de(g == 1), int((g == 3).sum()), pads_de(g == 3),
                       pads_de(np.ones(len(y), dtype=bool)))
    if n_inf < MIN_CELDAS_INFORMATIVAS:
        v = "sin muestra"
    prin[1] = prin[1][:12] + (v,) + prin[1][13:]
    hay_cota = v != "sin muestra" and hijo.nulo(ctrl[1][4], ctrl[1][5])
    nan = float("nan")
    resumen = [(v, int(len(y)), pads_de(np.ones(len(y), dtype=bool)), int(len(np.unique(cel))), n_inf, h_inf, vm,
                prin[1][4] if hay_cota else nan, prin[1][9] if hay_cota else nan)]
    coef = prin + ctrl
    for lado in LADOS_DESCRIPTIVOS:
        c2 = celdas(H["lat"], H["lon"], lado)
        coef += modelo_grupos(y, g, c2, c2, C, f"celdas_{lado:g}_km")[0]
    coef += modelo_grupos(y, g, cel, cel, controles_celda(H, dens, False), "sin_densidad")[0]
    coef += modelo_grupos(y, g, cel, H["pad"], C, "errores_por_pad")[0]
    coef.append(modelo_continuo(y, em, cel, cel, C, "continua", vm))
    coef.append(modelo_continuo(y, emc, cel, cel, C, "continua_control_negativo", vm))
    T = np.column_stack([(g == 2).astype(float), (g == 3).astype(float)])
    eq = []
    for nombre, x in (("rama_horizontal_m", H["rama"]), ("etapas", H["etapas"]), ("arena_tn_por_m", H["arena"] / H["rama"]),
                      ("cohorte", H["cohorte"].astype(float)), ("densidad_final", dens)):
        r = hijo.ols_celdas(x.astype(float), T, cel, cel)
        eq.append((nombre, *[float(x[g == b].mean()) if (g == b).any() else nan for b in (1, 2, 3)],
                   hijo.p_conjunto(r["beta"], r["cov"])))
    return {"coef": coef, "resumen": resumen, "equilibrio": eq, "veredicto": v}


# ------------------------------------------------------------------ pagina

MODELOS = {"principal": "Principal (celdas de 2 km)", "control_negativo": "Control negativo", "celdas_1_km": "Celdas de 1 km",
           "celdas_5_km": "Celdas de 5 km", "sin_densidad": "Sin densidad final", "errores_por_pad": "Errores por pad",
           "continua": "Continua", "continua_control_negativo": "Continua, control negativo"}
EQUILIBRIO_TXT = [("rama_horizontal_m", "Rama horizontal (m)", 0), ("etapas", "Etapas", 1), ("arena_tn_por_m", "Arena por metro (tn/m)", 2),
                  ("cohorte", "Cohorte (año del primer petróleo)", 2), ("densidad_final", "Pozos a menos de 1 km (cualquier fecha)", 1)]


def _anio(x: float) -> str:
    """Un ano medio sin punto de miles: 2022.915 -> '2022,92'."""
    return f"{x:.2f}".replace(".", ",")


def _texto_veredicto(v: str, prin: tuple, ctrl: tuple) -> str:
    g = hijo._g
    ic_pct = f"{g(prin[3], 1)}% del rendimiento virgen (IC 95%: {g(prin[9], 1)}% a {g(prin[10], 1)}%)"
    if v == "sostiene":
        return (f"Dentro de un mismo lugar, el hijo muy depletado rinde menos: {ic_pct}, con IC que excluye cero y control negativo "
                "nulo. Es una asociación con control de diseño y de ubicación, no una afirmación causal.")
    if v == "no se sostiene":
        return (f"Dentro de un mismo lugar no se ve que el hijo muy depletado rinda menos: {ic_pct}, punto menor que 5% del virgen "
                "y control negativo nulo.")
    if v == "ubicacion":
        return (f"El hijo muy depletado rinde menos ({ic_pct}), pero el control negativo tampoco es nulo: aun dentro de celdas de 2 km "
                "la asociación es de ubicación.")
    if v == "sin muestra":
        return "No se alcanzan los mínimos fijados (hijos y pads por grupo, o 30 celdas con hijos virgen y muy depletado) y no hay veredicto."
    if hijo.nulo(prin[4], prin[5]) and hijo.nulo(ctrl[4], ctrl[5]):
        return (f"La regla no permite concluir en ningún sentido. El control negativo del grupo que decide ahora es nulo, a diferencia "
                f"de hijo.md, pero el hijo muy depletado queda en {ic_pct}: el IC incluye cero y el punto supera el 5% del virgen. "
                "Con este dato no se puede afirmar ni descartar una degradación del hijo.")
    return "La regla no permite concluir en ningún sentido."


def pagina_hijo_celdas(con) -> str:
    g = hijo._g
    coef = {(r[0], r[1]): r for r in con.execute("select * from mart_hijo_celdas_coef").fetchall()}
    res = con.execute("select * from mart_hijo_celdas_resumen").fetchone()
    eq = {r[0]: r for r in con.execute("select * from mart_hijo_celdas_equilibrio").fetchall()}
    prin, ctrl = coef[("principal", "muy_depletado")], coef[("control_negativo", "muy_depletado")]
    ctrl2 = coef[("control_negativo", "poco_depletado")]
    c5, c1 = coef[("celdas_5_km", "muy_depletado")], coef[("celdas_1_km", "muy_depletado")]
    v = res[0]
    ic = lambda r: f"IC 95%: {g(r[4], 1)} a {g(r[5], 1)}"  # noqa: E731
    L = ["# Hijos cerca de pozos depletados, dentro de celdas de 2 km", "",
         "Página generada por `pipeline/hijo_celdas.py`. Repite la pregunta de [Hijos cerca de pozos depletados](hijo.md) comparando "
         "hijos del mismo cuadrado de 2 km: el que se fracturó cuando sus vecinos ya habían producido mucho contra el que se fracturó "
         "en zona virgen, con el año del primer petróleo, el diseño de la fractura, el operador y la densidad final de pozos alrededor "
         "como controles. Este diseño se fijó después de ver el resultado de [hijo.md](hijo.md), que quedó no firme porque su control "
         "negativo no es nulo; la regla se escribió antes de calcular nada con él y no cambia el veredicto de `hijo_depletado`.", "",
         "## Resumen", "",
         f"Veredicto contra la regla fijada: **{v}**. {_texto_veredicto(v, prin, ctrl)}", "",
         f"- Muy depletado contra virgen, dentro de celdas de 2 km: {g(prin[2], 1)} bbl por metro de rama ({ic(prin)}), o sea "
         f"{g(prin[3], 1)}% del rendimiento virgen (IC 95%: {g(prin[9], 1)}% a {g(prin[10], 1)}%), sobre {g(prin[6])} hijos en "
         f"{g(prin[7])} celdas.",
         f"- Rendimiento de los hijos en zona virgen a 12 meses: mediana de {g(res[6], 1)} bbl por metro de rama.",
         f"- Control negativo, muy depletado contra virgen: {g(ctrl[2], 1)} bbl por metro de rama ({ic(ctrl)}). "
         + ("Es nulo." if hijo.nulo(ctrl[4], ctrl[5]) else "No es nulo.")
         + f" El del grupo poco depletado, que la regla no usa, da {g(ctrl2[2], 1)} ({ic(ctrl2)})"
         + (", que no es nulo: el control queda limpio solo en el grupo que decide, y aun ahí su punto es positivo." if not hijo.nulo(ctrl2[4], ctrl2[5]) else "."),
         ]
    if res[7] == res[7]:   # no es nan
        L.append(f"- Cota superior de la pérdida del hijo muy depletado: {g(-res[7], 1)} bbl por metro de rama, o {g(-res[8], 1)}% "
                 "del rendimiento virgen. Es la mayor pérdida compatible con el dato público (límite bajo del IC), no una estimación.")
    L += [f"- Celdas que comparan: {g(res[4])} celdas tienen a la vez hijos virgen y muy depletados, con {g(res[5])} de los "
          f"{g(res[1])} hijos; las demás aportan a los controles pero no a la comparación.",
          f"- Con celdas de 5 km (descriptivo) el muy depletado da {g(c5[2], 1)} bbl por metro ({ic(c5)}); con celdas de 1 km, "
          f"{g(c1[2], 1)} ({ic(c1)}). El signo depende del tamaño de la celda y ningún IC excluye cero.",
          f"- Dentro de las celdas, el hijo muy depletado es de cohorte más reciente (año medio {_anio(eq['cohorte'][3])} contra "
          f"{_anio(eq['cohorte'][1])}), con más etapas ({g(eq['etapas'][3], 1)} contra {g(eq['etapas'][1], 1)}) y más pozos "
          f"alrededor ({g(eq['densidad_final'][3], 1)} contra {g(eq['densidad_final'][1], 1)}); el modelo los controla, pero "
          "cambios de práctica propios de un lugar quedan confundidos con la depleción.", "",
          "## Qué le dice a un operador", "",
          "Con datos públicos, la degradación del hijo no se puede medir con precisión útil: el punto dice que un hijo muy depletado "
          "rinde algo menos que uno en zona virgen del mismo lugar, pero el intervalo va de una pérdida grande a una ganancia. Lo que "
          "lo resolvería es dato interno: espaciamiento real entre ramas, zona de aterrizaje, trayectorias y presiones de reservorio "
          "al fracturar el hijo.", "",
          "## Regla fijada antes de correr", "",
          "Muestra, exposición, grupos y resultado son los de [hijo.md](hijo.md). Cambia el modelo: efectos fijos de un cuadrado de "
          "2 km de una grilla fija, indicadores de año del primer petróleo, rama, arena por metro, etapas, operador y densidad final "
          "(pozos de shale a menos de 1 km en cualquier fecha), con errores agrupados por celda. El control negativo usa la misma "
          "exposición de pozos posteriores a la ventana del hijo. Veredicto con la regla de hijo.md; además se exigen 30 celdas con "
          "hijos virgen y muy depletados. Si el control negativo es nulo se publica el límite bajo del IC como cota superior de la "
          "pérdida.", "",
          "## Coeficientes", "",
          "Diferencia de petróleo de 12 meses por metro de rama contra el grupo virgen (en el modelo continuo, por cada 100 bbl por "
          "metro de exposición), en bbl por metro, y en porcentaje de la mediana del virgen. IC de 95%; los errores se agrupan por "
          "celda salvo en la fila de errores por pad. Solo la fila principal del grupo muy depletado y su control negativo deciden.", "",
          "| Modelo | Término | Coeficiente (bbl/m) | % del virgen | IC 95% (bbl/m) | Hijos | Conglomerados | p |",
          "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |"]
    for (modelo, termino), r in coef.items():
        L.append(f"| {MODELOS[modelo]} | {hijo.TERMINOS_TXT[termino]} | {g(r[2], 1)} | {g(r[3], 1)} | {g(r[4], 1)} a {g(r[5], 1)} | "
                 f"{g(r[6])} | {g(r[7])} | {g(r[8], 3)} |")
    L += ["", "## Equilibrio dentro de las celdas", "",
          "Medias por grupo de exposición real y p de la prueba conjunta (Wald, errores por celda) de que los grupos poco y muy "
          "depletado no difieren del virgen dentro de las celdas de 2 km. Descriptivo: no condiciona el veredicto. Un p de 0,000 "
          "es menor que 0,0005.", "",
          "| Variable | Virgen | Poco depletado | Muy depletado | p dentro de celdas |", "| --- | ---: | ---: | ---: | ---: |"]
    for nombre, rot, dec in EQUILIBRIO_TXT:
        r = eq[nombre]
        f = (lambda x, d: _anio(x)) if nombre == "cohorte" else g
        L.append(f"| {rot} | {f(r[1], dec)} | {f(r[2], dec)} | {f(r[3], dec)} | {g(r[4], 3)} |")
    L += ["", "## Límites", "",
          "- Los de [hijo.md](hijo.md): distancia de superficie, espaciamiento no observado, asociación y no causa, pozos recientes "
          "fuera.",
          "- Dentro de una celda, el hijo depletado es casi siempre el que se fracturó después. El año se controla, pero cambios de "
          "práctica dentro del año o propios de un lugar se confunden con la depleción.",
          "- El diseño se eligió después de ver el control negativo de hijo.md; se publican todos los modelos calculados, "
          "favorables o no, y los IC no tienen ajuste por comparaciones múltiples.", ""]
    return "\n".join(L)


def main(path=DATA / "warehouse.duckdb") -> None:
    con = duckdb.connect(str(path))
    R = calcular(hijo.cargar(con))
    _escribir(con, "mart_hijo_celdas_coef", COLS_COEF, R["coef"])
    _escribir(con, "mart_hijo_celdas_resumen", COLS_RESUMEN, R["resumen"])
    _escribir(con, "mart_hijo_celdas_equilibrio", COLS_EQUILIBRIO, R["equilibrio"])
    for t in ("mart_hijo_celdas_resumen", "mart_hijo_celdas_coef", "mart_hijo_celdas_equilibrio"):
        for r in con.execute(f"select * from {t}").fetchall():
            print(f"[hijo_celdas] {t[17:]:11}", tuple(round(x, 4) if isinstance(x, float) else x for x in r))
    con.close()


if __name__ == "__main__":
    main()
