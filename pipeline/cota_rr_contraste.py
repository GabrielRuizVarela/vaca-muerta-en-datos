"""Contraste de la cota condicional de Rambachan y Roth con el paquete HonestDiD, y la misma cota sobre E y E2 (ronda 4, S1).

Las reglas de este modulo se citan tal como se escribieron: "este commit" es el commit en que se fijo la regla, y el plan que
nombra (docs/plan-siguiente-nivel.md) no se publica. El SHA, la fecha y el texto de la regla estan en docs/reglas-fijadas.md.

REGLA FIJADA ANTES DE CALCULAR (2026-11-27, ronda 4 de docs/plan-siguiente-nivel.md). Este commit trae la regla, las constantes y
las firmas. Antes de fijarla no se corrio HonestDiD sobre ninguna entrada real ni se calculo la cota condicional de E o de E2. Si
algo resulta ambiguo al calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocen las cifras de pipeline.cota_rr_condicional (regla de19052, enmienda 55a709a). El quiebre de
D1 ATT(1) es 0; su conjunto con Mbar = 0 va de -35,0 a 6,8 y con Mbar = 0,25 de -34,5 a 3,6, asi que no estan anidados. El de la
media de D2 es 1,83 y el de D2 tau_W(1) es mayor que 2. Tambien se conocen los quiebres de la union de E y E2 (0,32 y 0,51). Se
leyo el codigo de HonestDiD 0.2.8 (computeConditionalCS_DeltaRM, .computeConditionalCS_DeltaRM_fixedS, .create_A_RM,
.ARP_computeCI, .compute_least_favorable_cv y .lp_conditional_test_fn); solo se corrio sobre datos inventados, para medir el
tiempo. El paquete simula el valor critico de la primera etapa con 1000 sorteos y el modulo con 10000. Por defecto
(postPeriodMomentsOnly = TRUE) la prueba del paquete usa solo las filas de A que tocan meses posteriores. Ademas, sus poliedros
traen una fila de signo para el salto mayor, que la de este proyecto no tiene: dentro del conjunto identificado es redundante,
pero en la prueba cuenta.

Por que. Fable, en la pasada sobre la copia publica 2c2ae47, pidio dos cosas: comparar la implementacion propia con HonestDiD y
correr la prueba condicional sobre E y E2. Tambien noto que los conjuntos de D1 no estan anidados en Mbar, y no pudo decir si eso
viene del metodo o de un error.

Entradas. Por estimando, beta = (b(-3), b(-2), b(-1), b(0), b(1)) y Sigma, armados exactamente como los arma
pipeline.cota_rr_condicional.calcular_estimando: beta es el punto de la muestra completa y Sigma = np.cov de los sorteos completos
(un sorteo con algun valor faltante se descarta).
  * D1 ATT(1), D2 tau_W(1) y D2 media tau_W(0,1) salen de cota_rr_condicional._entradas_reales.
  * E ATT(1) y E2 ATT(1) salen de la serie principal de pipeline.stacked.calcular, con los mismos sorteos (r["est"] y
    r["sorteos"] en e = -3, -2, -1, 0, 1). E usa km_max = KM_CONTROL_MAX y E2 usa KM_CONTROL_MAX_E2. En los dos, a = (0, 1),
    b = (1, 0) y meses = (1,).
Se escriben en ENTRADAS, por estimando: beta, Sigma, n_tratados, el numero de sorteos completos, l_vec, el quiebre del modulo
y su valor critico LF por poliedro para cada Mbar que R necesita en L1. No lleva datos de pozos. La salida de R guarda el SHA-256
de ese archivo. Si el archivo cambia, el contraste queda "desactualizado" y no se lee hasta volver a correr R.

Cambio de base. HonestDiD pone el periodo de referencia justo antes del primer mes posterior; este proyecto lo pone antes de
b(-3). beta_H = M beta y Sigma_H = M Sigma M'. M tiene las filas (0,0,-1,0,0), (1,0,-1,0,0), (0,1,-1,0,0), (0,0,-1,1,0) y
(0,0,-1,0,1): los tres previos de HonestDiD son la base, -3 y -2, medidos contra b(-1); la referencia es -1; los posteriores son
b(0) - b(-1) y b(1) - b(-1). numPrePeriods = 3 y numPostPeriods = 2. Con eso, los saltos previos de HonestDiD son s(-3), s(-2)
y s(-1), los posteriores son los mismos dos, y Delta^RM es el mismo conjunto. l_vec = (0, 1) para ATT(1) y (0,5; 0,5) para la
media.

Cuatro lecturas con HonestDiD 0.2.8 de CRAN, todas con alfa = ALFA, hybrid_flag = "LF", hybrid_kappa = alfa / 10 y
seed = 0. R corre en un contenedor con limites (scripts/contraste_honestdid.sh). Para cada theta de la grilla, el paquete
decide con .test_delta_lp_fn_wrapper, la prueba que llama .ARP_computeCI; las filas que usa la prueba (rowsForARP) se pasan
siempre explicitas.
  * L1, misma A y mismo valor critico. Para cada uno de los seis poliedros (j, sg), la matriz A de
    cota_rr_condicional.matriz_rm(j, sg, Mbar) se pasa a la base de HonestDiD (A_H = A M^-1, mismas filas y mismo orden) y
    entra con d = 0 y todas las filas. El valor critico de la primera etapa es el del modulo para ese poliedro y ese Mbar
    (hybrid_list$lf_cv): es el cuerpo de .ARP_computeCI sin la linea que lo vuelve a calcular. El conjunto es la union de los
    seis. Este es el contraste de la implementacion: las mismas filas, el mismo metodo y el mismo valor critico, con otro
    codigo para el estadistico, los vertices, el truncamiento y el valor p.
  * L1p, misma A y valor critico del paquete: lo mismo, por .ARP_computeCI tal cual. El paquete simula el valor critico con
    1000 sorteos y semilla 0 (.compute_least_favorable_cv); el modulo, con N_LF = 10000 y su semilla. La diferencia con L1
    mide cuanto mueve el conjunto la simulacion del valor critico.
  * L2, HonestDiD completo: computeConditionalCS_DeltaRM con postPeriodMomentsOnly = FALSE, con los poliedros del paquete (que
    traen la fila de signo).
  * L3, HonestDiD por defecto: computeConditionalCS_DeltaRM con sus valores por defecto (postPeriodMomentsOnly = TRUE). Es lo
    que obtiene quien corre el paquete sin cambiar nada, salvo la grilla.
  Grilla de theta en las cuatro: GRID_PUNTOS puntos, de l'beta_H - GRID_SD sd a l'beta_H + GRID_SD sd, con
  sd = raiz de l' Sigma_H,post l, que es el `desvio` de calcular_estimando. No es la grilla por defecto del paquete (de -20 a
  20 sd alrededor de cero), que puede quedar corta lejos del cero. Si un extremo de la grilla queda aceptado, el conjunto se
  publica abierto de ese lado, sin ampliar la grilla. Si el programa lineal no converge, el paquete no rechaza ese theta; se
  cuenta y se publica. Mbar recorre la GRILLA_MBAR de cota_rr_condicional.
  Quiebre: el menor Mbar en [0, MBAR_MAX] cuyo conjunto contiene el cero. El cero esta en el conjunto si el punto del medio
  de la grilla CERO_GRILLA (-1e-9, 0, 1e-9) se acepta. En L1p, L2 y L3, por biseccion con TOL_BISECCION, como en
  cota_rr_condicional, con el valor critico que el paquete calcula para cada Mbar. En L1 no hay biseccion, porque el valor
  critico del modulo solo se lleva a R para algunos Mbar: con q el quiebre del modulo, L1 pasa si acepta el cero con
  Mbar = min(q + TOL_QUIEBRE, MBAR_MAX) y lo rechaza con Mbar = max(q - TOL_QUIEBRE, 0); si q = 0, si lo acepta con
  Mbar = 0; si q es mayor que MBAR_MAX, si lo rechaza con MBAR_MAX.

Validacion antes de las entradas reales. R corre primero sobre entradas sinteticas: Sigma = SIGMA_SINT y un solo beta, el valor
esperado de la simulacion de cobertura de cota_rr_condicional con Mbar = 0,5 y theta = -3 (DELTA_PREVIA y saltos posteriores en
el borde), para ATT(1) y para la media. L1 tiene que dar "coincide" con la regla de abajo. Si no da, R no se corre sobre las
entradas reales hasta entender por que, y la pagina lo dice.

Regla de coincidencia (L1 contra el modulo, por estimando):
  * para cada Mbar de la grilla, cada extremo del conjunto de L1 queda a no mas de TOL_SD sd mas el paso de las dos grillas
    (la del modulo y la de R) del extremo del modulo, y los dos son abiertos o cerrados del mismo lado;
  * L1 pasa la prueba del quiebre de arriba.
"Coincide" si se cumple para los cinco estimandos; si no, "no coincide", con la lista de lo que no se cumple.

Que pasa con cada resultado (fijado ahora, antes de verlo):
  * Si coincide, las cifras del modulo siguen siendo las que se citan. La pagina dice que coinciden con la prueba de HonestDiD
    0.2.8 con las mismas filas y el mismo valor critico, y publica la mayor diferencia, en sd.
  * Si no coincide, un PR de texto aparte hace que el README, la portada y el paper citen las cifras de L1p (el codigo del
    paquete de punta a punta, con las filas de este proyecto) en lugar de las del modulo. La pagina publica las dos y la lista
    de diferencias. El modulo se corrige solo en un commit nuevo que diga por que.
  * L1p, L2 y L3 se publican como dato en la pagina, con su quiebre y su veredicto (pipeline.cota_rr.veredicto_rr), y no
    cambian ningun veredicto. De L1p se publica tambien la mayor diferencia con el modulo, en sd.
  * La frase del README que cita la cota condicional de D1 ATT(1) agrega, sea cual sea, el quiebre que da HonestDiD por
    defecto (L3), y dice que esa lectura usa solo las filas que tocan meses posteriores. La portada lo agrega solo si el
    veredicto de L3 es distinto del del modulo.
  * E y E2: la cota condicional del modulo (cota_rr_condicional.calcular_estimando con sus entradas) es cifra nueva. Su
    quiebre y su veredicto_rr se publican al lado de los de la union, en la pagina, en las filas de E y E2 del README y en el
    paper. Los veredictos de E y de E2 no cambian: pipeline.stacked.veredicto_apilado sigue recibiendo el veredicto de la
    union, y da "sin muestra" por el numero de eventos.
  * Anidamiento: para cada lectura y estimando, la pagina dice si cada conjunto de la grilla contiene al del Mbar anterior,
    con tolerancia de TOL_SD sd mas el paso de la grilla. Es un dato, sin veredicto.

Que se publica:
  * ENTRADAS y SALIDA_R (data/), el script de R (scripts/contraste_honestdid.R) y el que lo corre en el contenedor;
  * mart_cota_rr_contraste: una fila por estimando, lectura (modulo, L1, L1p, L2, L3) y Mbar de la grilla, mas una fila de
    quiebre por estimando y lectura y una fila de veredicto del contraste;
  * una seccion "Contraste con HonestDiD" y una seccion "E y E2" en wiki/hallazgos/cota_rr_condicional.md.

Validacion fijada antes de leer cifras reales (tests/test_cota_rr_contraste.py, sin warehouse y sin R):
  * cambio de base: para beta al azar, los cinco saltos de beta_H en la base de HonestDiD son los de beta en la del proyecto, y
    A_H beta_H = A beta para los seis poliedros y la grilla de Mbar;
  * la regla de coincidencia, sobre la salida sintetica de R que se guarda en el repositorio (SALIDA_SINT), da "coincide" en L1;
  * una salida de R con el SHA-256 de otras entradas queda "desactualizado".

Lo que no dice: el contraste prueba que la misma prueba da lo mismo con otro codigo. No prueba que Delta^RM sea la restriccion
correcta ni que la base de los coeficientes sea la que usaria HonestDiD con los datos crudos: usa la de este proyecto, que es la
de pipeline.cota_rr.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np

from pipeline import cota_rr_condicional as crc

# ---- regla fijada (no cambiar despues de ver cifras) ----
ALFA = crc.ALFA                 # 0,05
GRID_PUNTOS = 3001
GRID_SD = 30.0
TOL_SD = 0.05
TOL_QUIEBRE = 0.02
CERO_GRILLA = (-1e-9, 0.0, 1e-9)
SEMILLA_R = 0
TOL_BISECCION = crc.TOL_BISECCION
MBAR_MAX = crc.MBAR_MAX
GRILLA_MBAR = crc.GRILLA_MBAR
HONESTDID_VERSION = "0.2.8"
LECTURAS = ("modulo", "L1", "L1p", "L2", "L3")
M_BASE = ((0, 0, -1, 0, 0), (1, 0, -1, 0, 0), (0, 1, -1, 0, 0), (0, 0, -1, 1, 0), (0, 0, -1, 0, 1))
ENTRADAS = Path("data/cota_rr_contraste_entradas.json")
SALIDA_R = Path("data/cota_rr_contraste_honestdid.json")
ENTRADAS_SINT = Path("tests/fixtures/cota_rr_contraste_entradas_sint.json")
SALIDA_SINT = Path("tests/fixtures/cota_rr_contraste_honestdid_sint.json")
COMMIT_REGLA = "06f7720"        # el commit que fijo la regla; el de las aclaraciones es COMMIT_ACLARACIONES
COMMIT_ACLARACIONES = "21e1a91"
PAGINA = crc.PAGINA

# ---- aclaraciones de la regla (2026-11-27), fijadas antes de correr R sobre entradas reales; solo se vio la salida sintetica ----
# 1. Si el paquete falla con un error en un theta, esa prueba no rechaza, como cuando el programa lineal no converge. En la
#    salida sintetica pasa con solve() de una matriz singular en theta = -2, que cae justo en la grilla, en dos poliedros de
#    ATT(1) con Mbar = 0, y no mueve ningun extremo. El envoltorio esta en scripts/contraste_honestdid.R; se cuenta por
#    lectura (errores_paquete) y se publica al lado de los fallos del programa lineal.
# 2. Si un lado queda abierto en el modulo y en L1, de ese lado solo se compara que los dos esten abiertos: los dos extremos son
#    el borde de su grilla.
# 3. En la biseccion de L1p, L2 y L3, un Mbar que no esta en la grilla usa A_H(Mbar) = A_H(0) + Mbar (A_H(1) - A_H(0)): A es
#    lineal en Mbar, y tests/test_cota_rr_contraste.py lo prueba.
# 4. Los conjuntos y el quiebre del modulo que van en ENTRADAS se recalculan con cota_rr_condicional.conjunto_confianza y
#    quiebre_condicional sobre el beta y la Sigma de la entrada. Para D1 y D2 tienen que dar los de mart_cota_rr_condicional,
#    hasta el paso de su grilla; si no dan, no se corre R.


# ---- armado (no es parte de la regla: estructura de los archivos) ----
NUM_PREVIOS = 3
NUM_POSTERIORES = 2
_M = np.array(M_BASE, float)
_M_INV = np.linalg.inv(_M)


def base_honestdid(beta, Sigma):
    """(beta_H, Sigma_H) en la base de HonestDiD."""
    return _M @ np.asarray(beta, float), _M @ np.asarray(Sigma, float) @ _M.T


def a_honestdid(A):
    """A_H = A M^-1."""
    return np.asarray(A, float) @ _M_INV


def clave_mbar(mbar: float) -> str:
    return format(float(mbar), ".10g")


def desvio_estimando(Sigma, l_vec) -> float:
    """raiz de l' Sigma_H,post l: el `desvio` de calcular_estimando."""
    _, SH = base_honestdid(np.zeros(5), Sigma)
    l = np.asarray(l_vec, float)
    return float(np.sqrt(l @ SH[NUM_PREVIOS:, NUM_PREVIOS:] @ l))


def mbars_quiebre(q: float | None) -> list[float]:
    """Los Mbar en que L1 prueba el cero para el quiebre q del modulo (None = mayor que MBAR_MAX)."""
    if q is None:
        return [float(MBAR_MAX)]
    if q <= 0:
        return [0.0]
    return [float(max(q - TOL_QUIEBRE, 0.0)), float(min(q + TOL_QUIEBRE, MBAR_MAX))]


def _lista(x):
    return np.asarray(x, float).tolist()


def entrada_estimando(nombre: str, a, b, meses, beta, Sigma, n_tratados=None, sorteos=None) -> dict:
    """Una entrada de ENTRADAS: beta, Sigma, l_vec, el conjunto y el quiebre del modulo, y A_H y c_LF por poliedro."""
    beta = np.asarray(beta, float)
    Sigma = np.asarray(Sigma, float)
    meses = tuple(meses)
    l_vec = np.full(len(meses), 1.0 / len(meses)) if len(meses) == 2 else np.array([0.0, 1.0])
    sd = desvio_estimando(Sigma, l_vec)
    l_pt = float(beta[[3 + e for e in meses]].mean())
    b3, b2, b1 = (float(x) for x in beta[:3])
    sets = []
    for m in GRILLA_MBAR:
        lo, hi = crc.cota_rr.conjunto(l_pt, b3, b2, b1, m, meses)
        cc = crc.conjunto_confianza(beta, Sigma, a, b, m, (float(lo), float(hi)), sd)
        sets.append({"mbar": float(m), **cc})
    q = float(crc.quiebre_condicional(beta, Sigma, a, b))
    q = None if not np.isfinite(q) else q
    bh, sh = base_honestdid(beta, Sigma)
    por_mbar = []
    for m in sorted({float(x) for x in GRILLA_MBAR} | set(mbars_quiebre(q))):
        pol = []
        for P, (j, sg) in zip(crc._pruebas(Sigma, a, b, m), crc.POLIEDROS):
            pol.append({"j": j, "sg": sg, "A": _lista(a_honestdid(P.A)),
                        "c_lf": None if not np.isfinite(P.c_lf) else float(P.c_lf)})
        por_mbar.append({"mbar": m, "poliedros": pol})
    return {"nombre": nombre, "a": [float(x) for x in a], "b": [float(x) for x in b], "meses": [int(e) for e in meses],
            "l_vec": _lista(l_vec), "beta": _lista(beta), "Sigma": _lista(Sigma), "beta_h": _lista(bh),
            "Sigma_h": _lista(sh), "sd": sd, "n_tratados": n_tratados, "sorteos": sorteos,
            "modulo": {"sets": sets, "quiebre": q}, "mbars_quiebre": mbars_quiebre(q), "por_mbar": por_mbar}


def entradas_sinteticas() -> list[dict]:
    """Las entradas sinteticas fijadas por la regla: SIGMA_SINT y el valor esperado de la simulacion con Mbar = 0,5 y theta = -3."""
    d = np.array(crc.DELTA_PREVIA)
    delta = np.concatenate([d, [d[-1] + crc.M_SINT, d[-1] + 2 * crc.M_SINT]])
    beta = delta + np.array([0, 0, 0, -3.0, -3.0])
    return [entrada_estimando(nom, a, b, meses, beta, crc.SIGMA_SINT) for nom, (a, b, meses) in crc._NOMBRE_SINT.items()]


def escribir_json(obj, path) -> str:
    """JSON determinista (claves ordenadas, flotantes con repr) y su SHA-256."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, sort_keys=True, indent=1, allow_nan=False, ensure_ascii=True) + "\n"
    path.write_bytes(txt.encode("ascii"))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_archivo(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def escribir_entradas(lista: list[dict], path) -> str:
    parametros = {"alfa": ALFA, "kappa": crc.KAPPA, "grid_puntos": GRID_PUNTOS, "grid_sd": GRID_SD, "tol_sd": TOL_SD,
                  "tol_quiebre": TOL_QUIEBRE, "cero_grilla": list(CERO_GRILLA), "semilla_r": SEMILLA_R,
                  "tol_biseccion": TOL_BISECCION, "mbar_max": MBAR_MAX, "grilla_mbar": list(GRILLA_MBAR),
                  "num_previos": NUM_PREVIOS, "num_posteriores": NUM_POSTERIORES, "honestdid": HONESTDID_VERSION}
    return escribir_json({"regla": "ronda 4 S1", "parametros": parametros, "estimandos": lista}, path)


def leer_salida(path_salida, path_entradas) -> tuple[str, dict | None]:
    """('ok', salida) si el SHA-256 de entradas de la salida es el del archivo de entradas; si no, ('desactualizado', None)."""
    if not Path(path_salida).exists():
        return "sin_salida", None
    salida = json.loads(Path(path_salida).read_text())
    if salida.get("sha256_entradas") != sha256_archivo(path_entradas):
        return "desactualizado", None
    return "ok", salida


def _entrada_de_sorteos(nombre: str, a, b, meses, beta, vals, n_tratados: int) -> dict:
    """Una entrada con Sigma = np.cov de los sorteos completos (un sorteo con algun valor faltante se descarta), como calcular_estimando."""
    beta = np.asarray(beta, float)
    vals = np.asarray(vals, float).reshape(-1, 5)
    vv = vals[~np.isnan(vals).any(axis=1)]
    if not np.all(np.isfinite(beta)) or len(vv) < 10:
        raise ValueError(f"{nombre}: falta algun previo o muy pocos sorteos completos")
    ent = entrada_estimando(nombre, a, b, meses, beta, np.cov(vv, rowvar=False), int(n_tratados), int(len(vv)))
    return ent


def _estimandos_e(con) -> list[tuple]:
    """(diseno, estimando, a, b, meses, beta, vals, n_tratados) de E y E2, de la serie principal de pipeline.stacked.calcular."""
    from pipeline import stacked
    D = stacked.cargar(con)
    out = []
    for diseno, km in (("E", stacked.KM_CONTROL_MAX), ("E2", stacked.KM_CONTROL_MAX_E2)):
        res = stacked.calcular(D, km_max=km)
        r, j1 = res["r"], res["j1"]
        ix = [stacked.E_SERIE.index(e) for e in (-3, -2, -1, 0, 1)]
        beta = np.array([float(r["est"][j]) for j in ix])
        vals = np.column_stack([np.asarray(r["sorteos"][:, j], float) for j in ix])
        out.append((diseno, "ATT(1)", (0, 1), (1, 0), (1,), beta, vals, int(r["n_tratados"][j1])))
    return out


def entradas(con) -> list[dict]:
    """Los cinco estimandos con beta, Sigma, n_tratados y sorteos. Cada uno lleva ademas `union_quiebre`, el de la union que
    calcula cota_rr_condicional.calcular_estimando con las mismas entradas (se compara con las marts, no entra en la regla)."""
    crudas = crc._entradas_reales(con) + _estimandos_e(con)
    out = []
    for diseno, nombre, a, b, meses, beta, vals, n in crudas:
        ent = _entrada_de_sorteos(f"{diseno} {nombre}", a, b, meses, beta, vals, n)
        ref = crc.calcular_estimando(diseno, nombre, a, b, tuple(meses), beta, vals, n)
        ent["diseno"], ent["estimando"] = diseno, nombre
        ent["union_quiebre"] = ref["extra"]["union_quiebre"]
        ent["ref_quiebre"] = None if ref["quiebre"] is None or not np.isfinite(ref["quiebre"]) else float(ref["quiebre"])
        out.append(ent)
    return out


def verificar_modulo(con, lista: list[dict]) -> list[str]:
    """Aclaracion 4: los conjuntos y el quiebre del modulo de D1 y D2 en `lista` (recalculados de beta y Sigma) tienen que dar los de
    mart_cota_rr_condicional hasta el paso de su grilla; y el quiebre de la entrada es el de calcular_estimando. Devuelve las fallas."""
    falla: list[str] = []
    filas = con.execute("select diseno, estimando, fila, mbar, cc_bajo, cc_alto, cc_abierto, mbar_quiebre from mart_cota_rr_condicional").fetchall()
    for e in lista:
        q, ref = e["modulo"]["quiebre"], e.get("ref_quiebre")
        if (q is None) != (ref is None) or (q is not None and abs(q - ref) > TOL_BISECCION):
            falla.append(f"{e['nombre']}: quiebre de la entrada {q} y de calcular_estimando {ref}")
        if e["diseno"] not in ("D1", "D2"):
            continue
        mine = {clave_mbar(s["mbar"]): s for s in e["modulo"]["sets"]}
        for d, n, fila, m, lo, hi, ab, qm in filas:
            if (d, n) != (e["diseno"], e["estimando"]):
                continue
            if fila == "quiebre":
                if (qm is None) != (q is None) or (q is not None and abs(qm - q) > TOL_BISECCION):
                    falla.append(f"{e['nombre']}: quiebre {q} contra {qm} en la mart")
                continue
            s = mine.get(clave_mbar(m))
            if s is None:
                falla.append(f"{e['nombre']}: falta Mbar {m}")
            elif (s["bajo"] is None) != (lo is None) or (s["abierto"] or None) != (ab or None):
                falla.append(f"{e['nombre']} Mbar {m}: vacio o abierto distinto ({s['bajo']}, {s['abierto']}) contra ({lo}, {ab})")
            elif lo is not None and (abs(s["bajo"] - lo) > s["paso"] or abs(s["alto"] - hi) > s["paso"]):
                falla.append(f"{e['nombre']} Mbar {m}: [{s['bajo']}, {s['alto']}] contra [{lo}, {hi}] en la mart (paso {s['paso']})")
    return falla


def _por_mbar(sets: list[dict]) -> dict:
    return {clave_mbar(s["mbar"]): s for s in sets}


def coincide(modulo: dict, l1: dict) -> tuple[bool, list[str]]:
    """Regla de coincidencia de L1 contra el modulo para un estimando.

    `modulo`: {"sets", "quiebre", "sd"}; `l1`: {"sets", "paso_r", "quiebre_prueba"}. Devuelve (coincide, lista de lo que no se cumple)."""
    falla: list[str] = []
    sd, paso_r = modulo["sd"], l1["paso_r"]
    sm, s1 = _por_mbar(modulo["sets"]), _por_mbar(l1["sets"])
    for m in GRILLA_MBAR:
        k = clave_mbar(m)
        if k not in s1 or k not in sm:
            falla.append(f"Mbar {k}: falta el conjunto")
            continue
        a, r = sm[k], s1[k]
        tol = TOL_SD * sd + a["paso"] + paso_r
        vacio_a, vacio_r = a["bajo"] is None, r["bajo"] is None
        if vacio_a and vacio_r:
            continue
        if vacio_a != vacio_r:
            falla.append(f"Mbar {k}: uno de los dos conjuntos es vacio")
            continue
        for lado in ("bajo", "alto"):
            ab_a = a["abierto"] in (lado, "ambos")
            ab_r = r["abierto"] in (lado, "ambos")
            if ab_a != ab_r:
                falla.append(f"Mbar {k}: extremo {lado} abierto en uno solo")
            elif not ab_a and abs(a[lado] - r[lado]) > tol:
                falla.append(f"Mbar {k}: extremo {lado} difiere {abs(a[lado] - r[lado]) / sd:.4f} sd (tolerancia {tol / sd:.4f} sd)")
    falla += _falla_quiebre(modulo["quiebre"], l1["quiebre_prueba"])
    return not falla, falla


def _falla_quiebre(q, pruebas: list[dict]) -> list[str]:
    acepta = {clave_mbar(p["mbar"]): bool(p["acepta_cero"]) for p in pruebas}
    falla = []
    if q is None:
        m = clave_mbar(MBAR_MAX)
        if acepta.get(m) is not False:
            falla.append(f"quiebre: el modulo no contiene el cero en {m} y L1 si (o falta la prueba)")
    elif q <= 0:
        if acepta.get("0") is not True:
            falla.append("quiebre: el modulo contiene el cero con Mbar = 0 y L1 no (o falta la prueba)")
    else:
        arriba, abajo = clave_mbar(min(q + TOL_QUIEBRE, MBAR_MAX)), clave_mbar(max(q - TOL_QUIEBRE, 0.0))
        if acepta.get(arriba) is not True:
            falla.append(f"quiebre: L1 no acepta el cero con Mbar = {arriba}")
        if acepta.get(abajo) is not False:
            falla.append(f"quiebre: L1 no rechaza el cero con Mbar = {abajo}")
    return falla


def diferencia_maxima_sd(modulo: dict, lectura: dict) -> dict:
    """Mayor diferencia de extremo (bajo, alto) entre la lectura y el modulo, en sd, sobre los Mbar con extremo cerrado en ambos."""
    sd = modulo["sd"]
    sm, sl = _por_mbar(modulo["sets"]), _por_mbar(lectura["sets"])
    out = {"bajo": 0.0, "alto": 0.0}
    for k, a in sm.items():
        r = sl.get(k)
        if r is None or a["bajo"] is None or r["bajo"] is None:
            continue
        for lado in out:
            if a["abierto"] in (lado, "ambos") or r["abierto"] in (lado, "ambos"):
                continue
            out[lado] = max(out[lado], abs(a[lado] - r[lado]) / sd)
    return out


def anidamiento(sets: list[dict], sd: float) -> list[dict]:
    """Por Mbar de la grilla (desde el segundo): el conjunto contiene al del Mbar anterior, con tolerancia TOL_SD sd mas el paso."""
    out = []
    for prev, cur in zip(sets[:-1], sets[1:]):
        if prev["bajo"] is None:
            ok = True
        elif cur["bajo"] is None:
            ok = False
        else:
            tol = TOL_SD * sd + max(prev.get("paso") or 0.0, cur.get("paso") or 0.0)
            ok = cur["bajo"] <= prev["bajo"] + tol and cur["alto"] >= prev["alto"] - tol
        out.append({"mbar": cur["mbar"], "contiene_al_anterior": ok})
    return out


def evaluar(path_entradas, path_salida) -> dict:
    """Por estimando: coincidencia de L1, diferencias de las demas lecturas y anidamiento; 'desactualizado' si el SHA no es el del archivo."""
    estado, salida = leer_salida(path_salida, path_entradas)
    if estado != "ok":
        return {"estado": estado}
    ent = json.loads(Path(path_entradas).read_text())["estimandos"]
    res = {}
    for e in ent:
        s = salida["estimandos"][e["nombre"]]
        mod = {"sets": e["modulo"]["sets"], "quiebre": e["modulo"]["quiebre"], "sd": e["sd"]}
        l1 = {"sets": s["L1"]["sets"], "paso_r": s["paso_r"], "quiebre_prueba": s["L1"]["quiebre_prueba"]}
        ok, falla = coincide(mod, l1)
        res[e["nombre"]] = {
            "L1_coincide": ok, "falla": falla,
            "dif_max_sd": {lec: diferencia_maxima_sd(mod, {"sets": s[lec]["sets"]}) for lec in ("L1", "L1p", "L2", "L3")},
            "quiebre": {"modulo": e["modulo"]["quiebre"], **{lec: s[lec]["quiebre"] for lec in ("L1p", "L2", "L3")}},
            "anidamiento": {"modulo": anidamiento(mod["sets"], e["sd"]),
                            **{lec: anidamiento(s[lec]["sets"], e["sd"]) for lec in ("L1", "L1p", "L2", "L3")}},
            "lp_fallos": {lec: s[lec]["lp_fallos"] for lec in ("L1", "L1p", "L2", "L3")}}
    return {"estado": "ok", "estimandos": res, "coincide": all(v["L1_coincide"] for v in res.values())}


# ---- mart y pagina (estructura de salida, no es parte de la regla) ----
COLS_CONTRASTE = [("estimando", "varchar"), ("lectura", "varchar"), ("fila", "varchar"), ("mbar", "double"), ("bajo", "double"),
                  ("alto", "double"), ("abierto", "varchar"), ("con_huecos", "boolean"), ("contiene_al_anterior", "boolean"),
                  ("mbar_quiebre", "double"), ("veredicto_rr", "varchar"), ("coincide", "boolean"),
                  ("dif_max_bajo_sd", "double"), ("dif_max_alto_sd", "double"), ("lp_fallos", "integer"),
                  ("errores_paquete", "integer"), ("n_tratados", "integer"), ("sorteos", "integer"), ("nota", "varchar")]
LECTURAS_R = ("L1", "L1p", "L2", "L3")


def _veredicto_rr(q) -> str:
    return crc.cota_rr.veredicto_rr(True, float("inf") if q is None else float(q))


def _suma(sets: list[dict], clave: str):
    return int(sum(int(s.get(clave) or 0) for s in sets))


def filas_mart(lista: list[dict], ev: dict, salida: dict | None) -> list[tuple]:
    """Filas de mart_cota_rr_contraste: por estimando y lectura (modulo, L1, L1p, L2, L3), una fila por Mbar de la grilla y una de
    quiebre; por estimando, una de veredicto de la coincidencia de L1. Sin salida de R al dia solo van las del modulo."""
    filas = []
    for e in lista:
        nom, nt, so = e["nombre"], e["n_tratados"], e["sorteos"]
        r = ev["estimandos"].get(nom) if ev.get("estado") == "ok" else None
        lecturas = {"modulo": e["modulo"]["sets"]}
        if r is not None:
            lecturas.update({lec: salida["estimandos"][nom][lec]["sets"] for lec in LECTURAS_R})
        for lec, sets in lecturas.items():
            anid = {round(a["mbar"], 9): a["contiene_al_anterior"] for a in anidamiento(sets, e["sd"])}
            for s in sets:
                filas.append((nom, lec, "grilla", float(s["mbar"]), s["bajo"], s["alto"], s.get("abierto"), s.get("con_huecos"),
                              anid.get(round(s["mbar"], 9)), None, None, None, None, None,
                              None if lec == "modulo" else int(s.get("lp_fallos") or 0),
                              None if lec == "modulo" else int(s.get("errores_paquete") or 0), nt, so, None))
            dif = r["dif_max_sd"].get(lec, {}) if r is not None else {}
            if lec == "modulo":
                q = e["modulo"]["quiebre"]
                filas.append((nom, lec, "quiebre", None, None, None, None, None, None, q, _veredicto_rr(q), None, None, None,
                              None, None, nt, so, "quiebre del modulo (pipeline.cota_rr_condicional)"))
            elif lec == "L1":
                filas.append((nom, lec, "quiebre", None, None, None, None, None, None, None, None, r["L1_coincide"],
                              dif["bajo"], dif["alto"], _suma(sets, "lp_fallos"), _suma(sets, "errores_paquete"), nt, so,
                              "no se biseca: pasa o no la prueba del cero en Mbar = q +- TOL_QUIEBRE del modulo"))
            else:
                q = r["quiebre"][lec]
                filas.append((nom, lec, "quiebre", None, None, None, None, None, None, q, _veredicto_rr(q), None,
                              dif["bajo"], dif["alto"], r_lp(salida, nom, lec), r_err(salida, nom, lec), nt, so,
                              None if lec != "L3" else "usa solo las filas de A que tocan meses posteriores"))
        if r is not None:
            nota = "coincide" if r["L1_coincide"] else "no coincide: " + "; ".join(r["falla"])
            filas.append((nom, "L1", "veredicto", None, None, None, None, None, None, None, None, bool(r["L1_coincide"]),
                          r["dif_max_sd"]["L1"]["bajo"], r["dif_max_sd"]["L1"]["alto"], None, None, nt, so, nota))
        else:
            filas.append((nom, "L1", "veredicto", None, None, None, None, None, None, None, None, None, None, None, None, None,
                          nt, so, "desactualizado: correr scripts/contraste_honestdid.sh"))
    return filas


def r_lp(salida: dict, nom: str, lec: str) -> int:
    return int(salida["estimandos"][nom][lec]["lp_fallos"])


def r_err(salida: dict, nom: str, lec: str) -> int:
    return int(salida["estimandos"][nom][lec]["errores_paquete"])


def _txt_q(q) -> str:
    return crc._qtxt(q)


def _txt_dif(d: dict) -> str:
    return f"{crc._fmt(d['bajo'], 3)} y {crc._fmt(d['alto'], 3)}"


def _txt_anid(a: list[dict]) -> str:
    malos = [crc._fmt(x["mbar"], 2) for x in a if not x["contiene_al_anterior"]]
    return f"{len(a) - len(malos)} de {len(a)}" + (f" (no contiene al anterior en Mbar = {', '.join(malos)})" if malos else "")


def seccion_contraste(lista: list[dict], ev: dict, salida: dict | None) -> list[str]:
    L = ["## Contraste con HonestDiD", "",
         f"Regla fijada en el commit {COMMIT_REGLA} antes de calcular, con sus aclaraciones en el commit {COMMIT_ACLARACIONES} "
         "(fijadas antes de correr R sobre entradas reales). Generada por `pipeline/cota_rr_contraste.py`. La prueba condicional e "
         f"híbrida de esta página se corre otra vez con el paquete HonestDiD {HONESTDID_VERSION} de CRAN, en R dentro de un "
         "contenedor con límites (`scripts/contraste_honestdid.sh`). Las entradas son `data/cota_rr_contraste_entradas.json` (beta, "
         "Sigma y las matrices A por poliedro; sin datos de pozos) y la salida de R es `data/cota_rr_contraste_honestdid.json`."]
    if ev.get("estado") != "ok":
        L += ["", "**Desactualizado: correr scripts/contraste_honestdid.sh.** La salida de R "
              + ("no existe" if ev.get("estado") == "sin_salida" else "es de otras entradas (su SHA-256 no es el del archivo de entradas)")
              + ", así que esta página no publica cifras del contraste.", ""]
        return L + _texto_no_dice_contraste()
    ok = ev["coincide"]
    mx = {lado: max(v["dif_max_sd"]["L1"][lado] for v in ev["estimandos"].values()) for lado in ("bajo", "alto")}
    L += ["", f"R {salida['r'].replace('R version ', '')}, HonestDiD {salida['honestdid']}, semilla {salida['seed']}. "
          f"**Lectura L1 (misma A y mismo valor crítico que el módulo): {'coincide' if ok else 'no coincide'}** con la regla de "
          f"coincidencia en los {len(ev['estimandos'])} estimandos. La mayor diferencia de un extremo entre L1 y el módulo es "
          f"{crc._fmt(mx['bajo'], 3)} sd (extremo bajo) y {crc._fmt(mx['alto'], 3)} sd (extremo alto), en desvíos del estimando.", ""]
    if not ok:
        L += ["Lo que no se cumple:", ""]
        for nom, v in ev["estimandos"].items():
            for f in v["falla"]:
                L.append(f"- {nom}: {f}")
        L += ["", "Con esto, como dice la regla, un PR de texto aparte hace que el README, la portada y el paper citen las cifras "
              "de L1p (el código del paquete de punta a punta, con las filas de este proyecto). Esta página publica las dos.", ""]
    L += ["Las cuatro lecturas: L1 (misma A y mismo valor crítico), L1p (misma A y valor crítico del paquete, 1000 sorteos), "
          "L2 (HonestDiD completo, `postPeriodMomentsOnly = FALSE`) y L3 (HonestDiD por defecto: usa solo las filas de A que tocan "
          "meses posteriores). L1p, L2 y L3 se publican como dato: no cambian ningún veredicto. Las diferencias son en sd contra "
          "el módulo, extremo bajo y extremo alto, sobre los Mbar de la grilla con ese extremo cerrado en los dos conjuntos.", ""]
    for e in lista:
        nom = e["nombre"]
        v = ev["estimandos"][nom]
        L += [f"### {nom}", "",
              "| Lectura | Mbar de quiebre | Veredicto | Mayor diferencia con el módulo (sd) | Fallos del programa lineal | Errores del paquete | Conjuntos que contienen al anterior |",
              "|---|---|---|---|---|---|---|",
              f"| módulo | {_txt_q(e['modulo']['quiebre'])} | {_veredicto_rr(e['modulo']['quiebre'])} | - | - | - | {_txt_anid(v['anidamiento']['modulo'])} |"]
        s = salida["estimandos"][nom]
        pasa = "pasa la prueba del cero alrededor del quiebre del módulo" if not [f for f in v["falla"] if f.startswith("quiebre")] else "no pasa la prueba del quiebre"
        for lec in LECTURAS_R:
            if lec == "L1":
                qt, vt = f"no se biseca: {pasa}", "-"
            else:
                q = v["quiebre"][lec]
                qt, vt = _txt_q(q), _veredicto_rr(q)
            L.append(f"| {lec} | {qt} | {vt} | {_txt_dif(v['dif_max_sd'][lec])} | {s[lec]['lp_fallos']} | {s[lec]['errores_paquete']} | "
                     f"{_txt_anid(v['anidamiento'][lec])} |")
        L += [""]
    dist = [e["nombre"] for e in lista if _veredicto_rr(ev["estimandos"][e["nombre"]]["quiebre"]["L3"])
            != _veredicto_rr(e["modulo"]["quiebre"])]
    L += ["El veredicto de L3 " + (f"es distinto del del módulo en {', '.join(dist)}." if dist else "es el mismo que el del módulo en los cinco estimandos.")
          + " Es un dato de esta lectura: ningún veredicto publicado cambia por él.", ""]
    L += ["El anidamiento es un dato, sin veredicto: para cada lectura se cuenta en cuántos Mbar de la grilla (desde el segundo) el "
          f"conjunto contiene al del Mbar anterior, con tolerancia de {crc._fmt(TOL_SD, 2)} sd más el paso de la grilla. "
          "Cuando el paquete falla con un error en un theta, o su programa lineal no converge, esa prueba no rechaza; se cuenta y se publica. "
          "L3 usa solo las filas de A que tocan meses posteriores.", ""]
    return L + _texto_no_dice_contraste()


def _texto_no_dice_contraste() -> list[str]:
    return ["### Lo que no dice el contraste", "",
            "Prueba que la misma prueba da lo mismo con otro código. No prueba que Delta^RM sea la restricción correcta ni que la "
            "base de los coeficientes sea la que usaría HonestDiD con los datos crudos: usa la de este proyecto, que es la de "
            "`pipeline.cota_rr`.", ""]


def seccion_e_e2(lista: list[dict], union: dict, veredicto_apilado: dict) -> list[str]:
    L = ["## E y E2", "",
         f"La misma cota condicional del módulo (regla {COMMIT_REGLA}, aclaraciones {COMMIT_ACLARACIONES}) sobre las series principales de "
         "los diseños apilados E (controles a 2 a 5 km) y E2 (a 2 a 10 km), con los mismos sorteos que sus páginas: beta es el punto "
         "de la muestra completa y Sigma la covarianza de los sorteos completos de e = -3, -2, -1, 0 y 1. Es cifra nueva. El quiebre "
         "condicional va al lado del de la unión, que sale de las marts de cada diseño. Unidades: puntos de índice, los del estimando de cada diseño.", "",
         "| Diseño | Tratados | Sorteos completos | Mbar de quiebre condicional | Veredicto condicional | Mbar de quiebre de la unión | Veredicto de la unión |",
         "|---|---|---|---|---|---|---|"]
    for e in lista:
        if e["diseno"] not in ("E", "E2"):
            continue
        qu, vu = union.get(e["diseno"], (e["union_quiebre"], _veredicto_rr(e["union_quiebre"])))
        q = e["modulo"]["quiebre"]
        L.append(f"| {e['diseno']} ATT(1) | {e['n_tratados']} | {e['sorteos']} | {_txt_q(q)} | {_veredicto_rr(q)} | {_txt_q(qu)} | {vu} |")
    L += [""]
    for e in lista:
        if e["diseno"] not in ("E", "E2"):
            continue
        L += [f"### {e['diseno']} ATT(1): conjunto de confianza condicional", "", "| Mbar | Conjunto condicional |", "|---|---|"]
        for s in e["modulo"]["sets"]:
            L.append(f"| {crc._fmt(s['mbar'], 2)} | " + crc._texto_cc({"cc_bajo": s["bajo"], "cc_alto": s["alto"],
                                                                      "cc_abierto": s.get("abierto"), "cc_con_huecos": s.get("con_huecos")}) + " |")
        L.append("")
    ver = " y ".join(f"{d}: **{v}**" for d, v in veredicto_apilado.items())
    L += ["Los veredictos de E y de E2 no cambian: `pipeline.stacked.veredicto_apilado` sigue recibiendo el veredicto de la unión "
          "y " + (f"da {ver}" if ver else "da \"sin muestra\"") + " por el número de eventos, no por la cota.", ""]
    return L


def _pos(txt: str, titulo: str) -> int:
    """Posicion de un encabezado de nivel 2 al comienzo de una linea (un '###' que lo contiene no cuenta); -1 si no esta."""
    m = re.search(r"(?m)^" + re.escape(titulo) + r"\b", txt)
    return m.start() if m else -1


def quitar_secciones(txt: str) -> str:
    """Saca de la pagina las dos secciones que agrega este modulo (desde '## Contraste con HonestDiD' hasta '## Lo que no dice')."""
    fin, ini = _pos(txt, "## Lo que no dice"), _pos(txt, "## Contraste con HonestDiD")
    if ini < 0 or fin < 0 or ini > fin:
        return txt
    return txt[:ini] + txt[fin:]


def insertar_secciones(txt: str, secciones: list[str]) -> str:
    """Pone las secciones justo antes de '## Lo que no dice', despues de sacar cualquier copia anterior. Idempotente."""
    txt = quitar_secciones(txt)
    fin = _pos(txt, "## Lo que no dice")
    if fin < 0:
        raise ValueError("la pagina no tiene la seccion '## Lo que no dice'")
    return txt[:fin] + "\n".join(secciones).rstrip("\n") + "\n\n" + txt[fin:]


def _union_apilado(con) -> tuple[dict, dict]:
    """({diseno: (quiebre, veredicto)}, {diseno: veredicto del diseno}) de mart_apilado y mart_apilado_e2."""
    union, ver = {}, {}
    # Los nombres de tabla van escritos en cada consulta para que pipeline.linaje vea las dos lecturas.
    consultas = {
        "E": ("mart_apilado",
              "select valor, veredicto from mart_apilado where resultado = 'cota_quiebre'",
              "select veredicto from mart_apilado where resultado = 'ATT(1)'"),
        "E2": ("mart_apilado_e2",
               "select valor, veredicto from mart_apilado_e2 where resultado = 'cota_quiebre'",
               "select veredicto from mart_apilado_e2 where resultado = 'ATT(1)'"),
    }
    for d, (tabla, sql_quiebre, sql_att) in consultas.items():
        if not con.execute("select count(*) from information_schema.tables where table_name = ?", [tabla]).fetchone()[0]:
            continue
        r = con.execute(sql_quiebre).fetchone()
        if r:
            union[d] = (r[0], r[1])
        v = con.execute(sql_att).fetchone()
        if v and v[0]:
            ver[d] = v[0]
    return union, ver


def main(path=None) -> None:
    """Escribe ENTRADAS; si SALIDA_R es de esas entradas, escribe mart_cota_rr_contraste y las dos secciones de la pagina."""
    import time

    import duckdb

    from pipeline import causal as cz
    from pipeline.costo import _escribir
    t0 = time.time()
    path = path or cz.DATA / "warehouse.duckdb"
    con = duckdb.connect(str(path), read_only=True)
    lista = entradas(con)
    fallas = verificar_modulo(con, lista)
    union, veredicto_ap = _union_apilado(con)
    con.close()
    if fallas:
        print("ACLARACION 4 NO SE CUMPLE: no se escribe ENTRADAS ni se corre R:\n  " + "\n  ".join(fallas))
        raise SystemExit(2)
    for e in lista:
        d = union.get(e["diseno"])
        if d is not None and e["union_quiebre"] is not None and d[0] is not None and abs(d[0] - e["union_quiebre"]) > 1e-3:
            print(f"AVISO: el quiebre de la union de {e['nombre']} ({e['union_quiebre']}) no coincide con la mart ({d[0]})")
    sha = escribir_entradas(lista, ENTRADAS)
    print(f"escrito {ENTRADAS} ({ENTRADAS.stat().st_size} bytes, sha256 {sha[:12]})  ({time.time() - t0:.1f} s)")
    ev = evaluar(ENTRADAS, SALIDA_R)
    salida = leer_salida(SALIDA_R, ENTRADAS)[1]
    print(f"salida de R: {ev['estado']}")
    if ev["estado"] == "ok":
        for nom, v in ev["estimandos"].items():
            print(f"  {nom}: L1 {'coincide' if v['L1_coincide'] else 'NO coincide'} dif max {v['dif_max_sd']['L1']}  "
                  f"quiebre modulo {v['quiebre']['modulo']} L1p {v['quiebre']['L1p']} L2 {v['quiebre']['L2']} L3 {v['quiebre']['L3']}  "
                  f"lp {v['lp_fallos']}")
            for f in v["falla"]:
                print(f"    - {f}")
    filas = filas_mart(lista, ev, salida)
    con = duckdb.connect(str(path))
    _escribir(con, "mart_cota_rr_contraste", COLS_CONTRASTE, filas)
    con.close()
    if PAGINA.exists():
        sec = seccion_contraste(lista, ev, salida) + seccion_e_e2(lista, union, veredicto_ap)
        PAGINA.write_text(insertar_secciones(PAGINA.read_text(encoding="utf-8"), sec), encoding="utf-8")
        print(f"escrito mart_cota_rr_contraste ({len(filas)} filas) y las secciones en {PAGINA}  (total {time.time() - t0:.1f} s)")
    else:
        print(f"escrito mart_cota_rr_contraste ({len(filas)} filas); falta {PAGINA}: correr antes pipeline.cota_rr_condicional")


if __name__ == "__main__":
    main()
