-- Marts for the report. Rates are calendar-day rates: monthly volume / days in the month.
-- 1 m3 = 6.2898 bbl.

-- Vaca Muerta oil and gas per operator and month.
create or replace table mart_vm_mensual as
select
    mes,
    operador,
    sum(petroleo_m3) * 6.2898 / any_value(dias_mes) / 1000  as petroleo_kbbl_d,
    sum(gas_miles_m3) / any_value(dias_mes) / 1000          as gas_mmm3_d,
    count(*) filter (where petroleo_m3 > 0 or gas_miles_m3 > 0) as pozos_activos
from fct_produccion
where formacion = 'vaca muerta'
group by mes, operador;

-- Shale oil wells in Vaca Muerta, month-on-production index from first oil.
create or replace table int_pozo_mop as
select
    f.pozo_id,
    d.operador,
    year(d.primer_mes_petroleo)                              as cohorte,
    date_diff('month', d.primer_mes_petroleo, f.mes) + 1     as mop,
    f.petroleo_m3 * 6.2898 / f.dias_mes                      as petroleo_bbl_d,
    f.petroleo_m3
from fct_produccion f
join dim_pozo d using (pozo_id)
where d.formacion = 'vaca muerta'
  and d.subtipo_recurso = 'SHALE'
  and d.tipo_pozo = 'Petrolífero'
  and d.primer_mes_petroleo is not null
  and f.mes >= d.primer_mes_petroleo;

-- Average type curve per cohort, YPF against the rest. Points with fewer than 10 wells are dropped.
create or replace table mart_curva_tipo as
select
    cohorte,
    case when operador = 'YPF' then 'YPF' else 'Resto' end as grupo,
    mop,
    count(*)                    as pozos,
    avg(petroleo_bbl_d)         as petroleo_bbl_d
from int_pozo_mop
where mop <= 36 and cohorte between 2017 and 2025
group by all
having count(*) >= 10;

-- First-12-month cumulative oil, only for wells with 12 published months.
create or replace table mart_pozo_12m as
select
    m.pozo_id,
    any_value(m.operador)                          as operador,
    any_value(m.cohorte)                           as cohorte,
    sum(m.petroleo_m3) * 6.2898                    as petroleo_12m_bbl,
    any_value(fr.rama_horizontal_m)                as rama_horizontal_m,
    any_value(fr.etapas)                           as etapas,
    any_value(fr.arena_tn)                         as arena_tn
from int_pozo_mop m
join dim_pozo d using (pozo_id)
left join dim_fractura_pozo fr using (pozo_id)
where m.mop <= 12
  and d.primer_mes_petroleo <= (select mes from ultimo_mes) - interval 11 month
group by m.pozo_id;

-- Completion design and productivity by cohort.
create or replace table mart_diseno_productividad as
select
    cohorte,
    case when operador = 'YPF' then 'YPF' else 'Resto' end as grupo,
    count(*)                                       as pozos,
    count(rama_horizontal_m)                       as pozos_con_fractura,
    median(rama_horizontal_m)                      as rama_m_mediana,
    median(etapas)                                 as etapas_mediana,
    median(arena_tn / rama_horizontal_m)           as arena_tn_por_m_mediana,
    median(petroleo_12m_bbl)                       as petroleo_12m_bbl_mediana,
    median(petroleo_12m_bbl / rama_horizontal_m)   as bbl_12m_por_m_mediana
from mart_pozo_12m
where cohorte between 2017 and 2025
group by all
having count(*) >= 10;
