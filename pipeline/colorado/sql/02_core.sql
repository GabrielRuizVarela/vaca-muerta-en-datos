-- Nucleo del Colorado con los mismos nombres y columnas que el warehouse de Vaca Muerta (fct_produccion, ultimo_mes, dim_pozo,
-- stg_fractura, dim_fractura_pozo), mas lo propio del Colorado (co_hijo, co_pozo_pad). Todo se reconstruye con create or replace.
-- Parametros: {bbl_a_m3}, {mcf_a_miles_m3}, {horizontal_tvd_min_ft}, {horizontal_lateral_min_ft}, {ft_a_m}, {ventana_ini}, {ventana_fin}, {fecha_dudosa_dias},
-- {pad_km}, {km_por_grado}.

-- Una fila por (pozo, mes). El archivo no trae duplicados de (pozo, sidetrack, formacion, mes); si una revision los trajera, gana la
-- ultima aceptada. Se suman las formaciones y los sidetracks del pozo; los dias efectivos son el maximo.
create or replace table fct_produccion as
with d as (
    select * from stg_co_produccion
    where pozo_id is not null and mes is not null
    qualify row_number() over (partition by pozo_id, sidetrack, formacion, mes
                               order by aceptado desc nulls last, doc desc nulls last) = 1
)
select
    pozo_id,
    mes,
    arg_max(operador, (coalesce(petroleo_m3, 0), formacion, sidetrack))  as operador,
    arg_max(formacion, (coalesce(petroleo_m3, 0), formacion, sidetrack)) as formacion,
    -- La suma se hace en decimal (exacta, sin depender del orden de los hilos) y recien despues se pasa de unidades.
    greatest(coalesce(sum(petroleo_bbl), 0), 0)::double * {bbl_a_m3}     as petroleo_m3,
    greatest(coalesce(sum(gas_mcf), 0), 0)::double * {mcf_a_miles_m3}    as gas_miles_m3,
    greatest(coalesce(sum(agua_bbl), 0), 0)::double * {bbl_a_m3}         as agua_m3,
    max(dias)                                   as dias_efectivos,
    day(last_day(mes))                          as dias_mes,
    arg_max(estado, (coalesce(petroleo_m3, 0), formacion, sidetrack)) as estado,
    null::varchar                               as extraccion
from d
group by pozo_id, mes
order by pozo_id, mes;

create or replace table ultimo_mes as select max(mes) as mes from fct_produccion;

-- Condado a nombre, desde FracFocus (el nombre mas frecuente de cada codigo).
create or replace table co_condado as
select condado, arg_max(condado_nombre, (n, condado_nombre)) as nombre
from (select condado, condado_nombre, count(*) as n from stg_co_fracfocus where condado_nombre is not null group by all)
group by condado
order by condado;

-- Un pozo por fila: el archivo de pozos mas los pozos que solo aparecen en produccion. Atributos de produccion del ultimo mes reportado.
create or replace table dim_pozo as
with ult as (
    select pozo_id, arg_max(operador, mes) as operador, arg_max(formacion, mes) as formacion, arg_max(estado, mes) as estado
    from fct_produccion group by pozo_id
), inicio as (
    select pozo_id,
           min(mes) filter (where petroleo_m3 > 0) as primer_mes_petroleo,
           min(mes) filter (where petroleo_m3 > 0 or gas_miles_m3 > 0) as primer_mes_produccion
    from fct_produccion group by pozo_id
), universo as (
    select pozo_id from stg_co_pozos union select pozo_id from fct_produccion
)
select
    u.pozo_id,
    w.nombre                                                    as sigla,
    coalesce(ult.operador, w.operador)                          as operador,
    ult.formacion                                               as formacion,
    case when coalesce(w.tvd_ft > {horizontal_tvd_min_ft} and w.md_ft - w.tvd_ft > {horizontal_lateral_min_ft}, false) then 'HORIZONTAL'
         when w.md_ft is not null and w.tvd_ft is not null then 'VERTICAL'
         else 'SIN_DATO' end                                    as subtipo_recurso,
    w.clase                                                     as tipo_pozo,
    coalesce(ult.estado, upper(w.estado))                       as estado,
    null::varchar                                               as yacimiento,
    coalesce(c.nombre, 'condado ' || lpad(cast(u.pozo_id // 100000 as varchar), 3, '0')) as area,
    'Colorado'                                                  as provincia,
    w.lon, w.lat,
    i.primer_mes_petroleo, i.primer_mes_produccion,
    -- lo propio del Colorado
    lpad(cast(u.pozo_id // 100000 as varchar), 3, '0')          as condado,
    w.md_ft, w.tvd_ft,
    case when w.md_ft is not null and w.tvd_ft is not null then greatest(w.md_ft - w.tvd_ft, 0) * {ft_a_m} end as rama_horizontal_m,
    coalesce(w.tvd_ft > {horizontal_tvd_min_ft} and w.md_ft - w.tvd_ft > {horizontal_lateral_min_ft}, false) as horizontal,
    w.fecha_spud,
    w.calidad_ubicacion,
    i.primer_mes_petroleo is not null and i.primer_mes_petroleo = (select min(mes) from fct_produccion) as primer_petroleo_censurado,
    ult.pozo_id is not null                                     as con_produccion,
    w.pozo_id is not null                                       as en_archivo_pozos
from universo u
left join stg_co_pozos w using (pozo_id)
left join ult using (pozo_id)
left join inicio i using (pozo_id)
left join co_condado c on c.condado = lpad(cast(u.pozo_id // 100000 as varchar), 3, '0')
order by u.pozo_id;

-- Pads: componentes conexos de ubicaciones de superficie a menos de {pad_km} km (la misma regla que 04_interferencia.sql);
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

-- Divulgaciones al formato de stg_fractura de Vaca Muerta. El largo de rama es el proxy MD menos TVD; sin etapas ni arena.
create or replace table stg_fractura as
select
    row_number() over (order by f.divulgacion)  as fractura_id,
    f.pozo_id,
    f.operador,
    null::varchar                               as formacion,
    null::varchar                               as subtipo_recurso,
    f.fecha_inicio,
    f.fecha_fin,
    case when d.horizontal then d.rama_horizontal_m end as rama_horizontal_m,
    null::integer                               as etapas,
    null::double                                as arena_tn,
    f.agua_m3,
    null::varchar                               as terminacion,
    null::double                                as presion_maxima_psi,
    f.api14, f.sidetrack, f.divulgacion
from stg_co_fracfocus f
left join dim_pozo d on d.pozo_id = f.pozo_id
order by f.divulgacion;

-- Un pozo fracturado por fila. Los trabajos despues del ultimo mes de produccion no se observan y quedan fuera.
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
where pozo_id is not null and (fecha_inicio is null or fecha_inicio < (select mes from ultimo_mes) + interval 1 month)
group by pozo_id
order by pozo_id;

-- Candidatos a hijo: la PRIMERA divulgacion de cada pozo (de cualquier ano). Es hijo si esta en la ventana de meses, el pozo esta en el
-- archivo de pozos con coordenadas, es horizontal y la fecha no es dudosa (mas de {fecha_dudosa_dias} dias despues de su primer petroleo).
create or replace table co_hijo as
with prim as (
    select pozo_id, min(fecha_inicio) as fecha_frac, count(*) as divulgaciones
    from stg_co_fracfocus where pozo_id is not null and fecha_inicio is not null group by pozo_id
), x as (
    select
        p.pozo_id, p.fecha_frac, date_trunc('month', p.fecha_frac)::date as mes_frac, p.divulgaciones,
        coalesce(d.en_archivo_pozos, false) as en_archivo_pozos,
        coalesce(d.lat is not null and d.lon is not null, false) as con_coordenadas,
        coalesce(d.horizontal, false) as horizontal,
        d.primer_mes_petroleo,
        date_diff('day', d.primer_mes_petroleo, p.fecha_frac) as dias_desde_primer_petroleo,
        p.fecha_frac between date '{ventana_ini}' and date '{ventana_fin}' as en_ventana
    from prim p left join dim_pozo d using (pozo_id)
)
select x.*,
       coalesce(dias_desde_primer_petroleo > {fecha_dudosa_dias}, false) as fecha_dudosa,
       en_ventana and en_archivo_pozos and con_coordenadas and horizontal
           and not coalesce(dias_desde_primer_petroleo > {fecha_dudosa_dias}, false) as hijo
from x
order by pozo_id;
