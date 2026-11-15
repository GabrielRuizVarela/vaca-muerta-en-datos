# Linaje de datos

Qué dataset crudo alimenta cada tabla del warehouse. Se genera leyendo `pipeline/sql` y el código de `pipeline.costo` y `pipeline.robustez`; no consulta el warehouse ni lleva marcas de tiempo.

Capas: crudo (CSV inmutable en `data/raw`), staging (`stg_`), intermedia (`int_`), hecho (`fct_`), dimensión (`dim_`) y mart (`mart_`). Los marts de costo y de robustez los escriben módulos de Python y se alimentan de las tablas que ese módulo lee.

Hay 35 tablas con 104 relaciones de origen.

## Árbol

```
raw:fractura_adjunto_iv
  stg_fractura
    dim_fractura_pozo
      mart_anisotropia_area
        mart_robustez_costo
        mart_robustez_eje
      mart_costo_calibracion
      mart_costo_coef
      mart_costo_cv
      mart_costo_residuales
      mart_perdida_permanente
      mart_pozo_12m
        mart_diseno_productividad
    fct_evento
    int_frac_hijo
      int_par_padre_hijo
        int_interferencia_evento
          fct_evento (ver arriba)
          int_interferencia_clase
            mart_anisotropia_area (ver arriba)
            mart_costo_calibracion (ver arriba)
            mart_costo_coef (ver arriba)
            mart_costo_cv (ver arriba)
            mart_costo_residuales (ver arriba)
            mart_perdida_permanente (ver arriba)
          int_interferencia_mes
            fct_evento (ver arriba)
            mart_anisotropia_area (ver arriba)
            mart_costo_calibracion (ver arriba)
            mart_costo_coef (ver arriba)
            mart_costo_cv (ver arriba)
            mart_costo_residuales (ver arriba)
            mart_interferencia_anual
            mart_interferencia_brecha
              mart_anisotropia_area (ver arriba)
              mart_costo_calibracion (ver arriba)
              mart_costo_coef (ver arriba)
              mart_costo_cv (ver arriba)
              mart_costo_residuales (ver arriba)
              mart_interferencia_diferida
                mart_anisotropia_area (ver arriba)
                mart_costo_calibracion (ver arriba)
                mart_costo_coef (ver arriba)
                mart_costo_cv (ver arriba)
                mart_costo_residuales (ver arriba)
                mart_perdida_permanente (ver arriba)
              mart_perdida_permanente (ver arriba)
            mart_interferencia_curva
            mart_interferencia_diferida (ver arriba)
            mart_perdida_permanente (ver arriba)
          mart_anisotropia_area (ver arriba)
          mart_costo_calibracion (ver arriba)
          mart_costo_coef (ver arriba)
          mart_costo_cv (ver arriba)
          mart_costo_residuales (ver arriba)
          mart_interferencia_diferida (ver arriba)
          mart_perdida_permanente (ver arriba)
          mart_robustez_costo (ver arriba)
          mart_robustez_eje (ver arriba)
raw:produccion_no_convencional
  stg_produccion
    dim_pozo
      fct_evento (ver arriba)
      int_pozo_base
        int_pozo_arista
          int_pozo_pad
            int_pozo_ubicacion
              fct_evento (ver arriba)
              int_frac_hijo (ver arriba)
              int_interferencia_clase (ver arriba)
              int_interferencia_evento (ver arriba)
              int_par_padre_hijo (ver arriba)
              int_prod_corte
                fct_evento (ver arriba)
                int_interferencia_clase (ver arriba)
              mart_anisotropia_area (ver arriba)
              mart_costo_calibracion (ver arriba)
              mart_costo_coef (ver arriba)
              mart_costo_cv (ver arriba)
              mart_costo_residuales (ver arriba)
              mart_perdida_permanente (ver arriba)
        int_pozo_pad (ver arriba)
        int_pozo_ubicacion (ver arriba)
      int_pozo_mop
        mart_curva_tipo
        mart_pozo_12m (ver arriba)
      mart_pozo_12m (ver arriba)
    fct_produccion
      dim_pozo (ver arriba)
      int_interferencia_evento (ver arriba)
      int_interferencia_mes (ver arriba)
      int_pozo_mop (ver arriba)
      int_prod_corte (ver arriba)
      mart_anisotropia_area (ver arriba)
      mart_costo_calibracion (ver arriba)
      mart_costo_coef (ver arriba)
      mart_costo_cv (ver arriba)
      mart_costo_residuales (ver arriba)
      mart_perdida_permanente (ver arriba)
      mart_vm_mensual
      ultimo_mes
        int_frac_hijo (ver arriba)
        mart_pozo_12m (ver arriba)
seed:operadores
  operadores
    stg_fractura (ver arriba)
    stg_produccion (ver arriba)
```

## Relaciones

| Destino | Tipo | Origen | Escrito por |
| --- | --- | --- | --- |
| dim_fractura_pozo | dimensión | stg_fractura | pipeline/sql/02_core.sql |
| dim_pozo | dimensión | fct_produccion | pipeline/sql/02_core.sql |
| dim_pozo | dimensión | stg_produccion | pipeline/sql/02_core.sql |
| fct_evento | hecho | dim_pozo | pipeline/sql/05_eventos.sql |
| fct_evento | hecho | int_interferencia_evento | pipeline/sql/05_eventos.sql |
| fct_evento | hecho | int_interferencia_mes | pipeline/sql/05_eventos.sql |
| fct_evento | hecho | int_pozo_ubicacion | pipeline/sql/05_eventos.sql |
| fct_evento | hecho | int_prod_corte | pipeline/sql/05_eventos.sql |
| fct_evento | hecho | stg_fractura | pipeline/sql/05_eventos.sql |
| fct_produccion | hecho | stg_produccion | pipeline/sql/02_core.sql |
| int_frac_hijo | intermedia | int_pozo_ubicacion | pipeline/sql/04_interferencia.sql |
| int_frac_hijo | intermedia | stg_fractura | pipeline/sql/04_interferencia.sql |
| int_frac_hijo | intermedia | ultimo_mes | pipeline/sql/04_interferencia.sql |
| int_interferencia_clase | intermedia | int_interferencia_evento | pipeline/sql/05_eventos.sql |
| int_interferencia_clase | intermedia | int_pozo_ubicacion | pipeline/sql/05_eventos.sql |
| int_interferencia_clase | intermedia | int_prod_corte | pipeline/sql/05_eventos.sql |
| int_interferencia_evento | intermedia | fct_produccion | pipeline/sql/04_interferencia.sql |
| int_interferencia_evento | intermedia | int_par_padre_hijo | pipeline/sql/04_interferencia.sql |
| int_interferencia_evento | intermedia | int_pozo_ubicacion | pipeline/sql/04_interferencia.sql |
| int_interferencia_mes | intermedia | fct_produccion | pipeline/sql/04_interferencia.sql |
| int_interferencia_mes | intermedia | int_interferencia_evento | pipeline/sql/04_interferencia.sql |
| int_par_padre_hijo | intermedia | int_frac_hijo | pipeline/sql/04_interferencia.sql |
| int_par_padre_hijo | intermedia | int_pozo_ubicacion | pipeline/sql/04_interferencia.sql |
| int_pozo_arista | intermedia | int_pozo_base | pipeline/sql/04_interferencia.sql |
| int_pozo_base | intermedia | dim_pozo | pipeline/sql/04_interferencia.sql |
| int_pozo_mop | intermedia | dim_pozo | pipeline/sql/03_marts.sql |
| int_pozo_mop | intermedia | fct_produccion | pipeline/sql/03_marts.sql |
| int_pozo_pad | intermedia | int_pozo_arista | pipeline/sql/04_interferencia.sql |
| int_pozo_pad | intermedia | int_pozo_base | pipeline/sql/04_interferencia.sql |
| int_pozo_ubicacion | intermedia | int_pozo_base | pipeline/sql/04_interferencia.sql |
| int_pozo_ubicacion | intermedia | int_pozo_pad | pipeline/sql/04_interferencia.sql |
| int_prod_corte | intermedia | fct_produccion | pipeline/sql/05_eventos.sql |
| int_prod_corte | intermedia | int_pozo_ubicacion | pipeline/sql/05_eventos.sql |
| mart_anisotropia_area | mart | dim_fractura_pozo | pipeline.costo |
| mart_anisotropia_area | mart | fct_produccion | pipeline.costo |
| mart_anisotropia_area | mart | int_interferencia_clase | pipeline.costo |
| mart_anisotropia_area | mart | int_interferencia_evento | pipeline.costo |
| mart_anisotropia_area | mart | int_interferencia_mes | pipeline.costo |
| mart_anisotropia_area | mart | int_pozo_ubicacion | pipeline.costo |
| mart_anisotropia_area | mart | mart_interferencia_brecha | pipeline.costo |
| mart_anisotropia_area | mart | mart_interferencia_diferida | pipeline.costo |
| mart_costo_calibracion | mart | dim_fractura_pozo | pipeline.costo |
| mart_costo_calibracion | mart | fct_produccion | pipeline.costo |
| mart_costo_calibracion | mart | int_interferencia_clase | pipeline.costo |
| mart_costo_calibracion | mart | int_interferencia_evento | pipeline.costo |
| mart_costo_calibracion | mart | int_interferencia_mes | pipeline.costo |
| mart_costo_calibracion | mart | int_pozo_ubicacion | pipeline.costo |
| mart_costo_calibracion | mart | mart_interferencia_brecha | pipeline.costo |
| mart_costo_calibracion | mart | mart_interferencia_diferida | pipeline.costo |
| mart_costo_coef | mart | dim_fractura_pozo | pipeline.costo |
| mart_costo_coef | mart | fct_produccion | pipeline.costo |
| mart_costo_coef | mart | int_interferencia_clase | pipeline.costo |
| mart_costo_coef | mart | int_interferencia_evento | pipeline.costo |
| mart_costo_coef | mart | int_interferencia_mes | pipeline.costo |
| mart_costo_coef | mart | int_pozo_ubicacion | pipeline.costo |
| mart_costo_coef | mart | mart_interferencia_brecha | pipeline.costo |
| mart_costo_coef | mart | mart_interferencia_diferida | pipeline.costo |
| mart_costo_cv | mart | dim_fractura_pozo | pipeline.costo |
| mart_costo_cv | mart | fct_produccion | pipeline.costo |
| mart_costo_cv | mart | int_interferencia_clase | pipeline.costo |
| mart_costo_cv | mart | int_interferencia_evento | pipeline.costo |
| mart_costo_cv | mart | int_interferencia_mes | pipeline.costo |
| mart_costo_cv | mart | int_pozo_ubicacion | pipeline.costo |
| mart_costo_cv | mart | mart_interferencia_brecha | pipeline.costo |
| mart_costo_cv | mart | mart_interferencia_diferida | pipeline.costo |
| mart_costo_residuales | mart | dim_fractura_pozo | pipeline.costo |
| mart_costo_residuales | mart | fct_produccion | pipeline.costo |
| mart_costo_residuales | mart | int_interferencia_clase | pipeline.costo |
| mart_costo_residuales | mart | int_interferencia_evento | pipeline.costo |
| mart_costo_residuales | mart | int_interferencia_mes | pipeline.costo |
| mart_costo_residuales | mart | int_pozo_ubicacion | pipeline.costo |
| mart_costo_residuales | mart | mart_interferencia_brecha | pipeline.costo |
| mart_costo_residuales | mart | mart_interferencia_diferida | pipeline.costo |
| mart_curva_tipo | mart | int_pozo_mop | pipeline/sql/03_marts.sql |
| mart_diseno_productividad | mart | mart_pozo_12m | pipeline/sql/03_marts.sql |
| mart_interferencia_anual | mart | int_interferencia_mes | pipeline/sql/04_interferencia.sql |
| mart_interferencia_brecha | mart | int_interferencia_mes | pipeline/sql/04_interferencia.sql |
| mart_interferencia_curva | mart | int_interferencia_mes | pipeline/sql/04_interferencia.sql |
| mart_interferencia_diferida | mart | int_interferencia_evento | pipeline/sql/04_interferencia.sql |
| mart_interferencia_diferida | mart | int_interferencia_mes | pipeline/sql/04_interferencia.sql |
| mart_interferencia_diferida | mart | mart_interferencia_brecha | pipeline/sql/04_interferencia.sql |
| mart_perdida_permanente | mart | dim_fractura_pozo | pipeline.costo |
| mart_perdida_permanente | mart | fct_produccion | pipeline.costo |
| mart_perdida_permanente | mart | int_interferencia_clase | pipeline.costo |
| mart_perdida_permanente | mart | int_interferencia_evento | pipeline.costo |
| mart_perdida_permanente | mart | int_interferencia_mes | pipeline.costo |
| mart_perdida_permanente | mart | int_pozo_ubicacion | pipeline.costo |
| mart_perdida_permanente | mart | mart_interferencia_brecha | pipeline.costo |
| mart_perdida_permanente | mart | mart_interferencia_diferida | pipeline.costo |
| mart_pozo_12m | mart | dim_fractura_pozo | pipeline/sql/03_marts.sql |
| mart_pozo_12m | mart | dim_pozo | pipeline/sql/03_marts.sql |
| mart_pozo_12m | mart | int_pozo_mop | pipeline/sql/03_marts.sql |
| mart_pozo_12m | mart | ultimo_mes | pipeline/sql/03_marts.sql |
| mart_robustez_costo | mart | int_interferencia_evento | pipeline.robustez |
| mart_robustez_costo | mart | mart_anisotropia_area | pipeline.robustez |
| mart_robustez_eje | mart | int_interferencia_evento | pipeline.robustez |
| mart_robustez_eje | mart | mart_anisotropia_area | pipeline.robustez |
| mart_vm_mensual | mart | fct_produccion | pipeline/sql/03_marts.sql |
| operadores | auxiliar | seed:operadores | pipeline/sql/01_staging.sql |
| stg_fractura | staging | operadores | pipeline/sql/01_staging.sql |
| stg_fractura | staging | raw:fractura_adjunto_iv | pipeline/sql/01_staging.sql |
| stg_produccion | staging | operadores | pipeline/sql/01_staging.sql |
| stg_produccion | staging | raw:produccion_no_convencional | pipeline/sql/01_staging.sql |
| ultimo_mes | auxiliar | fct_produccion | pipeline/sql/02_core.sql |
