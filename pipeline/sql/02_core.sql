-- Core model. Grain of fct_produccion: one row per (pozo_id, mes).

create or replace table fct_produccion as
select
    pozo_id,
    mes,
    operador,
    formacion,
    greatest(coalesce(petroleo_m3, 0), 0)  as petroleo_m3,
    greatest(coalesce(gas_miles_m3, 0), 0) as gas_miles_m3,
    greatest(coalesce(agua_m3, 0), 0)      as agua_m3,
    dias_efectivos,
    day(last_day(mes))                     as dias_mes
from stg_produccion
where pozo_id is not null and mes is not null;

-- Last month that the source covers; months after it are not "missing", just not published yet.
create or replace table ultimo_mes as select max(mes) as mes from fct_produccion;

-- One row per well. Attributes come from the well's latest reported month.
create or replace table dim_pozo as
with ultimo as (
    select *, row_number() over (partition by pozo_id order by mes desc) as rn
    from stg_produccion where pozo_id is not null
), inicio as (
    select pozo_id,
           min(mes) filter (where petroleo_m3 > 0) as primer_mes_petroleo,
           min(mes) filter (where petroleo_m3 > 0 or gas_miles_m3 > 0) as primer_mes_produccion
    from fct_produccion group by pozo_id
)
select u.pozo_id, u.sigla, u.operador, u.formacion, u.subtipo_recurso, u.tipo_pozo, u.estado,
       u.yacimiento, u.area, u.provincia, u.lon, u.lat,
       i.primer_mes_petroleo, i.primer_mes_produccion
from ultimo u join inicio i using (pozo_id)
where u.rn = 1;

-- One row per fractured well. Some wells report several stimulation jobs; they are summed.
-- Jobs dated after the extraction date are excluded here and reported by the checks.
create or replace table dim_fractura_pozo as
select
    pozo_id,
    any_value(operador)          as operador,
    min(fecha_inicio)            as primera_fractura,
    count(*)                     as trabajos,
    max(rama_horizontal_m)       as rama_horizontal_m,
    sum(etapas)                  as etapas,
    sum(arena_tn)                as arena_tn,
    sum(agua_m3)                 as agua_m3
from stg_fractura
where pozo_id is not null and (fecha_inicio is null or fecha_inicio <= current_date)
group by pozo_id;
