-- Staging de Wyoming: tipado y unidades. Una fila por fila de la fuente (pozo y anio en produccion; pozo en encabezados).
-- Parametros: {produccion_csvs} (lista SQL de rutas), {pozos_csv}, {bbl_a_m3}, {mcf_a_miles_m3}.
-- pozo_id = APINO como entero: condado (3 digitos) + secuencia (5 digitos), igual que en Colorado.
-- FIRSTCOMP (y FIRSTSPUD) viene como AAAAMMDD o AAAAMDD (mes sin cero: 2024615 es el 2024-06-15); lo que no se lee
-- como una fecha valida es NULL y se cuenta en la conciliacion.

create or replace table stg_wy_produccion as
select
    try_cast(try_cast(APINO as double) as bigint)              as pozo_id,
    APINO                                                     as apino,
    try_cast(YR as integer)                                   as anio,
    nullif(trim(COMPANY), '')                                 as operador,
    nullif(lower(trim(FIELD)), '')                            as field,
    try_cast(JAN_OIL as double) as oil_01, try_cast(JAN_GAS as double) as gas_01,
    try_cast(JAN_WATER as double) as water_01, try_cast(JAN_DAYS as integer) as days_01,
    try_cast(FEB_OIL as double) as oil_02, try_cast(FEB_GAS as double) as gas_02,
    try_cast(FEB_WATER as double) as water_02, try_cast(FEB_DAYS as integer) as days_02,
    try_cast(MAR_OIL as double) as oil_03, try_cast(MAR_GAS as double) as gas_03,
    try_cast(MAR_WATER as double) as water_03, try_cast(MAR_DAYS as integer) as days_03,
    try_cast(APR_OIL as double) as oil_04, try_cast(APR_GAS as double) as gas_04,
    try_cast(APR_WATER as double) as water_04, try_cast(APR_DAYS as integer) as days_04,
    try_cast(MAY_OIL as double) as oil_05, try_cast(MAY_GAS as double) as gas_05,
    try_cast(MAY_WATER as double) as water_05, try_cast(MAY_DAYS as integer) as days_05,
    try_cast(JUN_OIL as double) as oil_06, try_cast(JUN_GAS as double) as gas_06,
    try_cast(JUN_WATER as double) as water_06, try_cast(JUN_DAYS as integer) as days_06,
    try_cast(JUL_OIL as double) as oil_07, try_cast(JUL_GAS as double) as gas_07,
    try_cast(JUL_WATER as double) as water_07, try_cast(JUL_DAYS as integer) as days_07,
    try_cast(AUG_OIL as double) as oil_08, try_cast(AUG_GAS as double) as gas_08,
    try_cast(AUG_WATER as double) as water_08, try_cast(AUG_DAYS as integer) as days_08,
    try_cast(SEP_OIL as double) as oil_09, try_cast(SEP_GAS as double) as gas_09,
    try_cast(SEP_WATER as double) as water_09, try_cast(SEP_DAYS as integer) as days_09,
    try_cast(OCT_OIL as double) as oil_10, try_cast(OCT_GAS as double) as gas_10,
    try_cast(OCT_WATER as double) as water_10, try_cast(OCT_DAYS as integer) as days_10,
    try_cast(NOV_OIL as double) as oil_11, try_cast(NOV_GAS as double) as gas_11,
    try_cast(NOV_WATER as double) as water_11, try_cast(NOV_DAYS as integer) as days_11,
    try_cast(DEC_OIL as double) as oil_12, try_cast(DEC_GAS as double) as gas_12,
    try_cast(DEC_WATER as double) as water_12, try_cast(DEC_DAYS as integer) as days_12
from read_csv({produccion_csvs}, header = true, all_varchar = true, union_by_name = true, quote = '"');

-- Encabezados de pozos de WOGCC (el DBF WH; la columna de direccion HORIZ_DIR no se usa, ver la regla fijada).
-- Si un APINO aparece dos veces se conserva la fila con el spud mas antiguo.
create or replace table stg_wy_pozos as
select
    try_cast(try_cast(APINO as double) as bigint)             as pozo_id,
    APINO                                                     as apino,
    nullif(trim(COMPANY), '')                                 as operador,
    nullif(trim(UNIT_LEASE), '')                              as unidad,
    nullif(trim(FIELD_NAME), '')                              as campo,
    nullif(trim(BASIN), '')                                   as cuenca,
    nullif(trim(COUNTYTXT), '')                               as condado_nombre,
    nullif(trim(COUNTY), '')                                  as condado_codigo,
    try_cast(LON as double)                                   as lon,
    try_cast(LAT as double)                                   as lat,
    try_cast(TD as double)                                    as td_ft,
    try_cast(MD as double)                                    as md_ft,
    nullif(trim(WELL_CLASS), '')                              as clase,
    case when length(trim(FIRSTSPUD)) = 7 and try_cast(trim(FIRSTSPUD) as bigint) is not null
         then try_strptime(substr(trim(FIRSTSPUD), 1, 4) || '0' || substr(trim(FIRSTSPUD), 5, 3), '%Y%m%d')::date
         else try_strptime(trim(FIRSTSPUD), '%Y%m%d')::date end as fecha_spud,
    -- Siete digitos: AAAAMDD (mes sin cero) o AAAAMMD (dia sin cero). Si se leen como fecha valida de las dos maneras
    -- (por ejemplo 2024104: 4 de enero o 4 de octubre) la fecha es ambigua y no se lee: el pozo queda afuera y se cuenta.
    case when length(trim(FIRSTCOMP)) = 7 and try_cast(trim(FIRSTCOMP) as bigint) is not null
         then case when try_strptime(substr(trim(FIRSTCOMP), 1, 6) || '0' || substr(trim(FIRSTCOMP), 7, 1), '%Y%m%d') is not null then null
                   else try_strptime(substr(trim(FIRSTCOMP), 1, 4) || '0' || substr(trim(FIRSTCOMP), 5, 3), '%Y%m%d')::date end
         else try_strptime(trim(FIRSTCOMP), '%Y%m%d')::date end as fecha_firstcomp,
    coalesce(length(trim(FIRSTCOMP)) = 7 and try_cast(trim(FIRSTCOMP) as bigint) is not null
             and try_strptime(substr(trim(FIRSTCOMP), 1, 6) || '0' || substr(trim(FIRSTCOMP), 7, 1), '%Y%m%d') is not null
             and try_strptime(substr(trim(FIRSTCOMP), 1, 4) || '0' || substr(trim(FIRSTCOMP), 5, 3), '%Y%m%d') is not null, false) as firstcomp_ambigua,
    nullif(trim(FIRSTCOMP), '')                               as firstcomp_crudo,
    nullif(trim(STATUS), '')                                  as estado
from read_csv('{pozos_csv}', header = true, all_varchar = true, quote = '"')
where APINO <> ''
qualify row_number() over (partition by try_cast(try_cast(APINO as double) as bigint)
                           order by try_strptime(trim(FIRSTSPUD), '%Y%m%d') asc nulls last) = 1;
