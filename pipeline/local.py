"""Modo con datos propios: el mismo estudio de eventos y el mismo modelo de dosis sobre los CSV de un operador.

Uso:  uv run python -m pipeline.local --wells POZOS.csv --monthly MENSUAL.csv --out CARPETA [--reps N]
Esquema de los CSV y garantia de privacidad: docs/operador-datos-propios.md.

REGLA FIJADA ANTES DE CORRER (2026-11-17, antes de correr este modulo sobre ningun dato; no se cambia despues de ver resultados).
No es una prueba nueva ni un estimador nuevo: es la misma cuenta del dato publico sobre otras tablas. Por eso NO se reimplementa
nada: se arman en una base DuckDB en memoria las mismas tablas que usa el pipeline y se llama al mismo codigo.

Tablas que se arman (mismas columnas que pipeline/sql/01 a 02; el pipeline las lee de esos nombres):
  * dim_pozo: pozo_id, operador, area, tipo_pozo, lon, lat, primer_mes_petroleo, con formacion = 'vaca muerta' y subtipo_recurso =
    'SHALE' para todos los pozos del archivo (el operador entrega solo los pozos que quiere incluir). primer_mes_petroleo = primer mes
    del archivo mensual con petroleo_m3 > 0 (igual que dim_pozo de 02_core.sql). operador y area, si el archivo no las trae, valen
    'propio' y 'unica'.
  * fct_produccion: pozo_id, mes (primer dia del mes), petroleo_m3 (negativos pasan a 0, faltantes a 0), dias_mes (dias del mes
    calendario). Igual que 02_core.sql, el indice usa los dias del mes calendario y NO los dias de produccion; la columna
    dias_produccion del CSV mensual se valida (no puede superar los dias del mes) y no se usa en el calculo (el resultado B del
    pipeline publico, que usa dias efectivos, no se calcula aca).
  * ultimo_mes: el mayor mes del archivo mensual.
  * stg_fractura y dim_fractura_pozo: una fila por trabajo de fractura (pozo_id, fecha_inicio, rama_horizontal_m, etapas, arena_tn,
    presion_maxima_psi; terminacion nula; operador). Se aplican las reglas de stg_fractura: rama 0 pasa a faltante.
Luego se ejecuta, tal cual, pipeline/sql/04_interferencia.sql (pad por vecindad de 50 m, hijos, pares a menos de 5 km, evento por
(padre, mes), banda por el hijo mas cercano, indice del mes -3 al +6, brecha por edad, diferido). Despues, int_pozo_ubicacion.pad_id se
sobreescribe con el pad_id del archivo de pozos (es obligatorio): el conglomerado del bootstrap es el pad del HIJO.

Evento y brecha del mes 1 (el resultado principal del estudio publico): pipeline.placebo.cargar y pipeline.placebo.marco con la base
original (meses -3 a -1), ks = (1, 6): el hijo mas cercano (desempate por id) fija la banda (cercano < 1 km, intermedio 1 a 2 km, control
2 a 5 km), el padre debe tener al menos placebo.EDAD_MIN meses de produccion y una base mayor que placebo.BASE_MIN. Brecha = mediana del
indice de los cercanos menos mediana de los controles, con IC 95% de percentiles por pads hijo: pipeline.placebo.brecha_ic con
placebo.REPS_BOOT repeticiones (o --reps) y semilla placebo.SEMILLA_PLACEBO, en k = 1 y en k = 6 (el mes 6 solo cuenta eventos con ese
mes en la base). Se informa la brecha en puntos (indice por 100) y el n de cercanos, de controles y de pads hijo de los cercanos.

Modelo de dosis (si hay datos): los eventos 'cercano' con pipeline.dosis._dataset_a (variables v1 a v4 en bruto: ln(arena / etapas),
ln(arena / rama), presion maxima con 0 < presion < 20.000, depleccion del padre = ln(petroleo acumulado antes de mes_frac / rama del
padre)). Una variable existe si tiene al menos MIN_CASOS_VARIABLE = 30 eventos con valor finito y desvio mayor que cero; si no, queda
fuera y el informe dice por que. El modelo conjunto usa solo las variables que existen: caso completo de esas variables y de los
controles (km, ln(edad con minimo 1), base / 10, hijos a menos de 1 km; sin dummies de terminacion porque el archivo no las trae;
efectos fijos de area por ano de dosis._controles con sin_term = True; sin la dummy de terminacion no se pide terminacion en la
mascara), variables estandarizadas dentro de la muestra, resultado A = caida del indice al mes 1 (indice del control menos indice del
evento, cada uno acotado a [0, 2]), pipeline.dosis._ajuste con B = --reps o dosis.B_MAIN, semilla dosis.SEMILLA_DOSIS + 3_000_000 (un solo ajuste conjunto, sin
indice de variable), p de dos colas de dosis._p_boot y Holm sobre las variables que entran (dosis._holm).
Se informa por variable: coeficiente en unidades del indice por desvio de la dosis y en desvios de la caida (dividido por el desvio de la
caida de la muestra), IC 95% de percentiles, p, p de Holm y la cota superior del IC en desvios de la caida. "cumple" = coeficiente positivo
y p de Holm menor que 0,05, como en pipeline.dosis; no se escribe ningun veredicto de dosis y respuesta ni "efecto descartado".
Condicion de muestra: el modelo no se corre si tiene menos de MIN_EVENTOS_DOSIS = 100 eventos o menos de MIN_PADS_DOSIS = 20 pads hijo.
Aviso de muestra chica de la brecha: menos de MIN_CERCANOS = 30 eventos cercanos o menos de MIN_PADS = 10 pads hijo de los cercanos.

Salidas (SOLO en la carpeta --out): resumen.json (todas las cifras), resumen.md (el informe en espanol) y eventos.csv (un renglon por
evento cercano con ids, km, mes, indice a k = 1, caida y variables). Nada se escribe en el repo, en el warehouse ni en otra carpeta.

Privacidad por construccion: el modulo REHUSA correr, con un mensaje que dice por que y codigo de salida 2, si cualquier ruta de
entrada o de salida cae dentro del repositorio y esta versionada (git ls-files) o no esta ignorada por git (git check-ignore); fuera
del repositorio no hay restriccion. Asi los datos privados no pueden terminar en git por un descuido. Los datos se cargan en una base
en memoria que no se guarda. No hay llamadas de red.

Que NO prueba:
  * Es el mismo estimador del dato publico: no corrige por nada que el operador sepa y no este en las columnas (espaciamiento real,
    geometria, presion de fondo). Con datos propios y esas columnas, el modelo de dosis es el lugar donde agregarlas.
  * Con pocos eventos el IC es ancho; el informe lo dice con el n y los pads. Un IC que incluye cero no dice que no haya efecto.
  * Una brecha del mes 1 con datos mensuales no separa cierre preventivo de dano (igual que en el estudio publico).
  * Los pozos del archivo se toman todos como padres e hijos posibles; si el archivo es una parte del campo, la distancia al hijo mas
    cercano ignora los pozos que no estan.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import duckdb
import numpy as np

from pipeline import dosis, placebo
from pipeline.ingest import ROOT
from pipeline.placebo import _g

MIN_CASOS_VARIABLE = 30
MIN_EVENTOS_DOSIS = 100
MIN_PADS_DOSIS = 20
MIN_CERCANOS = 30
MIN_PADS = 10
SQL_DIR = Path(__file__).parent / "sql"

POZOS_OBLIGATORIAS = ("pozo_id", "pad_id", "lon", "lat", "fecha_fractura", "arena_tn", "etapas", "rama_m",
                      "presion_max_psi")
MENSUAL_OBLIGATORIAS = ("pozo_id", "mes", "petroleo_m3")
VARS_DOSIS = ("arena_etapa", "arena_rama", "presion", "deplecion")

_E_INT = "try_cast(nullif(trim({c}), '') as integer)"
_E_DBL = "try_cast(nullif(trim({c}), '') as double)"
_E_PAD = "nullif(trim({c}), '')"
_E_MES = "try_cast(case when trim({c}) like '____-__' then trim({c}) || '-01' else trim({c}) end as date)"
_E_FECHA = "try_cast(nullif(trim({c}), '') as date)"

_MENSAJE_RUTA = ("la ruta {ruta} cae dentro del repositorio y está versionada o no está ignorada por git; los datos "
                 "privados no deben terminar en git. Usá una carpeta fuera del repo (o una ignorada por .gitignore).")


def _error(mensaje: str) -> None:
    print(f"pipeline.local: {mensaje}", file=sys.stderr)
    raise SystemExit(2)


def comprobar_rutas(rutas, raiz=ROOT) -> None:
    """Rehúsa con SystemExit 2 si alguna ruta cae en el repo versionada o sin ignorar por git.

    Las rutas fuera del repositorio siempre están permitidas. Dentro del repositorio solo se permite una ruta
    ignorada por git (git check-ignore) y no versionada (git ls-files); si git no está disponible o falla de
    forma no prevista, se rehúsa. No escribe nada: corre antes de leer o escribir.
    """
    root = Path(raiz).resolve()
    for ruta in rutas:
        try:
            rel = Path(ruta).resolve().relative_to(root)
        except ValueError:
            continue
        try:
            ign = subprocess.run(["git", "check-ignore", "-q", str(rel)], cwd=root, capture_output=True)
        except OSError:
            _error(_MENSAJE_RUTA.format(ruta=ruta))
        if ign.returncode != 0:
            _error(_MENSAJE_RUTA.format(ruta=ruta))
        try:
            trk = subprocess.run(["git", "ls-files", "--", str(rel)], cwd=root, capture_output=True, text=True)
        except OSError:
            _error(_MENSAJE_RUTA.format(ruta=ruta))
        if trk.returncode != 0 or trk.stdout.strip():
            _error(_MENSAJE_RUTA.format(ruta=ruta))


def _columnas(con, tabla: str) -> list:
    return [d[0] for d in con.execute(f"select * from {tabla} limit 0").description]


def _normalizar_columnas(con, tabla: str) -> None:
    for col in _columnas(con, tabla):
        nuevo = col.replace(chr(0xFEFF), "").strip()
        if nuevo and nuevo != col:
            viejo = '"' + col.replace('"', '""') + '"'
            con.execute(f"alter table {tabla} rename {viejo} to " + '"' + nuevo.replace('"', '""') + '"')


def leer_csvs(pozos_csv, mensual_csv):
    """Lee y valida los dos CSV del operador en tablas crudas de una base DuckDB en memoria.

    pozos.csv, una fila por pozo. Columnas obligatorias: pozo_id (entero, sin repetir), pad_id (texto, el pad
    del hijo es el conglomerado del bootstrap), lon y lat (grados decimales WGS84), fecha_fractura (YYYY-MM-DD,
    vacía si el pozo no tuvo fractura propia en el período; sin fecha solo puede ser padre), arena_tn, etapas,
    rama_m y presion_max_psi (números, pueden venir vacíos). Opcionales: operador y area (si faltan o vienen
    vacías valen 'propio' y 'unica'). mensual.csv, una fila por (pozo, mes). Columnas obligatorias: pozo_id, mes
    (YYYY-MM o YYYY-MM-DD, se lleva al primer día del mes) y petroleo_m3 (los negativos pasan a 0, los faltantes
    a 0). Opcional: dias_produccion, que se valida (no puede superar los días del mes) y no se usa en el cálculo.
    Las filas del mensual de pozos ausentes en pozos.csv se ignoran y se cuentan en los avisos. Los errores de
    entrada (columna obligatoria ausente, pozo_id duplicado o no interpretable, lon, lat o pad_id no
    interpretables, mes no interpretable) salen con código 2 y un mensaje que solo nombra columnas y conteos,
    nunca valores de las celdas.
    """
    con = duckdb.connect(":memory:")
    for etiqueta, ruta, tabla in (("pozos.csv", pozos_csv, "raw_pozos"),
                                  ("mensual.csv", mensual_csv, "raw_mensual")):
        p = str(ruta).replace("'", "''")
        try:
            con.execute(f"create table {tabla} as select * from read_csv('{p}', header = true, all_varchar = true)")
        except Exception:
            _error(f"{etiqueta}: no se pudo leer el archivo (¿existe y es un CSV con encabezado?).")
    _normalizar_columnas(con, "raw_pozos")
    _normalizar_columnas(con, "raw_mensual")
    cols_p = _columnas(con, "raw_pozos")
    cols_m = _columnas(con, "raw_mensual")
    faltan = [c for c in POZOS_OBLIGATORIAS if c not in cols_p]
    if faltan:
        _error(f"pozos.csv: faltan columnas obligatorias: {', '.join(faltan)}.")
    faltan = [c for c in MENSUAL_OBLIGATORIAS if c not in cols_m]
    if faltan:
        _error(f"mensual.csv: faltan columnas obligatorias: {', '.join(faltan)}.")
    if con.execute("select count(*) from raw_pozos").fetchone()[0] == 0:
        _error("pozos.csv: el archivo no trae filas de pozos.")
    if con.execute("select count(*) from raw_mensual").fetchone()[0] == 0:
        _error("mensual.csv: el archivo no trae filas mensuales.")
    id_p = _E_INT.format(c="pozo_id")
    for etiqueta, donde in (("pozo_id no interpretable como entero (columna pozo_id)", f"{id_p} is null"),
                            ("pad_id vacío o ausente (columna pad_id)",
                             f"{_E_PAD.format(c='pad_id')} is null"),
                            ("lon no interpretable como número (columna lon)",
                             f"{_E_DBL.format(c='lon')} is null"),
                            ("lat no interpretable como número (columna lat)",
                             f"{_E_DBL.format(c='lat')} is null")):
        n = con.execute(f"select count(*) from raw_pozos where {donde}").fetchone()[0]
        if n:
            _error(f"pozos.csv: {n} filas con {etiqueta}.")
    n = con.execute(f"select count(*) from (select {id_p} as x from raw_pozos where {id_p} is not null "
                    "group by x having count(*) > 1) t").fetchone()[0]
    if n:
        _error(f"pozos.csv: pozo_id duplicado (columna pozo_id): {n} valores repetidos.")
    n = con.execute(f"select count(*) from raw_mensual where {_E_MES.format(c='mes')} is null").fetchone()[0]
    if n:
        _error(f"mensual.csv: {n} filas con mes no interpretable (columna mes, formatos YYYY-MM o YYYY-MM-DD).")
    return con

def armar_base(pozos_csv, mensual_csv):
    """Arma las tablas del pipeline en una base DuckDB en memoria y devuelve (con, info).

    Crea dim_pozo, fct_produccion, ultimo_mes, stg_fractura y dim_fractura_pozo desde las tablas crudas,
    ejecuta tal cual pipeline/sql/04_interferencia.sql y sobreescribe int_pozo_ubicacion.pad_id con el pad_id
    del archivo de pozos. info trae conteos (pozos, pozos_con_fractura, filas_mensual, mes_desde, mes_hasta) y
    la lista avisos (filas ignoradas y columnas inválidas, solo conteos).
    """
    con = leer_csvs(pozos_csv, mensual_csv)
    cols_p = set(_columnas(con, "raw_pozos"))
    cols_m = set(_columnas(con, "raw_mensual"))
    op = "coalesce(nullif(trim(operador), ''), 'propio')" if "operador" in cols_p else "'propio'"
    ar = "coalesce(nullif(trim(area), ''), 'unica')" if "area" in cols_p else "'unica'"
    id_p = _E_INT.format(c="pozo_id")
    id_m = _E_INT.format(c="pozo_id")
    mes_m = _E_MES.format(c="mes")
    pet = _E_DBL.format(c="petroleo_m3")
    con.execute(f"""create table fct_produccion as
        with m as (
            select {id_m} as pozo_id, date_trunc('month', {mes_m}) as mes,
                case when {pet} is null or {pet} < 0 then 0.0 else {pet} end as petroleo_m3
            from raw_mensual
        )
        select m.pozo_id, m.mes, sum(m.petroleo_m3) as petroleo_m3,
            extract(day from last_day(m.mes))::integer as dias_mes
        from m join (select distinct {id_p} as pozo_id from raw_pozos) p using (pozo_id)
        group by m.pozo_id, m.mes""")
    if con.execute("select count(*) from fct_produccion").fetchone()[0] == 0:
        _error("mensual.csv: ninguna fila corresponde a un pozo de pozos.csv.")
    id_r = _E_INT.format(c="r.pozo_id")
    op_r = op.replace("trim(operador)", "trim(r.operador)")
    ar_r = ar.replace("trim(area)", "trim(r.area)")
    con.execute(f"""create table dim_pozo as
        with f as (select pozo_id, min(mes) as primer from fct_produccion where petroleo_m3 > 0 group by pozo_id)
        select {id_r} as pozo_id, {op_r} as operador, {ar_r} as area, 'productor' as tipo_pozo,
            {_E_DBL.format(c='r.lon')} as lon, {_E_DBL.format(c='r.lat')} as lat,
            f.primer as primer_mes_petroleo, 'vaca muerta' as formacion, 'SHALE' as subtipo_recurso
        from raw_pozos r left join f on f.pozo_id = {id_r}""")
    con.execute("create table ultimo_mes as select max(mes) as mes from fct_produccion")
    fecha = _E_FECHA.format(c="fecha_fractura")
    con.execute(f"""create table stg_fractura as
        select {id_p} as pozo_id, {fecha} as fecha_inicio,
            nullif({_E_DBL.format(c='rama_m')}, 0) as rama_horizontal_m,
            {_E_INT.format(c='etapas')} as etapas, {_E_DBL.format(c='arena_tn')} as arena_tn,
            cast(null as varchar) as terminacion, {_E_DBL.format(c='presion_max_psi')} as presion_maxima_psi,
            cast(null as date) as mes_carga,
            {op} as operador
        from raw_pozos where {fecha} is not null""")
    # la rama de cada pozo sale del archivo de pozos aunque no tenga fecha de fractura: un padre sin fecha aporta su rama a la depleccion
    con.execute(f"""create table dim_fractura_pozo as
        select {id_p} as pozo_id, nullif({_E_DBL.format(c='rama_m')}, 0) as rama_horizontal_m from raw_pozos""")
    con.execute((SQL_DIR / "04_interferencia.sql").read_text().format(**{}))
    con.execute(f"""create temp table tmp_pad_local as
        select {id_p} as pozo_id, {_E_PAD.format(c='pad_id')} as pad_id from raw_pozos""")
    con.execute("""update int_pozo_ubicacion set pad_id = t.pad_id
        from tmp_pad_local t where int_pozo_ubicacion.pozo_id = t.pozo_id""")
    n_pozos = con.execute("select count(*) from raw_pozos").fetchone()[0]
    n_frac = con.execute("select count(*) from stg_fractura").fetchone()[0]
    n_filas = con.execute("select count(*) from raw_mensual").fetchone()[0]
    dmin, dmax = con.execute("select min(mes), max(mes) from fct_produccion").fetchone()
    n_ign = con.execute(f"""select count(*) from raw_mensual r
        left join (select distinct {id_p} as pozo_id from raw_pozos) p
        on {_E_INT.format(c='r.pozo_id')} = p.pozo_id where p.pozo_id is null""").fetchone()[0]
    if "dias_produccion" in cols_m:
        lim = f"extract(day from last_day(date_trunc('month', {_E_MES.format(c='mes')})))"
        n_dias = con.execute(f"""select count(*) from raw_mensual
            where nullif(trim(dias_produccion), '') is not null
            and (try_cast(trim(dias_produccion) as integer) is null
                or try_cast(trim(dias_produccion) as integer) < 0
                or try_cast(trim(dias_produccion) as integer) > {lim})""").fetchone()[0]
    else:
        n_dias = 0
    n_fecha = con.execute(f"""select count(*) from raw_pozos
        where nullif(trim(fecha_fractura), '') is not null and {_E_FECHA.format(c='fecha_fractura')} is null"""
                        ).fetchone()[0]
    n_pet = con.execute(f"""select count(*) from raw_mensual
        where nullif(trim(petroleo_m3), '') is not null and {_E_DBL.format(c='petroleo_m3')} is null"""
                        ).fetchone()[0]
    avisos = []
    if n_ign:
        avisos.append(f"Se ignoraron {n_ign} filas del mensual con pozo ausente en pozos.csv.")
    if n_dias:
        avisos.append(f"{n_dias} filas del mensual traen dias_produccion mayor que los días del mes o no "
                      "interpretable; esa columna no se usa en el cálculo.")
    if n_fecha:
        avisos.append(f"{n_fecha} pozos traen fecha_fractura no interpretable; se tomaron como pozos sin "
                      "fractura propia.")
    if n_pet:
        avisos.append(f"{n_pet} filas del mensual traen petroleo_m3 no interpretable; se tomaron como 0.")
    info = {"pozos": n_pozos, "pozos_con_fractura": n_frac, "filas_mensual": n_filas,
            "mes_desde": dmin.strftime("%Y-%m"), "mes_hasta": dmax.strftime("%Y-%m"), "avisos": avisos}
    return con, info


def _brecha_vacia():
    return {"n_cercanos": 0, "n_controles": 0, "pads_hijo_cercanos": 0, "brecha": float("nan"),
            "ic_bajo": float("nan"), "ic_alto": float("nan"), "aviso_muestra_chica": True}


def brecha(con, reps=placebo.REPS_BOOT):
    """Brecha cercano menos control a k = 1 y k = 6 con el mismo marco del estudio público.

    Devuelve un dict con k1 y k6; cada uno trae n_cercanos, n_controles, pads_hijo_cercanos, brecha (en índice),
    ic_bajo, ic_alto y aviso_muestra_chica (menos de MIN_CERCANOS cercanos o MIN_PADS pads).
    """
    if con.execute("select count(*) from int_par_padre_hijo").fetchone()[0] == 0:
        return {"k1": _brecha_vacia(), "k6": _brecha_vacia()}
    d = placebo.cargar(con)
    m = placebo.marco(d, d["hijo_mes"], ks=(1, 6), base=placebo.BASE_ORIGINAL)
    out = {}
    for k, nombre in ((1, "k1"), (6, "k6")):
        r = placebo.brecha_ic(m["idx"][k], m["banda"], m["clave"], reps, placebo.SEMILLA_PLACEBO)
        pads = len(set(m["clave"][m["banda"] == 0]))
        out[nombre] = {"n_cercanos": r["n_near"], "n_controles": r["n_ctrl"], "pads_hijo_cercanos": pads,
                       "brecha": r["brecha"], "ic_bajo": r["ic_bajo"], "ic_alto": r["ic_alto"],
                       "aviso_muestra_chica": bool(r["n_near"] < MIN_CERCANOS or pads < MIN_PADS)}
    return out

def modelo_dosis(con, reps=dosis.B_MAIN):
    """Modelo conjunto de dosis sobre los eventos cercanos; devuelve (resultado, d, y).

    resultado trae corrio, motivo, n, pads, sd_caida, variables (nombre, coef en índice por desvío de la dosis,
    coef_sd en desvíos de la caída, ic_bajo, ic_alto, ic_bajo_sd, ic_alto_sd, cota_superior, p, p_holm, cumple)
    y excluidas (nombre para mostrar y motivo). d es el dict de dosis._dataset_a e y el vector de caída.
    """
    d = dosis._dataset_a(con)
    y = d["caida"]
    mascara = (np.isfinite(d["km"]) & np.isfinite(d["edad"]) & np.isfinite(d["base"])
               & np.isfinite(d["hijos"]) & np.isfinite(y)
               & np.array([a is not None for a in d["area"]]))
    base = np.flatnonzero(mascara)
    elegidas, excluidas = [], {}
    for j, nombre in enumerate(VARS_DOSIS):
        mostrar = dosis.NOMBRES[nombre]
        fin = d[f"v{j + 1}"][base]
        fin = fin[np.isfinite(fin)]
        if len(fin) < MIN_CASOS_VARIABLE:
            excluidas[mostrar] = (f"solo {len(fin)} eventos con valor finito (mínimo {MIN_CASOS_VARIABLE})")
        elif float(fin.std()) <= 0:
            excluidas[mostrar] = "sin variación entre eventos (desvío cero)"
        else:
            elegidas.append(j)
    cc = base
    if elegidas:
        ok = np.ones(len(base), dtype=bool)
        for j in elegidas:
            ok &= np.isfinite(d[f"v{j + 1}"][base])
        cc = base[ok]
    n = len(cc)
    pads = len(set(d["cluster"][cc])) if n else 0
    res = {"corrio": False, "motivo": "", "n": n, "pads": pads, "sd_caida": None, "variables": [],
           "excluidas": excluidas}
    if n < MIN_EVENTOS_DOSIS or pads < MIN_PADS_DOSIS:
        res["motivo"] = (f"muestra chica: {n} eventos y {pads} pads hijo "
                         f"(mínimos {MIN_EVENTOS_DOSIS} eventos y {MIN_PADS_DOSIS} pads)")
        return res, d, y
    if not elegidas:
        res["motivo"] = (f"ninguna variable tiene al menos {MIN_CASOS_VARIABLE} eventos con valor finito y "
                         "desvío mayor que cero")
        return res, d, y
    x = np.column_stack([dosis._std(d[f"v{j + 1}"][cc]) for j in elegidas])
    c, grupo = dosis._controles(d, cc, sin_term=True)
    semilla = dosis.SEMILLA_DOSIS + 3_000_000 + 0
    coefs, ics, ps = dosis._ajuste(y[cc], x, c, grupo, d["cluster"][cc], semilla, reps)
    ph = dosis._holm(ps)
    sd = float(y[cc].std())
    res.update({"corrio": True, "motivo": "", "sd_caida": sd})
    for t, j in enumerate(elegidas):
        coef, lo, hi, p, q = float(coefs[t]), float(ics[t][0]), float(ics[t][1]), float(ps[t]), float(ph[t])
        res["variables"].append({"nombre": dosis.NOMBRES[VARS_DOSIS[j]], "coef": coef, "coef_sd": coef / sd,
                                "ic_bajo": lo, "ic_alto": hi, "ic_bajo_sd": lo / sd, "ic_alto_sd": hi / sd,
                                "cota_superior": hi / sd, "p": p, "p_holm": q,
                                "cumple": bool(coef > 0 and q < 0.05)})
    return res, d, y


def informe(res) -> str:
    """Informe Markdown en español con entradas, brechas, dosis, avisos y qué no prueba."""
    ent, br, dz = res["entradas"], res["brecha"], res["dosis"]
    k1, k6 = br["k1"], br["k6"]
    lin = ["# Estudio local con datos propios", "", "## Datos de entrada",
           f"- Pozos en el archivo: {_g(ent['pozos'])}; con fractura en el período: "
           f"{_g(ent['pozos_con_fractura'])}.",
           f"- Filas mensuales: {_g(ent['filas_mensual'])}; meses cubiertos: {ent['mes_desde']} a "
           f"{ent['mes_hasta']}.",
           "", "## Brecha cercano menos control",
           "La brecha es la mediana del índice de los padres cercanos (menos de 1 km) menos la de los controles "
           "(2 a 5 km), en puntos (índice por 100), con intervalo de confianza del 95% por pads hijo."]
    for etiqueta, r in (("Mes 1", k1), ("Mes 6", k6)):
        lin.append(f"- {etiqueta}: {_g(r['brecha'] * 100, 1)} puntos (IC 95%: {_g(r['ic_bajo'] * 100, 1)} a "
                   f"{_g(r['ic_alto'] * 100, 1)}; n cercanos: {_g(r['n_cercanos'])}, n controles: "
                   f"{_g(r['n_controles'])}, pads hijo: {_g(r['pads_hijo_cercanos'])}).")
        if r["aviso_muestra_chica"]:
            lin.append(f"  Aviso: muestra chica en el {etiqueta.lower()} (mínimos {MIN_CERCANOS} eventos cercanos "
                       f"y {MIN_PADS} pads hijo).")
    lin += ["", "## Modelo de dosis"]
    if dz["corrio"]:
        lin.append(f"Caída del índice al mes 1; coeficientes por desvío de cada dosis (n: {_g(dz['n'])}, pads: "
                   f"{_g(dz['pads'])}, desvío de la caída: {_g(dz['sd_caida'], 3)}).")
        lin.append("")
        lin.append("| Variable | Coef. por desvío | Coef. en desvíos de la caída | IC 95% | p | p Holm | "
                   "Cota superior | Cumple |")
        lin.append("|---|---|---|---|---|---|---|---|")
        for v in dz["variables"]:
            lin.append(f"| {v['nombre']} | {_g(v['coef'], 3)} | {_g(v['coef_sd'], 2)} | {_g(v['ic_bajo'], 3)} a "
                       f"{_g(v['ic_alto'], 3)} | {_g(v['p'], 3)} | {_g(v['p_holm'], 3)} | "
                       f"{_g(v['cota_superior'], 2)} | {'sí' if v['cumple'] else 'no'} |")
    else:
        lin.append(f"El modelo no se corrió: {dz['motivo']}.")
    if dz["excluidas"]:
        lin += ["", "Variables fuera del modelo: "
                + "; ".join(f"{k} ({v})" for k, v in dz["excluidas"].items()) + "."]
    lin += ["", "## Avisos"]
    if res["avisos"]:
        lin += [f"- {a}" for a in res["avisos"]]
    else:
        lin.append("Sin avisos.")
    lin += ["", "## Qué no prueba",
            "- Es el mismo estimador del dato público: no corrige por nada que el operador sepa y no esté en las "
            "columnas (espaciamiento real, geometría, presión de fondo). Con datos propios y esas columnas, el "
            "modelo de dosis es el lugar donde agregarlas.",
            "- Con pocos eventos el IC es ancho; el informe lo dice con el n y los pads. Un IC que incluye cero no "
            "dice que no haya efecto.",
            "- Una brecha del mes 1 con datos mensuales no separa cierre preventivo de daño (igual que en el "
            "estudio público).",
            "- Los pozos del archivo se toman todos como padres e hijos posibles; si el archivo es una parte del "
            "campo, la distancia al hijo más cercano ignora los pozos que no están.",
            "", "Los datos no salieron de la carpeta de salida: el módulo solo escribió resumen.json, resumen.md y "
            "eventos.csv en ella."]
    return "\n".join(lin) + "\n"

def _redondear(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        return None if math.isnan(x) or math.isinf(x) else round(x, 6)
    if isinstance(x, dict):
        return {k: _redondear(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_redondear(v) for v in x]
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return _redondear(float(x))
    if isinstance(x, np.ndarray):
        return _redondear(x.tolist())
    return x


def _num(x) -> str:
    if x is None:
        return ""
    x = float(x)
    if math.isnan(x):
        return ""
    return str(int(x)) if x.is_integer() else repr(x)


def _escribir_eventos(ruta, d, y) -> None:
    with open(ruta, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["padre", "hijo_cercano", "mes_frac", "km_min", "edad_meses", "caida", "v1", "v2", "v3", "v4"])
        for i in range(len(d["padre"])):
            if not np.isfinite(y[i]):
                continue
            mf = d["mes"][i]
            fila = [str(int(d["padre"][i])), str(int(d["hijo"][i])), f"{mf.year}-{mf.month:02d}",
                    _num(d["km"][i]), _num(d["edad"][i]), _num(y[i])]
            fila += [_num(d[f"v{j}"][i]) for j in range(1, 5)]
            w.writerow(fila)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Estudio de eventos y modelo de dosis sobre CSV propios.")
    ap.add_argument("--wells", required=True)
    ap.add_argument("--monthly", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=None)
    args = ap.parse_args(argv)
    comprobar_rutas([args.wells, args.monthly, args.out])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    reps_b = args.reps if args.reps is not None else placebo.REPS_BOOT
    reps_d = args.reps if args.reps is not None else dosis.B_MAIN
    con, info = armar_base(args.wells, args.monthly)
    br = brecha(con, reps_b)
    dz, d, y = modelo_dosis(con, reps_d)
    res = {"entradas": {k: info[k] for k in ("pozos", "pozos_con_fractura", "filas_mensual", "mes_desde",
                                            "mes_hasta")},
           "avisos": info["avisos"], "brecha": br, "dosis": dz}
    (out / "resumen.json").write_text(json.dumps(_redondear(res), indent=2, ensure_ascii=False) + "\n")
    (out / "resumen.md").write_text(informe(res))
    _escribir_eventos(out / "eventos.csv", d, y)
    k1, k6 = br["k1"], br["k6"]
    print(f"pozos: {_g(info['pozos'])}, meses: {info['mes_desde']} a {info['mes_hasta']}")
    for etiqueta, r in (("mes 1", k1), ("mes 6", k6)):
        print(f"brecha {etiqueta}: {_g(r['brecha'] * 100, 1)} puntos "
              f"(IC {_g(r['ic_bajo'] * 100, 1)} a {_g(r['ic_alto'] * 100, 1)}), n cercanos: "
              f"{_g(r['n_cercanos'])}, controles: {_g(r['n_controles'])}, pads: {_g(r['pads_hijo_cercanos'])}")
    if dz["corrio"]:
        for v in dz["variables"]:
            print(f"dosis {v['nombre']}: coef {_g(v['coef'], 3)} (IC {_g(v['ic_bajo'], 3)} a "
                  f"{_g(v['ic_alto'], 3)}), p Holm {_g(v['p_holm'], 3)}")
    else:
        print(f"dosis: no se corrió ({dz['motivo']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

