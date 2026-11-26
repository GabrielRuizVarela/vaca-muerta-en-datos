-- Parent/child interference ("frac hits") in Vaca Muerta shale.
--
-- Event: a new well (child) starts its first frac job. For every older producing well
-- (parent, first oil at least 6 months earlier) within 5 km of surface location, the
-- parent's calendar-day oil rate in months -3..6 around the child's frac month is indexed
-- to its mean over months -3..-1. Parents within 1 km are compared with parents 2-5 km
-- away of the same age (the control), so normal decline is netted out.
--
-- Limits: coordinates are surface locations (pads), not lateral paths; a deliberate
-- protective shut-in or choke-back by the operator looks the same as damage in monthly
-- data. The result is a measured footprint, not a cause.

-- Shale wells with a location. Pad: single-linkage clusters of surface locations within 50 m
-- (connected components); pad_id = 'p' || smallest pozo_id of the component, stable across builds.
create or replace table int_pozo_base as
select pozo_id, operador, area, tipo_pozo, lon, lat, primer_mes_petroleo
from dim_pozo
where formacion = 'vaca muerta' and subtipo_recurso = 'SHALE'
  and lon is not null and lat is not null;

create or replace table int_pozo_arista as
select a.pozo_id as a, b.pozo_id as b
from int_pozo_base a
join int_pozo_base b
  on b.pozo_id <> a.pozo_id
 and abs(a.lat - b.lat) < 0.001 and abs(a.lon - b.lon) < 0.001
where 111.32 * sqrt(power((a.lon - b.lon) * cos(radians(a.lat)), 2) + power(a.lat - b.lat, 2)) < 0.05;

create or replace table int_pozo_pad as
with recursive lab(pozo_id, etiqueta) as (
    select pozo_id, pozo_id from int_pozo_base
    union
    select e.b, l.etiqueta from lab l join int_pozo_arista e on e.a = l.pozo_id
)
select pozo_id, 'p' || min(etiqueta) as pad_id from lab group by pozo_id;

create or replace table int_pozo_ubicacion as
select b.pozo_id, b.operador, b.area, b.tipo_pozo, b.lon, b.lat, b.primer_mes_petroleo, p.pad_id
from int_pozo_base b join int_pozo_pad p using (pozo_id);

-- First frac month of each child well (refracs are not new children).
create or replace table int_frac_hijo as
select f.pozo_id as hijo, date_trunc('month', min(f.fecha_inicio)) as mes_frac,
       -- mes de carga del trabajo de fractura que fija mes_frac. Las filas con esa misma fecha de inicio cuentan como el
       -- mismo trabajo cargado mas de una vez: vale la primera carga conocida. Si ninguna de esas filas trae mes de carga
       -- queda nulo (arg_min saltearia el nulo y tomaria el de un trabajo posterior).
       array_agg(f.mes_carga order by f.fecha_inicio, f.mes_carga)[1] as mes_carga
from stg_fractura f
join int_pozo_ubicacion u using (pozo_id)
where f.fecha_inicio is not null
  and f.fecha_inicio < (select mes from ultimo_mes) + interval 1 month
group by f.pozo_id;

-- Parent/child pairs within 5 km.
create or replace table int_par_padre_hijo as
select * from (
select
    h.hijo, p.pozo_id as padre, h.mes_frac,
    111.32 * sqrt(power((p.lon - c.lon) * cos(radians(c.lat)), 2) + power(p.lat - c.lat, 2)) as km
from int_frac_hijo h
join int_pozo_ubicacion c on c.pozo_id = h.hijo
join int_pozo_ubicacion p
  on p.pozo_id <> h.hijo
 and abs(p.lat - c.lat) < 0.05 and abs(p.lon - c.lon) < 0.07
 and p.primer_mes_petroleo <= h.mes_frac - interval 6 month
) where km < 5;

-- One event per (parent, month): the nearest child sets the band.
create or replace table int_interferencia_evento as
with ev as (
    select padre, mes_frac, min(km) as km_min, count(*) filter (where km < 1) as hijos_1km,
           arg_min(hijo, (km, hijo)) as hijo_cercano  -- ties (same pad) break on the lowest id
    from int_par_padre_hijo group by padre, mes_frac
), base as (
    select ev.padre, ev.mes_frac, avg(x.petroleo_m3 / x.dias_mes) as base_m3_d
    from ev join fct_produccion x
      on x.pozo_id = ev.padre and x.mes between ev.mes_frac - interval 3 month and ev.mes_frac - interval 1 month
    group by all
)
select
    ev.*, base.base_m3_d,
    case when km_min < 1 then 'cercano' when km_min < 2 then 'intermedio' else 'control' end as banda,
    date_diff('month', u.primer_mes_petroleo, ev.mes_frac) as edad_meses,
    case when date_diff('month', u.primer_mes_petroleo, ev.mes_frac) < 12 then '06-11'
         when date_diff('month', u.primer_mes_petroleo, ev.mes_frac) < 24 then '12-23'
         when date_diff('month', u.primer_mes_petroleo, ev.mes_frac) < 48 then '24-47'
         else '48+' end as grupo_edad,
    u.operador, u.area, u.pad_id
from ev join base using (padre, mes_frac)
join int_pozo_ubicacion u on u.pozo_id = ev.padre
where base.base_m3_d > 1;   -- parents producing at least 1 m3/d of oil before the event

-- Parent monthly rate index around each event, months -3..6.
create or replace table int_interferencia_mes as
select e.padre, e.mes_frac, e.banda, e.grupo_edad,
       date_diff('month', e.mes_frac, x.mes) as k,
       x.petroleo_m3 / x.dias_mes / e.base_m3_d as indice,
       x.petroleo_m3 / x.dias_mes as m3_d, x.dias_mes
from int_interferencia_evento e
join fct_produccion x
  on x.pozo_id = e.padre and x.mes between e.mes_frac - interval 3 month and e.mes_frac + interval 6 month;

-- Median index per band and month offset.
create or replace table mart_interferencia_curva as
select banda, k, count(*) as eventos, median(indice) as indice_mediana
from int_interferencia_mes group by all;

-- Near minus control, matched by parent age.
create or replace table mart_interferencia_brecha as
select grupo_edad, k,
       count(*) filter (where banda = 'cercano')             as eventos_cercanos,
       median(indice) filter (where banda = 'cercano')       as indice_cercano,
       median(indice) filter (where banda = 'control')       as indice_control,
       median(indice) filter (where banda = 'cercano')
         - median(indice) filter (where banda = 'control')   as brecha
from int_interferencia_mes group by all;

-- Oil deferred per near event, months 0..6: (control-expected rate - actual rate) x days.
create or replace table mart_interferencia_diferida as
select e.padre, e.mes_frac, e.hijo_cercano, e.km_min, e.hijos_1km, e.operador, e.area, e.pad_id, e.grupo_edad,
       sum((b.indice_control * e.base_m3_d - m.m3_d) * m.dias_mes) * 6.2898 as petroleo_diferido_bbl,
       count(*) as meses
from int_interferencia_evento e
join int_interferencia_mes m using (padre, mes_frac)
join mart_interferencia_brecha b on b.grupo_edad = e.grupo_edad and b.k = m.k
where e.banda = 'cercano' and m.k between 0 and 6
group by all;

-- Footprint per year of child frac.
create or replace table mart_interferencia_anual as
select year(mes_frac) as anio,
       count(*) filter (where banda = 'cercano' and k = 1)                  as eventos_cercanos,
       median(indice) filter (where banda = 'cercano' and k = 1)
         - median(indice) filter (where banda = 'control' and k = 1)        as brecha_mes_1
from int_interferencia_mes
group by 1;
