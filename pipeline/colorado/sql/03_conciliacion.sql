-- Conciliacion: conteos por etapa y conteo de hijos, padres cercanos y controles contra la estimacion de la memoria de factibilidad.
-- Solo CUENTA eventos con las reglas fijadas en pipeline/colorado/__init__.py. No calcula brecha, rendimiento ni indice alguno.
-- Parametros: {ventana_ini}, {ventana_fin}, {edad_min}, {base_min}, {km_cercano}, {km_control_min}, {km_max}, {km_por_grado}.

create or replace table mart_co_conciliacion (orden integer, clave varchar, valor bigint);

-- produccion
insert into mart_co_conciliacion select 10, 'prod_filas_fuente', count(*) from stg_co_produccion;
insert into mart_co_conciliacion select 11, 'prod_filas_sin_pozo_o_mes', count(*) from stg_co_produccion where pozo_id is null or mes is null;
insert into mart_co_conciliacion
select 12, 'prod_filas_tras_revision', count(*) from (
    select 1 from stg_co_produccion where pozo_id is not null and mes is not null group by pozo_id, sidetrack, formacion, mes);
insert into mart_co_conciliacion select 13, 'prod_pozo_mes', count(*) from fct_produccion;
insert into mart_co_conciliacion select 14, 'prod_pozos', count(distinct pozo_id) from fct_produccion;
insert into mart_co_conciliacion select 15, 'prod_pozos_varios_sidetracks', count(*) from (
    select pozo_id from stg_co_produccion where pozo_id is not null group by pozo_id having count(distinct sidetrack) > 1);
insert into mart_co_conciliacion select 16, 'prod_pozo_mes_con_varias_filas', count(*) from (
    select pozo_id, mes from stg_co_produccion where pozo_id is not null and mes is not null group by pozo_id, mes having count(*) > 1);
insert into mart_co_conciliacion select 17, 'prod_pozo_mes_cero_dias', count(*) from fct_produccion where coalesce(dias_efectivos, 0) = 0;
insert into mart_co_conciliacion select 18, 'prod_pozo_mes_con_petroleo', count(*) from fct_produccion where petroleo_m3 > 0;

-- pozos
insert into mart_co_conciliacion select 20, 'pozos_archivo', count(*) from stg_co_pozos;
insert into mart_co_conciliacion select 21, 'pozos_archivo_con_coordenadas', count(*) from stg_co_pozos where lat is not null and lon is not null;
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

-- FracFocus y la cadena hasta los hijos
insert into mart_co_conciliacion select 40, 'ff_divulgaciones', count(*) from stg_co_fracfocus;
insert into mart_co_conciliacion select 41, 'ff_api_invalidos', count(*) from stg_co_fracfocus where pozo_id is null;
insert into mart_co_conciliacion select 42, 'ff_pozos', count(distinct pozo_id) from stg_co_fracfocus;
insert into mart_co_conciliacion select 43, 'ff_pozos_en_archivo', count(*) from dim_pozo d where en_archivo_pozos and pozo_id in (select pozo_id from stg_co_fracfocus);
insert into mart_co_conciliacion select 44, 'ff_pozos_con_produccion', count(*) from dim_pozo d where con_produccion and pozo_id in (select pozo_id from stg_co_fracfocus);
insert into mart_co_conciliacion select 45, 'ff_pozos_con_fecha', count(*) from co_hijo;
insert into mart_co_conciliacion select 46, 'ff_primera_en_ventana', count(*) from co_hijo where en_ventana;
insert into mart_co_conciliacion select 47, 'ff_ventana_con_coordenadas', count(*) from co_hijo where en_ventana and en_archivo_pozos and con_coordenadas;
insert into mart_co_conciliacion select 48, 'ff_ventana_horizontales', count(*) from co_hijo where en_ventana and en_archivo_pozos and con_coordenadas and horizontal;
insert into mart_co_conciliacion select 49, 'ff_ventana_horizontales_fecha_dudosa', count(*) from co_hijo
    where en_ventana and en_archivo_pozos and con_coordenadas and horizontal and fecha_dudosa;
insert into mart_co_conciliacion select 50, 'hijos', count(*) from co_hijo where hijo;
insert into mart_co_conciliacion select 51, 'hijos_sin_produccion', count(*) from co_hijo where hijo and primer_mes_petroleo is null;
insert into mart_co_conciliacion select 52, 'hijos_ubicacion_planificada', count(*) from co_hijo h join dim_pozo d using (pozo_id)
    where h.hijo and lower(d.calidad_ubicacion) like '%planned%';
insert into mart_co_conciliacion select 53, 'ff_ventana_verticales_o_sin_dato', count(*) from co_hijo
    where en_ventana and en_archivo_pozos and con_coordenadas and not horizontal;
insert into mart_co_conciliacion select 54, 'ff_ventana_con_coordenadas_fecha_dudosa', count(*) from co_hijo
    where en_ventana and en_archivo_pozos and con_coordenadas and fecha_dudosa;

-- Hijos segun la regla de la memoria (la divulgacion MAS ANTIGUA DENTRO de la ventana, sin la regla de fecha dudosa): para explicar la diferencia.
create or replace temp table t_hijo as
select pozo_id as hijo, mes_frac, 'regla' as conjunto from co_hijo where hijo
union all
select f.pozo_id, date_trunc('month', min(f.fecha_inicio))::date, 'memoria'
from stg_co_fracfocus f join dim_pozo d using (pozo_id)
where d.en_archivo_pozos and d.lat is not null and d.lon is not null and d.horizontal
  and f.fecha_inicio between date '{ventana_ini}' and date '{ventana_fin}'
group by f.pozo_id;

insert into mart_co_conciliacion select 60, 'hijos_memoria', count(*) from t_hijo where conjunto = 'memoria';
insert into mart_co_conciliacion select 61, 'hijos_memoria_con_coordenadas_sin_horizontal', count(distinct f.pozo_id)
    from stg_co_fracfocus f join dim_pozo d using (pozo_id)
    where d.en_archivo_pozos and d.lat is not null and d.lon is not null and f.fecha_inicio between date '{ventana_ini}' and date '{ventana_fin}';

-- Pares hijo y padre posible a menos de {km_max} km (padre con primer petroleo al menos {edad_min} meses antes de la fractura).
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

-- Evento = (padre, mes de fractura) con la base mayor que {base_min} m3/d. El hijo mas cercano fija la banda (km_min).
create or replace temp table t_ev as
select p.conjunto, p.padre, p.mes_frac, p.padre_horizontal, min(p.km) as km_min,
       bool_or(p.km < {km_cercano}) as alguno_cercano, bool_or(p.km >= {km_control_min}) as alguno_control
from t_par p join t_base b using (padre, mes_frac)
where b.base_m3_d > {base_min}
group by p.conjunto, p.padre, p.mes_frac, p.padre_horizontal;

-- Cortes: todos los padres (el de la memoria) y solo padres horizontales (el corte principal).
create or replace temp table t_corte as select 'todos' as corte union all select 'horizontales';

insert into mart_co_conciliacion
select 70 + 10 * (k.conjunto = 'memoria')::int + (c.corte = 'horizontales')::int * 5 + o.i, 'ev_' || k.conjunto || '_' || c.corte || '_' || o.nombre,
       count(*) filter (where case o.nombre
            when 'cercanos' then (case when k.conjunto = 'regla' then e.km_min < {km_cercano} else e.alguno_cercano end)
            when 'intermedios' then e.km_min >= {km_cercano} and e.km_min < {km_control_min}
            else (case when k.conjunto = 'regla' then e.km_min >= {km_control_min} else e.alguno_control end) end)
from (select 'regla' as conjunto union all select 'memoria') k
cross join t_corte c
cross join (values (0, 'cercanos'), (1, 'intermedios'), (2, 'controles')) o(i, nombre)
left join t_ev e on e.conjunto = k.conjunto and (c.corte = 'todos' or e.padre_horizontal)
group by k.conjunto, c.corte, o.i, o.nombre;

insert into mart_co_conciliacion
select 100 + 10 * (k.conjunto = 'memoria')::int + (c.corte = 'horizontales')::int, 'hijos_con_padre_cercano_' || k.conjunto || '_' || c.corte,
       count(distinct p.hijo)
from (select 'regla' as conjunto union all select 'memoria') k
cross join t_corte c
join t_par p on p.conjunto = k.conjunto and (c.corte = 'todos' or p.padre_horizontal) and p.km < {km_cercano}
join t_base b on b.padre = p.padre and b.mes_frac = p.mes_frac and b.base_m3_d > {base_min}
group by k.conjunto, c.corte;

-- Eventos cercanos por ano de la fractura del hijo.
create or replace table mart_co_eventos_anio as
select k.conjunto, c.corte, year(e.mes_frac) as anio,
       count(*) filter (where case when k.conjunto = 'regla' then e.km_min < {km_cercano} else e.alguno_cercano end) as cercanos,
       count(*) filter (where case when k.conjunto = 'regla' then e.km_min >= {km_control_min} else e.alguno_control end) as controles
from (select 'regla' as conjunto union all select 'memoria') k
cross join t_corte c
join t_ev e on e.conjunto = k.conjunto and (c.corte = 'todos' or e.padre_horizontal)
group by all
order by 1, 2, 3;

drop table t_ev;
drop table t_base;
drop table t_par;
drop table t_hijo;
drop table t_corte;
