-- Event register and classification of parent/child interference events.
--
-- fct_evento: one row per dated event of a shale well with a location. Frac jobs carry a daily date;
-- every other type is detected on monthly data, so fecha is the first day of the month.
-- Water cut = agua / (agua + petroleo), defined only for months with oil + water > 0.

create or replace table int_prod_corte as
select x.pozo_id, x.mes, x.petroleo_m3, x.gas_miles_m3, x.agua_m3, x.dias_efectivos, x.dias_mes,
       x.estado, x.extraccion,
       case when x.agua_m3 + x.petroleo_m3 > 0 then x.agua_m3 / (x.agua_m3 + x.petroleo_m3) end as corte_agua,
       x.dias_efectivos / x.dias_mes as tef_frac
from fct_produccion x
join int_pozo_ubicacion u using (pozo_id);

create or replace table fct_evento as
with ord as (
    select *,
           lag(mes) over w as mes_prev,
           lag(estado) over w as estado_prev,
           lag(extraccion) over w as extraccion_prev,
           lag(petroleo_m3) over w as pet_prev,
           lag(gas_miles_m3) over w as gas_prev,
           avg(corte_agua) over (partition by pozo_id order by mes
               range between interval 3 month preceding and interval 1 month preceding) as corte_prev
    from int_prod_corte
    window w as (partition by pozo_id order by mes)
)
select u.pozo_id, f.fecha_inicio as fecha, date_trunc('month', f.fecha_inicio)::date as mes,
       'fractura' as tipo, null::varchar as detalle, f.etapas::double as valor
from stg_fractura f join int_pozo_ubicacion u using (pozo_id)
where f.fecha_inicio is not null
union all
select d.pozo_id, d.primer_mes_produccion, d.primer_mes_produccion, 'primera_produccion', null, null
from dim_pozo d join int_pozo_ubicacion u using (pozo_id)
where d.primer_mes_produccion is not null
union all
select pozo_id, mes, mes, 'cambio_estado', estado_prev || ' -> ' || estado, null
from ord
where mes_prev is not null and estado is distinct from estado_prev
union all
select pozo_id, mes, mes, 'cambio_extraccion', extraccion_prev || ' -> ' || extraccion, null
from ord
where mes_prev is not null and extraccion is distinct from extraccion_prev
union all
select o.pozo_id, o.mes, o.mes, 'cierre', null, null
from ord o join dim_pozo d using (pozo_id)
where o.petroleo_m3 = 0 and o.gas_miles_m3 = 0
  and o.mes > d.primer_mes_produccion
  and (o.pet_prev > 0 or o.gas_prev > 0)
union all
select pozo_id, mes, mes, 'salto_agua', printf('%.2f -> %.2f', corte_prev, corte_agua), corte_agua - corte_prev
from ord
where corte_agua is not null and corte_prev is not null and corte_agua - corte_prev > 0.15
union all
-- quiebre_caudal: flow rate break of a parent well at the frac month of a neighbour. It is a flag at KNOWN
-- neighbour frac dates (event table int_interferencia_evento, banda 'cercano': child frac within 1 km), NOT blind
-- change-point detection. For each (parent, frac month) it is emitted when the mean oil rate index of months 0 and 1
-- (rate / base rate, int_interferencia_mes) is below 0.75; both months must be present. valor is the fraction lost
-- (1 - mean index); detalle is the nearest child pad and its distance in km. One row per (padre, mes_frac).
select q.padre, q.mes_frac::date, q.mes_frac::date, 'quiebre_caudal',
       'pad ' || u.pad_id || ' a ' || printf('%.2f', q.km_min) || ' km', 1 - q.indice_medio
from (
    select e.padre, e.mes_frac, e.km_min, e.hijo_cercano, avg(m.indice) as indice_medio
    from int_interferencia_evento e
    join int_interferencia_mes m using (padre, mes_frac)
    where e.banda = 'cercano' and m.k in (0, 1)
    group by e.padre, e.mes_frac, e.km_min, e.hijo_cercano
    having count(*) = 2 and avg(m.indice) < 0.75
) q
join int_pozo_ubicacion u on u.pozo_id = q.hijo_cercano
order by 1, 2, 3, 4, 5;

-- One row per interference event (parent, frac month) with its classification.
create or replace table int_interferencia_clase as
with m as (
    select e.padre, e.mes_frac, date_diff('month', e.mes_frac, x.mes) as k,
           x.corte_agua, x.estado, x.tef_frac
    from int_interferencia_evento e
    join int_prod_corte x
      on x.pozo_id = e.padre and x.mes between e.mes_frac - interval 3 month and e.mes_frac + interval 1 month
), agg as (
    select padre, mes_frac,
           avg(corte_agua) filter (where k between -3 and -1) as agua_base,
           max(corte_agua) filter (where k between 0 and 1) as agua_max,
           coalesce(bool_or(estado = 'Parado Transitoriamente') filter (where k between 0 and 1), false) as parado,
           avg(tef_frac) filter (where k between -3 and -1) as tef_base,
           min(tef_frac) filter (where k between 0 and 1) as tef_0
    from m group by padre, mes_frac
), c as (
    select e.padre, e.mes_frac, e.banda, e.km_min, e.hijo_cercano, e.operador, e.area,
           (degrees(atan2((p.lon - h.lon) * cos(radians(h.lat)), p.lat - h.lat)) + 360) % 180 as rumbo_eje,
           coalesce(a.agua_max - a.agua_base > 0.15, false) as salto_agua,
           a.parado,
           coalesce(a.tef_0 < 0.8 * a.tef_base, false) as tef_caida
    from int_interferencia_evento e
    join agg a using (padre, mes_frac)
    join int_pozo_ubicacion p on p.pozo_id = e.padre
    join int_pozo_ubicacion h on h.pozo_id = e.hijo_cercano
)
select *,
       case when salto_agua and (parado or tef_caida) then 'ambos'
            when salto_agua then 'golpe'
            when parado or tef_caida then 'cierre_preventivo'
            else 'sin_efecto' end as clase
from c;
