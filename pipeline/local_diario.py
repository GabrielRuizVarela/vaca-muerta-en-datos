"""Lector local de produccion diaria (modo con datos propios, brecha B02): lee diario.csv y arma tablas diarias y mensuales.

REGLA FIJADA ANTES DE LEER (2026-11-28, antes de que este modulo lea ningun dato; no se cambia despues de ver resultados).
Este modulo NO estima nada: lee un CSV, lo valida y agrega. Vive aparte de pipeline.local a proposito: pipeline.claims decide que
lee el modo local a partir de local.ENTRADAS, y sumar una entrada ahi cambia 9 oraciones; ese cableado es un paso aparte (L1c).
No escribe en disco, en el warehouse ni en el repo, no hace llamadas de red y no tiene __main__.

API publica (lo unico que usa quien lo cablea):
  ENTRADA = "diario.csv"   etiqueta de los mensajes y texto que se agrega a local.ENTRADAS (contiene "diari").
  leer(con, ruta) -> dict  lee el CSV en la base DuckDB en memoria con (la que devuelve local.armar_base, con la tabla dim_pozo),
                           valida, arma las tablas de salida y devuelve info.

Columnas de diario.csv, una fila por (pozo, dia). Todo se lee como texto y se convierte con las plantillas de pipeline.local
(local._E_INT, local._E_DBL, local._E_FECHA); los nombres de columna se normalizan con local._normalizar_columnas (BOM, espacios).
  * pozo_id            obligatoria, entero, mismos ids que pozos.csv.
  * fecha              obligatoria, YYYY-MM-DD.
  * petroleo_m3        obligatoria, petroleo del dia. Negativo o vacio pasan a 0 (igual que mensual.csv); no interpretable o no finito
                       (nan, inf) tambien pasa a 0 y se cuenta aparte.
  * agua_m3            opcional, agua del dia. Negativa, no interpretable o no finita queda nula (como mensual.csv); vacia es nula.
  * horas_produccion   opcional, horas en produccion ese dia, de 0 a 24; vacia es nula.

Validaciones y salida (error = SystemExit con codigo 2 y un mensaje que nombra columnas y conteos, NUNCA valores de las celdas;
aviso = conteo en info["avisos"], lista de textos en espanol):
  error  el archivo no se puede leer;
  error  falta una columna obligatoria (se nombra);
  error  el archivo no trae filas;
  error  pozo_id no interpretable como entero (cuenta de filas);
  error  fecha no interpretable (cuenta de filas);
  error  (pozo_id, fecha) repetido (cuenta de pares repetidos);
  error  horas_produccion presente pero no interpretable, no finita o fuera de [0, 24] (cuenta de filas);
  error  ninguna fila corresponde a un pozo de dim_pozo (igual que mensual.csv), o la conexion no trae dim_pozo;
  aviso  filas de pozos que no estan en dim_pozo: se ignoran y se cuentan (como local.leer_csvs con el mensual);
  aviso  petroleo_m3 vacio o negativo, pasado a 0 (conteo);
  aviso  petroleo_m3 no interpretable o no finito, pasado a 0 (conteo);
  aviso  agua_m3 negativa, no interpretable o no finita, dejada nula (conteo);
  aviso  meses del diario que difieren del mensual (ver diario_contra_mensual), solo si la conexion trae fct_produccion.

Transformaciones: un dia "produjo" si petroleo_m3 > 0 o horas_produccion > 0 (horas nulas no cuentan); un dia registrado con
petroleo 0 y sin horas NO produjo. Un dia sin fila no es un dia sin produccion: dias_registrados y dias_mes (dias del mes
calendario, el 2024-02 tiene 29) se informan por separado y completo = (dias_registrados = dias_mes). El mes es el primer dia del mes.

Tablas de salida en con (se reemplazan si ya existen):
  * fct_diario: pozo_id, fecha, petroleo_m3, agua_m3, horas_produccion, produjo. Solo pozos de dim_pozo.
  * diario_mes: una fila por (pozo_id, mes): petroleo_m3 (suma), agua_m3 (suma; nula si todos los dias son nulos), dias_registrados
    (filas), dias_con_produccion (dias con produjo), dias_mes, completo.
  * diario_contra_mensual (solo si con trae fct_produccion): por (pozo_id, mes) presente en los dos, petroleo_mensual_m3 (el de
    fct_produccion), petroleo_diario_m3 (la suma diaria) y difiere = |diario - mensual| mayor que TOLERANCIA_MENSUAL por el valor
    mensual (los dos en cero no difieren; mensual en cero y diario mayor que cero si). Un mes con dias faltantes puede diferir por eso.
    Es un aviso, nunca un error. info trae meses_comparados y meses_difieren.

info: filas_leidas, filas_ignoradas (pozos fuera de dim_pozo), filas_usadas, pozos, fecha_desde y fecha_hasta (YYYY-MM-DD, texto),
meses (filas de diario_mes), meses_comparados y meses_difieren (None si no hay fct_produccion), con_agua, con_horas, avisos.

Que NO prueba: lee y agrega. No estima ningun efecto, no separa dias sin produccion de dias sin registro mas alla de los conteos de
arriba, no compara dias contra caudal ni etiqueta cierres preventivos (eso es un analisis aparte con su propia regla). Que el diario
coincida con el mensual dentro de la tolerancia no prueba que ninguno de los dos sea correcto.
"""
from __future__ import annotations

from pipeline import local

ENTRADA = "diario.csv"
DIARIO_OBLIGATORIAS = ("pozo_id", "fecha", "petroleo_m3")
DIARIO_OPCIONALES = ("agua_m3", "horas_produccion")
HORAS_MAX = 24.0
TOLERANCIA_MENSUAL = 0.02


def _num(col: str) -> str:
    """Expresion SQL: el numero de la celda, o nulo si esta vacia, no se interpreta o no es finita (nan, inf)."""
    e = local._E_DBL.format(c=col)
    return f"case when isfinite({e}) then {e} end"


def _tiene_tabla(con, tabla: str) -> bool:
    return con.execute("select count(*) from information_schema.tables where table_name = ?", [tabla]).fetchone()[0] > 0


def leer(con, ruta) -> dict:
    """Lee diario.csv en la base con, lo valida y arma fct_diario, diario_mes y (si hay fct_produccion) diario_contra_mensual.

    Los errores de entrada salen con SystemExit 2 y un mensaje con columnas y conteos, nunca valores de las celdas.
    Devuelve info (ver el encabezado del modulo). No escribe nada fuera de con.
    """
    if not _tiene_tabla(con, "dim_pozo"):
        local._error(f"{ENTRADA}: la base no trae dim_pozo (se lee despues de local.armar_base).")
    p = str(ruta).replace("'", "''")
    try:
        con.execute(f"create or replace table raw_diario as select * from read_csv('{p}', header = true, all_varchar = true)")
    except Exception:
        local._error(f"{ENTRADA}: no se pudo leer el archivo (¿existe y es un CSV con encabezado?).")
    try:
        return _validar_y_armar(con)
    finally:
        con.execute("drop table if exists raw_diario")


def _validar_y_armar(con) -> dict:
    local._normalizar_columnas(con, "raw_diario")
    cols = set(local._columnas(con, "raw_diario"))
    faltan = [c for c in DIARIO_OBLIGATORIAS if c not in cols]
    if faltan:
        local._error(f"{ENTRADA}: faltan columnas obligatorias: {', '.join(faltan)}.")
    n_leidas = con.execute("select count(*) from raw_diario").fetchone()[0]
    if n_leidas == 0:
        local._error(f"{ENTRADA}: el archivo no trae filas diarias.")
    con_agua = "agua_m3" in cols
    con_horas = "horas_produccion" in cols
    id_ = local._E_INT.format(c="pozo_id")
    fecha = local._E_FECHA.format(c="fecha")
    n = con.execute(f"select count(*) from raw_diario where {id_} is null").fetchone()[0]
    if n:
        local._error(f"{ENTRADA}: {n} filas con pozo_id no interpretable como entero (columna pozo_id).")
    n = con.execute(f"select count(*) from raw_diario where {fecha} is null").fetchone()[0]
    if n:
        local._error(f"{ENTRADA}: {n} filas con fecha no interpretable (columna fecha, formato YYYY-MM-DD).")
    n = con.execute(f"""select count(*) from (select 1 from raw_diario group by {id_}, {fecha}
        having count(*) > 1) t""").fetchone()[0]
    if n:
        local._error(f"{ENTRADA}: (pozo_id, fecha) repetido (columnas pozo_id y fecha): {n} pares repetidos.")
    hor = local._E_DBL.format(c="horas_produccion")
    if con_horas:
        n = con.execute(f"""select count(*) from raw_diario
            where nullif(trim(horas_produccion), '') is not null
            and not coalesce(isfinite({hor}) and {hor} >= 0 and {hor} <= {HORAS_MAX}, false)""").fetchone()[0]
        if n:
            local._error(f"{ENTRADA}: {n} filas con horas_produccion no interpretable o fuera de [0, {HORAS_MAX:g}] "
                         "(columna horas_produccion).")
    n_ign = con.execute(f"""select count(*) from raw_diario where {id_} not in (select pozo_id from dim_pozo)""").fetchone()[0]
    pet, pet_raw = _num("petroleo_m3"), "nullif(trim(petroleo_m3), '')"
    n_pet0 = con.execute(f"""select count(*) from raw_diario where {id_} in (select pozo_id from dim_pozo)
        and ({pet_raw} is null or {pet} < 0)""").fetchone()[0]
    n_pet_mal = con.execute(f"""select count(*) from raw_diario where {id_} in (select pozo_id from dim_pozo)
        and {pet_raw} is not null and {pet} is null""").fetchone()[0]
    ag = _num("agua_m3")
    n_agua = con.execute(f"""select count(*) from raw_diario where {id_} in (select pozo_id from dim_pozo)
        and nullif(trim(agua_m3), '') is not null and ({ag} is null or {ag} < 0)""").fetchone()[0] if con_agua else 0
    agua_sel = f"case when {ag} >= 0 then {ag} end" if con_agua else "cast(null as double)"
    horas_sel = hor if con_horas else "cast(null as double)"
    con.execute(f"""create or replace table fct_diario as
        with d as (
            select {id_} as pozo_id, {fecha} as fecha,
                case when {pet} >= 0 then {pet} else 0.0 end as petroleo_m3,
                {agua_sel} as agua_m3, {horas_sel} as horas_produccion
            from raw_diario
        )
        select d.pozo_id, d.fecha, d.petroleo_m3, d.agua_m3, d.horas_produccion,
            (d.petroleo_m3 > 0 or coalesce(d.horas_produccion > 0, false)) as produjo
        from d join (select distinct pozo_id from dim_pozo) p using (pozo_id)
        order by d.pozo_id, d.fecha""")
    n_usadas = con.execute("select count(*) from fct_diario").fetchone()[0]
    if n_usadas == 0:
        local._error(f"{ENTRADA}: ninguna fila corresponde a un pozo de dim_pozo (columna pozo_id).")
    con.execute("""create or replace table diario_mes as
        select pozo_id, cast(date_trunc('month', fecha) as date) as mes, sum(petroleo_m3) as petroleo_m3,
            sum(agua_m3) as agua_m3, count(*)::integer as dias_registrados,
            count(*) filter (where produjo)::integer as dias_con_produccion,
            extract(day from last_day(date_trunc('month', min(fecha))))::integer as dias_mes,
            count(*) = extract(day from last_day(date_trunc('month', min(fecha)))) as completo
        from fct_diario group by pozo_id, cast(date_trunc('month', fecha) as date)
        order by pozo_id, mes""")
    n_comp = n_dif = None
    if _tiene_tabla(con, "fct_produccion"):
        con.execute(f"""create or replace table diario_contra_mensual as
            select d.pozo_id, d.mes, m.petroleo_m3 as petroleo_mensual_m3, d.petroleo_m3 as petroleo_diario_m3,
                abs(d.petroleo_m3 - m.petroleo_m3) > {TOLERANCIA_MENSUAL} * abs(m.petroleo_m3) as difiere
            from diario_mes d join fct_produccion m on m.pozo_id = d.pozo_id and cast(m.mes as date) = d.mes
            order by d.pozo_id, d.mes""")
        n_comp, n_dif = con.execute("select count(*), count(*) filter (where difiere) from diario_contra_mensual").fetchone()
    dmin, dmax, n_pozos = con.execute("select min(fecha), max(fecha), count(distinct pozo_id) from fct_diario").fetchone()
    n_meses = con.execute("select count(*) from diario_mes").fetchone()[0]
    avisos = []
    if n_ign:
        avisos.append(f"Se ignoraron {n_ign} filas del diario con pozo ausente en pozos.csv.")
    if n_pet0:
        avisos.append(f"{n_pet0} filas del diario traen petroleo_m3 vacío o negativo; se tomaron como 0.")
    if n_pet_mal:
        avisos.append(f"{n_pet_mal} filas del diario traen petroleo_m3 no interpretable; se tomaron como 0.")
    if n_agua:
        avisos.append(f"{n_agua} filas del diario traen agua_m3 negativa o no interpretable; se tomaron como sin dato.")
    if n_dif:
        avisos.append(f"{n_dif} de {n_comp} meses del diario difieren del mensual en más de "
                      f"{TOLERANCIA_MENSUAL:.0%} del valor mensual (un mes con días faltantes puede diferir por eso).")
    return {"filas_leidas": n_leidas, "filas_ignoradas": n_ign, "filas_usadas": n_usadas, "pozos": n_pozos,
            "fecha_desde": dmin.isoformat(), "fecha_hasta": dmax.isoformat(), "meses": n_meses,
            "meses_comparados": n_comp, "meses_difieren": n_dif, "con_agua": con_agua, "con_horas": con_horas,
            "avisos": avisos}
