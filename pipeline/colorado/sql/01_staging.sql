-- Staging del Colorado: tipado y unidades. Una fila por fila de la fuente (produccion, pozos y divulgaciones).
-- Parametros: {produccion_csvs} (lista SQL de rutas), {pozos_csv}, {fracfocus_csv}, {bbl_a_m3}, {mcf_a_miles_m3}, {gal_a_m3}.
-- pozo_id = condado (3 digitos) + secuencia (5 digitos) del API: los sidetracks quedan en el mismo pozo.

create or replace table stg_co_produccion as
select
    try_cast(ApiCountyCode as integer) * 100000 + try_cast(ApiSequenceNumber as integer)  as pozo_id,
    ApiCountyCode                                                    as condado,
    ApiSidetrack                                                     as sidetrack,
    make_date(try_cast(ReportYear as integer), try_cast(ReportMonth as integer), 1) as mes,
    try_cast(DaysProduced as integer)                                as dias,
    try_strptime(AcceptedDate, '%m/%d/%Y %H:%M:%S')                  as aceptado,
    try_cast(DocNum as bigint)                                       as doc,
    coalesce(upper(trim(Revised)) = 'Y', false)                      as revisado,
    trim(OpName)                                                     as operador,
    upper(trim(WellStatus))                                          as estado,
    lower(trim(FormationCode))                                       as formacion,
    try_cast(OilProduced as decimal(18, 3))                          as petroleo_bbl,
    try_cast(GasProduced as decimal(18, 3))                          as gas_mcf,
    try_cast(WaterProduced as decimal(18, 3))                        as agua_bbl,
    try_cast(OilProduced as double) * {bbl_a_m3}                     as petroleo_m3,
    try_cast(GasProduced as double) * {mcf_a_miles_m3}               as gas_miles_m3,
    try_cast(WaterProduced as double) * {bbl_a_m3}                   as agua_m3
from read_csv({produccion_csvs}, header = true, all_varchar = true, union_by_name = true);

-- Archivo de pozos de ECMC. 16 API aparecen dos veces (solo difiere la fecha de spud): se conserva la fila con el spud mas
-- antiguo y, de empate, el Facil_Id mas bajo.
create or replace table stg_co_pozos as
select
    try_cast(API_County as integer) * 100000 + try_cast(API_Seq as integer) as pozo_id,
    API_County                              as condado,
    nullif(trim(Well_Name), '')             as nombre,
    nullif(trim(Operator), '')              as operador,
    nullif(trim(Facil_Stat), '')            as estado,
    nullif(trim(Well_Class), '')            as clase,
    try_strptime(Spud_Date, '%Y%m%d')::date as fecha_spud,
    try_cast(Max_MD as double)              as md_ft,
    try_cast(Max_TVD as double)             as tvd_ft,
    try_cast(Latitude as double)            as lat,
    try_cast(Longitude as double)           as lon,
    nullif(trim(Loc_Qual), '')              as calidad_ubicacion
from read_csv('{pozos_csv}', header = true, all_varchar = true)
where API_County <> '' and API_Seq <> ''
qualify row_number() over (partition by API_County, API_Seq
                           order by try_strptime(Spud_Date, '%Y%m%d') asc nulls last, try_cast(Facil_Id as bigint)) = 1;

-- Divulgaciones de FracFocus (DisclosureList_1.csv), solo Colorado. APINumber de 14 digitos:
-- estado(2) condado(3) secuencia(5) sidetrack(2) terminacion(2).
create or replace table stg_co_fracfocus as
select
    DisclosureId                                                   as divulgacion,
    APINumber                                                      as api14,
    case when length(APINumber) = 14 and regexp_matches(APINumber, '^[0-9]+$')
         then try_cast(substr(APINumber, 3, 3) as integer) * 100000 + try_cast(substr(APINumber, 6, 5) as integer) end as pozo_id,
    substr(APINumber, 3, 3)                                        as condado,
    substr(APINumber, 11, 2)                                       as sidetrack,
    try_strptime(JobStartDate, '%m/%d/%Y %I:%M:%S %p')::date       as fecha_inicio,
    try_strptime(JobEndDate, '%m/%d/%Y %I:%M:%S %p')::date         as fecha_fin,
    trim(CountyName)                                               as condado_nombre,
    trim(OperatorName)                                             as operador,
    try_cast(Latitude as double)                                   as lat,
    try_cast(Longitude as double)                                  as lon,
    try_cast(TVD as double)                                        as tvd_ft,
    try_cast(TotalBaseWaterVolume as double) * {gal_a_m3}          as agua_m3
from read_csv('{fracfocus_csv}', header = true, all_varchar = true)
where StateName = 'Colorado';
