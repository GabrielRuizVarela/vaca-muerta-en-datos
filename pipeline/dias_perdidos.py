"""Dias de produccion que pierde un padre alrededor de la fractura de un hijo, por operador, y si esos dias compran algo.

Se corre despues de pipeline.descomposicion:  uv run python -m pipeline.dias_perdidos

La descomposicion ya publicada (pipeline/descomposicion.py) dice que buena parte de la brecha de volumen de los meses 0
y 1 son dias sin producir y no caudal por dia. Este modulo mide esos dias en dias, los abre por operador del padre,
prueba si la diferencia entre operadores se mantiene en el tiempo (una practica y no ruido) y si mas dias parados se
asocian con un caudal mejor despues. Es la primera entrada del libro de estrategias: la decision es que padres se
cierran, a que distancia y por cuanto tiempo.

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna
funcion de calculo; no se cambia despues de ver resultados). Se publican todos los resultados, favorables o no.

Que se habia mirado antes de fijarla
- Publicado en el repo: mart_descomposicion_k y mart_descomposicion_aditiva (la parte de los dias en la brecha, mes a
  mes, para toda la cuenca: los dias caen desde el mes -1 y vuelven hacia el mes 3), mart_descomposicion_cierres,
  la brecha por dia producido de Colorado (wiki/hallazgos/replicacion.md) y la robustez por operador de la brecha de
  volumen (wiki/hallazgos/robustez_operador.md). La ventana y los umbrales de abajo se fijaron conociendo eso.
- Una consulta exploratoria del 2026-11-20 sobre el warehouse de Vaca Muerta, fuera del repo y sin intervalos, con la
  ventana -1 a 2 y la base -6 a -4: la media del exceso de dias por banda (cercanos 15,8; 1 a 2 km 5,1; control 1,0);
  la media por operador del padre entre los cercanos (siete operadores, de 3,7 a 28,7 dias); por distancia dentro
  del kilometro; la mediana del caudal por dia efectivo de los meses 4 a 6 sobre la base por cuartil de exceso
  (0,71; 0,64; 0,66; 0,68; control 0,72); y la suma de exceso por caudal de base.
- Por eso, en Vaca Muerta: la medida A y la tabla por operador son DESCRIPTIVAS (ya miradas). La prueba B (mitades
  en el tiempo) y la pendiente C (ajustada, dentro del operador) no se habian calculado, pero su regla se fijo
  conociendo la dispersion entre operadores de toda la muestra y los cuartiles sin ajustar: son pruebas con REGLA
  INFORMADA y la pagina lo dice junto a cada veredicto. La tabla F (estado declarado) no se habia mirado.
- En Colorado no se habia mirado nada de este modulo (solo la brecha por dia producido de toda la cuenca, ya
  publicada). Ahi A, B y C son confirmatorias con esta misma regla. Este commit no corre Colorado: se corre en un
  cambio posterior, sin tocar la regla.

Datos y marco
- Eventos: el marco de pipeline.descomposicion, placebo.marco(D, D["hijo_mes"], ks=(1,), base=BASE_LIMPIA): mismo
  hijo mas cercano, misma edad minima del padre y misma base positiva. Bandas: cercano (menos de 1 km), 1 a 2 km y
  control (2 a 5 km). El conglomerado del bootstrap es el pad del hijo (m["clave"]).
- Operador y area del padre: int_pozo_ubicacion, como en pipeline.robustez_operador.
- Dias parados del mes k: dias del mes menos dias efectivos (acotados a los dias del mes, como en
  descomposicion.cargar_ext). Un mes sin fila en fct_produccion es dato faltante, no un mes parado.
- Base de dias parados: media de los meses de BASE (-6 a -4) con dato.
- Exceso de dias del evento: suma de los dias parados de los meses de VENTANA (-1 a 2) menos 4 veces la base.
- Entran los eventos con dato de dias en los cuatro meses de la ventana y en al menos un mes de la base; los demas
  se cuentan y se publica cuantos son.
- Caudal de base: media del petroleo por dia efectivo de los meses de la base con dias producidos.
- Volumen de los dias (m3): caudal de base por la suma, sobre los meses de la ventana, de (dias parados menos base)
  por el indice de control de ese mes, que es la mediana entre los controles del caudal por dia efectivo del mes
  sobre su base. El indice de control descuenta la declinacion que el padre habria tenido igual.
- Caudal posterior: logaritmo natural de la media del petroleo por dia efectivo de los meses de POST (4 a 6) con
  dias producidos, sobre el caudal de base. Sin dias producidos en esos meses el evento no entra en C.

Medidas y reglas de veredicto
A. Brecha de dias de la cuenca: media del exceso de los cercanos menos la de los controles, con IC 95% de percentiles
   por pads hijo (REPS_BOOT repeticiones). La banda de 1 a 2 km se informa igual, sin veredicto. Veredicto:
   "sostiene" si el limite bajo del IC es mayor que cero y la brecha es de al menos UMBRAL_DIAS; "no se sostiene" si
   el limite alto queda por debajo de UMBRAL_DIAS; "no firme" en otro caso. En Vaca Muerta se publica como
   descriptiva (ya mirada); en Colorado decide.
B. Persistencia entre operadores (si es una practica del operador):
   - Brecha del operador en una mitad: media del exceso de sus padres cercanos menos la de sus propios padres de
     control en esa mitad (restar el control propio quita lo que el operador informa distinto siempre).
   - Corte: la mediana del mes del evento entre los cercanos con ventana completa. Primera mitad: eventos hasta ese
     mes inclusive. Segunda mitad: los posteriores.
   - Entran los operadores con al menos MIN_MITAD cercanos y MIN_MITAD controles en cada mitad. Con menos de
     MIN_OPERADORES operadores el veredicto es "no aplicable".
   - Se ordenan por su brecha de la primera mitad (empates por nombre). La mitad de abajo, redondeada hacia arriba,
     es el grupo "bajo"; el resto, el grupo "alto".
   - Estadistico: media de las brechas de la segunda mitad de los operadores del grupo alto menos la del grupo bajo
     (cada operador pesa lo mismo). IC 95% de percentiles por pads hijo sobre los eventos de la segunda mitad, con
     los grupos fijos; una repeticion en la que a un operador le falta cercano o control se descarta y se cuenta.
   - Veredicto: "sostiene" si el limite bajo del IC es mayor que cero y la diferencia es de al menos UMBRAL_DIAS;
     "no se sostiene" si el limite alto queda por debajo de UMBRAL_DIAS; "no firme" en otro caso.
   - Descriptivo, sin veredicto: la tabla por operador y mitad y la correlacion de Spearman entre mitades.
C. Mas dias parados y caudal posterior (asociacion dentro del operador), solo cercanos:
   - Minimos cuadrados del caudal posterior sobre el exceso de dias dividido por 10, con efectos fijos de operador
     (los que tienen menos de MIN_MITAD eventos en la muestra van juntos como "otros"), de grupo de edad del padre
     (6 a 11, 12 a 23, 24 a 47, 48 o mas meses) y de ano del evento, mas la distancia al hijo en km y el logaritmo
     del caudal de base.
   - IC 95% de percentiles por pads hijo. Se publican la pendiente (puntos logaritmicos por cada 10 dias), su IC,
     su error (desvio de las repeticiones) y el efecto minimo detectable (2,8 errores).
   - Veredicto: "mas dias, mejor caudal posterior" si el limite bajo es mayor que cero; "mas dias, peor caudal
     posterior" si el limite alto es menor que cero; "no se ve relacion" en otro caso.
   - Cualquiera sea el veredicto, ningun documento dice que cerrar no protege: un golpe mas fuerte da a la vez mas
     dias parados y peor caudal despues, y eso sesga la pendiente hacia abajo. Se publica el limite alto del IC como
     el mayor beneficio por cada 10 dias compatible con el dato.
D. Tabla por operador (cercanos de al menos MIN_OPERADOR eventos, toda la muestra): brecha de dias contra su propio
   control y volumen de los dias por evento, los dos con IC 95% por pads hijo. Descriptiva. El valor en dinero usa
   decision.valor_indicativo con las grillas de decision (PRECIOS, TASAS, REZAGOS): precio y tasa son entradas de
   quien lo usa, y solo se publica el costo de diferir.
E. Tamano de un ensayo: eventos por rama para ver una diferencia de DELTAS (5, 10 y 20 puntos logaritmicos) en el
   caudal posterior con 80% de potencia y 5% de significacion a dos colas, con el desvio de los residuos de C:
   2 por (1,96 + 0,84) al cuadrado por la varianza sobre delta al cuadrado. Es un piso: no cuenta la correlacion
   dentro del pad.
F. Estado declarado (solo Vaca Muerta, descriptivo): entre los meses de la ventana con cero dias efectivos, la
   parte de cada valor de `estado` de fct_produccion, para cercanos y para controles, y la parte de eventos con al
   menos un mes cerrado entero.

Que cambia en los documentos con cada veredicto
- B sostiene en Vaca Muerta: la pagina dice que los dias que pierde un padre dependen de su operador y que la
  diferencia se mantuvo en el tiempo, con regla informada. Solo si ademas sostiene en Colorado se dice sin esa
  salvedad. B no firme o no se sostiene: la tabla por operador se presenta como diferencias que no se separan del
  ruido de un periodo.
- C no cambia ninguna recomendacion: la pagina dice que dato lo resolveria (un ensayo con el tamano de E, o los
  registros de cierre y la presion del padre de un operador).

Que NO prueba
- Con dato mensual un cierre preventivo y un pozo que queda fuera de servicio por el golpe se ven igual: los dias
  parados no son todos una decision.
- La comparacion entre operadores no es entre iguales: cambian la roca, el fluido, la edad de los pozos y como
  informa cada uno sus dias efectivos (restar el control propio corrige solo lo ultimo).
- El volumen de los dias es volumen diferido valuado al caudal que el pozo traia: no dice que ese petroleo se pierda.

ADAPTACION A COLORADO (2026-11-20, escrita antes de correr el modulo en Colorado, en un commit que solo trae este
texto y ninguna funcion de calculo). La regla de arriba, sus constantes y sus umbrales no cambian. Lo que sigue es lo
que el dato de Colorado obliga a decidir y como se decidio, mirando solo la forma del dato (columnas, nulos, meses sin
fila, censura), sin calcular ninguna cifra de este modulo en Colorado.
- Eventos: las entradas del corte principal de la replicacion, pipeline.replicacion.preparar(con, todos_los_padres=False),
  sobre data/colorado/warehouse.duckdb abierto solo para leer: padres horizontales, hijos de co_hijo con el mes de inicio
  de la fractura de FracFocus, el pad de co_pozo_pad (el conglomerado del bootstrap) y el condado como area. Se corre ese
  corte solo; no se corren otros (todos los padres, por dia producido), para no elegir despues entre varios.
- Operador del padre: el de int_pozo_ubicacion, como dice la regla; en Colorado sale de dim_pozo.operador, que es el
  operador del ultimo mes informado a ECMC, con el nombre como lo escribe ECMC y sin normalizar. Un pozo que cambio de
  manos (compras, fusiones) cuenta con su operador actual en B, en C y en la tabla por operador; no se reconstruye el
  operador del mes del evento.
- Dias: Colorado informa los cierres como filas con cero dias efectivos (los dias del pozo son el maximo entre sus filas
  por formacion y sidetrack) y nunca informa mas dias efectivos que dias del mes. Entre la primera y la ultima fila de un
  pozo horizontal falta el 0,1% de los meses. La regla (un mes sin fila es dato faltante) se aplica tal cual.
- Ventana de datos: la produccion descargada va de 2018-01 a 2024-12. Un evento sin dato en la base o en la ventana
  queda fuera y se cuenta, como en Vaca Muerta.
- Edad del padre: el primer petroleo esta censurado en 2018-01 (el primer mes descargado) para casi la mitad de los
  pozos horizontales, asi que su edad contada desde ahi es una cota inferior. La edad minima de placebo.marco queda como
  en la replicacion (una cota inferior de al menos 6 meses asegura los 6 meses). En C, un padre censurado con menos de 48
  meses contados desde 2018-01 va a un grupo de edad propio (edad desconocida), porque su grupo real no se sabe; con 48 o
  mas su grupo es seguro (48 o mas).
- Intervalos: por pads hijo, como dice la regla (no por bloques de 5 km, que es la lectura de la replicacion), con las
  mismas semillas y repeticiones que en Vaca Muerta.
- F no se corre: la regla la limita a Vaca Muerta (el `estado` de Colorado son codigos de ECMC, otra cosa).
- D y E se calculan igual y se publican como descriptivos. El valor en dinero de D (la tabla de costo de diferir) no se
  publica para Colorado: la pagina da el volumen de los dias por evento.
- Tablas: se escriben en el warehouse de Vaca Muerta (el de Colorado se abre solo para leer) con el nombre de la cuenca,
  como mart_replicacion_colorado: mart_dias_perdidos_colorado, mart_dias_perdidos_colorado_operador,
  mart_dias_perdidos_colorado_mitades y mart_dias_perdidos_colorado_prueba. Se corre con
  `uv run python -m pipeline.dias_perdidos --cuenca colorado` (paso de la corrida solo con --with-colorado).
- La pagina de dias perdidos agrega una seccion de Colorado con los tres veredictos y sus tablas, y cambia lo que dice
  "Que cambia en los documentos con cada veredicto" segun lo que salga.
"""
from __future__ import annotations

import argparse
import math
import warnings

import duckdb
import numpy as np

from pipeline import descomposicion, placebo, replicacion
from pipeline.cuencas import COLORADO, Cuenca, cuenca as _cuenca
from pipeline.costo import SEMILLA, _clusters, _escribir, _remuestra
from pipeline.decision import PRECIOS, REZAGOS, TASAS, valor_indicativo  # grillas y valor tiempo de la regla D
from pipeline.diferido import BBL_M3
from pipeline.ingest import DATA
from pipeline.placebo import BASE_LIMPIA, PAD, REPS_BOOT, _g

BASE = BASE_LIMPIA          # meses de la base de dias parados y del caudal de base
VENTANA = (-1, 2)           # meses del evento en los que se cuentan los dias parados (extremos incluidos)
POST = (4, 6)               # meses del caudal posterior (extremos incluidos)
UMBRAL_DIAS = 5.0           # dias: tamano minimo de la brecha (A) y de la diferencia entre grupos (B)
MIN_OPERADOR = 50           # cercanos para entrar en la tabla por operador (D), como en robustez_operador
MIN_MITAD = 30              # cercanos y controles por mitad para entrar en B; eventos para tener efecto fijo propio en C
MIN_OPERADORES = 4          # operadores que hacen falta para que B se pueda decidir
DELTAS = (0.05, 0.10, 0.20)  # diferencias de caudal posterior (logaritmo) del tamano de ensayo (E)
EDADES = ((6, 11), (12, 23), (24, 47), (48, None))  # grupos de edad del padre en meses (C)
VEREDICTOS_AB = ("sostiene", "no se sostiene", "no firme", "no aplicable")
VEREDICTOS_C = ("mas dias, mejor caudal posterior", "mas dias, peor caudal posterior", "no se ve relacion")

SEMILLA_DIAS = SEMILLA + 60
BANDAS = ("cercano", "intermedio", "control")
COLS_BANDA = [("banda", "varchar"), ("n", "integer"), ("excluidos", "integer"), ("exceso_medio", "double"),
              ("exceso_mediano", "double"), ("brecha", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
              ("vol_medio_m3", "double"), ("brecha_vol_m3", "double"), ("vol_ic_bajo", "double"), ("vol_ic_alto", "double")]
COLS_OPERADOR = [("operador", "varchar"), ("n_cercanos", "integer"), ("n_control", "integer"), ("exceso_cercano", "double"),
                 ("exceso_control", "double"), ("brecha", "double"), ("ic_bajo", "double"), ("ic_alto", "double"),
                 ("brecha_vol_m3", "double"), ("vol_ic_bajo", "double"), ("vol_ic_alto", "double"), ("caudal_base", "double")]
COLS_ESTADO = [("banda", "varchar"), ("estado", "varchar"), ("meses", "integer"), ("parte", "double")]
COLS_MITADES = [("operador", "varchar"), ("grupo", "varchar"), ("n_cercanos_1", "integer"), ("n_control_1", "integer"),
                ("brecha_1", "double"), ("n_cercanos_2", "integer"), ("n_control_2", "integer"), ("brecha_2", "double")]
COLS_PRUEBA = [("prueba", "varchar"), ("estadistico", "varchar"), ("valor", "double"), ("ic_bajo", "double"),
               ("ic_alto", "double"), ("n", "integer"), ("veredicto", "varchar")]


def mart(sufijo: str = "", cuenca: str = "") -> str:
    """Nombre de una tabla del modulo: mart_dias_perdidos[_<cuenca>]<sufijo>; Vaca Muerta va sin cuenca."""
    return "mart_dias_perdidos" + (f"_{cuenca}" if cuenca else "") + sufijo


def _f(x):
    """Un float NaN se escribe como None; lo demas pasa a float."""
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else float(x)


def _media(x) -> float:
    return float(np.mean(x)) if len(x) else math.nan


def _mediana(x) -> float:
    return float(np.median(x)) if len(x) else math.nan


def cargar_dias(con, D: dict) -> dict:
    """D mas dias del mes, operador del padre y estado declarado, con las posiciones de cargar_ext."""
    pos = {int(p): i for i, (p,) in enumerate(con.execute("select pozo_id from int_pozo_ubicacion order by pozo_id").fetchall())}
    filas = con.execute("select x.pozo_id, x.mes, x.dias_mes, coalesce(x.estado, 'sin dato') from fct_produccion x "
                        "join int_pozo_ubicacion u on u.pozo_id = x.pozo_id order by x.pozo_id, x.mes").fetchall()
    out = dict(D)
    forma = D["tasa"].shape
    dmes = np.full(forma, np.nan)
    estados = sorted({r[3] for r in filas})
    cod = np.full(forma, -1, dtype=np.int16)
    if filas:
        fila = np.array([pos[int(r[0])] for r in filas])
        col = placebo._mes_idx([r[1] for r in filas]) + PAD
        ok = (col >= 0) & (col < forma[1])
        idx = {e: k for k, e in enumerate(estados)}
        dmes[fila[ok], col[ok]] = np.array([float(r[2]) for r in filas])[ok]
        cod[fila[ok], col[ok]] = np.array([idx[r[3]] for r in filas], dtype=np.int16)[ok]
    out["dmes"] = dmes
    out["operador"] = np.array([r[0] or "" for r in con.execute("select operador from int_pozo_ubicacion order by pozo_id").fetchall()])
    out["estados"], out["estado_cod"] = estados, cod
    return out


def eventos(D: dict) -> dict:
    """Eventos con ventana completa: exceso de dias parados, volumen de los dias y caudal posterior."""
    m = placebo.marco(D, D["hijo_mes"], ks=(1,), base=BASE)
    parado = (1 - D["tef"]) * D["dmes"]
    cols = m["mes"][:, None] + np.arange(VENTANA[0], VENTANA[1] + 1)[None, :] + PAD
    pv = parado[m["padre"][:, None], cols]
    base_parado = placebo._media({"tasa": parado}, m["padre"], m["mes"], *BASE)
    ok = ~np.isnan(pv).any(1) & ~np.isnan(base_parado)
    exceso = pv.sum(1) - pv.shape[1] * base_parado
    caudal = placebo._media({"tasa": D["tasa_ef"]}, m["padre"], m["mes"], *BASE)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rel = D["tasa_ef"][m["padre"][:, None], cols] / caudal[:, None]
        indice = np.nanmedian(rel[ok & (m["banda"] == 2)], axis=0)
        if np.isnan(indice).any():
            raise ValueError("indice de control sin dato en algun mes de la ventana")
        vol = caudal * ((pv - base_parado[:, None]) * indice[None, :]).sum(1)
        post = placebo._media({"tasa": D["tasa_ef"]}, m["padre"], m["mes"], *POST)
        y = np.where((post > 0) & (caudal > 0), np.log(post / caudal), np.nan)
    e = {k: m[k][ok] for k in ("padre", "mes", "km", "banda", "clave", "edad")}
    e.update(operador=D["operador"][e["padre"]], exceso=exceso[ok], pv=pv[ok], caudal=caudal[ok], vol=vol[ok], y=y[ok],
             anio=2000 + e["mes"] // 12)
    e["excluidos"] = tuple(int(((m["banda"] == b) & ~ok).sum()) for b in range(3))
    # Colorado: con el primer petroleo censurado la edad es una cota inferior; por debajo del ultimo grupo, el grupo no se sabe
    censura = D.get("censurado")
    e["edad_desconocida"] = (censura[e["padre"]] & (e["edad"] < EDADES[-1][0]) if censura is not None
                             else np.zeros(len(e["padre"]), dtype=bool))
    e["indice_control"] = tuple(float(v) for v in indice)
    return e


def brecha_medias_ic(vals, a, b, clave, reps: int = REPS_BOOT, semilla: int = SEMILLA_DIAS) -> dict:
    """Media de vals en a menos media en b, con IC 95% de percentiles por conglomerado (medias, no medianas)."""
    k = (a | b) & ~np.isnan(vals)
    v, ka, kb, c = vals[k], a[k], b[k], clave[k]
    n_a, n_b = int(ka.sum()), int(kb.sum())
    media_a, media_b = _media(v[ka]), _media(v[kb])
    out = {"n_a": n_a, "n_b": n_b, "media_a": media_a, "media_b": media_b, "brecha": media_a - media_b,
           "ic_bajo": math.nan, "ic_alto": math.nan}
    if n_a < 5 or n_b < 5:
        return out
    grupos, rng, rep = _clusters(c), np.random.default_rng(semilla), []
    for _ in range(reps):
        i = _remuestra(rng, grupos)
        ra, rb = ka[i], kb[i]
        if ra.any() and rb.any():
            rep.append(v[i][ra].mean() - v[i][rb].mean())
    if rep:
        out["ic_bajo"], out["ic_alto"] = (float(q) for q in np.percentile(rep, [2.5, 97.5]))
    return out


def veredicto_umbral(valor, ic_bajo, ic_alto, umbral: float = UMBRAL_DIAS) -> str:
    if any(x is None or math.isnan(x) for x in (valor, ic_bajo, ic_alto, umbral)):
        return "no aplicable"
    if ic_bajo > 0 and valor >= umbral:
        return "sostiene"
    return "no se sostiene" if ic_alto < umbral else "no firme"


def tabla_bandas(e: dict, reps: int = REPS_BOOT) -> list[tuple]:
    """Tres filas (cercano, intermedio, control): exceso de dias y volumen de los dias, la brecha contra el control con IC."""
    filas, ctrl = [], e["banda"] == 2
    for b, nombre in enumerate(BANDAS):
        en = e["banda"] == b
        fila = [nombre, int(en.sum()), e["excluidos"][b], _media(e["exceso"][en]), _mediana(e["exceso"][en])]
        if b < 2:
            d = brecha_medias_ic(e["exceso"], en, ctrl, e["clave"], reps, SEMILLA_DIAS + b)
            v = brecha_medias_ic(e["vol"], en, ctrl, e["clave"], reps, SEMILLA_DIAS + 10 + b)
            fila += [d["brecha"], d["ic_bajo"], d["ic_alto"], v["media_a"], v["brecha"], v["ic_bajo"], v["ic_alto"]]
        else:
            fila += [None, None, None, _media(e["vol"][en & ~np.isnan(e["vol"])]), None, None, None]
        filas.append(tuple(x if isinstance(x, (str, int)) else _f(x) for x in fila))
    return filas


def tabla_operador(e: dict, reps: int = REPS_BOOT, minimo: int = MIN_OPERADOR) -> list[tuple]:
    """Una fila por operador con al menos `minimo` cercanos: su brecha de dias y de volumen contra su propio control."""
    ops = sorted(o for o in set(e["operador"].tolist()) if o and int(((e["operador"] == o) & (e["banda"] == 0)).sum()) >= minimo)
    filas = []
    for i, o in enumerate(ops):
        a, b = (e["operador"] == o) & (e["banda"] == 0), (e["operador"] == o) & (e["banda"] == 2)
        d = brecha_medias_ic(e["exceso"], a, b, e["clave"], reps, SEMILLA_DIAS + 100 + i)
        v = brecha_medias_ic(e["vol"], a, b, e["clave"], reps, SEMILLA_DIAS + 200 + i)
        filas.append((o, int(a.sum()), int(b.sum()), _f(d["media_a"]), _f(d["media_b"]), _f(d["brecha"]), _f(d["ic_bajo"]),
                      _f(d["ic_alto"]), _f(v["brecha"]), _f(v["ic_bajo"]), _f(v["ic_alto"]), _f(np.nanmean(e["caudal"][a]))))
    return sorted(filas, key=lambda f: (-(f[5] if f[5] is not None else -math.inf), f[0]))


def tabla_estado(D: dict, e: dict) -> tuple[list[tuple], dict]:
    """Estado declarado de los meses de la ventana con cero dias efectivos, para cercanos y controles."""
    if "estado_cod" not in D:
        return [], {}
    filas, cierre = [], {}
    for b in (0, 2):
        sel = e["banda"] == b
        cols = e["mes"][sel, None] + np.arange(VENTANA[0], VENTANA[1] + 1)[None, :] + PAD
        padre = e["padre"][sel, None]
        cerrado = D["tef"][padre, cols] == 0
        cod = D["estado_cod"][padre, cols][cerrado]
        cuenta = np.bincount(cod[cod >= 0], minlength=len(D["estados"]))
        total = int(cuenta.sum())
        filas += sorted(((BANDAS[b], D["estados"][k], int(c), c / total) for k, c in enumerate(cuenta) if c),
                        key=lambda f: (-f[2], f[1]))
        cierre[BANDAS[b]] = float(cerrado.any(1).mean()) if sel.any() else math.nan
    return filas, cierre


def _brechas(e: dict, ops: list[str], sel, b0, b2) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Por operador: cercanos, controles y media del exceso de cercanos menos la de controles (NaN con un lado vacio)."""
    n0 = np.array([int((sel & b0 & (e["operador"] == o)).sum()) for o in ops])
    n2 = np.array([int((sel & b2 & (e["operador"] == o)).sum()) for o in ops])
    br = np.array([_media(e["exceso"][sel & b0 & (e["operador"] == o)]) - _media(e["exceso"][sel & b2 & (e["operador"] == o)])
                   for o in ops])
    return n0, n2, br


def persistencia(e: dict, reps: int = REPS_BOOT, min_mitad: int = MIN_MITAD, min_operadores: int = MIN_OPERADORES) -> dict:
    """Regla B: la diferencia entre operadores de la primera mitad se mantiene en la segunda (grupos fijos, IC por pads)."""
    b0, b2 = e["banda"] == 0, e["banda"] == 2
    nan = math.nan
    corte = int(np.floor(np.median(e["mes"][b0]))) if b0.any() else 0
    h1, h2 = e["mes"] <= corte, e["mes"] > corte
    todos = sorted(o for o in set(e["operador"].tolist()) if o and int((b0 & (e["operador"] == o)).sum()) >= min_mitad)
    n01, n21, br1 = _brechas(e, todos, h1, b0, b2)
    n02, n22, br2 = _brechas(e, todos, h2, b0, b2)
    elegible = (n01 >= min_mitad) & (n21 >= min_mitad) & (n02 >= min_mitad) & (n22 >= min_mitad)
    nombres = [o for o, k in zip(todos, elegible) if k]
    out = {"corte": corte, "n_operadores": len(nombres), "valor": nan, "ic_bajo": nan, "ic_alto": nan,
           "veredicto": "no aplicable", "spearman": nan, "descartadas": 0}
    grupo = {o: "" for o in todos}
    if len(nombres) >= min_operadores:
        orden = sorted(nombres, key=lambda o: (br1[todos.index(o)], o))
        bajo = set(orden[:math.ceil(len(orden) / 2)])
        grupo.update({o: "bajo" if o in bajo else "alto" for o in orden})
        ix = [todos.index(o) for o in nombres]
        es_alto = np.array([grupo[o] == "alto" for o in nombres])
        out["valor"] = float(br2[ix][es_alto].mean() - br2[ix][~es_alto].mean())
        r1, r2 = (np.argsort(np.argsort(x[ix])) for x in (br1, br2))
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out["spearman"] = float(np.corrcoef(r1, r2)[0, 1])
        k = h2 & (b0 | b2) & np.isin(e["operador"], nombres)
        oi, ban, x, grupos = (np.searchsorted(nombres, e["operador"][k]), e["banda"][k], e["exceso"][k], _clusters(e["clave"][k]))
        rng, rep = np.random.default_rng(SEMILLA_DIAS + 300), []
        for _ in range(reps):
            i = _remuestra(rng, grupos)
            c0, c2 = (np.bincount(oi[i][ban[i] == b], minlength=len(nombres)) for b in (0, 2))
            if (c0 == 0).any() or (c2 == 0).any():
                out["descartadas"] += 1
                continue
            s0, s2 = (np.bincount(oi[i][ban[i] == b], weights=x[i][ban[i] == b], minlength=len(nombres)) for b in (0, 2))
            br = s0 / c0 - s2 / c2
            rep.append(br[es_alto].mean() - br[~es_alto].mean())
        if rep:
            out["ic_bajo"], out["ic_alto"] = (float(q) for q in np.percentile(rep, [2.5, 97.5]))
        out["veredicto"] = veredicto_umbral(out["valor"], out["ic_bajo"], out["ic_alto"])
    out["filas"] = [(o, grupo[o], int(n01[j]), int(n21[j]), _f(br1[j]), int(n02[j]), int(n22[j]), _f(br2[j]))
                    for j, o in enumerate(todos)]
    return out


def _dummies(valores) -> list[np.ndarray]:
    cats = sorted(set(valores.tolist()))
    return [(valores == c).astype(float) for c in cats[1:]]


def pendiente(e: dict, reps: int = REPS_BOOT, min_mitad: int = MIN_MITAD) -> dict:
    """Regla C: caudal posterior (logaritmo) sobre exceso de dias / 10 en los cercanos, con efectos fijos y IC por pads."""
    s = (e["banda"] == 0) & np.isfinite(e["y"]) & (e["caudal"] > 0)
    op = e["operador"][s]
    cuenta = {o: int((op == o).sum()) for o in set(op.tolist())}
    op = np.array([o if cuenta[o] >= min_mitad else "otros" for o in op])
    ed, edad = e["edad"][s], np.full(int(s.sum()), -1)
    for g, (lo, hi) in enumerate(EDADES):
        edad[(ed >= lo) & (ed <= hi if hi is not None else True)] = g
    if "edad_desconocida" in e:
        edad[e["edad_desconocida"][s]] = len(EDADES)  # grupo propio: edad desconocida (adaptacion a Colorado)
    cols = [np.ones(int(s.sum())), e["exceso"][s] / 10, e["km"][s], np.log(e["caudal"][s])]
    X = np.column_stack(cols + _dummies(op) + _dummies(edad) + _dummies(e["anio"][s]))
    y, n = e["y"][s], int(s.sum())
    out = {k: math.nan for k in ("pendiente", "ic_bajo", "ic_alto", "error", "mde", "sigma")}
    # Sin muestra para estimar no hay pendiente ni veredicto. La regla no preve el caso; se informa como en B.
    out.update(n=n, veredicto="no aplicable")
    if n < X.shape[1] + 10:
        return out
    beta, _, rango, _ = np.linalg.lstsq(X, y, rcond=None)
    out["pendiente"] = float(beta[1])
    out["sigma"] = float(math.sqrt(((y - X @ beta) ** 2).sum() / (n - rango)))
    grupos, rng, rep = _clusters(e["clave"][s]), np.random.default_rng(SEMILLA_DIAS + 400), []
    for _ in range(reps):
        i = _remuestra(rng, grupos)
        rep.append(np.linalg.lstsq(X[i], y[i], rcond=None)[0][1])
    out["ic_bajo"], out["ic_alto"] = (float(q) for q in np.percentile(rep, [2.5, 97.5]))
    out["error"] = float(np.std(rep, ddof=1))
    out["mde"] = 2.8 * out["error"]
    if out["ic_bajo"] > 0:
        out["veredicto"] = "mas dias, mejor caudal posterior"
    elif out["ic_alto"] < 0:
        out["veredicto"] = "mas dias, peor caudal posterior"
    else:
        out["veredicto"] = "no se ve relacion"
    return out


def tamano_ensayo(sigma: float, deltas=DELTAS) -> list[tuple[float, int]]:
    """Eventos por rama para ver cada delta con 80% de potencia y 5% a dos colas (piso: sin correlacion dentro del pad)."""
    if sigma is None or math.isnan(sigma):
        return []
    return [(d, math.ceil(2 * (1.96 + 0.84) ** 2 * sigma ** 2 / d ** 2)) for d in deltas]


def calcular(D: dict, reps: int = REPS_BOOT) -> dict[str, list[tuple]]:
    """Todas las tablas del modulo a partir de las matrices cargadas."""
    e = eventos(D)
    a = brecha_medias_ic(e["exceso"], e["banda"] == 0, e["banda"] == 2, e["clave"], reps, SEMILLA_DIAS)
    p, c = persistencia(e, reps), pendiente(e, reps)
    estado, cierre = tabla_estado(D, e)
    n0 = int((e["banda"] == 0).sum())
    nb = p["n_operadores"]
    ult = int(((e["banda"] == 0) & (e["mes"] > e["mes"].max() - 12)).sum()) if len(e["mes"]) else 0
    prueba = [("A", "brecha_dias", a["brecha"], a["ic_bajo"], a["ic_alto"], n0,
               veredicto_umbral(a["brecha"], a["ic_bajo"], a["ic_alto"])),
              ("A", "eventos_cercanos_12m", ult, None, None, None, None),
              ("B", "diferencia_dias", p["valor"], p["ic_bajo"], p["ic_alto"], nb, p["veredicto"]),
              ("B", "spearman", p["spearman"], None, None, nb, None),
              ("B", "corte_mes", p["corte"], None, None, None, None),
              ("B", "repeticiones_descartadas", p["descartadas"], None, None, reps, None),
              ("C", "pendiente", c["pendiente"], c["ic_bajo"], c["ic_alto"], c["n"], c["veredicto"])]
    prueba += [("C", k, c[k], None, None, c["n"], None) for k in ("error", "mde", "sigma")]
    prueba += [("E", f"n_por_rama_{round(d * 100)}", n, None, None, None, None) for d, n in tamano_ensayo(c["sigma"])]
    prueba += [("F", f"parte_con_mes_cerrado_{k}", v, None, None, None, None) for k, v in cierre.items()]
    prueba = [tuple(_f(x) if k in (2, 3, 4) else x for k, x in enumerate(f)) for f in prueba]
    return {"mart_dias_perdidos": tabla_bandas(e, reps), "mart_dias_perdidos_operador": tabla_operador(e, reps),
            "mart_dias_perdidos_mitades": p["filas"], "mart_dias_perdidos_estado": [(b, s, k, _f(x)) for b, s, k, x in estado],
            "mart_dias_perdidos_prueba": prueba}


ETQ_BANDA = {"cercano": "Cercano (menos de 1 km)", "intermedio": "1 a 2 km", "control": "Control (2 a 5 km)"}
FRASE_A = {
    "sostiene": f"Los padres cercanos pierden más días que los controles, y la brecha pasa el umbral de {_g(UMBRAL_DIAS)} días.",
    "no se sostiene": f"La brecha de días queda por debajo del umbral de {_g(UMBRAL_DIAS)} días.",
    "no firme": f"El intervalo no alcanza para decidir si la brecha de días pasa el umbral de {_g(UMBRAL_DIAS)} días.",
    "no aplicable": "No hay eventos suficientes para medir la brecha de días.",
}
FRASE_B = {
    "sostiene": "Los días que pierde un padre dependen de su operador, y la diferencia se mantuvo en el tiempo.",
    "no se sostiene": "Las diferencias entre operadores no se separan del ruido de un período: las de la primera mitad no se repiten en la segunda.",
    "no firme": "Las diferencias entre operadores no se separan del ruido de un período: el intervalo no alcanza para decidir.",
    "no aplicable": f"No hay operadores suficientes para decidir: hacen falta {MIN_OPERADORES} con al menos {MIN_MITAD} cercanos y "
                    f"{MIN_MITAD} controles en cada mitad.",
}
FRASE_C = {  # veredicto de C: (como se escribe en la pagina, frase)
    "mas dias, mejor caudal posterior": ("más días, mejor caudal posterior", "Dentro de un mismo operador, más días parados van con mejor caudal después."),
    "mas dias, peor caudal posterior": ("más días, peor caudal posterior", "Dentro de un mismo operador, más días parados van con peor caudal después."),
    "no se ve relacion": ("no se ve relación", "Dentro de un mismo operador no se ve relación entre los días parados y el caudal posterior."),
}


SALVEDAD_B = "La regla es informada (se fijó conociendo la dispersión entre operadores de toda la muestra)"


def cola_b(v: str, v_co: str | None) -> str:
    """Lo que sigue a B de Vaca Muerta cuando sostiene: el veredicto de Colorado decide la salvedad ("Que cambia en los documentos")."""
    if v != "sostiene":
        return ""
    if v_co is None:
        return f" {SALVEDAD_B} y falta confirmarla en Colorado."
    if v_co == "sostiene":
        return " También se sostiene en Colorado, donde la prueba es confirmatoria."
    return f" {SALVEDAD_B}, y en Colorado, donde la prueba es confirmatoria, no se confirmó (veredicto: {v_co})."


def _ic(lo, hi, dec: int = 1) -> str:
    return f"{_g(lo, dec)} a {_g(hi, dec)}"


def _mes(corte: int) -> str:
    return f"{2000 + corte // 12}-{corte % 12 + 1:02d}"


def _pc(x):
    return None if x is None else 100 * x


def marts(con, cuenca: str = "") -> dict | None:
    """Las tablas del modulo de una cuenca (None si no se corrio): bandas, operadores, mitades y pruebas."""
    if not con.execute("select count(*) from information_schema.tables where table_name = ?", [mart("_prueba", cuenca)]).fetchone()[0]:
        return None
    return {"ban": {r[0]: r for r in con.execute(f"select * from {mart('', cuenca)}").fetchall()},
            "ops": con.execute(f"select * from {mart('_operador', cuenca)} order by brecha desc nulls last, operador").fetchall(),
            "mit": con.execute(f"select * from {mart('_mitades', cuenca)} order by operador").fetchall(),
            "p": {(r[0], r[1]): r for r in con.execute(f"select * from {mart('_prueba', cuenca)}").fetchall()}}


def _tabla_bandas(ban: dict) -> list[str]:
    L = ["| Banda | Eventos | Sin ventana completa | Exceso medio (días) | Exceso mediano (días) | Brecha contra el control (días) | IC 95% | "
         "Volumen de la brecha (m3 por evento) | IC 95% |", "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |"]
    for k in BANDAS:
        r = ban[k]
        gap = ["", "", "", ""] if r[5] is None else [_g(r[5], 1), _ic(r[6], r[7]), _g(r[9]), _ic(r[10], r[11], 0)]
        L.append(f"| {ETQ_BANDA[k]} | {_g(r[1])} | {_g(r[2])} | {_g(r[3], 1)} | {_g(r[4], 1)} | {gap[0]} | {gap[1]} | {gap[2]} | {gap[3]} |")
    return L


def _tabla_operador(ops: list) -> list[str]:
    return (["| Operador | Cercanos | Controles | Brecha (días) | IC 95% | Volumen de la brecha (m3 por evento) | IC 95% | Caudal de base (m3/d) |",
             "| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |"]
            + [f"| {r[0]} | {_g(r[1])} | {_g(r[2])} | {_g(r[5], 1)} | {_ic(r[6], r[7])} | {_g(r[8])} | {_ic(r[9], r[10], 0)} | {_g(r[11], 1)} |"
               for r in ops])


def _tabla_mitades(mit: list) -> list[str]:
    return (["| Operador | Grupo | Cercanos, 1.ª mitad | Controles, 1.ª mitad | Brecha, 1.ª mitad (días) | Cercanos, 2.ª mitad | Controles, 2.ª mitad | "
             "Brecha, 2.ª mitad (días) |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
            + [f"| {r[0]} | {r[1] or 'no entra'} | {_g(r[2])} | {_g(r[3])} | {_g(r[4], 1)} | {_g(r[5])} | {_g(r[6])} | {_g(r[7], 1)} |" for r in mit])


def _linea_c(c, etiqueta: str, en: str = "") -> str:
    """Viñeta de la prueba C; `en` antepone la cuenca a la pendiente ("En Colorado la pendiente es de")."""
    if c[6] == "no aplicable":
        return (f"- {etiqueta}: no aplicable. Con {_g(c[5])} eventos cercanos no alcanza para estimar la pendiente con sus efectos fijos, "
                "así que no hay veredicto.")
    pend = f"{en} la pendiente es de {_g(_pc(c[2]), 1)}" if en else f"Pendiente: {_g(_pc(c[2]), 1)}"
    return (f"- {etiqueta}: {FRASE_C[c[6]][1]} {pend} puntos logarítmicos por cada 10 días (IC 95% {_ic(_pc(c[3]), _pc(c[4]))}; "
            f"{_g(c[5])} eventos; veredicto: {FRASE_C[c[6]][0]}). El mayor beneficio compatible con el dato es {_g(_pc(c[4]), 1)} puntos por "
            "cada 10 días. No prueba que cerrar no proteja: un golpe más fuerte da a la vez más días parados y peor caudal después, y eso "
            "sesga la pendiente hacia abajo.")


def _seccion_colorado(co: dict, vm_a, vm_b: str) -> list[str]:
    """Seccion de Colorado: los tres veredictos confirmatorios, sus tablas y lo que cambia en la pagina con cada uno."""
    p, ban = co["p"], co["ban"]
    a, b, c, cer = p[("A", "brecha_dias")], p[("B", "diferencia_dias")], p[("C", "pendiente")], ban["cercano"]
    L = ["", "## Colorado: la prueba confirmatoria", "",
         "En Colorado (cuenca DJ) no se había mirado nada de este módulo antes de fijar la regla, así que ahí la brecha de días (A), la "
         "prueba B y la prueba C son confirmatorias. Se corrió con la misma regla, sin cambiarla, sobre el corte principal de la "
         "[replicación en Colorado](replicacion.md): padres horizontales, hijos con la fecha de fractura de FracFocus y producción de "
         "2018-01 a 2024-12. Lo que el dato de Colorado obligó a decidir se escribió antes de correr, en un commit propio, al pie del "
         "encabezado de `pipeline/dias_perdidos.py`: el operador es el del último mes informado a ECMC, con el nombre que usa ECMC (un pozo "
         f"que cambió de manos cuenta con su operador actual); en C, un padre con el primer petróleo censurado en 2018-01 y menos de "
         f"{EDADES[-1][0]} meses contados desde ahí va a un grupo de edad propio; el estado declarado no se mira; los IC son por pads hijo, "
         "como en Vaca Muerta.", "",
         f"- Brecha de días (A, confirmatoria): {FRASE_A[a[6]]} En Colorado la brecha es de {_g(a[2], 1)} días (IC 95% {_ic(a[3], a[4])}; "
         f"{_g(a[5])} eventos cercanos; veredicto: {a[6]}), contra {_g(vm_a, 1)} días en Vaca Muerta.",
         f"- Prueba B (confirmatoria): {FRASE_B[b[6]]} En Colorado la diferencia entre el grupo alto y el bajo en la segunda mitad es de "
         f"{_g(b[2], 1)} días (IC 95% {_ic(b[3], b[4])}; {_g(b[5])} operadores; veredicto: {b[6]}).",
         _linea_c(c, "Prueba C (confirmatoria)", "En Colorado"),
         f"- En Colorado los días de más equivalen a {_g(cer[9])} m3 de petróleo por evento cercano (IC 95% {_ic(cer[10], cer[11], 0)}), "
         "valuados al caudal que el pozo traía. Es volumen diferido: el dato no dice que ese petróleo se pierda.", "", *_tabla_bandas(ban), "",
         f"Por operador del padre, con al menos {MIN_OPERADOR} eventos cercanos y la brecha contra sus propios controles (descriptiva)."
         + ("" if b[6] == "sostiene" else f" Con la prueba B {b[6]} en Colorado, estas diferencias no se separan del ruido de un período."),
         "", *_tabla_operador(co["ops"]), "",
         f"Prueba B en Colorado: corte en {_mes(int(p[('B', 'corte_mes')][2]))}, la mediana del mes de los eventos cercanos; entran los "
         f"operadores con al menos {MIN_MITAD} cercanos y {MIN_MITAD} controles en cada mitad.", "", *_tabla_mitades(co["mit"]), "",
         f"Correlación de Spearman entre las dos mitades: {_g(p[('B', 'spearman')][2], 2)} (descriptiva). Repeticiones descartadas porque a un "
         f"operador le faltó un lado: {_g(p[('B', 'repeticiones_descartadas')][2])} de {_g(p[('B', 'repeticiones_descartadas')][5])}."]
    ens = [p.get(("E", f"n_por_rama_{round(100 * d)}")) for d in DELTAS]
    if all(ens):
        L += ["", "Tamaño de un ensayo en Colorado, con el desvío de sus residuos de C "
              f"({_g(p[('C', 'sigma')][2], 2)}): para ver " + _lista(_g(100 * d) for d in DELTAS) + " puntos logarítmicos de caudal posterior "
              "entre dos formas de cerrar se necesitan " + _lista(_g(e[2]) for e in ens) + " eventos por rama, en ese orden (un piso, igual que arriba)."]
    if vm_b == "sostiene":
        cambia_b = ("se sostiene en las dos cuencas, así que la lectura dice sin salvedad que los días que pierde un padre dependen de su "
                    "operador." if b[6] == "sostiene" else
                    f"{b[6]} en Colorado, así que la lectura de Vaca Muerta conserva la salvedad de regla informada: allí la diferencia "
                    "entre operadores se mantuvo en el tiempo, pero no se confirmó en otra cuenca.")
    else:
        cambia_b = (f"{vm_b} en Vaca Muerta y {b[6]} en Colorado: la tabla por operador no se lee como una práctica del operador."
                    if b[6] != "sostiene" else
                    f"{vm_b} en Vaca Muerta y sostiene en Colorado: la tabla por operador de Vaca Muerta no se lee como una práctica del operador.")
    cambia_a = ("la brecha de días aparece también en otra cuenca, con otro regulador y otra convención de reporte." if a[6] == "sostiene"
                else f"la brecha de días de Vaca Muerta no se confirma en Colorado (veredicto: {a[6]}).")
    L += ["", "Qué cambia con Colorado, según la regla:", "", f"- A: {cambia_a}", f"- B: {cambia_b}",
          "- C: no cambia ninguna recomendación en ninguna de las dos cuencas. Lo que la resolvería es un ensayo con el tamaño de arriba, "
          "o los registros de cierre y la presión del padre de un operador."]
    return L


def _lista(xs) -> str:
    xs = list(xs)
    return ", ".join(xs[:-1]) + " y " + xs[-1] if len(xs) > 1 else "".join(xs)


def pagina_dias_perdidos(con) -> str:
    """Pagina de la wiki a partir de los marts (solo lee)."""
    ban = {r[0]: r for r in con.execute("select * from mart_dias_perdidos").fetchall()}
    ops = con.execute("select * from mart_dias_perdidos_operador order by brecha desc nulls last, operador").fetchall()
    mit = con.execute("select * from mart_dias_perdidos_mitades order by operador").fetchall()
    p = {(r[0], r[1]): r for r in con.execute("select * from mart_dias_perdidos_prueba").fetchall()}
    est = con.execute("select * from mart_dias_perdidos_estado order by banda, meses desc, estado").fetchall()
    a, b, c, cer = p[("A", "brecha_dias")], p[("B", "diferencia_dias")], p[("C", "pendiente")], ban["cercano"]
    n12, corte = int(p[("A", "eventos_cercanos_12m")][2]), int(p[("B", "corte_mes")][2])
    pc = _pc
    co = marts(con, COLORADO.id)
    pco = co["p"] if co else {}
    v_co = {k: pco[(k, e)][6] for k, e in (("A", "brecha_dias"), ("B", "diferencia_dias"), ("C", "pendiente"))} if co else {}
    L = ["# Días que pierde un padre cuando fracturan a un hijo", "",
         "Alrededor de la fractura de un hijo, un pozo padre pasa días sin producir: lo cierran para protegerlo o queda fuera de servicio por "
         f"el golpe. Esta página cuenta esos días (meses {VENTANA[0]} a {VENTANA[1]} contra la base de los meses {BASE[0]} a {BASE[1]}), los abre "
         "por operador del padre y prueba dos cosas: si la diferencia entre operadores se mantiene en el tiempo y si más días parados se "
         "asocian con mejor caudal después. La regla se fijó antes de calcular; más abajo dice qué se había mirado antes."
         + (" En Colorado la misma regla se corrió después, como prueba confirmatoria (sección al final)." if co else ""), "",
         "## Lectura", "",
         f"- Un padre a menos de 1 km pierde {_g(a[2], 1)} días más que un control (IC 95% {_ic(a[3], a[4])}; {_g(a[5])} eventos cercanos). "
         "Es una medida descriptiva: se había mirado antes de fijar la regla.",
         f"- {'Prueba B' if b[6] == v_co.get('B') == 'sostiene' else 'Prueba B (regla informada)'}: {FRASE_B[b[6]]} Diferencia entre el grupo "
         f"alto y el bajo en la segunda mitad: {_g(b[2], 1)} días (IC 95% {_ic(b[3], b[4])}; {_g(b[5])} operadores; veredicto: {b[6]})."
         + cola_b(b[6], v_co.get("B")),
         _linea_c(c, "Prueba C (regla informada)"),
         f"- Los días de más equivalen a {_g(cer[9])} m3 de petróleo por evento cercano (IC 95% {_ic(cer[10], cer[11], 0)}), valuados al caudal "
         "que el pozo traía. Es volumen diferido: el dato no dice que ese petróleo se pierda."]
    if co:
        aco = pco[("A", "brecha_dias")]
        L.append(f"- Colorado, prueba confirmatoria con la misma regla: brecha de días, {v_co['A']} ({_g(aco[2], 1)} días, IC 95% "
                 f"{_ic(aco[3], aco[4])}); prueba B, {v_co['B']}; prueba C, {FRASE_C[v_co['C']][0] if v_co['C'] in FRASE_C else v_co['C']}. "
                 "El detalle está en la sección de Colorado, al final.")
    L += ["", "## Cuántos días, por distancia al hijo", "", *_tabla_bandas(ban)]
    L += ["", "## Por operador del padre", "",
          f"Operadores con al menos {MIN_OPERADOR} eventos cercanos. La brecha de cada uno es contra sus propios controles, para quitar lo que "
          "cada operador informa distinto siempre. Es descriptiva: las medias por operador, sin intervalos, se habían mirado antes de fijar la regla.", "",
          *_tabla_operador(ops)]
    L += ["", "## Prueba B: si la diferencia entre operadores se mantiene en el tiempo", "",
          f"Corte: {_mes(corte)}, la mediana del mes de los eventos cercanos. Los operadores se ordenan por su brecha de la "
          "primera mitad (grupo bajo y grupo alto) y se mira si el grupo alto sigue por encima en la segunda. Entran los que tienen al menos "
          f"{MIN_MITAD} cercanos y {MIN_MITAD} controles en cada mitad.", "", *_tabla_mitades(mit)]
    L += ["", f"Veredicto: {b[6]}. Correlación de Spearman entre las dos mitades: {_g(p[('B', 'spearman')][2], 2)} (descriptiva). "
          f"Repeticiones descartadas porque a un operador le faltó un lado: {_g(p[('B', 'repeticiones_descartadas')][2])} de "
          f"{_g(p[('B', 'repeticiones_descartadas')][5])}.", "",
          "## Prueba C: si más días parados van con mejor caudal después", "",
          f"Mínimos cuadrados del logaritmo del caudal por día efectivo de los meses {POST[0]} a {POST[1]} sobre el de la base, contra el exceso de "
          "días dividido por 10, solo en los cercanos, con efectos fijos de operador, de grupo de edad del padre y de año, más la distancia al hijo "
          "y el logaritmo del caudal de base. " + (
              "No hay eventos suficientes para estimarla, así que no hay error ni efecto mínimo detectable." if c[6] == "no aplicable" else
              f"Error de la pendiente: {_g(pc(p[('C', 'error')][2]), 1)} puntos; efecto mínimo detectable: "
              f"{_g(pc(p[('C', 'mde')][2]), 1)} puntos por cada 10 días. Esta prueba no cambia ninguna recomendación. Lo que la resolvería es "
              "un ensayo con el tamaño de abajo, o los registros de cierre y la presión del padre de un operador."), "",
          "## Cuánto vale", "",
          f"El volumen de la brecha por evento, por los {_g(n12)} eventos cercanos de los últimos 12 meses con ventana completa, da "
          f"{_g(cer[9] * n12)} m3 por año ({_g(cer[9] * n12 * BBL_M3)} barriles). En promedio, cada día de la brecha son "
          f"{_g(cer[9] / a[2], 1) if a[2] else 'n/d'} m3 por evento. La tabla da el costo de diferir ese volumen (el valor tiempo de cobrarlo más "
          "tarde), en millones de dólares por año, según cuánto tarde en recuperarse. Precio y tasa son entradas de quien lo usa, no resultados.", "",
          "| Precio (USD/bbl) | Tasa anual | " + " | ".join(f"Se recupera en {z} meses" for z in REZAGOS) + " |", "| ---: | ---: |" + " ---: |" * len(REZAGOS)]
    for precio in PRECIOS:
        for tasa in TASAS:
            celdas = [_g(valor_indicativo(cer[9] * n12, precio, tasa, z)["costo_de_diferir"] / 1e6, 1) for z in REZAGOS]
            L.append(f"| {precio} | {_g(100 * tasa)}% | " + " | ".join(celdas) + " |")
    ens = [p.get(("E", f"n_por_rama_{round(100 * d)}")) for d in DELTAS]
    if all(ens):
        L += ["", "## Tamaño de un ensayo", "",
              "Para ver una diferencia de caudal posterior de " + _lista(_g(100 * d) for d in DELTAS) + " puntos logarítmicos entre dos formas de "
              f"cerrar (80% de potencia, 5% a dos colas, desvío de los residuos {_g(p[('C', 'sigma')][2], 2)}) hacen falta "
              + _lista(_g(e[2]) for e in ens) + " eventos por rama, en ese orden. Es un piso: no cuenta la correlación dentro del pad."]
    if est:
        L += ["", "## Estado declarado de los meses cerrados", "",
              f"El {_g(pc(p[('F', 'parte_con_mes_cerrado_cercano')][2]), 1)}% de los eventos cercanos tiene al menos un mes de la ventana con cero días "
              f"efectivos, contra el {_g(pc(p[('F', 'parte_con_mes_cerrado_control')][2]), 1)}% de los controles. El estado que declara el operador en "
              "esos meses (estados con al menos 1% de los meses):", "",
              "| Banda | Estado declarado | Meses | Parte |", "| --- | --- | ---: | ---: |"]
        L += [f"| {ETQ_BANDA[r[0]]} | {r[1]} | {_g(r[2])} | {_g(100 * r[3], 1)}% |" for r in est if r[3] >= 0.01]
    if co:
        L += _seccion_colorado(co, a[2], b[6])
    L += ["", "## Regla fijada antes de correr", "",
          "- La regla está en el encabezado de `pipeline/dias_perdidos.py`, en un commit anterior a cualquier cálculo de este módulo.",
          f"- Brecha de la cuenca y prueba B: sostiene si el IC 95% queda por encima de cero y el valor es de al menos {_g(UMBRAL_DIAS)} días; no se "
          f"sostiene si el límite alto queda por debajo de {_g(UMBRAL_DIAS)} días; no firme en otro caso.",
          "- Prueba C: el veredicto sale del signo del IC 95% de la pendiente.",
          "- Los IC son de percentiles, por pads hijo, y comparan medias: unos pocos cierres largos pesan en el volumen y la mediana no los ve.",
          "- Qué se había mirado antes en Vaca Muerta: la descomposición ya publicada, y una consulta exploratoria sin intervalos con las medias "
          "del exceso por banda, por operador y por distancia, y el caudal posterior por cuartil de exceso. Por eso la brecha y la tabla por "
          "operador son descriptivas, y las pruebas B y C son de regla informada.",
          ("- Colorado: se corrió después, con la misma regla y sin cambiarla; ahí las tres medidas son confirmatorias. Lo que el dato de "
           "Colorado obligó a decidir está al pie del encabezado, en un commit anterior a la corrida de Colorado." if co else
           "- Colorado: este módulo todavía no se corrió ahí. Con la misma regla, ahí las tres medidas son confirmatorias."), "",
          "## Qué no prueba", "",
          "- Con dato mensual, un cierre preventivo y un pozo que queda fuera de servicio por el golpe se ven igual: los días parados no son todos una decisión.",
          "- La comparación entre operadores no es entre iguales: cambian la roca, el fluido, la edad de los pozos y cómo informa cada uno sus "
          "días efectivos. Restar el control propio corrige solo lo último.",
          "- El volumen de los días es volumen diferido valuado al caudal que el pozo traía: no dice que ese petróleo se pierda.",
          "- Los IC conservan la dependencia por pad hijo, pero no la de un mismo padre en varios eventos.", ""]
    return "\n".join(L)


def cargar_cuenca(con) -> dict:
    """Matrices de una cuenca de la replicacion (adaptacion a Colorado del encabezado): corte principal, sin estado declarado.

    `con` puede estar abierto solo para leer: replicacion.preparar arma sus entradas como tablas temporales.
    """
    replicacion.preparar(con, todos_los_padres=False)
    D = cargar_dias(con, descomposicion.cargar_ext(con, placebo.cargar(con)))
    del D["estados"], D["estado_cod"]  # F solo en Vaca Muerta
    D["censurado"] = np.array([bool(r[0]) for r in con.execute(
        "select coalesce(d.primer_petroleo_censurado, false) from int_pozo_ubicacion u join dim_pozo d using (pozo_id) "
        "order by u.pozo_id").fetchall()], dtype=bool)
    assert len(D["censurado"]) == D["tasa"].shape[0]
    return D


def escribir(con, t: dict[str, list[tuple]], cuenca: str = "") -> None:
    """Escribe las tablas de calcular con el nombre de la cuenca; fuera de Vaca Muerta no hay tabla de estado (F).

    Una llamada por mart, que es lo que lee pipeline.linaje: las de Colorado tambien quedan en el warehouse de Vaca Muerta.
    Solo Vaca Muerta y Colorado: otra cuenca necesita antes su adaptacion escrita en el encabezado.
    """
    if not cuenca:
        _escribir(con, "mart_dias_perdidos", COLS_BANDA, t["mart_dias_perdidos"])
        _escribir(con, "mart_dias_perdidos_operador", COLS_OPERADOR, t["mart_dias_perdidos_operador"])
        _escribir(con, "mart_dias_perdidos_mitades", COLS_MITADES, t["mart_dias_perdidos_mitades"])
        _escribir(con, "mart_dias_perdidos_estado", COLS_ESTADO, t["mart_dias_perdidos_estado"])
        _escribir(con, "mart_dias_perdidos_prueba", COLS_PRUEBA, t["mart_dias_perdidos_prueba"])
        return
    _solo_colorado(cuenca)
    _escribir(con, "mart_dias_perdidos_colorado", COLS_BANDA, t["mart_dias_perdidos"])
    _escribir(con, "mart_dias_perdidos_colorado_operador", COLS_OPERADOR, t["mart_dias_perdidos_operador"])
    _escribir(con, "mart_dias_perdidos_colorado_mitades", COLS_MITADES, t["mart_dias_perdidos_mitades"])
    _escribir(con, "mart_dias_perdidos_colorado_prueba", COLS_PRUEBA, t["mart_dias_perdidos_prueba"])


def _solo_colorado(cuenca: str) -> None:
    if cuenca != COLORADO.id:
        raise ValueError(f"dias_perdidos no tiene adaptacion escrita para la cuenca {cuenca!r}: solo Vaca Muerta y Colorado")


def _resumen(t: dict, nombre: str) -> None:
    v = {(f[0], f[1]): f[6] for f in t[mart("_prueba")] if f[6]}
    print(f"[{nombre}] A {v.get(('A', 'brecha_dias'))} | B {v.get(('B', 'diferencia_dias'))} | C {v.get(('C', 'pendiente'))}")


def main(path=DATA / "warehouse.duckdb", cuenca: Cuenca | None = None) -> None:
    """Vaca Muerta sobre su warehouse; con `cuenca`, esa cuenca sobre el suyo (solo lectura) y las tablas en el de Vaca Muerta."""
    if cuenca is None:
        con = duckdb.connect(str(path))
        t = calcular(cargar_dias(con, descomposicion.cargar_ext(con, placebo.cargar(con))))
        escribir(con, t)
        con.close()
        _resumen(t, "dias_perdidos")
        return
    _solo_colorado(cuenca.id)
    con_c = duckdb.connect(str(cuenca.db), read_only=True)
    try:
        t = calcular(cargar_cuenca(con_c))
    finally:
        con_c.close()
    con = duckdb.connect(str(path))
    escribir(con, t, cuenca.id)
    con.close()
    _resumen(t, f"dias_perdidos {cuenca.id}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="pipeline.dias_perdidos")
    ap.add_argument("--cuenca", help="id de una cuenca de la replicacion (pipeline/cuencas.py); sin argumento, Vaca Muerta")
    a = ap.parse_args()
    main(cuenca=_cuenca(a.cuenca) if a.cuenca else None)
