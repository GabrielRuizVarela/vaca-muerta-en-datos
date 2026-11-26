-- Conciliacion: conteos por etapa y conteo de hijos, padres cercanos y controles con las reglas fijadas en pipeline/wyoming/__init__.py.
-- Solo CUENTA eventos con la regla fijada. No calcula brecha, rendimiento ni indice alguno.
-- Parametros: {ventana_ini}, {ventana_fin}, {edad_min}, {base_min}, {km_cercano}, {km_control_min}, {km_max}, {km_por_grado}.

create or replace table mart_co_conciliacion (orden integer, clave varchar, valor bigint);

-- produccion
insert into mart_co_conciliacion select 10, 'prod_filas_fuente', count(*) from stg_wy_produccion;
insert into mart_co_conciliacion select 11, 'prod_filas_sin_pozo_o_anio', count(*) from stg_wy_produccion where pozo_id is null or anio is null;
insert into mart_co_conciliacion select 12, 'prod_pozo_anio', count(*) from (
    select distinct pozo_id, anio from stg_wy_produccion where pozo_id is not null and anio is not null);
insert into mart_co_conciliacion select 13, 'prod_pozo_mes', count(*) from fct_produccion;
insert into mart_co_conciliacion select 14, 'prod_pozos', count(distinct pozo_id) from fct_produccion;
insert into mart_co_conciliacion select 15, 'prod_pozo_anio_con_varias_filas', count(*) from (
    select pozo_id, anio from stg_wy_produccion where pozo_id is not null and anio is not null group by pozo_id, anio having count(*) > 1);
insert into mart_co_conciliacion select 16, 'prod_pozo_mes_con_varias_filas', count(*) from (
    select pozo_id, anio, m as mes from stg_wy_produccion cross join (values (1),(2),(3),(4),(5),(6),(7),(8),(9),(10),(11),(12)) t(m)
    where pozo_id is not null and anio is not null group by pozo_id, anio, m having count(*) > 1);
insert into mart_co_conciliacion select 17, 'prod_pozo_mes_cero_dias', count(*) from fct_produccion where dias_efectivos = 0;
insert into mart_co_conciliacion select 18, 'prod_pozo_mes_con_petroleo', count(*) from fct_produccion where petroleo_m3 > 0;
insert into mart_co_conciliacion select 19, 'prod_pozo_mes_sin_dias_validos', count(*) from fct_produccion where dias_efectivos is null;

-- pozos
insert into mart_co_conciliacion select 20, 'pozos_archivo', count(*) from stg_wy_pozos;
insert into mart_co_conciliacion select 21, 'pozos_archivo_con_coordenadas', count(*) from stg_wy_pozos where lat is not null and lon is not null;
insert into mart_co_conciliacion select 22, 'pozos_archivo_horizontales', count(*) from dim_pozo where en_archivo_pozos and horizontal;
insert into mart_co_conciliacion select 23, 'pozos_prod_en_archivo', count(*) from dim_pozo where con_produccion and en_archivo_pozos;
insert into mart_co_conciliacion select 24, 'pozos_prod_fuera_del_archivo', count(*) from dim_pozo where con_produccion and not en_archivo_pozos;
insert into mart_co_conciliacion select 25, 'pozos_prod_con_coordenadas', count(*) from dim_pozo where con_produccion and lat is not null;
insert into mart_co_conciliacion select 26, 'pozos_prod_horizontales', count(*) from dim_pozo where con_produccion and horizontal;
insert into mart_co_conciliacion select 27, 'pozos_prod_con_petroleo', count(*) from dim_pozo where primer_mes_petroleo is not null;
insert into mart_co_conciliacion select 28, 'pozos_primer_petroleo_censurado', count(*) from dim_pozo where primer_petroleo_censurado;
insert into mart_co_conciliacion select 29, 'pads', count(distinct pad_id) from co_pozo_pad;
insert into mart_co_conciliacion select 30, 'pozos_en_pads_de_3_o_mas', count(*) from (
    select pad_id, count(*) over (partition by pad_id) as n from co_pozo_pad) where n >= 3;

-- FIRSTCOMP y la cadena hasta los hijos
insert into mart_co_conciliacion select 40, 'fc_pozos_con_fecha', count(*) from co_hijo;
insert into mart_co_conciliacion select 41, 'fc_vacios', count(*) from stg_wy_pozos where firstcomp_crudo is null;
insert into mart_co_conciliacion select 42, 'fc_no_parsean', count(*) from stg_wy_pozos where firstcomp_crudo is not null and fecha_firstcomp is null;
insert into mart_co_conciliacion select 43, 'fc_en_archivo', count(*) from co_hijo where en_archivo_pozos;
insert into mart_co_conciliacion select 44, 'fc_pozos_con_produccion', count(*) from dim_pozo d
    where con_produccion and pozo_id in (select pozo_id from co_hijo);
insert into mart_co_conciliacion select 45, 'fc_primera_en_ventana', count(*) from co_hijo where en_ventana;
insert into mart_co_conciliacion select 46, 'fc_ventana_con_coordenadas', count(*) from co_hijo where en_ventana and en_archivo_pozos and con_coordenadas;
insert into mart_co_conciliacion select 47, 'fc_ventana_horizontales', count(*) from co_hijo
    where en_ventana and en_archivo_pozos and con_coordenadas and horizontal;
insert into mart_co_conciliacion select 48, 'fc_ventana_horizontales_fecha_dudosa', count(*) from co_hijo
    where en_ventana and en_archivo_pozos and con_coordenadas and horizontal and fecha_dudosa;
insert into mart_co_conciliacion select 49, 'hijos', count(*) from co_hijo where hijo;
insert into mart_co_conciliacion select 50, 'hijos_sin_produccion', count(*) from co_hijo where hijo and primer_mes_petroleo is null;
insert into mart_co_conciliacion select 51, 'hijos_sin_petroleo_excluidos', count(*) from co_hijo
    where en_ventana and en_archivo_pozos and con_coordenadas and horizontal and not fecha_dudosa and primer_mes_petroleo is null;
insert into mart_co_conciliacion select 52, 'fc_ventana_verticales_o_sin_dato', count(*) from co_hijo
    where en_ventana and en_archivo_pozos and con_coordenadas and not horizontal;
insert into mart_co_conciliacion select 53, 'fc_ventana_con_coordenadas_fecha_dudosa', count(*) from co_hijo
    where en_ventana and en_archivo_pozos and con_coordenadas and fecha_dudosa;

insert into mart_co_conciliacion select 54, 'fc_ambiguas', count(*) from stg_wy_pozos where firstcomp_ambigua;
-- Mes de la terminacion contra el primer mes con petroleo, entre los hijos: la fecha de WOGCC es la de la primera terminacion.
insert into mart_co_conciliacion select 55, 'hijos_terminacion_mes_primer_petroleo', count(*) from co_hijo
    where hijo and date_trunc('month', fecha_frac)::date = primer_mes_petroleo;
insert into mart_co_conciliacion select 56, 'hijos_primer_petroleo_posterior', count(*) from co_hijo
    where hijo and date_trunc('month', fecha_frac)::date < primer_mes_petroleo;
insert into mart_co_conciliacion select 57, 'hijos_primer_petroleo_anterior', count(*) from co_hijo
    where hijo and date_trunc('month', fecha_frac)::date > primer_mes_petroleo;

-- Hijos con la regla fijada.
create or replace temp table t_hijo as
select pozo_id as hijo, mes_frac, 'regla' as conjunto from co_hijo where hijo;

-- Pares hijo y padre posible a menos de {km_max} km (padre con primer petroleo al menos {edad_min} meses antes de la terminacion).
create or replace temp table t_par as
select * from (
    select h.hijo, h.mes_frac, h.conjunto, p.pozo_id as padre, p.horizontal as padre_horizontal,
           {km_por_grado} * sqrt(power((p.lon - c.lon) * cos(radians(c.lat)), 2) + power(p.lat - c.lat, 2)) as km
    from t_hijo h
    join dim_pozo c on c.pozo_id = h.hijo
    join dim_pozo p
      on p.pozo_id <> h.hijo and p.lat is not null and p.lon is not null
     and abs(p.lat - c.lat) < 0.05 and abs(p.lon - c.lon) < 0.07
     and p.primer_mes_petroleo <= h.mes_frac - to_months({edad_min})
) where km < {km_max};

-- Caudal base del padre: media de petroleo por dia calendario en los meses -3 a -1.
create or replace temp table t_base as
select e.padre, e.mes_frac, avg(x.petroleo_m3 / x.dias_mes) as base_m3_d
from (select distinct padre, mes_frac from t_par) e
join fct_produccion x on x.pozo_id = e.padre and x.mes between e.mes_frac - interval 3 month and e.mes_frac - interval 1 month
group by all;

-- Evento = (padre, mes de terminacion) con la base mayor que {base_min} m3/d. El hijo mas cercano fija la banda (km_min).
create or replace temp table t_ev as
select p.conjunto, p.padre, p.mes_frac, p.padre_horizontal, min(p.km) as km_min
from t_par p join t_base b using (padre, mes_frac)
where b.base_m3_d > {base_min}
group by p.conjunto, p.padre, p.mes_frac, p.padre_horizontal;

-- Cortes: todos los padres y solo padres horizontales (el corte principal).
create or replace temp table t_corte as select 'todos' as corte union all select 'horizontales';

insert into mart_co_conciliacion
select 70 + (c.corte = 'horizontales')::int * 5 + o.i, 'ev_regla_' || c.corte || '_' || o.nombre,
       count(*) filter (where case o.nombre
            when 'cercanos' then e.km_min < {km_cercano}
            when 'intermedios' then e.km_min >= {km_cercano} and e.km_min < {km_control_min}
            else e.km_min >= {km_control_min} end)
from t_corte c
cross join (values (0, 'cercanos'), (1, 'intermedios'), (2, 'controles')) o(i, nombre)
left join t_ev e on (c.corte = 'todos' or e.padre_horizontal)
group by c.corte, o.i, o.nombre;

insert into mart_co_conciliacion
select 100 + (c.corte = 'horizontales')::int, 'hijos_con_padre_cercano_regla_' || c.corte,
       count(distinct p.hijo)
from t_corte c
join t_par p on (c.corte = 'todos' or p.padre_horizontal) and p.km < {km_cercano}
join t_base b on b.padre = p.padre and b.mes_frac = p.mes_frac and b.base_m3_d > {base_min}
group by c.corte;

-- Eventos por ano de la terminacion del hijo.
create or replace table mart_co_eventos_anio as
select 'regla' as conjunto, c.corte, year(e.mes_frac) as anio,
       count(*) filter (where e.km_min < {km_cercano}) as cercanos,
       count(*) filter (where e.km_min >= {km_control_min}) as controles
from t_corte c
join t_ev e on (c.corte = 'todos' or e.padre_horizontal)
group by all
order by 1, 2, 3;

drop table t_ev;
drop table t_base;
drop table t_par;
drop table t_hijo;
drop table t_corte;
