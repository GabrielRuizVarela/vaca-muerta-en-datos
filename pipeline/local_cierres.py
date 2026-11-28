"""Lector de registros de cierres de pozos para el modo con datos propios (lane LR, slice L1b, brecha B03).

REGLA FIJADA ANTES DE LEER (2026-11-28, antes de correr este modulo sobre ningun dato; no se cambia despues de ver resultados).
Este modulo LEE y AGREGA: no estima ningun efecto, no etiqueta cierres preventivos ni danos y no calcula nada sobre fracturas.
Es la entrada de datos que el modo local (pipeline.local) todavia no tiene: el dato mensual publico no separa un cierre preventivo
de un dano; el registro de cierres de un operador (cuando se cerro cada pozo y cuando volvio) si trae las horas cerradas.

Entrada: un CSV con encabezado, una fila por intervalo de cierre (ENTRADA = "cierres.csv"). Se lee como texto (all_varchar) en una
tabla cruda de la base DuckDB en memoria que arma local.armar_base (la misma conexion), igual que local.leer_csvs; los nombres de
columna se normalizan con local._normalizar_columnas.
  * pozo_id (obligatoria): entero, los mismos ids que pozos.csv.
  * inicio (obligatoria): YYYY-MM-DD HH:MM o YYYY-MM-DD (medianoche). Se interpreta con try_cast a timestamp, sin zona horaria.
  * fin (obligatoria como columna; el valor puede venir vacio): mismos formatos. Vacio significa que el pozo sigue cerrado: el
    intervalo se cierra al final del ultimo mes de la tabla ultimo_mes de la conexion (primer instante del mes siguiente) si esa
    tabla existe; si no existe, en el mayor instante (inicio o fin) de todo el archivo. Si ese instante es anterior al inicio del
    intervalo, el intervalo queda de largo cero y se cuenta en los avisos. info["cierre_abiertos"] dice cual de los dos se uso.
  * motivo (opcional): texto libre; se recorta, se pasa a minusculas y, si queda vacio o la columna falta, vale "sin motivo".
    Es una categoria que se guarda tal cual: el modulo nunca la interpreta.

Validaciones y salida (error = SystemExit con codigo 2 por local._error; el mensaje nombra columnas y conteos, nunca valores de
celdas):
  * error: falta una columna obligatoria; el archivo no trae filas; pozo_id vacio o no entero; inicio vacio o no interpretable;
    fin con texto que no se interpreta; fin anterior a inicio (se compara antes de cerrar los abiertos); ninguna fila
    corresponde a un pozo de dim_pozo.
  * aviso contado (info["avisos"], frases en espanol con conteos solamente): filas de pozos que no estan en dim_pozo (se ignoran,
    como local.leer_csvs con el mensual; si la conexion no trae dim_pozo no se ignora ninguna); intervalos que se superponen con
    otro del mismo pozo (se fusionan, ver abajo); intervalos abiertos; abiertos con inicio posterior al cierre del archivo.

Transformaciones:
  * horas = (fin - inicio) en horas, con segundos exactos.
  * Por pozo se fusionan los intervalos que se superponen o se tocan (el inicio es menor o igual que el mayor fin anterior); un
    instante cerrado cuenta una sola vez. Dos intervalos se superponen si cada inicio es menor que el fin del otro; intervalos que
    solo se tocan no son un aviso.
  * Los intervalos fusionados se cortan en los limites de mes calendario; las horas de un pozo en un mes nunca superan las horas del
    mes (dias del mes por 24).
  * Un dia es "cerrado completo" si las 24 h de ese dia calendario caen dentro de un intervalo fusionado.

Tablas que se arman en la conexion (se crean o se reemplazan; nada se escribe en disco, en el warehouse ni en el repo):
  * cierres: pozo_id, inicio, fin, horas, motivo, abierto. Una fila por fila de entrada de un pozo que esta en dim_pozo; fin ya
    trae el cierre de los abiertos y abierto es verdadero si el fin de entrada estaba vacio.
  * cierres_mes: una fila por (pozo_id, mes) con alguna hora cerrada (mes = primer dia del mes): horas_cerrado (horas cerradas en
    ese mes, intervalos fusionados y cortados), dias_cerrado_completo (dias calendario cerrados las 24 h), n_cierres (filas de
    cierres cuyo inicio cae en el mes, sin fusionar) y cerrado_todo_el_mes (horas_cerrado igual a las horas del mes).

API (lo unico que llama el modo local): leer(con, ruta) -> info. info trae: filas (de cierres), pozos, desde y hasta (primer inicio
y ultimo fin, texto ISO), abiertos, superpuestos, ignoradas, cierre_abiertos ("ultimo_mes" o "archivo" o None si no hay abiertos)
y avisos (lista de frases). No hay llamadas de red ni __main__. La comprobacion de rutas (local.comprobar_rutas) la hace quien
llama, antes de leer.

Que NO prueba: lee y agrega. No estima ningun efecto ni dice por que se cerro un pozo (el motivo es una categoria sin
interpretar); no separa cierre preventivo de dano; no cruza cierres con fracturas, para eso hace falta otra regla fijada antes
(slice R aparte). Un registro de cierres incompleto da horas cerradas de menos y este modulo no puede saberlo.
"""
from __future__ import annotations

from pipeline import local

ENTRADA = "cierres.csv"
OBLIGATORIAS = ("pozo_id", "inicio", "fin")
OPCIONALES = ("motivo",)
MOTIVO_VACIO = "sin motivo"

_TS = "try_cast(nullif(trim({c}), '') as timestamp)"
_HORAS = "date_diff('second', {a}, {b}) / 3600.0"


def _existe(con, tabla: str) -> bool:
    return con.execute("select count(*) from information_schema.tables where table_name = ?",
                       [tabla]).fetchone()[0] > 0


def _leer_crudo(con, ruta) -> list:
    p = str(ruta).replace("'", "''")
    try:
        con.execute(f"create or replace temp table raw_cierres as select * from read_csv('{p}', header = true, "
                    "all_varchar = true)")
    except Exception:
        local._error(f"{ENTRADA}: no se pudo leer el archivo (¿existe y es un CSV con encabezado?).")
    local._normalizar_columnas(con, "raw_cierres")
    cols = local._columnas(con, "raw_cierres")
    faltan = [c for c in OBLIGATORIAS if c not in cols]
    if faltan:
        local._error(f"{ENTRADA}: faltan columnas obligatorias: {', '.join(faltan)}.")
    if con.execute("select count(*) from raw_cierres").fetchone()[0] == 0:
        local._error(f"{ENTRADA}: el archivo no trae filas de cierres.")
    return cols


def _validar(con) -> None:
    pid, ini, fin = local._E_INT.format(c="pozo_id"), _TS.format(c="inicio"), _TS.format(c="fin")
    for etiqueta, donde in (
            ("pozo_id no interpretable como entero (columna pozo_id)", f"{pid} is null"),
            ("inicio vacío o no interpretable (columna inicio, formatos YYYY-MM-DD HH:MM o YYYY-MM-DD)",
             f"{ini} is null"),
            ("fin no interpretable (columna fin, formatos YYYY-MM-DD HH:MM o YYYY-MM-DD)",
             f"nullif(trim(fin), '') is not null and {fin} is null"),
            ("fin anterior a inicio (columnas fin e inicio)", f"{fin} < {ini}")):
        n = con.execute(f"select count(*) from raw_cierres where {donde}").fetchone()[0]
        if n:
            local._error(f"{ENTRADA}: {n} filas con {etiqueta}.")


def leer(con, ruta) -> dict:
    """Lee el CSV de cierres en `con`, lo valida (errores con código 2) y arma las tablas cierres y cierres_mes.

    Ver el encabezado del módulo: columnas, validaciones, cortes por mes y qué no prueba. Devuelve info con conteos y
    avisos (frases con conteos, nunca valores de celdas). No escribe nada fuera de la conexión.
    """
    cols = _leer_crudo(con, ruta)
    _validar(con)
    pid, ini, fin = local._E_INT.format(c="pozo_id"), _TS.format(c="inicio"), _TS.format(c="fin")
    motivo = "coalesce(nullif(lower(trim(motivo)), ''), '" + MOTIVO_VACIO + "')" if "motivo" in cols \
        else f"'{MOTIVO_VACIO}'"
    filtra = _existe(con, "dim_pozo")
    n_ign = con.execute(f"select count(*) from raw_cierres where {pid} not in (select pozo_id from dim_pozo)"
                        ).fetchone()[0] if filtra else 0
    if _existe(con, "ultimo_mes"):
        origen = "ultimo_mes"
        tope = "(select cast(mes as timestamp) + interval 1 month from ultimo_mes)"
    else:
        origen = "archivo"
        tope = f"(select max(greatest({ini}, coalesce({fin}, {ini}))) from raw_cierres)"
    con.execute(f"""create or replace temp table _cierres_n as
        select row_number() over () as n, {pid} as pozo_id, {ini} as inicio, {fin} as fin_entrada, {motivo} as motivo
        from raw_cierres
        {f"where {pid} in (select pozo_id from dim_pozo)" if filtra else ""}""")
    if con.execute("select count(*) from _cierres_n").fetchone()[0] == 0:
        local._error(f"{ENTRADA}: ninguna fila corresponde a un pozo de dim_pozo.")
    con.execute(f"""create or replace temp table _cierres_t as
        select n, pozo_id, inicio, fin_fila, fin_entrada is null as abierto, motivo from (
            select *, {tope} as tope, coalesce(fin_entrada, greatest(inicio, {tope})) as fin_fila from _cierres_n)""")
    con.execute(f"""create or replace table cierres as
        select pozo_id, inicio, fin_fila as fin, {_HORAS.format(a='inicio', b='fin_fila')} as horas, motivo, abierto
        from _cierres_t order by n""")
    # abiertos con inicio posterior al cierre del archivo: el cierre se llevo a inicio (largo cero)
    n_abiertos, n_tarde = con.execute(f"""select count(*) filter (where abierto),
        count(*) filter (where abierto and {_HORAS.format(a='inicio', b='fin')} = 0)
        from cierres""").fetchone()
    n_sup = con.execute("""select count(*) from _cierres_t a where exists (
        select 1 from _cierres_t b where b.pozo_id = a.pozo_id and b.n <> a.n
        and a.inicio < b.fin_fila and b.inicio < a.fin_fila)""").fetchone()[0]
    con.execute("""create or replace temp table _fusion as
        with o as (
            select pozo_id, inicio, fin_fila as fin,
                max(fin_fila) over (partition by pozo_id order by inicio, fin_fila
                                    rows between unbounded preceding and 1 preceding) as previo
            from _cierres_t),
        g as (
            select *, sum(case when previo is null or inicio > previo then 1 else 0 end)
                over (partition by pozo_id order by inicio, fin rows unbounded preceding) as grupo from o)
        select pozo_id, min(inicio) as inicio, max(fin) as fin from g group by pozo_id, grupo""")
    con.execute(f"""create or replace table cierres_mes as
        with m as (
            select pozo_id, inicio, fin,
                unnest(generate_series(cast(date_trunc('month', inicio) as timestamp),
                                       cast(date_trunc('month', fin) as timestamp), interval 1 month)) as mes
            from _fusion),
        h as (
            select pozo_id, cast(mes as date) as mes, inicio, fin, mes as t0, mes + interval 1 month as t1,
                {_HORAS.format(a='greatest(inicio, mes)', b='least(fin, mes + interval 1 month)')} as horas,
                case when inicio = date_trunc('day', inicio) then inicio
                     else date_trunc('day', inicio) + interval 1 day end as dia_ini,
                date_trunc('day', fin) as dia_fin
            from m),
        d as (
            select pozo_id, mes, horas,
                greatest(0, date_diff('day', greatest(dia_ini, t0), least(dia_fin, t1))) as dias, t1
            from h where horas > 0),
        s as (
            select pozo_id, mes, sum(horas) as horas_cerrado, sum(dias)::integer as dias_cerrado_completo
            from d group by pozo_id, mes),
        c as (
            select pozo_id, cast(date_trunc('month', inicio) as date) as mes, count(*)::integer as n_cierres
            from cierres group by pozo_id, mes)
        select s.pozo_id, s.mes, s.horas_cerrado, s.dias_cerrado_completo, coalesce(c.n_cierres, 0) as n_cierres,
            abs(s.horas_cerrado - extract(day from last_day(s.mes)) * 24.0) < 1e-6 as cerrado_todo_el_mes
        from s left join c using (pozo_id, mes) order by s.pozo_id, s.mes""")
    for t in ("raw_cierres", "_cierres_n", "_cierres_t", "_fusion"):
        con.execute(f"drop table if exists {t}")
    filas, pozos, desde, hasta = con.execute(
        "select count(*), count(distinct pozo_id), min(inicio), max(fin) from cierres").fetchone()
    avisos = []
    if n_ign:
        avisos.append(f"Se ignoraron {n_ign} filas de {ENTRADA} con pozo ausente en pozos.csv.")
    if n_sup:
        avisos.append(f"{n_sup} intervalos de {ENTRADA} se superponen con otro del mismo pozo; se fusionaron y cada hora "
                      "cerrada cuenta una sola vez.")
    if n_abiertos:
        avisos.append(f"{n_abiertos} intervalos de {ENTRADA} no traen fin; se cerraron al final del "
                      + ("último mes de los datos mensuales." if origen == "ultimo_mes"
                         else "último instante del archivo de cierres."))
    if n_tarde:
        avisos.append(f"{n_tarde} intervalos abiertos empiezan después de ese cierre; quedaron con 0 horas.")
    return {"filas": filas, "pozos": pozos, "desde": desde.isoformat(sep=" "), "hasta": hasta.isoformat(sep=" "),
            "abiertos": n_abiertos, "superpuestos": n_sup, "ignoradas": n_ign,
            "cierre_abiertos": origen if n_abiertos else None, "avisos": avisos}
