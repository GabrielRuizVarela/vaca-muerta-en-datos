-- Nucleo de Wyoming con los mismos nombres y columnas que el warehouse del Colorado (fct_produccion, ultimo_mes,
-- dim_pozo, co_pozo_pad, co_hijo), mas lo propio de Wyoming. Todo se reconstruye con create or replace.
-- Parametros: {bbl_a_m3}, {mcf_a_miles_m3}, {horizontal_tvd_min_ft}, {horizontal_lateral_min_ft}, {ft_a_m}, {ventana_ini}, {ventana_fin}, {fecha_dudosa_dias},
-- {pad_km}, {km_por_grado}.

-- Una fila por (pozo, mes). Cada fila de la fuente (pozo y anio) se abre en sus doce meses; las filas repetidas de un
-- mismo pozo y anio se SUMAN al pozo y mes, y los dias efectivos son el maximo. El petroleo NULL del mes es 0.
-- Dias fuera de 0 a 31 (la fuente trae 99, un codigo y no un conteo) se excluyen del maximo; el maximo valido se topa
-- en el largo del mes.
create or replace table fct_produccion as
with u as (
    select
        pozo_id, operador, field,
        make_date(anio, m, 1) as mes,
        case m when 1 then oil_01 when 2 then oil_02 when 3 then oil_03 when 4 then oil_04 when 5 then oil_05
                 when 6 then oil_06 when 7 then oil_07 when 8 then oil_08 when 9 then oil_09 when 10 then oil_10
                 when 11 then oil_11 else oil_12 end as oil_bbl,
        case m when 1 then gas_01 when 2 then gas_02 when 3 then gas_03 when 4 then gas_04 when 5 then gas_05
                 when 6 then gas_06 when 7 then gas_07 when 8 then gas_08 when 9 then gas_09 when 10 then gas_10
                 when 11 then gas_11 else gas_12 end as gas_mcf,
        case m when 1 then water_01 when 2 then water_02 when 3 then water_03 when 4 then water_04 when 5 then water_05
                 when 6 then water_06 when 7 then water_07 when 8 then water_08 when 9 then water_09 when 10 then water_10
                 when 11 then water_11 else water_12 end as water_bbl,
        case m when 1 then days_01 when 2 then days_02 when 3 then days_03 when 4 then days_04 when 5 then days_05
                 when 6 then days_06 when 7 then days_07 when 8 then days_08 when 9 then days_09 when 10 then days_10
                 when 11 then days_11 else days_12 end as dias
    from stg_wy_produccion
    cross join (values (1), (2), (3), (4), (5), (6), (7), (8), (9), (10), (11), (12)) t(m)
    where pozo_id is not null and anio is not null
)
select
    pozo_id,
    mes,
    arg_max(operador, (coalesce(oil_bbl, 0), field))  as operador,
    arg_max(field, (coalesce(oil_bbl, 0), field))     as formacion,
    greatest(coalesce(sum(oil_bbl), 0), 0)::double * {bbl_a_m3}     as petroleo_m3,
    greatest(coalesce(sum(gas_mcf), 0), 0)::double * {mcf_a_miles_m3} as gas_miles_m3,
    greatest(coalesce(sum(water_bbl), 0), 0)::double * {bbl_a_m3}   as agua_m3,
    case when max(case when dias between 0 and 31 then dias end) is null then cast(null as integer)
         else least(max(case when dias between 0 and 31 then dias end), day(last_day(mes))) end as dias_efectivos,
    day(last_day(mes))                          as dias_mes,
    null::varchar                               as estado,
    null::varchar                               as extraccion
from u
group by pozo_id, mes
order by pozo_id, mes;

create or replace table ultimo_mes as select max(mes) as mes from fct_produccion;

-- Condado a nombre, desde los encabezados (el nombre mas frecuente de cada codigo).
create or replace table co_condado as
select condado, arg_max(condado_nombre, (n, condado_nombre)) as nombre
from (select lpad(cast(pozo_id // 100000 as varchar), 3, '0') as condado, condado_nombre, count(*) as n
      from stg_wy_pozos where pozo_id is not null and condado_nombre is not null group by all)
group by condado
order by condado;

-- Un pozo por fila: los encabezados mas los pozos que solo aparecen en produccion. Atributos de produccion del ultimo mes reportado.
create or replace table dim_pozo as
with ult as (
    select pozo_id, arg_max(operador, mes) as operador, arg_max(formacion, mes) as formacion
    from fct_produccion group by pozo_id
), inicio as (
    select pozo_id,
           min(mes) filter (where petroleo_m3 > 0) as primer_mes_petroleo,
           min(mes) filter (where petroleo_m3 > 0 or gas_miles_m3 > 0) as primer_mes_produccion
    from fct_produccion group by pozo_id
), universo as (
    select pozo_id from stg_wy_pozos union select pozo_id from fct_produccion
)
select
    u.pozo_id,
    w.unidad                                                    as sigla,
    coalesce(ult.operador, w.operador)                          as operador,
    ult.formacion                                               as formacion,
    case when coalesce(w.td_ft > {horizontal_tvd_min_ft} and w.md_ft - w.td_ft > {horizontal_lateral_min_ft}, false) then 'HORIZONTAL'
         when w.md_ft is not null and w.td_ft is not null then 'VERTICAL'
         else 'SIN_DATO' end                                    as subtipo_recurso,
    w.clase                                                     as tipo_pozo,
    upper(w.estado)                                             as estado,
    null::varchar                                               as yacimiento,
    coalesce(c.nombre, 'condado ' || lpad(cast(u.pozo_id // 100000 as varchar), 3, '0')) as area,
    'Wyoming'                                                   as provincia,
    w.lon, w.lat,
    i.primer_mes_petroleo, i.primer_mes_produccion,
    -- lo propio de Wyoming
    lpad(cast(u.pozo_id // 100000 as varchar), 3, '0')          as condado,
    w.md_ft, w.td_ft as tvd_ft,
    case when w.md_ft is not null and w.td_ft is not null then greatest(w.md_ft - w.td_ft, 0) * {ft_a_m} end as rama_horizontal_m,
    coalesce(w.td_ft > {horizontal_tvd_min_ft} and w.md_ft - w.td_ft > {horizontal_lateral_min_ft}, false) as horizontal,
    w.fecha_spud,
    null::varchar                                               as calidad_ubicacion,
    i.primer_mes_petroleo is not null and i.primer_mes_petroleo = (select min(mes) from fct_produccion) as primer_petroleo_censurado,
    ult.pozo_id is not null                                     as con_produccion,
    w.pozo_id is not null                                       as en_archivo_pozos
from universo u
left join stg_wy_pozos w using (pozo_id)
left join ult using (pozo_id)
left join inicio i using (pozo_id)
left join co_condado c on c.condado = lpad(cast(u.pozo_id // 100000 as varchar), 3, '0')
order by u.pozo_id;

-- Pads: componentes conexos de ubicaciones de superficie a menos de {pad_km} km (la misma regla que Colorado);
-- pad_id = 'p' || el menor pozo_id del componente, estable entre builds.
-- Las celdas de 0,001 grados (mas grandes que {pad_km} km) acotan los candidatos con un join por igualdad; el filtro de distancia decide.
create or replace table co_pozo_arista as
with celda as (
    select pozo_id, lat, lon, cast(floor(lat * 1000) as bigint) as cy, cast(floor(lon * 1000) as bigint) as cx
    from dim_pozo where lat is not null and lon is not null
)
select a.pozo_id as a, b.pozo_id as b
from celda a
cross join (values (-1), (0), (1)) dy(i)
cross join (values (-1), (0), (1)) dx(j)
join celda b on b.cy = a.cy + dy.i and b.cx = a.cx + dx.j and b.pozo_id <> a.pozo_id
where {km_por_grado} * sqrt(power((a.lon - b.lon) * cos(radians(a.lat)), 2) + power(a.lat - b.lat, 2)) < {pad_km}
order by 1, 2;

create or replace table co_pozo_pad as
with recursive lab(pozo_id, etiqueta) as (
    select pozo_id, pozo_id from dim_pozo where lat is not null and lon is not null
    union
    select e.b, l.etiqueta from lab l join co_pozo_arista e on e.a = l.pozo_id
)
select pozo_id, 'p' || min(etiqueta) as pad_id from lab group by pozo_id order by pozo_id;

-- Candidatos a hijo: la fecha de primera terminacion (FIRSTCOMP) de cada pozo. Es hijo si cae en la ventana de meses, el
-- pozo esta en los encabezados con coordenadas, es horizontal, tiene petroleo en el archivo y la fecha no es dudosa
-- (mas de {fecha_dudosa_dias} dias despues de su primer petroleo).
create or replace table co_hijo as
with x as (
    select
        w.pozo_id,
        w.fecha_firstcomp as fecha_frac,
        date_trunc('month', w.fecha_firstcomp)::date as mes_frac,
        w.fecha_firstcomp between date '{ventana_ini}' and date '{ventana_fin}' as en_ventana,
        true as en_archivo_pozos,
        coalesce(d.lat is not null and d.lon is not null, false) as con_coordenadas,
        coalesce(d.horizontal, false) as horizontal,
        d.primer_mes_petroleo,
        date_diff('day', d.primer_mes_petroleo, w.fecha_firstcomp) as dias_desde_primer_petroleo
    from stg_wy_pozos w
    left join dim_pozo d using (pozo_id)
    where w.fecha_firstcomp is not null
)
select
    pozo_id, fecha_frac, mes_frac, en_ventana, en_archivo_pozos, con_coordenadas, horizontal,
    coalesce(dias_desde_primer_petroleo > {fecha_dudosa_dias}, false) as fecha_dudosa,
    primer_mes_petroleo, dias_desde_primer_petroleo,
    en_ventana and en_archivo_pozos and con_coordenadas and horizontal and primer_mes_petroleo is not null
        and not coalesce(dias_desde_primer_petroleo > {fecha_dudosa_dias}, false) as hijo
from x
order by pozo_id;
