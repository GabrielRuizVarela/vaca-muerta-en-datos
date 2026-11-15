-- Staging: typed, trimmed, operator names normalised. One row per source row.
-- Units from the source: petróleo and agua in m3 per month, gas in miles de m3 per month.

create or replace table operadores as
select trim(empresa_raw) as empresa_raw, operador
from read_csv('{seed_operadores}', header = true, all_varchar = true);

create or replace table stg_produccion as
select
    try_cast(p.idpozo as integer)                              as pozo_id,
    make_date(try_cast(p.anio as integer), try_cast(p.mes as integer), 1) as mes,
    trim(p.empresa)                                            as empresa_raw,
    coalesce(o.operador, trim(p.empresa))                      as operador,
    p.sigla,
    lower(trim(p.formacion))                                   as formacion,
    p.sub_tipo_recurso                                         as subtipo_recurso,
    p.tipopozo                                                 as tipo_pozo,
    p.tipoestado                                               as estado,
    p.tipoextraccion                                           as extraccion,
    p.areayacimiento                                           as yacimiento,
    p.areapermisoconcesion                                     as area,
    p.provincia,
    try_cast(p.coordenadax as double)                          as lon,
    try_cast(p.coordenaday as double)                          as lat,
    try_cast(p.prod_pet as double)                             as petroleo_m3,
    try_cast(p.prod_gas as double)                             as gas_miles_m3,
    try_cast(p.prod_agua as double)                            as agua_m3,
    try_cast(p.tef as double)                                  as dias_efectivos,
    p.rectificado = 't'                                        as rectificado
from read_csv('{produccion_no_convencional}', header = true, all_varchar = true) p
left join operadores o on o.empresa_raw = trim(p.empresa);

create or replace table stg_fractura as
select
    try_cast(f.id_base_fractura_adjiv as integer)              as fractura_id,
    try_cast(f.idpozo as integer)                              as pozo_id,
    coalesce(o.operador, trim(f.empresa_informante))           as operador,
    lower(trim(f.formacion_productiva))                        as formacion,
    f.subtipo_reservorio                                       as subtipo_recurso,
    try_cast(f.fecha_inicio_fractura as date)                  as fecha_inicio,
    try_cast(f.fecha_fin_fractura as date)                     as fecha_fin,
    nullif(try_cast(f.longitud_rama_horizontal_m as double), 0) as rama_horizontal_m,
    try_cast(f.cantidad_fracturas as integer)                  as etapas,
    coalesce(try_cast(f.arena_bombeada_nacional_tn as double), 0)
      + coalesce(try_cast(f.arena_bombeada_importada_tn as double), 0) as arena_tn,
    try_cast(f.agua_inyectada_m3 as double)                    as agua_m3,
    f.tipo_terminacion                                         as terminacion,
    try_cast(f.presion_maxima_psi as double)                   as presion_maxima_psi
from read_csv('{fractura_adjunto_iv}', header = true, all_varchar = true) f
left join operadores o on o.empresa_raw = trim(f.empresa_informante);
