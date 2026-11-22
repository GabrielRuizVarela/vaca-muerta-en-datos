# Linaje de datos

Qué dataset crudo alimenta cada tabla del warehouse. Se genera leyendo `pipeline/sql` y el código de los módulos de Python que escriben marts; no consulta el warehouse ni lleva marcas de tiempo.

Capas: crudo (CSV inmutable en `data/raw`), staging (`stg_`), intermedia (`int_`), hecho (`fct_`), dimensión (`dim_`) y mart (`mart_`). Los marts que escribe un módulo de Python se alimentan de las tablas que ese módulo lee en su código y en las funciones y el SQL de otros módulos de pipeline que importa y usa. El grano es el módulo: todos los marts de un módulo muestran los mismos orígenes, sin separar cuál de ellos usa cada mart. Un origen `manifiesto:` es un valor que `pipeline.build` lee de `data/manifest.json` y le pasa al SQL (la fecha de extracción del archivo de fracturas).

Queda fuera la réplica en el warehouse de Colorado (`pipeline.replicacion`), que escribe con nombres tomados de un diccionario y no con una llamada por mart. Los marts `mart_dias_perdidos_colorado*`, `mart_golpes_mismo_mes_colorado*`, `mart_golpes_mismo_padre_colorado*` y `mart_causal_profundo_d7` sí están: se guardan en este warehouse, pero se calculan desde el de Colorado, que tiene tablas con los mismos nombres.

Hay 168 tablas con 929 relaciones de origen.

## Árbol

```
manifiesto:fecha_extraccion
  extraccion_fractura
    dim_fractura_pozo
      mart_anisotropia_area
        mart_eje_exposicion
        mart_eje_exposicion_veredicto
          mart_eje_parada
        mart_eje_reponderado
        mart_potencia_eje
          mart_eje_parada (ver arriba)
        mart_potencia_resumen
          mart_eje_parada (ver arriba)
        mart_robustez_costo
        mart_robustez_eje
          mart_bloques
      mart_causal_profundo_d3
        mart_causal_extra
        mart_causal_operador
        mart_causal_placebo
        mart_causal_serie
        mart_causal_veredicto
          mart_causal_profundo_d3 (ver arriba)
          mart_causal_profundo_d4
          mart_causal_profundo_d5
            mart_causal_extra (ver arriba)
            mart_causal_operador (ver arriba)
            mart_causal_placebo (ver arriba)
            mart_causal_serie (ver arriba)
            mart_causal_veredicto (ver arriba)
          mart_causal_profundo_d6
            mart_causal_extra (ver arriba)
            mart_causal_operador (ver arriba)
            mart_causal_placebo (ver arriba)
            mart_causal_serie (ver arriba)
            mart_causal_veredicto (ver arriba)
          mart_causal_profundo_d7
            mart_causal_extra (ver arriba)
            mart_causal_operador (ver arriba)
            mart_causal_placebo (ver arriba)
            mart_causal_serie (ver arriba)
            mart_causal_veredicto (ver arriba)
          mart_causal_profundo_veredicto
            mart_causal_extra (ver arriba)
            mart_causal_operador (ver arriba)
            mart_causal_placebo (ver arriba)
            mart_causal_serie (ver arriba)
            mart_causal_veredicto (ver arriba)
      mart_causal_profundo_d4 (ver arriba)
      mart_causal_profundo_d5 (ver arriba)
      mart_causal_profundo_d6 (ver arriba)
      mart_causal_profundo_d7 (ver arriba)
      mart_causal_profundo_veredicto (ver arriba)
      mart_costo_calibracion
      mart_costo_coef
      mart_costo_cv
      mart_costo_residuales
      mart_dosis_geometria_modelo
      mart_dosis_geometria_muestra
      mart_dosis_geometria_orden
      mart_dosis_geometria_potencia
      mart_dosis_geometria_puerta
      mart_dosis_geometria_quintiles
      mart_dosis_geometria_sens
      mart_dosis_geometria_sim
      mart_dosis_geometria_veredicto
      mart_dosis_meses
      mart_dosis_meses_veredicto
      mart_dosis_modelo
        mart_dosis_geometria_modelo (ver arriba)
        mart_dosis_geometria_muestra (ver arriba)
        mart_dosis_geometria_orden (ver arriba)
        mart_dosis_geometria_potencia (ver arriba)
        mart_dosis_geometria_puerta (ver arriba)
        mart_dosis_geometria_quintiles (ver arriba)
        mart_dosis_geometria_sens (ver arriba)
        mart_dosis_geometria_sim (ver arriba)
        mart_dosis_geometria_veredicto (ver arriba)
        mart_dosis_meses (ver arriba)
        mart_dosis_meses_veredicto (ver arriba)
        mart_potencia_dosis
          mart_dosis_geometria_modelo (ver arriba)
          mart_dosis_geometria_muestra (ver arriba)
          mart_dosis_geometria_orden (ver arriba)
          mart_dosis_geometria_potencia (ver arriba)
          mart_dosis_geometria_puerta (ver arriba)
          mart_dosis_geometria_quintiles (ver arriba)
          mart_dosis_geometria_sens (ver arriba)
          mart_dosis_geometria_sim (ver arriba)
          mart_dosis_geometria_veredicto (ver arriba)
        mart_potencia_dosis_sim
        mart_potencia_dosis_veredicto
      mart_dosis_orden
      mart_dosis_pad
        mart_potencia_dosis (ver arriba)
        mart_potencia_dosis_sim (ver arriba)
        mart_potencia_dosis_veredicto (ver arriba)
      mart_dosis_pad_veredicto
      mart_dosis_quintiles
      mart_dosis_sens
      mart_dosis_veredicto
      mart_eje_controles
        mart_eje_parada (ver arriba)
      mart_eje_controles_rotacion
        mart_eje_parada (ver arriba)
      mart_eje_controles_veredicto
        mart_eje_parada (ver arriba)
      mart_eje_exposicion (ver arriba)
      mart_eje_exposicion_veredicto (ver arriba)
      mart_eje_reponderado (ver arriba)
      mart_hijo_celdas_coef
      mart_hijo_celdas_equilibrio
      mart_hijo_celdas_resumen
      mart_hijo_coef
        mart_bloques (ver arriba)
      mart_hijo_equilibrio
      mart_hijo_grupos
      mart_hijo_muestra
      mart_hijo_pad_anio
      mart_hijo_pad_coef
      mart_hijo_pad_equilibrio
      mart_hijo_pad_muestra
      mart_hijo_pad_resumen
      mart_perdida_permanente
        mart_decision_cierre
        mart_decision_distancia
        mart_decision_edad
        mart_decision_perdida
      mart_potencia_dosis (ver arriba)
      mart_potencia_dosis_sim (ver arriba)
      mart_potencia_dosis_veredicto (ver arriba)
      mart_potencia_eje (ver arriba)
      mart_potencia_resumen (ver arriba)
      mart_pozo_12m
        mart_diseno_productividad
        mart_hijo_celdas_coef (ver arriba)
        mart_hijo_celdas_equilibrio (ver arriba)
        mart_hijo_celdas_resumen (ver arriba)
        mart_hijo_coef (ver arriba)
        mart_hijo_equilibrio (ver arriba)
        mart_hijo_grupos (ver arriba)
        mart_hijo_muestra (ver arriba)
        mart_hijo_pad_anio (ver arriba)
        mart_hijo_pad_coef (ver arriba)
        mart_hijo_pad_equilibrio (ver arriba)
        mart_hijo_pad_muestra (ver arriba)
        mart_hijo_pad_resumen (ver arriba)
      mart_riesgo_anio
      mart_riesgo_calibracion
      mart_riesgo_coef
      mart_riesgo_modelo
      mart_riesgo_prueba
      mart_riesgo_rama
      mart_robustez_costo (ver arriba)
      mart_robustez_eje (ver arriba)
      mart_validacion_holdout
      mart_validacion_resultados
raw:fractura_adjunto_iv
  stg_fractura
    dim_fractura_pozo (ver arriba)
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
            mart_eje_controles (ver arriba)
            mart_eje_controles_rotacion (ver arriba)
            mart_eje_controles_veredicto (ver arriba)
            mart_eje_exposicion (ver arriba)
            mart_eje_exposicion_veredicto (ver arriba)
            mart_eje_reponderado (ver arriba)
            mart_perdida_permanente (ver arriba)
            mart_potencia_eje (ver arriba)
            mart_potencia_resumen (ver arriba)
            mart_robustez_costo (ver arriba)
            mart_robustez_eje (ver arriba)
            mart_validacion_holdout (ver arriba)
            mart_validacion_resultados (ver arriba)
          int_interferencia_mes
            fct_evento (ver arriba)
            mart_anillo
              mart_decision_cierre (ver arriba)
              mart_decision_distancia (ver arriba)
              mart_decision_edad (ver arriba)
              mart_decision_perdida (ver arriba)
            mart_anillo_veredicto
            mart_anisotropia_area (ver arriba)
            mart_costo_calibracion (ver arriba)
            mart_costo_coef (ver arriba)
            mart_costo_cv (ver arriba)
            mart_costo_residuales (ver arriba)
            mart_dosis_geometria_modelo (ver arriba)
            mart_dosis_geometria_muestra (ver arriba)
            mart_dosis_geometria_orden (ver arriba)
            mart_dosis_geometria_potencia (ver arriba)
            mart_dosis_geometria_puerta (ver arriba)
            mart_dosis_geometria_quintiles (ver arriba)
            mart_dosis_geometria_sens (ver arriba)
            mart_dosis_geometria_sim (ver arriba)
            mart_dosis_geometria_veredicto (ver arriba)
            mart_dosis_meses (ver arriba)
            mart_dosis_meses_veredicto (ver arriba)
            mart_dosis_modelo (ver arriba)
            mart_dosis_orden (ver arriba)
            mart_dosis_pad (ver arriba)
            mart_dosis_pad_veredicto (ver arriba)
            mart_dosis_quintiles (ver arriba)
            mart_dosis_sens (ver arriba)
            mart_dosis_veredicto (ver arriba)
            mart_eje_controles (ver arriba)
            mart_eje_controles_rotacion (ver arriba)
            mart_eje_controles_veredicto (ver arriba)
            mart_eje_exposicion (ver arriba)
            mart_eje_exposicion_veredicto (ver arriba)
            mart_eje_reponderado (ver arriba)
            mart_interferencia_anual
              mart_carga_anual
              mart_carga_anual_prueba
            mart_interferencia_brecha
              mart_anisotropia_area (ver arriba)
              mart_costo_calibracion (ver arriba)
              mart_costo_coef (ver arriba)
              mart_costo_cv (ver arriba)
              mart_costo_residuales (ver arriba)
              mart_decision_cierre (ver arriba)
              mart_decision_distancia (ver arriba)
              mart_decision_edad (ver arriba)
              mart_decision_perdida (ver arriba)
              mart_dosis_geometria_modelo (ver arriba)
              mart_dosis_geometria_muestra (ver arriba)
              mart_dosis_geometria_orden (ver arriba)
              mart_dosis_geometria_potencia (ver arriba)
              mart_dosis_geometria_puerta (ver arriba)
              mart_dosis_geometria_quintiles (ver arriba)
              mart_dosis_geometria_sens (ver arriba)
              mart_dosis_geometria_sim (ver arriba)
              mart_dosis_geometria_veredicto (ver arriba)
              mart_dosis_meses (ver arriba)
              mart_dosis_meses_veredicto (ver arriba)
              mart_dosis_modelo (ver arriba)
              mart_dosis_orden (ver arriba)
              mart_dosis_pad (ver arriba)
              mart_dosis_pad_veredicto (ver arriba)
              mart_dosis_quintiles (ver arriba)
              mart_dosis_sens (ver arriba)
              mart_dosis_veredicto (ver arriba)
              mart_eje_controles (ver arriba)
              mart_eje_controles_rotacion (ver arriba)
              mart_eje_controles_veredicto (ver arriba)
              mart_eje_exposicion (ver arriba)
              mart_eje_exposicion_veredicto (ver arriba)
              mart_eje_reponderado (ver arriba)
              mart_interferencia_diferida
                mart_anisotropia_area (ver arriba)
                mart_costo_calibracion (ver arriba)
                mart_costo_coef (ver arriba)
                mart_costo_cv (ver arriba)
                mart_costo_residuales (ver arriba)
                mart_decision_cierre (ver arriba)
                mart_decision_distancia (ver arriba)
                mart_decision_edad (ver arriba)
                mart_decision_perdida (ver arriba)
                mart_diferido_operador
                  mart_decision_cierre (ver arriba)
                  mart_decision_distancia (ver arriba)
                  mart_decision_edad (ver arriba)
                  mart_decision_perdida (ver arriba)
                mart_diferido_rango
                  mart_alcance_rama
                  mart_alcance_rama_anio
                  mart_alcance_rama_diferido
                  mart_alcance_rama_prueba
                  mart_decision_cierre (ver arriba)
                  mart_decision_distancia (ver arriba)
                  mart_decision_edad (ver arriba)
                  mart_decision_perdida (ver arriba)
                mart_eje_controles (ver arriba)
                mart_eje_controles_rotacion (ver arriba)
                mart_eje_controles_veredicto (ver arriba)
                mart_eje_exposicion (ver arriba)
                mart_eje_exposicion_veredicto (ver arriba)
                mart_eje_reponderado (ver arriba)
                mart_perdida_permanente (ver arriba)
                mart_potencia_eje (ver arriba)
                mart_potencia_resumen (ver arriba)
                mart_robustez_costo (ver arriba)
                mart_robustez_eje (ver arriba)
                mart_validacion_holdout (ver arriba)
                mart_validacion_resultados (ver arriba)
              mart_perdida_permanente (ver arriba)
              mart_potencia_dosis (ver arriba)
              mart_potencia_dosis_sim (ver arriba)
              mart_potencia_dosis_veredicto (ver arriba)
              mart_potencia_eje (ver arriba)
              mart_potencia_resumen (ver arriba)
              mart_riesgo_anio (ver arriba)
              mart_riesgo_calibracion (ver arriba)
              mart_riesgo_coef (ver arriba)
              mart_riesgo_modelo (ver arriba)
              mart_riesgo_prueba (ver arriba)
              mart_riesgo_rama (ver arriba)
              mart_robustez_costo (ver arriba)
              mart_robustez_eje (ver arriba)
              mart_validacion_holdout (ver arriba)
              mart_validacion_resultados (ver arriba)
            mart_interferencia_curva
            mart_interferencia_diferida (ver arriba)
            mart_perdida_permanente (ver arriba)
            mart_potencia_dosis (ver arriba)
            mart_potencia_dosis_sim (ver arriba)
            mart_potencia_dosis_veredicto (ver arriba)
            mart_potencia_eje (ver arriba)
            mart_potencia_resumen (ver arriba)
            mart_riesgo_anio (ver arriba)
            mart_riesgo_calibracion (ver arriba)
            mart_riesgo_coef (ver arriba)
            mart_riesgo_modelo (ver arriba)
            mart_riesgo_prueba (ver arriba)
            mart_riesgo_rama (ver arriba)
            mart_robustez_costo (ver arriba)
            mart_robustez_eje (ver arriba)
            mart_validacion_holdout (ver arriba)
            mart_validacion_resultados (ver arriba)
          mart_anisotropia_area (ver arriba)
          mart_costo_calibracion (ver arriba)
          mart_costo_coef (ver arriba)
          mart_costo_cv (ver arriba)
          mart_costo_residuales (ver arriba)
          mart_diferido_operador (ver arriba)
          mart_diferido_rango (ver arriba)
          mart_dosis_geometria_modelo (ver arriba)
          mart_dosis_geometria_muestra (ver arriba)
          mart_dosis_geometria_orden (ver arriba)
          mart_dosis_geometria_potencia (ver arriba)
          mart_dosis_geometria_puerta (ver arriba)
          mart_dosis_geometria_quintiles (ver arriba)
          mart_dosis_geometria_sens (ver arriba)
          mart_dosis_geometria_sim (ver arriba)
          mart_dosis_geometria_veredicto (ver arriba)
          mart_dosis_meses (ver arriba)
          mart_dosis_meses_veredicto (ver arriba)
          mart_dosis_modelo (ver arriba)
          mart_dosis_orden (ver arriba)
          mart_dosis_pad (ver arriba)
          mart_dosis_pad_veredicto (ver arriba)
          mart_dosis_quintiles (ver arriba)
          mart_dosis_sens (ver arriba)
          mart_dosis_veredicto (ver arriba)
          mart_eje_controles (ver arriba)
          mart_eje_controles_rotacion (ver arriba)
          mart_eje_controles_veredicto (ver arriba)
          mart_eje_exposicion (ver arriba)
          mart_eje_exposicion_veredicto (ver arriba)
          mart_eje_reponderado (ver arriba)
          mart_interferencia_diferida (ver arriba)
          mart_perdida_permanente (ver arriba)
          mart_potencia_dosis (ver arriba)
          mart_potencia_dosis_sim (ver arriba)
          mart_potencia_dosis_veredicto (ver arriba)
          mart_potencia_eje (ver arriba)
          mart_potencia_resumen (ver arriba)
          mart_riesgo_anio (ver arriba)
          mart_riesgo_calibracion (ver arriba)
          mart_riesgo_coef (ver arriba)
          mart_riesgo_modelo (ver arriba)
          mart_riesgo_prueba (ver arriba)
          mart_riesgo_rama (ver arriba)
          mart_robustez_costo (ver arriba)
          mart_robustez_eje (ver arriba)
          mart_validacion_holdout (ver arriba)
          mart_validacion_resultados (ver arriba)
        mart_par_rama
          mart_causal_extra (ver arriba)
          mart_causal_operador (ver arriba)
          mart_causal_placebo (ver arriba)
          mart_causal_profundo_d3 (ver arriba)
          mart_causal_profundo_d4 (ver arriba)
          mart_causal_profundo_d5 (ver arriba)
          mart_causal_profundo_d6 (ver arriba)
          mart_causal_profundo_d7 (ver arriba)
          mart_causal_profundo_veredicto (ver arriba)
          mart_causal_serie (ver arriba)
          mart_causal_veredicto (ver arriba)
          mart_mecanismo_banda
          mart_mecanismo_contraste
          mart_mecanismo_muestra
          mart_mecanismo_shmax
          mart_mecanismo_veredicto
            mart_eje_parada (ver arriba)
          mart_riesgo_anio (ver arriba)
          mart_riesgo_calibracion (ver arriba)
          mart_riesgo_coef (ver arriba)
          mart_riesgo_modelo (ver arriba)
          mart_riesgo_prueba (ver arriba)
          mart_riesgo_rama (ver arriba)
        mart_trayectoria_banda
        mart_trayectoria_cobertura
          mart_alcance_rama (ver arriba)
          mart_alcance_rama_anio (ver arriba)
          mart_alcance_rama_diferido (ver arriba)
          mart_alcance_rama_prueba (ver arriba)
          mart_causal_extra (ver arriba)
          mart_causal_operador (ver arriba)
          mart_causal_placebo (ver arriba)
          mart_causal_serie (ver arriba)
          mart_causal_veredicto (ver arriba)
          mart_hijo_pad_anio (ver arriba)
          mart_hijo_pad_coef (ver arriba)
          mart_hijo_pad_equilibrio (ver arriba)
          mart_hijo_pad_muestra (ver arriba)
          mart_hijo_pad_resumen (ver arriba)
          mart_mecanismo_banda (ver arriba)
          mart_mecanismo_contraste (ver arriba)
          mart_mecanismo_muestra (ver arriba)
          mart_mecanismo_shmax (ver arriba)
          mart_mecanismo_veredicto (ver arriba)
          mart_riesgo_anio (ver arriba)
          mart_riesgo_calibracion (ver arriba)
          mart_riesgo_coef (ver arriba)
          mart_riesgo_modelo (ver arriba)
          mart_riesgo_prueba (ver arriba)
          mart_riesgo_rama (ver arriba)
        mart_trayectoria_cruce
        mart_trayectoria_par
          mart_alcance_rama (ver arriba)
          mart_alcance_rama_anio (ver arriba)
          mart_alcance_rama_diferido (ver arriba)
          mart_alcance_rama_prueba (ver arriba)
          mart_dosis_geometria_modelo (ver arriba)
          mart_dosis_geometria_muestra (ver arriba)
          mart_dosis_geometria_orden (ver arriba)
          mart_dosis_geometria_potencia (ver arriba)
          mart_dosis_geometria_puerta (ver arriba)
          mart_dosis_geometria_quintiles (ver arriba)
          mart_dosis_geometria_sens (ver arriba)
          mart_dosis_geometria_sim (ver arriba)
          mart_dosis_geometria_veredicto (ver arriba)
          mart_mecanismo_banda (ver arriba)
          mart_mecanismo_contraste (ver arriba)
          mart_mecanismo_muestra (ver arriba)
          mart_mecanismo_shmax (ver arriba)
          mart_mecanismo_veredicto (ver arriba)
          mart_riesgo_anio (ver arriba)
          mart_riesgo_calibracion (ver arriba)
          mart_riesgo_coef (ver arriba)
          mart_riesgo_modelo (ver arriba)
          mart_riesgo_prueba (ver arriba)
          mart_riesgo_rama (ver arriba)
        mart_trayectoria_pozo
          mart_hijo_pad_anio (ver arriba)
          mart_hijo_pad_coef (ver arriba)
          mart_hijo_pad_equilibrio (ver arriba)
          mart_hijo_pad_muestra (ver arriba)
          mart_hijo_pad_resumen (ver arriba)
        mart_trayectoria_resumen
      mart_alcance_rama (ver arriba)
      mart_alcance_rama_anio (ver arriba)
      mart_alcance_rama_diferido (ver arriba)
      mart_alcance_rama_prueba (ver arriba)
      mart_anillo (ver arriba)
      mart_anillo_veredicto (ver arriba)
      mart_bloques (ver arriba)
      mart_calendario_costo_k
      mart_calendario_k
      mart_calendario_matriz
      mart_calendario_prueba
      mart_carga_anual (ver arriba)
      mart_carga_anual_prueba (ver arriba)
      mart_carga_curva
      mart_carga_fracturas
      mart_carga_operador
      mart_causal_extra (ver arriba)
      mart_causal_operador (ver arriba)
      mart_causal_placebo (ver arriba)
      mart_causal_profundo_d3 (ver arriba)
      mart_causal_profundo_d4 (ver arriba)
      mart_causal_profundo_d5 (ver arriba)
      mart_causal_profundo_d6 (ver arriba)
      mart_causal_profundo_d7 (ver arriba)
      mart_causal_profundo_veredicto (ver arriba)
      mart_causal_serie (ver arriba)
      mart_causal_veredicto (ver arriba)
      mart_descomposicion_aditiva
      mart_descomposicion_cierres
      mart_descomposicion_distancia
        mart_decision_cierre (ver arriba)
        mart_decision_distancia (ver arriba)
        mart_decision_edad (ver arriba)
        mart_decision_perdida (ver arriba)
      mart_descomposicion_k
      mart_dias_perdidos
      mart_dias_perdidos_colorado
      mart_dias_perdidos_colorado_mitades
      mart_dias_perdidos_colorado_operador
      mart_dias_perdidos_colorado_prueba
      mart_dias_perdidos_estado
      mart_dias_perdidos_mitades
      mart_dias_perdidos_operador
      mart_dias_perdidos_prueba
      mart_dosis_geometria_modelo (ver arriba)
      mart_dosis_geometria_muestra (ver arriba)
      mart_dosis_geometria_orden (ver arriba)
      mart_dosis_geometria_potencia (ver arriba)
      mart_dosis_geometria_puerta (ver arriba)
      mart_dosis_geometria_quintiles (ver arriba)
      mart_dosis_geometria_sens (ver arriba)
      mart_dosis_geometria_sim (ver arriba)
      mart_dosis_geometria_veredicto (ver arriba)
      mart_dosis_meses (ver arriba)
      mart_dosis_meses_veredicto (ver arriba)
      mart_dosis_modelo (ver arriba)
      mart_dosis_orden (ver arriba)
      mart_dosis_pad (ver arriba)
      mart_dosis_pad_veredicto (ver arriba)
      mart_dosis_quintiles (ver arriba)
      mart_dosis_sens (ver arriba)
      mart_dosis_veredicto (ver arriba)
      mart_eje_controles (ver arriba)
      mart_eje_controles_rotacion (ver arriba)
      mart_eje_controles_veredicto (ver arriba)
      mart_gas
      mart_gas_fechas
      mart_gas_gor
      mart_gas_pretendencia
      mart_gas_veredicto
      mart_golpes_mismo_mes
      mart_golpes_mismo_mes_colorado
      mart_golpes_mismo_mes_colorado_prueba
      mart_golpes_mismo_mes_prueba
        mart_calendario_costo_k (ver arriba)
        mart_calendario_k (ver arriba)
        mart_calendario_matriz (ver arriba)
        mart_calendario_prueba (ver arriba)
      mart_golpes_mismo_padre
      mart_golpes_mismo_padre_colorado
      mart_golpes_mismo_padre_colorado_prueba
      mart_golpes_mismo_padre_prueba
      mart_inyeccion
      mart_mecanismo_banda (ver arriba)
      mart_mecanismo_contraste (ver arriba)
      mart_mecanismo_muestra (ver arriba)
      mart_mecanismo_shmax (ver arriba)
      mart_mecanismo_veredicto (ver arriba)
      mart_par_rama (ver arriba)
      mart_placebo_eje
      mart_placebo_fechas
      mart_placebo_permutacion
      mart_placebo_pretrend
        mart_diferido_operador (ver arriba)
        mart_diferido_rango (ver arriba)
      mart_placebo_pretrend_base_original
      mart_placebo_pretrend_sin_previos
      mart_potencia_dosis (ver arriba)
      mart_potencia_dosis_sim (ver arriba)
      mart_potencia_dosis_veredicto (ver arriba)
      mart_robustez_operador
      mart_robustez_operador_veredicto
      mart_sincronia
        mart_bloques (ver arriba)
      mart_sincronia_pendiente
      mart_trayectoria_banda (ver arriba)
      mart_trayectoria_cobertura (ver arriba)
      mart_trayectoria_cruce (ver arriba)
      mart_trayectoria_par (ver arriba)
      mart_trayectoria_pozo (ver arriba)
      mart_trayectoria_resumen (ver arriba)
    mart_alcance_rama (ver arriba)
    mart_alcance_rama_anio (ver arriba)
    mart_alcance_rama_diferido (ver arriba)
    mart_alcance_rama_prueba (ver arriba)
    mart_bloques (ver arriba)
    mart_carga_anual (ver arriba)
    mart_carga_anual_prueba (ver arriba)
    mart_carga_curva (ver arriba)
    mart_carga_fracturas (ver arriba)
    mart_carga_operador (ver arriba)
    mart_dosis_geometria_modelo (ver arriba)
    mart_dosis_geometria_muestra (ver arriba)
    mart_dosis_geometria_orden (ver arriba)
    mart_dosis_geometria_potencia (ver arriba)
    mart_dosis_geometria_puerta (ver arriba)
    mart_dosis_geometria_quintiles (ver arriba)
    mart_dosis_geometria_sens (ver arriba)
    mart_dosis_geometria_sim (ver arriba)
    mart_dosis_geometria_veredicto (ver arriba)
    mart_dosis_meses (ver arriba)
    mart_dosis_meses_veredicto (ver arriba)
    mart_dosis_modelo (ver arriba)
    mart_dosis_orden (ver arriba)
    mart_dosis_pad (ver arriba)
    mart_dosis_pad_veredicto (ver arriba)
    mart_dosis_quintiles (ver arriba)
    mart_dosis_sens (ver arriba)
    mart_dosis_veredicto (ver arriba)
    mart_inyeccion (ver arriba)
    mart_potencia_dosis (ver arriba)
    mart_potencia_dosis_sim (ver arriba)
    mart_potencia_dosis_veredicto (ver arriba)
    mart_sincronia (ver arriba)
    mart_sincronia_pendiente (ver arriba)
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
                mart_validacion_holdout (ver arriba)
                mart_validacion_resultados (ver arriba)
              mart_alcance_rama (ver arriba)
              mart_alcance_rama_anio (ver arriba)
              mart_alcance_rama_diferido (ver arriba)
              mart_alcance_rama_prueba (ver arriba)
              mart_anillo (ver arriba)
              mart_anillo_veredicto (ver arriba)
              mart_anisotropia_area (ver arriba)
              mart_bloques (ver arriba)
              mart_calendario_costo_k (ver arriba)
              mart_calendario_k (ver arriba)
              mart_calendario_matriz (ver arriba)
              mart_calendario_prueba (ver arriba)
              mart_carga_anual (ver arriba)
              mart_carga_anual_prueba (ver arriba)
              mart_carga_curva (ver arriba)
              mart_carga_fracturas (ver arriba)
              mart_carga_operador (ver arriba)
              mart_causal_extra (ver arriba)
              mart_causal_operador (ver arriba)
              mart_causal_placebo (ver arriba)
              mart_causal_profundo_d3 (ver arriba)
              mart_causal_profundo_d4 (ver arriba)
              mart_causal_profundo_d5 (ver arriba)
              mart_causal_profundo_d6 (ver arriba)
              mart_causal_profundo_d7 (ver arriba)
              mart_causal_profundo_veredicto (ver arriba)
              mart_causal_serie (ver arriba)
              mart_causal_veredicto (ver arriba)
              mart_costo_calibracion (ver arriba)
              mart_costo_coef (ver arriba)
              mart_costo_cv (ver arriba)
              mart_costo_residuales (ver arriba)
              mart_decision_cierre (ver arriba)
              mart_decision_distancia (ver arriba)
              mart_decision_edad (ver arriba)
              mart_decision_perdida (ver arriba)
              mart_descomposicion_aditiva (ver arriba)
              mart_descomposicion_cierres (ver arriba)
              mart_descomposicion_distancia (ver arriba)
              mart_descomposicion_k (ver arriba)
              mart_dias_perdidos (ver arriba)
              mart_dias_perdidos_colorado (ver arriba)
              mart_dias_perdidos_colorado_mitades (ver arriba)
              mart_dias_perdidos_colorado_operador (ver arriba)
              mart_dias_perdidos_colorado_prueba (ver arriba)
              mart_dias_perdidos_estado (ver arriba)
              mart_dias_perdidos_mitades (ver arriba)
              mart_dias_perdidos_operador (ver arriba)
              mart_dias_perdidos_prueba (ver arriba)
              mart_diferido_operador (ver arriba)
              mart_diferido_rango (ver arriba)
              mart_dosis_geometria_modelo (ver arriba)
              mart_dosis_geometria_muestra (ver arriba)
              mart_dosis_geometria_orden (ver arriba)
              mart_dosis_geometria_potencia (ver arriba)
              mart_dosis_geometria_puerta (ver arriba)
              mart_dosis_geometria_quintiles (ver arriba)
              mart_dosis_geometria_sens (ver arriba)
              mart_dosis_geometria_sim (ver arriba)
              mart_dosis_geometria_veredicto (ver arriba)
              mart_dosis_meses (ver arriba)
              mart_dosis_meses_veredicto (ver arriba)
              mart_dosis_modelo (ver arriba)
              mart_dosis_orden (ver arriba)
              mart_dosis_pad (ver arriba)
              mart_dosis_pad_veredicto (ver arriba)
              mart_dosis_quintiles (ver arriba)
              mart_dosis_sens (ver arriba)
              mart_dosis_veredicto (ver arriba)
              mart_eje_controles (ver arriba)
              mart_eje_controles_rotacion (ver arriba)
              mart_eje_controles_veredicto (ver arriba)
              mart_eje_exposicion (ver arriba)
              mart_eje_exposicion_veredicto (ver arriba)
              mart_eje_reponderado (ver arriba)
              mart_gas (ver arriba)
              mart_gas_fechas (ver arriba)
              mart_gas_gor (ver arriba)
              mart_gas_pretendencia (ver arriba)
              mart_gas_veredicto (ver arriba)
              mart_golpes_mismo_mes (ver arriba)
              mart_golpes_mismo_mes_colorado (ver arriba)
              mart_golpes_mismo_mes_colorado_prueba (ver arriba)
              mart_golpes_mismo_mes_prueba (ver arriba)
              mart_golpes_mismo_padre (ver arriba)
              mart_golpes_mismo_padre_colorado (ver arriba)
              mart_golpes_mismo_padre_colorado_prueba (ver arriba)
              mart_golpes_mismo_padre_prueba (ver arriba)
              mart_hijo_celdas_coef (ver arriba)
              mart_hijo_celdas_equilibrio (ver arriba)
              mart_hijo_celdas_resumen (ver arriba)
              mart_hijo_coef (ver arriba)
              mart_hijo_equilibrio (ver arriba)
              mart_hijo_grupos (ver arriba)
              mart_hijo_muestra (ver arriba)
              mart_hijo_pad_anio (ver arriba)
              mart_hijo_pad_coef (ver arriba)
              mart_hijo_pad_equilibrio (ver arriba)
              mart_hijo_pad_muestra (ver arriba)
              mart_hijo_pad_resumen (ver arriba)
              mart_inyeccion (ver arriba)
              mart_mecanismo_banda (ver arriba)
              mart_mecanismo_contraste (ver arriba)
              mart_mecanismo_muestra (ver arriba)
              mart_mecanismo_shmax (ver arriba)
              mart_mecanismo_veredicto (ver arriba)
              mart_par_rama (ver arriba)
              mart_perdida_permanente (ver arriba)
              mart_placebo_eje (ver arriba)
              mart_placebo_fechas (ver arriba)
              mart_placebo_permutacion (ver arriba)
              mart_placebo_pretrend (ver arriba)
              mart_placebo_pretrend_base_original (ver arriba)
              mart_placebo_pretrend_sin_previos (ver arriba)
              mart_potencia_dosis (ver arriba)
              mart_potencia_dosis_sim (ver arriba)
              mart_potencia_dosis_veredicto (ver arriba)
              mart_potencia_eje (ver arriba)
              mart_potencia_resumen (ver arriba)
              mart_riesgo_anio (ver arriba)
              mart_riesgo_calibracion (ver arriba)
              mart_riesgo_coef (ver arriba)
              mart_riesgo_modelo (ver arriba)
              mart_riesgo_prueba (ver arriba)
              mart_riesgo_rama (ver arriba)
              mart_robustez_costo (ver arriba)
              mart_robustez_eje (ver arriba)
              mart_robustez_operador (ver arriba)
              mart_robustez_operador_veredicto (ver arriba)
              mart_sincronia (ver arriba)
              mart_sincronia_pendiente (ver arriba)
              mart_trayectoria_banda (ver arriba)
              mart_trayectoria_cobertura (ver arriba)
              mart_trayectoria_cruce (ver arriba)
              mart_trayectoria_par (ver arriba)
              mart_trayectoria_pozo (ver arriba)
              mart_trayectoria_resumen (ver arriba)
              mart_validacion_holdout (ver arriba)
              mart_validacion_resultados (ver arriba)
        int_pozo_pad (ver arriba)
        int_pozo_ubicacion (ver arriba)
      int_pozo_mop
        mart_curva_tipo
        mart_hijo_celdas_coef (ver arriba)
        mart_hijo_celdas_equilibrio (ver arriba)
        mart_hijo_celdas_resumen (ver arriba)
        mart_hijo_coef (ver arriba)
        mart_hijo_equilibrio (ver arriba)
        mart_hijo_grupos (ver arriba)
        mart_hijo_muestra (ver arriba)
        mart_hijo_pad_anio (ver arriba)
        mart_hijo_pad_coef (ver arriba)
        mart_hijo_pad_equilibrio (ver arriba)
        mart_hijo_pad_muestra (ver arriba)
        mart_hijo_pad_resumen (ver arriba)
        mart_pozo_12m (ver arriba)
      mart_causal_profundo_d3 (ver arriba)
      mart_causal_profundo_d4 (ver arriba)
      mart_causal_profundo_d5 (ver arriba)
      mart_causal_profundo_d6 (ver arriba)
      mart_causal_profundo_d7 (ver arriba)
      mart_causal_profundo_veredicto (ver arriba)
      mart_dias_perdidos (ver arriba)
      mart_dias_perdidos_colorado (ver arriba)
      mart_dias_perdidos_colorado_mitades (ver arriba)
      mart_dias_perdidos_colorado_operador (ver arriba)
      mart_dias_perdidos_colorado_prueba (ver arriba)
      mart_dias_perdidos_estado (ver arriba)
      mart_dias_perdidos_mitades (ver arriba)
      mart_dias_perdidos_operador (ver arriba)
      mart_dias_perdidos_prueba (ver arriba)
      mart_gas (ver arriba)
      mart_gas_fechas (ver arriba)
      mart_gas_gor (ver arriba)
      mart_gas_pretendencia (ver arriba)
      mart_gas_veredicto (ver arriba)
      mart_golpes_mismo_mes (ver arriba)
      mart_golpes_mismo_mes_colorado (ver arriba)
      mart_golpes_mismo_mes_colorado_prueba (ver arriba)
      mart_golpes_mismo_mes_prueba (ver arriba)
      mart_golpes_mismo_padre (ver arriba)
      mart_golpes_mismo_padre_colorado (ver arriba)
      mart_golpes_mismo_padre_colorado_prueba (ver arriba)
      mart_golpes_mismo_padre_prueba (ver arriba)
      mart_par_rama (ver arriba)
      mart_pozo_12m (ver arriba)
      mart_trayectoria_banda (ver arriba)
      mart_trayectoria_cobertura (ver arriba)
      mart_trayectoria_cruce (ver arriba)
      mart_trayectoria_par (ver arriba)
      mart_trayectoria_pozo (ver arriba)
      mart_trayectoria_resumen (ver arriba)
    fct_produccion
      dim_pozo (ver arriba)
      int_interferencia_evento (ver arriba)
      int_interferencia_mes (ver arriba)
      int_pozo_mop (ver arriba)
      int_prod_corte (ver arriba)
      mart_alcance_rama (ver arriba)
      mart_alcance_rama_anio (ver arriba)
      mart_alcance_rama_diferido (ver arriba)
      mart_alcance_rama_prueba (ver arriba)
      mart_anillo (ver arriba)
      mart_anillo_veredicto (ver arriba)
      mart_anisotropia_area (ver arriba)
      mart_bloques (ver arriba)
      mart_calendario_costo_k (ver arriba)
      mart_calendario_k (ver arriba)
      mart_calendario_matriz (ver arriba)
      mart_calendario_prueba (ver arriba)
      mart_carga_anual (ver arriba)
      mart_carga_anual_prueba (ver arriba)
      mart_causal_extra (ver arriba)
      mart_causal_operador (ver arriba)
      mart_causal_placebo (ver arriba)
      mart_causal_profundo_d3 (ver arriba)
      mart_causal_profundo_d4 (ver arriba)
      mart_causal_profundo_d5 (ver arriba)
      mart_causal_profundo_d6 (ver arriba)
      mart_causal_profundo_d7 (ver arriba)
      mart_causal_profundo_veredicto (ver arriba)
      mart_causal_serie (ver arriba)
      mart_causal_veredicto (ver arriba)
      mart_costo_calibracion (ver arriba)
      mart_costo_coef (ver arriba)
      mart_costo_cv (ver arriba)
      mart_costo_residuales (ver arriba)
      mart_descomposicion_aditiva (ver arriba)
      mart_descomposicion_cierres (ver arriba)
      mart_descomposicion_distancia (ver arriba)
      mart_descomposicion_k (ver arriba)
      mart_dias_perdidos (ver arriba)
      mart_dias_perdidos_colorado (ver arriba)
      mart_dias_perdidos_colorado_mitades (ver arriba)
      mart_dias_perdidos_colorado_operador (ver arriba)
      mart_dias_perdidos_colorado_prueba (ver arriba)
      mart_dias_perdidos_estado (ver arriba)
      mart_dias_perdidos_mitades (ver arriba)
      mart_dias_perdidos_operador (ver arriba)
      mart_dias_perdidos_prueba (ver arriba)
      mart_diferido_operador (ver arriba)
      mart_diferido_rango (ver arriba)
      mart_dosis_geometria_modelo (ver arriba)
      mart_dosis_geometria_muestra (ver arriba)
      mart_dosis_geometria_orden (ver arriba)
      mart_dosis_geometria_potencia (ver arriba)
      mart_dosis_geometria_puerta (ver arriba)
      mart_dosis_geometria_quintiles (ver arriba)
      mart_dosis_geometria_sens (ver arriba)
      mart_dosis_geometria_sim (ver arriba)
      mart_dosis_geometria_veredicto (ver arriba)
      mart_dosis_meses (ver arriba)
      mart_dosis_meses_veredicto (ver arriba)
      mart_dosis_modelo (ver arriba)
      mart_dosis_orden (ver arriba)
      mart_dosis_pad (ver arriba)
      mart_dosis_pad_veredicto (ver arriba)
      mart_dosis_quintiles (ver arriba)
      mart_dosis_sens (ver arriba)
      mart_dosis_veredicto (ver arriba)
      mart_eje_controles (ver arriba)
      mart_eje_controles_rotacion (ver arriba)
      mart_eje_controles_veredicto (ver arriba)
      mart_gas (ver arriba)
      mart_gas_fechas (ver arriba)
      mart_gas_gor (ver arriba)
      mart_gas_pretendencia (ver arriba)
      mart_gas_veredicto (ver arriba)
      mart_golpes_mismo_mes (ver arriba)
      mart_golpes_mismo_mes_colorado (ver arriba)
      mart_golpes_mismo_mes_colorado_prueba (ver arriba)
      mart_golpes_mismo_mes_prueba (ver arriba)
      mart_golpes_mismo_padre (ver arriba)
      mart_golpes_mismo_padre_colorado (ver arriba)
      mart_golpes_mismo_padre_colorado_prueba (ver arriba)
      mart_golpes_mismo_padre_prueba (ver arriba)
      mart_inyeccion (ver arriba)
      mart_mecanismo_banda (ver arriba)
      mart_mecanismo_contraste (ver arriba)
      mart_mecanismo_muestra (ver arriba)
      mart_mecanismo_shmax (ver arriba)
      mart_mecanismo_veredicto (ver arriba)
      mart_perdida_permanente (ver arriba)
      mart_placebo_eje (ver arriba)
      mart_placebo_fechas (ver arriba)
      mart_placebo_permutacion (ver arriba)
      mart_placebo_pretrend (ver arriba)
      mart_placebo_pretrend_base_original (ver arriba)
      mart_placebo_pretrend_sin_previos (ver arriba)
      mart_potencia_dosis (ver arriba)
      mart_potencia_dosis_sim (ver arriba)
      mart_potencia_dosis_veredicto (ver arriba)
      mart_riesgo_anio (ver arriba)
      mart_riesgo_calibracion (ver arriba)
      mart_riesgo_coef (ver arriba)
      mart_riesgo_modelo (ver arriba)
      mart_riesgo_prueba (ver arriba)
      mart_riesgo_rama (ver arriba)
      mart_robustez_operador (ver arriba)
      mart_robustez_operador_veredicto (ver arriba)
      mart_sincronia (ver arriba)
      mart_sincronia_pendiente (ver arriba)
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
| dim_fractura_pozo | dimensión | extraccion_fractura | pipeline/sql/02_core.sql |
| dim_fractura_pozo | dimensión | stg_fractura | pipeline/sql/02_core.sql |
| dim_pozo | dimensión | fct_produccion | pipeline/sql/02_core.sql |
| dim_pozo | dimensión | stg_produccion | pipeline/sql/02_core.sql |
| extraccion_fractura | auxiliar | manifiesto:fecha_extraccion | pipeline/sql/02_core.sql |
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
| mart_alcance_rama | mart | fct_produccion | pipeline.alcance_rama |
| mart_alcance_rama | mart | int_frac_hijo | pipeline.alcance_rama |
| mart_alcance_rama | mart | int_pozo_ubicacion | pipeline.alcance_rama |
| mart_alcance_rama | mart | mart_diferido_rango | pipeline.alcance_rama |
| mart_alcance_rama | mart | mart_trayectoria_cobertura | pipeline.alcance_rama |
| mart_alcance_rama | mart | mart_trayectoria_par | pipeline.alcance_rama |
| mart_alcance_rama | mart | stg_fractura | pipeline.alcance_rama |
| mart_alcance_rama_anio | mart | fct_produccion | pipeline.alcance_rama |
| mart_alcance_rama_anio | mart | int_frac_hijo | pipeline.alcance_rama |
| mart_alcance_rama_anio | mart | int_pozo_ubicacion | pipeline.alcance_rama |
| mart_alcance_rama_anio | mart | mart_diferido_rango | pipeline.alcance_rama |
| mart_alcance_rama_anio | mart | mart_trayectoria_cobertura | pipeline.alcance_rama |
| mart_alcance_rama_anio | mart | mart_trayectoria_par | pipeline.alcance_rama |
| mart_alcance_rama_anio | mart | stg_fractura | pipeline.alcance_rama |
| mart_alcance_rama_diferido | mart | fct_produccion | pipeline.alcance_rama |
| mart_alcance_rama_diferido | mart | int_frac_hijo | pipeline.alcance_rama |
| mart_alcance_rama_diferido | mart | int_pozo_ubicacion | pipeline.alcance_rama |
| mart_alcance_rama_diferido | mart | mart_diferido_rango | pipeline.alcance_rama |
| mart_alcance_rama_diferido | mart | mart_trayectoria_cobertura | pipeline.alcance_rama |
| mart_alcance_rama_diferido | mart | mart_trayectoria_par | pipeline.alcance_rama |
| mart_alcance_rama_diferido | mart | stg_fractura | pipeline.alcance_rama |
| mart_alcance_rama_prueba | mart | fct_produccion | pipeline.alcance_rama |
| mart_alcance_rama_prueba | mart | int_frac_hijo | pipeline.alcance_rama |
| mart_alcance_rama_prueba | mart | int_pozo_ubicacion | pipeline.alcance_rama |
| mart_alcance_rama_prueba | mart | mart_diferido_rango | pipeline.alcance_rama |
| mart_alcance_rama_prueba | mart | mart_trayectoria_cobertura | pipeline.alcance_rama |
| mart_alcance_rama_prueba | mart | mart_trayectoria_par | pipeline.alcance_rama |
| mart_alcance_rama_prueba | mart | stg_fractura | pipeline.alcance_rama |
| mart_anillo | mart | fct_produccion | pipeline.anillo |
| mart_anillo | mart | int_frac_hijo | pipeline.anillo |
| mart_anillo | mart | int_interferencia_mes | pipeline.anillo |
| mart_anillo | mart | int_pozo_ubicacion | pipeline.anillo |
| mart_anillo_veredicto | mart | fct_produccion | pipeline.anillo |
| mart_anillo_veredicto | mart | int_frac_hijo | pipeline.anillo |
| mart_anillo_veredicto | mart | int_interferencia_mes | pipeline.anillo |
| mart_anillo_veredicto | mart | int_pozo_ubicacion | pipeline.anillo |
| mart_anisotropia_area | mart | dim_fractura_pozo | pipeline.costo |
| mart_anisotropia_area | mart | fct_produccion | pipeline.costo |
| mart_anisotropia_area | mart | int_interferencia_clase | pipeline.costo |
| mart_anisotropia_area | mart | int_interferencia_evento | pipeline.costo |
| mart_anisotropia_area | mart | int_interferencia_mes | pipeline.costo |
| mart_anisotropia_area | mart | int_pozo_ubicacion | pipeline.costo |
| mart_anisotropia_area | mart | mart_interferencia_brecha | pipeline.costo |
| mart_anisotropia_area | mart | mart_interferencia_diferida | pipeline.costo |
| mart_bloques | mart | fct_produccion | pipeline.bloques |
| mart_bloques | mart | int_frac_hijo | pipeline.bloques |
| mart_bloques | mart | int_pozo_ubicacion | pipeline.bloques |
| mart_bloques | mart | mart_hijo_coef | pipeline.bloques |
| mart_bloques | mart | mart_robustez_eje | pipeline.bloques |
| mart_bloques | mart | mart_sincronia | pipeline.bloques |
| mart_bloques | mart | stg_fractura | pipeline.bloques |
| mart_calendario_costo_k | mart | fct_produccion | pipeline.calendario_golpes |
| mart_calendario_costo_k | mart | int_frac_hijo | pipeline.calendario_golpes |
| mart_calendario_costo_k | mart | int_pozo_ubicacion | pipeline.calendario_golpes |
| mart_calendario_costo_k | mart | mart_golpes_mismo_mes_prueba | pipeline.calendario_golpes |
| mart_calendario_k | mart | fct_produccion | pipeline.calendario_golpes |
| mart_calendario_k | mart | int_frac_hijo | pipeline.calendario_golpes |
| mart_calendario_k | mart | int_pozo_ubicacion | pipeline.calendario_golpes |
| mart_calendario_k | mart | mart_golpes_mismo_mes_prueba | pipeline.calendario_golpes |
| mart_calendario_matriz | mart | fct_produccion | pipeline.calendario_golpes |
| mart_calendario_matriz | mart | int_frac_hijo | pipeline.calendario_golpes |
| mart_calendario_matriz | mart | int_pozo_ubicacion | pipeline.calendario_golpes |
| mart_calendario_matriz | mart | mart_golpes_mismo_mes_prueba | pipeline.calendario_golpes |
| mart_calendario_prueba | mart | fct_produccion | pipeline.calendario_golpes |
| mart_calendario_prueba | mart | int_frac_hijo | pipeline.calendario_golpes |
| mart_calendario_prueba | mart | int_pozo_ubicacion | pipeline.calendario_golpes |
| mart_calendario_prueba | mart | mart_golpes_mismo_mes_prueba | pipeline.calendario_golpes |
| mart_carga_anual | mart | fct_produccion | pipeline.carga_anual |
| mart_carga_anual | mart | int_frac_hijo | pipeline.carga_anual |
| mart_carga_anual | mart | int_pozo_ubicacion | pipeline.carga_anual |
| mart_carga_anual | mart | mart_interferencia_anual | pipeline.carga_anual |
| mart_carga_anual | mart | stg_fractura | pipeline.carga_anual |
| mart_carga_anual_prueba | mart | fct_produccion | pipeline.carga_anual |
| mart_carga_anual_prueba | mart | int_frac_hijo | pipeline.carga_anual |
| mart_carga_anual_prueba | mart | int_pozo_ubicacion | pipeline.carga_anual |
| mart_carga_anual_prueba | mart | mart_interferencia_anual | pipeline.carga_anual |
| mart_carga_anual_prueba | mart | stg_fractura | pipeline.carga_anual |
| mart_carga_curva | mart | int_frac_hijo | pipeline.carga |
| mart_carga_curva | mart | int_pozo_ubicacion | pipeline.carga |
| mart_carga_curva | mart | stg_fractura | pipeline.carga |
| mart_carga_fracturas | mart | int_frac_hijo | pipeline.carga |
| mart_carga_fracturas | mart | int_pozo_ubicacion | pipeline.carga |
| mart_carga_fracturas | mart | stg_fractura | pipeline.carga |
| mart_carga_operador | mart | int_frac_hijo | pipeline.carga |
| mart_carga_operador | mart | int_pozo_ubicacion | pipeline.carga |
| mart_carga_operador | mart | stg_fractura | pipeline.carga |
| mart_causal_extra | mart | fct_produccion | pipeline.causal |
| mart_causal_extra | mart | int_frac_hijo | pipeline.causal |
| mart_causal_extra | mart | int_pozo_ubicacion | pipeline.causal |
| mart_causal_extra | mart | mart_causal_profundo_d3 | pipeline.causal |
| mart_causal_extra | mart | mart_causal_profundo_d5 | pipeline.causal |
| mart_causal_extra | mart | mart_causal_profundo_d6 | pipeline.causal |
| mart_causal_extra | mart | mart_causal_profundo_d7 | pipeline.causal |
| mart_causal_extra | mart | mart_causal_profundo_veredicto | pipeline.causal |
| mart_causal_extra | mart | mart_par_rama | pipeline.causal |
| mart_causal_extra | mart | mart_trayectoria_cobertura | pipeline.causal |
| mart_causal_operador | mart | fct_produccion | pipeline.causal |
| mart_causal_operador | mart | int_frac_hijo | pipeline.causal |
| mart_causal_operador | mart | int_pozo_ubicacion | pipeline.causal |
| mart_causal_operador | mart | mart_causal_profundo_d3 | pipeline.causal |
| mart_causal_operador | mart | mart_causal_profundo_d5 | pipeline.causal |
| mart_causal_operador | mart | mart_causal_profundo_d6 | pipeline.causal |
| mart_causal_operador | mart | mart_causal_profundo_d7 | pipeline.causal |
| mart_causal_operador | mart | mart_causal_profundo_veredicto | pipeline.causal |
| mart_causal_operador | mart | mart_par_rama | pipeline.causal |
| mart_causal_operador | mart | mart_trayectoria_cobertura | pipeline.causal |
| mart_causal_placebo | mart | fct_produccion | pipeline.causal |
| mart_causal_placebo | mart | int_frac_hijo | pipeline.causal |
| mart_causal_placebo | mart | int_pozo_ubicacion | pipeline.causal |
| mart_causal_placebo | mart | mart_causal_profundo_d3 | pipeline.causal |
| mart_causal_placebo | mart | mart_causal_profundo_d5 | pipeline.causal |
| mart_causal_placebo | mart | mart_causal_profundo_d6 | pipeline.causal |
| mart_causal_placebo | mart | mart_causal_profundo_d7 | pipeline.causal |
| mart_causal_placebo | mart | mart_causal_profundo_veredicto | pipeline.causal |
| mart_causal_placebo | mart | mart_par_rama | pipeline.causal |
| mart_causal_placebo | mart | mart_trayectoria_cobertura | pipeline.causal |
| mart_causal_profundo_d3 | mart | dim_fractura_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d3 | mart | dim_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d3 | mart | fct_produccion | pipeline.causal_profundo |
| mart_causal_profundo_d3 | mart | int_frac_hijo | pipeline.causal_profundo |
| mart_causal_profundo_d3 | mart | int_pozo_ubicacion | pipeline.causal_profundo |
| mart_causal_profundo_d3 | mart | mart_causal_veredicto | pipeline.causal_profundo |
| mart_causal_profundo_d3 | mart | mart_par_rama | pipeline.causal_profundo |
| mart_causal_profundo_d4 | mart | dim_fractura_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d4 | mart | dim_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d4 | mart | fct_produccion | pipeline.causal_profundo |
| mart_causal_profundo_d4 | mart | int_frac_hijo | pipeline.causal_profundo |
| mart_causal_profundo_d4 | mart | int_pozo_ubicacion | pipeline.causal_profundo |
| mart_causal_profundo_d4 | mart | mart_causal_veredicto | pipeline.causal_profundo |
| mart_causal_profundo_d4 | mart | mart_par_rama | pipeline.causal_profundo |
| mart_causal_profundo_d5 | mart | dim_fractura_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d5 | mart | dim_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d5 | mart | fct_produccion | pipeline.causal_profundo |
| mart_causal_profundo_d5 | mart | int_frac_hijo | pipeline.causal_profundo |
| mart_causal_profundo_d5 | mart | int_pozo_ubicacion | pipeline.causal_profundo |
| mart_causal_profundo_d5 | mart | mart_causal_veredicto | pipeline.causal_profundo |
| mart_causal_profundo_d5 | mart | mart_par_rama | pipeline.causal_profundo |
| mart_causal_profundo_d6 | mart | dim_fractura_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d6 | mart | dim_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d6 | mart | fct_produccion | pipeline.causal_profundo |
| mart_causal_profundo_d6 | mart | int_frac_hijo | pipeline.causal_profundo |
| mart_causal_profundo_d6 | mart | int_pozo_ubicacion | pipeline.causal_profundo |
| mart_causal_profundo_d6 | mart | mart_causal_veredicto | pipeline.causal_profundo |
| mart_causal_profundo_d6 | mart | mart_par_rama | pipeline.causal_profundo |
| mart_causal_profundo_d7 | mart | dim_fractura_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d7 | mart | dim_pozo | pipeline.causal_profundo |
| mart_causal_profundo_d7 | mart | fct_produccion | pipeline.causal_profundo |
| mart_causal_profundo_d7 | mart | int_frac_hijo | pipeline.causal_profundo |
| mart_causal_profundo_d7 | mart | int_pozo_ubicacion | pipeline.causal_profundo |
| mart_causal_profundo_d7 | mart | mart_causal_veredicto | pipeline.causal_profundo |
| mart_causal_profundo_d7 | mart | mart_par_rama | pipeline.causal_profundo |
| mart_causal_profundo_veredicto | mart | dim_fractura_pozo | pipeline.causal_profundo |
| mart_causal_profundo_veredicto | mart | dim_pozo | pipeline.causal_profundo |
| mart_causal_profundo_veredicto | mart | fct_produccion | pipeline.causal_profundo |
| mart_causal_profundo_veredicto | mart | int_frac_hijo | pipeline.causal_profundo |
| mart_causal_profundo_veredicto | mart | int_pozo_ubicacion | pipeline.causal_profundo |
| mart_causal_profundo_veredicto | mart | mart_causal_veredicto | pipeline.causal_profundo |
| mart_causal_profundo_veredicto | mart | mart_par_rama | pipeline.causal_profundo |
| mart_causal_serie | mart | fct_produccion | pipeline.causal |
| mart_causal_serie | mart | int_frac_hijo | pipeline.causal |
| mart_causal_serie | mart | int_pozo_ubicacion | pipeline.causal |
| mart_causal_serie | mart | mart_causal_profundo_d3 | pipeline.causal |
| mart_causal_serie | mart | mart_causal_profundo_d5 | pipeline.causal |
| mart_causal_serie | mart | mart_causal_profundo_d6 | pipeline.causal |
| mart_causal_serie | mart | mart_causal_profundo_d7 | pipeline.causal |
| mart_causal_serie | mart | mart_causal_profundo_veredicto | pipeline.causal |
| mart_causal_serie | mart | mart_par_rama | pipeline.causal |
| mart_causal_serie | mart | mart_trayectoria_cobertura | pipeline.causal |
| mart_causal_veredicto | mart | fct_produccion | pipeline.causal |
| mart_causal_veredicto | mart | int_frac_hijo | pipeline.causal |
| mart_causal_veredicto | mart | int_pozo_ubicacion | pipeline.causal |
| mart_causal_veredicto | mart | mart_causal_profundo_d3 | pipeline.causal |
| mart_causal_veredicto | mart | mart_causal_profundo_d5 | pipeline.causal |
| mart_causal_veredicto | mart | mart_causal_profundo_d6 | pipeline.causal |
| mart_causal_veredicto | mart | mart_causal_profundo_d7 | pipeline.causal |
| mart_causal_veredicto | mart | mart_causal_profundo_veredicto | pipeline.causal |
| mart_causal_veredicto | mart | mart_par_rama | pipeline.causal |
| mart_causal_veredicto | mart | mart_trayectoria_cobertura | pipeline.causal |
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
| mart_decision_cierre | mart | int_pozo_ubicacion | pipeline.decision |
| mart_decision_cierre | mart | mart_anillo | pipeline.decision |
| mart_decision_cierre | mart | mart_descomposicion_distancia | pipeline.decision |
| mart_decision_cierre | mart | mart_diferido_operador | pipeline.decision |
| mart_decision_cierre | mart | mart_diferido_rango | pipeline.decision |
| mart_decision_cierre | mart | mart_interferencia_brecha | pipeline.decision |
| mart_decision_cierre | mart | mart_interferencia_diferida | pipeline.decision |
| mart_decision_cierre | mart | mart_perdida_permanente | pipeline.decision |
| mart_decision_distancia | mart | int_pozo_ubicacion | pipeline.decision |
| mart_decision_distancia | mart | mart_anillo | pipeline.decision |
| mart_decision_distancia | mart | mart_descomposicion_distancia | pipeline.decision |
| mart_decision_distancia | mart | mart_diferido_operador | pipeline.decision |
| mart_decision_distancia | mart | mart_diferido_rango | pipeline.decision |
| mart_decision_distancia | mart | mart_interferencia_brecha | pipeline.decision |
| mart_decision_distancia | mart | mart_interferencia_diferida | pipeline.decision |
| mart_decision_distancia | mart | mart_perdida_permanente | pipeline.decision |
| mart_decision_edad | mart | int_pozo_ubicacion | pipeline.decision |
| mart_decision_edad | mart | mart_anillo | pipeline.decision |
| mart_decision_edad | mart | mart_descomposicion_distancia | pipeline.decision |
| mart_decision_edad | mart | mart_diferido_operador | pipeline.decision |
| mart_decision_edad | mart | mart_diferido_rango | pipeline.decision |
| mart_decision_edad | mart | mart_interferencia_brecha | pipeline.decision |
| mart_decision_edad | mart | mart_interferencia_diferida | pipeline.decision |
| mart_decision_edad | mart | mart_perdida_permanente | pipeline.decision |
| mart_decision_perdida | mart | int_pozo_ubicacion | pipeline.decision |
| mart_decision_perdida | mart | mart_anillo | pipeline.decision |
| mart_decision_perdida | mart | mart_descomposicion_distancia | pipeline.decision |
| mart_decision_perdida | mart | mart_diferido_operador | pipeline.decision |
| mart_decision_perdida | mart | mart_diferido_rango | pipeline.decision |
| mart_decision_perdida | mart | mart_interferencia_brecha | pipeline.decision |
| mart_decision_perdida | mart | mart_interferencia_diferida | pipeline.decision |
| mart_decision_perdida | mart | mart_perdida_permanente | pipeline.decision |
| mart_descomposicion_aditiva | mart | fct_produccion | pipeline.descomposicion |
| mart_descomposicion_aditiva | mart | int_frac_hijo | pipeline.descomposicion |
| mart_descomposicion_aditiva | mart | int_pozo_ubicacion | pipeline.descomposicion |
| mart_descomposicion_cierres | mart | fct_produccion | pipeline.descomposicion |
| mart_descomposicion_cierres | mart | int_frac_hijo | pipeline.descomposicion |
| mart_descomposicion_cierres | mart | int_pozo_ubicacion | pipeline.descomposicion |
| mart_descomposicion_distancia | mart | fct_produccion | pipeline.descomposicion |
| mart_descomposicion_distancia | mart | int_frac_hijo | pipeline.descomposicion |
| mart_descomposicion_distancia | mart | int_pozo_ubicacion | pipeline.descomposicion |
| mart_descomposicion_k | mart | fct_produccion | pipeline.descomposicion |
| mart_descomposicion_k | mart | int_frac_hijo | pipeline.descomposicion |
| mart_descomposicion_k | mart | int_pozo_ubicacion | pipeline.descomposicion |
| mart_dias_perdidos | mart | dim_pozo | pipeline.dias_perdidos |
| mart_dias_perdidos | mart | fct_produccion | pipeline.dias_perdidos |
| mart_dias_perdidos | mart | int_frac_hijo | pipeline.dias_perdidos |
| mart_dias_perdidos | mart | int_pozo_ubicacion | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado | mart | dim_pozo | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado | mart | fct_produccion | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado | mart | int_frac_hijo | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado | mart | int_pozo_ubicacion | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_mitades | mart | dim_pozo | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_mitades | mart | fct_produccion | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_mitades | mart | int_frac_hijo | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_mitades | mart | int_pozo_ubicacion | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_operador | mart | dim_pozo | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_operador | mart | fct_produccion | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_operador | mart | int_frac_hijo | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_operador | mart | int_pozo_ubicacion | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_prueba | mart | dim_pozo | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_prueba | mart | fct_produccion | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_prueba | mart | int_frac_hijo | pipeline.dias_perdidos |
| mart_dias_perdidos_colorado_prueba | mart | int_pozo_ubicacion | pipeline.dias_perdidos |
| mart_dias_perdidos_estado | mart | dim_pozo | pipeline.dias_perdidos |
| mart_dias_perdidos_estado | mart | fct_produccion | pipeline.dias_perdidos |
| mart_dias_perdidos_estado | mart | int_frac_hijo | pipeline.dias_perdidos |
| mart_dias_perdidos_estado | mart | int_pozo_ubicacion | pipeline.dias_perdidos |
| mart_dias_perdidos_mitades | mart | dim_pozo | pipeline.dias_perdidos |
| mart_dias_perdidos_mitades | mart | fct_produccion | pipeline.dias_perdidos |
| mart_dias_perdidos_mitades | mart | int_frac_hijo | pipeline.dias_perdidos |
| mart_dias_perdidos_mitades | mart | int_pozo_ubicacion | pipeline.dias_perdidos |
| mart_dias_perdidos_operador | mart | dim_pozo | pipeline.dias_perdidos |
| mart_dias_perdidos_operador | mart | fct_produccion | pipeline.dias_perdidos |
| mart_dias_perdidos_operador | mart | int_frac_hijo | pipeline.dias_perdidos |
| mart_dias_perdidos_operador | mart | int_pozo_ubicacion | pipeline.dias_perdidos |
| mart_dias_perdidos_prueba | mart | dim_pozo | pipeline.dias_perdidos |
| mart_dias_perdidos_prueba | mart | fct_produccion | pipeline.dias_perdidos |
| mart_dias_perdidos_prueba | mart | int_frac_hijo | pipeline.dias_perdidos |
| mart_dias_perdidos_prueba | mart | int_pozo_ubicacion | pipeline.dias_perdidos |
| mart_diferido_operador | mart | fct_produccion | pipeline.diferido |
| mart_diferido_operador | mart | int_interferencia_evento | pipeline.diferido |
| mart_diferido_operador | mart | int_pozo_ubicacion | pipeline.diferido |
| mart_diferido_operador | mart | mart_interferencia_diferida | pipeline.diferido |
| mart_diferido_operador | mart | mart_placebo_pretrend | pipeline.diferido |
| mart_diferido_rango | mart | fct_produccion | pipeline.diferido |
| mart_diferido_rango | mart | int_interferencia_evento | pipeline.diferido |
| mart_diferido_rango | mart | int_pozo_ubicacion | pipeline.diferido |
| mart_diferido_rango | mart | mart_interferencia_diferida | pipeline.diferido |
| mart_diferido_rango | mart | mart_placebo_pretrend | pipeline.diferido |
| mart_diseno_productividad | mart | mart_pozo_12m | pipeline/sql/03_marts.sql |
| mart_dosis_geometria_modelo | mart | dim_fractura_pozo | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | fct_produccion | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | int_frac_hijo | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | int_interferencia_evento | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | int_interferencia_mes | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | int_pozo_ubicacion | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | mart_dosis_modelo | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | mart_interferencia_brecha | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | mart_potencia_dosis | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | mart_trayectoria_par | pipeline.dosis_geometria |
| mart_dosis_geometria_modelo | mart | stg_fractura | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | dim_fractura_pozo | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | fct_produccion | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | int_frac_hijo | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | int_interferencia_evento | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | int_interferencia_mes | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | int_pozo_ubicacion | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | mart_dosis_modelo | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | mart_interferencia_brecha | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | mart_potencia_dosis | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | mart_trayectoria_par | pipeline.dosis_geometria |
| mart_dosis_geometria_muestra | mart | stg_fractura | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | dim_fractura_pozo | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | fct_produccion | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | int_frac_hijo | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | int_interferencia_evento | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | int_interferencia_mes | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | int_pozo_ubicacion | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | mart_dosis_modelo | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | mart_interferencia_brecha | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | mart_potencia_dosis | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | mart_trayectoria_par | pipeline.dosis_geometria |
| mart_dosis_geometria_orden | mart | stg_fractura | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | dim_fractura_pozo | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | fct_produccion | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | int_frac_hijo | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | int_interferencia_evento | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | int_interferencia_mes | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | int_pozo_ubicacion | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | mart_dosis_modelo | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | mart_interferencia_brecha | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | mart_potencia_dosis | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | mart_trayectoria_par | pipeline.dosis_geometria |
| mart_dosis_geometria_potencia | mart | stg_fractura | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | dim_fractura_pozo | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | fct_produccion | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | int_frac_hijo | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | int_interferencia_evento | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | int_interferencia_mes | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | int_pozo_ubicacion | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | mart_dosis_modelo | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | mart_interferencia_brecha | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | mart_potencia_dosis | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | mart_trayectoria_par | pipeline.dosis_geometria |
| mart_dosis_geometria_puerta | mart | stg_fractura | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | dim_fractura_pozo | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | fct_produccion | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | int_frac_hijo | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | int_interferencia_evento | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | int_interferencia_mes | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | int_pozo_ubicacion | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | mart_dosis_modelo | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | mart_interferencia_brecha | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | mart_potencia_dosis | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | mart_trayectoria_par | pipeline.dosis_geometria |
| mart_dosis_geometria_quintiles | mart | stg_fractura | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | dim_fractura_pozo | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | fct_produccion | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | int_frac_hijo | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | int_interferencia_evento | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | int_interferencia_mes | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | int_pozo_ubicacion | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | mart_dosis_modelo | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | mart_interferencia_brecha | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | mart_potencia_dosis | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | mart_trayectoria_par | pipeline.dosis_geometria |
| mart_dosis_geometria_sens | mart | stg_fractura | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | dim_fractura_pozo | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | fct_produccion | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | int_frac_hijo | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | int_interferencia_evento | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | int_interferencia_mes | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | int_pozo_ubicacion | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | mart_dosis_modelo | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | mart_interferencia_brecha | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | mart_potencia_dosis | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | mart_trayectoria_par | pipeline.dosis_geometria |
| mart_dosis_geometria_sim | mart | stg_fractura | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | dim_fractura_pozo | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | fct_produccion | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | int_frac_hijo | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | int_interferencia_evento | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | int_interferencia_mes | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | int_pozo_ubicacion | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | mart_dosis_modelo | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | mart_interferencia_brecha | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | mart_potencia_dosis | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | mart_trayectoria_par | pipeline.dosis_geometria |
| mart_dosis_geometria_veredicto | mart | stg_fractura | pipeline.dosis_geometria |
| mart_dosis_meses | mart | dim_fractura_pozo | pipeline.dosis_meses |
| mart_dosis_meses | mart | fct_produccion | pipeline.dosis_meses |
| mart_dosis_meses | mart | int_frac_hijo | pipeline.dosis_meses |
| mart_dosis_meses | mart | int_interferencia_evento | pipeline.dosis_meses |
| mart_dosis_meses | mart | int_interferencia_mes | pipeline.dosis_meses |
| mart_dosis_meses | mart | int_pozo_ubicacion | pipeline.dosis_meses |
| mart_dosis_meses | mart | mart_dosis_modelo | pipeline.dosis_meses |
| mart_dosis_meses | mart | mart_interferencia_brecha | pipeline.dosis_meses |
| mart_dosis_meses | mart | stg_fractura | pipeline.dosis_meses |
| mart_dosis_meses_veredicto | mart | dim_fractura_pozo | pipeline.dosis_meses |
| mart_dosis_meses_veredicto | mart | fct_produccion | pipeline.dosis_meses |
| mart_dosis_meses_veredicto | mart | int_frac_hijo | pipeline.dosis_meses |
| mart_dosis_meses_veredicto | mart | int_interferencia_evento | pipeline.dosis_meses |
| mart_dosis_meses_veredicto | mart | int_interferencia_mes | pipeline.dosis_meses |
| mart_dosis_meses_veredicto | mart | int_pozo_ubicacion | pipeline.dosis_meses |
| mart_dosis_meses_veredicto | mart | mart_dosis_modelo | pipeline.dosis_meses |
| mart_dosis_meses_veredicto | mart | mart_interferencia_brecha | pipeline.dosis_meses |
| mart_dosis_meses_veredicto | mart | stg_fractura | pipeline.dosis_meses |
| mart_dosis_modelo | mart | dim_fractura_pozo | pipeline.dosis |
| mart_dosis_modelo | mart | fct_produccion | pipeline.dosis |
| mart_dosis_modelo | mart | int_frac_hijo | pipeline.dosis |
| mart_dosis_modelo | mart | int_interferencia_evento | pipeline.dosis |
| mart_dosis_modelo | mart | int_interferencia_mes | pipeline.dosis |
| mart_dosis_modelo | mart | int_pozo_ubicacion | pipeline.dosis |
| mart_dosis_modelo | mart | mart_interferencia_brecha | pipeline.dosis |
| mart_dosis_modelo | mart | stg_fractura | pipeline.dosis |
| mart_dosis_orden | mart | dim_fractura_pozo | pipeline.dosis |
| mart_dosis_orden | mart | fct_produccion | pipeline.dosis |
| mart_dosis_orden | mart | int_frac_hijo | pipeline.dosis |
| mart_dosis_orden | mart | int_interferencia_evento | pipeline.dosis |
| mart_dosis_orden | mart | int_interferencia_mes | pipeline.dosis |
| mart_dosis_orden | mart | int_pozo_ubicacion | pipeline.dosis |
| mart_dosis_orden | mart | mart_interferencia_brecha | pipeline.dosis |
| mart_dosis_orden | mart | stg_fractura | pipeline.dosis |
| mart_dosis_pad | mart | dim_fractura_pozo | pipeline.dosis_pad |
| mart_dosis_pad | mart | fct_produccion | pipeline.dosis_pad |
| mart_dosis_pad | mart | int_frac_hijo | pipeline.dosis_pad |
| mart_dosis_pad | mart | int_interferencia_evento | pipeline.dosis_pad |
| mart_dosis_pad | mart | int_interferencia_mes | pipeline.dosis_pad |
| mart_dosis_pad | mart | int_pozo_ubicacion | pipeline.dosis_pad |
| mart_dosis_pad | mart | mart_interferencia_brecha | pipeline.dosis_pad |
| mart_dosis_pad | mart | stg_fractura | pipeline.dosis_pad |
| mart_dosis_pad_veredicto | mart | dim_fractura_pozo | pipeline.dosis_pad |
| mart_dosis_pad_veredicto | mart | fct_produccion | pipeline.dosis_pad |
| mart_dosis_pad_veredicto | mart | int_frac_hijo | pipeline.dosis_pad |
| mart_dosis_pad_veredicto | mart | int_interferencia_evento | pipeline.dosis_pad |
| mart_dosis_pad_veredicto | mart | int_interferencia_mes | pipeline.dosis_pad |
| mart_dosis_pad_veredicto | mart | int_pozo_ubicacion | pipeline.dosis_pad |
| mart_dosis_pad_veredicto | mart | mart_interferencia_brecha | pipeline.dosis_pad |
| mart_dosis_pad_veredicto | mart | stg_fractura | pipeline.dosis_pad |
| mart_dosis_quintiles | mart | dim_fractura_pozo | pipeline.dosis |
| mart_dosis_quintiles | mart | fct_produccion | pipeline.dosis |
| mart_dosis_quintiles | mart | int_frac_hijo | pipeline.dosis |
| mart_dosis_quintiles | mart | int_interferencia_evento | pipeline.dosis |
| mart_dosis_quintiles | mart | int_interferencia_mes | pipeline.dosis |
| mart_dosis_quintiles | mart | int_pozo_ubicacion | pipeline.dosis |
| mart_dosis_quintiles | mart | mart_interferencia_brecha | pipeline.dosis |
| mart_dosis_quintiles | mart | stg_fractura | pipeline.dosis |
| mart_dosis_sens | mart | dim_fractura_pozo | pipeline.dosis |
| mart_dosis_sens | mart | fct_produccion | pipeline.dosis |
| mart_dosis_sens | mart | int_frac_hijo | pipeline.dosis |
| mart_dosis_sens | mart | int_interferencia_evento | pipeline.dosis |
| mart_dosis_sens | mart | int_interferencia_mes | pipeline.dosis |
| mart_dosis_sens | mart | int_pozo_ubicacion | pipeline.dosis |
| mart_dosis_sens | mart | mart_interferencia_brecha | pipeline.dosis |
| mart_dosis_sens | mart | stg_fractura | pipeline.dosis |
| mart_dosis_veredicto | mart | dim_fractura_pozo | pipeline.dosis |
| mart_dosis_veredicto | mart | fct_produccion | pipeline.dosis |
| mart_dosis_veredicto | mart | int_frac_hijo | pipeline.dosis |
| mart_dosis_veredicto | mart | int_interferencia_evento | pipeline.dosis |
| mart_dosis_veredicto | mart | int_interferencia_mes | pipeline.dosis |
| mart_dosis_veredicto | mart | int_pozo_ubicacion | pipeline.dosis |
| mart_dosis_veredicto | mart | mart_interferencia_brecha | pipeline.dosis |
| mart_dosis_veredicto | mart | stg_fractura | pipeline.dosis |
| mart_eje_controles | mart | dim_fractura_pozo | pipeline.eje_controles |
| mart_eje_controles | mart | fct_produccion | pipeline.eje_controles |
| mart_eje_controles | mart | int_frac_hijo | pipeline.eje_controles |
| mart_eje_controles | mart | int_interferencia_clase | pipeline.eje_controles |
| mart_eje_controles | mart | int_interferencia_evento | pipeline.eje_controles |
| mart_eje_controles | mart | int_interferencia_mes | pipeline.eje_controles |
| mart_eje_controles | mart | int_pozo_ubicacion | pipeline.eje_controles |
| mart_eje_controles | mart | mart_interferencia_brecha | pipeline.eje_controles |
| mart_eje_controles | mart | mart_interferencia_diferida | pipeline.eje_controles |
| mart_eje_controles_rotacion | mart | dim_fractura_pozo | pipeline.eje_controles |
| mart_eje_controles_rotacion | mart | fct_produccion | pipeline.eje_controles |
| mart_eje_controles_rotacion | mart | int_frac_hijo | pipeline.eje_controles |
| mart_eje_controles_rotacion | mart | int_interferencia_clase | pipeline.eje_controles |
| mart_eje_controles_rotacion | mart | int_interferencia_evento | pipeline.eje_controles |
| mart_eje_controles_rotacion | mart | int_interferencia_mes | pipeline.eje_controles |
| mart_eje_controles_rotacion | mart | int_pozo_ubicacion | pipeline.eje_controles |
| mart_eje_controles_rotacion | mart | mart_interferencia_brecha | pipeline.eje_controles |
| mart_eje_controles_rotacion | mart | mart_interferencia_diferida | pipeline.eje_controles |
| mart_eje_controles_veredicto | mart | dim_fractura_pozo | pipeline.eje_controles |
| mart_eje_controles_veredicto | mart | fct_produccion | pipeline.eje_controles |
| mart_eje_controles_veredicto | mart | int_frac_hijo | pipeline.eje_controles |
| mart_eje_controles_veredicto | mart | int_interferencia_clase | pipeline.eje_controles |
| mart_eje_controles_veredicto | mart | int_interferencia_evento | pipeline.eje_controles |
| mart_eje_controles_veredicto | mart | int_interferencia_mes | pipeline.eje_controles |
| mart_eje_controles_veredicto | mart | int_pozo_ubicacion | pipeline.eje_controles |
| mart_eje_controles_veredicto | mart | mart_interferencia_brecha | pipeline.eje_controles |
| mart_eje_controles_veredicto | mart | mart_interferencia_diferida | pipeline.eje_controles |
| mart_eje_exposicion | mart | dim_fractura_pozo | pipeline.eje_exposicion |
| mart_eje_exposicion | mart | int_interferencia_clase | pipeline.eje_exposicion |
| mart_eje_exposicion | mart | int_interferencia_evento | pipeline.eje_exposicion |
| mart_eje_exposicion | mart | int_interferencia_mes | pipeline.eje_exposicion |
| mart_eje_exposicion | mart | int_pozo_ubicacion | pipeline.eje_exposicion |
| mart_eje_exposicion | mart | mart_anisotropia_area | pipeline.eje_exposicion |
| mart_eje_exposicion | mart | mart_interferencia_brecha | pipeline.eje_exposicion |
| mart_eje_exposicion | mart | mart_interferencia_diferida | pipeline.eje_exposicion |
| mart_eje_exposicion_veredicto | mart | dim_fractura_pozo | pipeline.eje_exposicion |
| mart_eje_exposicion_veredicto | mart | int_interferencia_clase | pipeline.eje_exposicion |
| mart_eje_exposicion_veredicto | mart | int_interferencia_evento | pipeline.eje_exposicion |
| mart_eje_exposicion_veredicto | mart | int_interferencia_mes | pipeline.eje_exposicion |
| mart_eje_exposicion_veredicto | mart | int_pozo_ubicacion | pipeline.eje_exposicion |
| mart_eje_exposicion_veredicto | mart | mart_anisotropia_area | pipeline.eje_exposicion |
| mart_eje_exposicion_veredicto | mart | mart_interferencia_brecha | pipeline.eje_exposicion |
| mart_eje_exposicion_veredicto | mart | mart_interferencia_diferida | pipeline.eje_exposicion |
| mart_eje_parada | mart | mart_eje_controles | pipeline.eje_parada |
| mart_eje_parada | mart | mart_eje_controles_rotacion | pipeline.eje_parada |
| mart_eje_parada | mart | mart_eje_controles_veredicto | pipeline.eje_parada |
| mart_eje_parada | mart | mart_eje_exposicion_veredicto | pipeline.eje_parada |
| mart_eje_parada | mart | mart_mecanismo_veredicto | pipeline.eje_parada |
| mart_eje_parada | mart | mart_potencia_eje | pipeline.eje_parada |
| mart_eje_parada | mart | mart_potencia_resumen | pipeline.eje_parada |
| mart_eje_reponderado | mart | dim_fractura_pozo | pipeline.eje_exposicion |
| mart_eje_reponderado | mart | int_interferencia_clase | pipeline.eje_exposicion |
| mart_eje_reponderado | mart | int_interferencia_evento | pipeline.eje_exposicion |
| mart_eje_reponderado | mart | int_interferencia_mes | pipeline.eje_exposicion |
| mart_eje_reponderado | mart | int_pozo_ubicacion | pipeline.eje_exposicion |
| mart_eje_reponderado | mart | mart_anisotropia_area | pipeline.eje_exposicion |
| mart_eje_reponderado | mart | mart_interferencia_brecha | pipeline.eje_exposicion |
| mart_eje_reponderado | mart | mart_interferencia_diferida | pipeline.eje_exposicion |
| mart_gas | mart | dim_pozo | pipeline.gas |
| mart_gas | mart | fct_produccion | pipeline.gas |
| mart_gas | mart | int_frac_hijo | pipeline.gas |
| mart_gas | mart | int_pozo_ubicacion | pipeline.gas |
| mart_gas_fechas | mart | dim_pozo | pipeline.gas |
| mart_gas_fechas | mart | fct_produccion | pipeline.gas |
| mart_gas_fechas | mart | int_frac_hijo | pipeline.gas |
| mart_gas_fechas | mart | int_pozo_ubicacion | pipeline.gas |
| mart_gas_gor | mart | dim_pozo | pipeline.gas |
| mart_gas_gor | mart | fct_produccion | pipeline.gas |
| mart_gas_gor | mart | int_frac_hijo | pipeline.gas |
| mart_gas_gor | mart | int_pozo_ubicacion | pipeline.gas |
| mart_gas_pretendencia | mart | dim_pozo | pipeline.gas |
| mart_gas_pretendencia | mart | fct_produccion | pipeline.gas |
| mart_gas_pretendencia | mart | int_frac_hijo | pipeline.gas |
| mart_gas_pretendencia | mart | int_pozo_ubicacion | pipeline.gas |
| mart_gas_veredicto | mart | dim_pozo | pipeline.gas |
| mart_gas_veredicto | mart | fct_produccion | pipeline.gas |
| mart_gas_veredicto | mart | int_frac_hijo | pipeline.gas |
| mart_gas_veredicto | mart | int_pozo_ubicacion | pipeline.gas |
| mart_golpes_mismo_mes | mart | dim_pozo | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes | mart | fct_produccion | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes | mart | int_frac_hijo | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes | mart | int_pozo_ubicacion | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_colorado | mart | dim_pozo | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_colorado | mart | fct_produccion | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_colorado | mart | int_frac_hijo | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_colorado | mart | int_pozo_ubicacion | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_colorado_prueba | mart | dim_pozo | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_colorado_prueba | mart | fct_produccion | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_colorado_prueba | mart | int_frac_hijo | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_colorado_prueba | mart | int_pozo_ubicacion | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_prueba | mart | dim_pozo | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_prueba | mart | fct_produccion | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_prueba | mart | int_frac_hijo | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_mes_prueba | mart | int_pozo_ubicacion | pipeline.golpes_mismo_mes |
| mart_golpes_mismo_padre | mart | dim_pozo | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre | mart | fct_produccion | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre | mart | int_frac_hijo | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre | mart | int_pozo_ubicacion | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_colorado | mart | dim_pozo | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_colorado | mart | fct_produccion | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_colorado | mart | int_frac_hijo | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_colorado | mart | int_pozo_ubicacion | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_colorado_prueba | mart | dim_pozo | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_colorado_prueba | mart | fct_produccion | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_colorado_prueba | mart | int_frac_hijo | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_colorado_prueba | mart | int_pozo_ubicacion | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_prueba | mart | dim_pozo | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_prueba | mart | fct_produccion | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_prueba | mart | int_frac_hijo | pipeline.golpes_mismo_padre |
| mart_golpes_mismo_padre_prueba | mart | int_pozo_ubicacion | pipeline.golpes_mismo_padre |
| mart_hijo_celdas_coef | mart | dim_fractura_pozo | pipeline.hijo_celdas |
| mart_hijo_celdas_coef | mart | int_pozo_mop | pipeline.hijo_celdas |
| mart_hijo_celdas_coef | mart | int_pozo_ubicacion | pipeline.hijo_celdas |
| mart_hijo_celdas_coef | mart | mart_pozo_12m | pipeline.hijo_celdas |
| mart_hijo_celdas_equilibrio | mart | dim_fractura_pozo | pipeline.hijo_celdas |
| mart_hijo_celdas_equilibrio | mart | int_pozo_mop | pipeline.hijo_celdas |
| mart_hijo_celdas_equilibrio | mart | int_pozo_ubicacion | pipeline.hijo_celdas |
| mart_hijo_celdas_equilibrio | mart | mart_pozo_12m | pipeline.hijo_celdas |
| mart_hijo_celdas_resumen | mart | dim_fractura_pozo | pipeline.hijo_celdas |
| mart_hijo_celdas_resumen | mart | int_pozo_mop | pipeline.hijo_celdas |
| mart_hijo_celdas_resumen | mart | int_pozo_ubicacion | pipeline.hijo_celdas |
| mart_hijo_celdas_resumen | mart | mart_pozo_12m | pipeline.hijo_celdas |
| mart_hijo_coef | mart | dim_fractura_pozo | pipeline.hijo |
| mart_hijo_coef | mart | int_pozo_mop | pipeline.hijo |
| mart_hijo_coef | mart | int_pozo_ubicacion | pipeline.hijo |
| mart_hijo_coef | mart | mart_pozo_12m | pipeline.hijo |
| mart_hijo_equilibrio | mart | dim_fractura_pozo | pipeline.hijo |
| mart_hijo_equilibrio | mart | int_pozo_mop | pipeline.hijo |
| mart_hijo_equilibrio | mart | int_pozo_ubicacion | pipeline.hijo |
| mart_hijo_equilibrio | mart | mart_pozo_12m | pipeline.hijo |
| mart_hijo_grupos | mart | dim_fractura_pozo | pipeline.hijo |
| mart_hijo_grupos | mart | int_pozo_mop | pipeline.hijo |
| mart_hijo_grupos | mart | int_pozo_ubicacion | pipeline.hijo |
| mart_hijo_grupos | mart | mart_pozo_12m | pipeline.hijo |
| mart_hijo_muestra | mart | dim_fractura_pozo | pipeline.hijo |
| mart_hijo_muestra | mart | int_pozo_mop | pipeline.hijo |
| mart_hijo_muestra | mart | int_pozo_ubicacion | pipeline.hijo |
| mart_hijo_muestra | mart | mart_pozo_12m | pipeline.hijo |
| mart_hijo_pad_anio | mart | dim_fractura_pozo | pipeline.hijo_pad |
| mart_hijo_pad_anio | mart | int_pozo_mop | pipeline.hijo_pad |
| mart_hijo_pad_anio | mart | int_pozo_ubicacion | pipeline.hijo_pad |
| mart_hijo_pad_anio | mart | mart_pozo_12m | pipeline.hijo_pad |
| mart_hijo_pad_anio | mart | mart_trayectoria_cobertura | pipeline.hijo_pad |
| mart_hijo_pad_anio | mart | mart_trayectoria_pozo | pipeline.hijo_pad |
| mart_hijo_pad_coef | mart | dim_fractura_pozo | pipeline.hijo_pad |
| mart_hijo_pad_coef | mart | int_pozo_mop | pipeline.hijo_pad |
| mart_hijo_pad_coef | mart | int_pozo_ubicacion | pipeline.hijo_pad |
| mart_hijo_pad_coef | mart | mart_pozo_12m | pipeline.hijo_pad |
| mart_hijo_pad_coef | mart | mart_trayectoria_cobertura | pipeline.hijo_pad |
| mart_hijo_pad_coef | mart | mart_trayectoria_pozo | pipeline.hijo_pad |
| mart_hijo_pad_equilibrio | mart | dim_fractura_pozo | pipeline.hijo_pad |
| mart_hijo_pad_equilibrio | mart | int_pozo_mop | pipeline.hijo_pad |
| mart_hijo_pad_equilibrio | mart | int_pozo_ubicacion | pipeline.hijo_pad |
| mart_hijo_pad_equilibrio | mart | mart_pozo_12m | pipeline.hijo_pad |
| mart_hijo_pad_equilibrio | mart | mart_trayectoria_cobertura | pipeline.hijo_pad |
| mart_hijo_pad_equilibrio | mart | mart_trayectoria_pozo | pipeline.hijo_pad |
| mart_hijo_pad_muestra | mart | dim_fractura_pozo | pipeline.hijo_pad |
| mart_hijo_pad_muestra | mart | int_pozo_mop | pipeline.hijo_pad |
| mart_hijo_pad_muestra | mart | int_pozo_ubicacion | pipeline.hijo_pad |
| mart_hijo_pad_muestra | mart | mart_pozo_12m | pipeline.hijo_pad |
| mart_hijo_pad_muestra | mart | mart_trayectoria_cobertura | pipeline.hijo_pad |
| mart_hijo_pad_muestra | mart | mart_trayectoria_pozo | pipeline.hijo_pad |
| mart_hijo_pad_resumen | mart | dim_fractura_pozo | pipeline.hijo_pad |
| mart_hijo_pad_resumen | mart | int_pozo_mop | pipeline.hijo_pad |
| mart_hijo_pad_resumen | mart | int_pozo_ubicacion | pipeline.hijo_pad |
| mart_hijo_pad_resumen | mart | mart_pozo_12m | pipeline.hijo_pad |
| mart_hijo_pad_resumen | mart | mart_trayectoria_cobertura | pipeline.hijo_pad |
| mart_hijo_pad_resumen | mart | mart_trayectoria_pozo | pipeline.hijo_pad |
| mart_interferencia_anual | mart | int_interferencia_mes | pipeline/sql/04_interferencia.sql |
| mart_interferencia_brecha | mart | int_interferencia_mes | pipeline/sql/04_interferencia.sql |
| mart_interferencia_curva | mart | int_interferencia_mes | pipeline/sql/04_interferencia.sql |
| mart_interferencia_diferida | mart | int_interferencia_evento | pipeline/sql/04_interferencia.sql |
| mart_interferencia_diferida | mart | int_interferencia_mes | pipeline/sql/04_interferencia.sql |
| mart_interferencia_diferida | mart | mart_interferencia_brecha | pipeline/sql/04_interferencia.sql |
| mart_inyeccion | mart | fct_produccion | pipeline.inyeccion |
| mart_inyeccion | mart | int_frac_hijo | pipeline.inyeccion |
| mart_inyeccion | mart | int_pozo_ubicacion | pipeline.inyeccion |
| mart_inyeccion | mart | stg_fractura | pipeline.inyeccion |
| mart_mecanismo_banda | mart | fct_produccion | pipeline.mecanismo |
| mart_mecanismo_banda | mart | int_frac_hijo | pipeline.mecanismo |
| mart_mecanismo_banda | mart | int_pozo_ubicacion | pipeline.mecanismo |
| mart_mecanismo_banda | mart | mart_par_rama | pipeline.mecanismo |
| mart_mecanismo_banda | mart | mart_trayectoria_cobertura | pipeline.mecanismo |
| mart_mecanismo_banda | mart | mart_trayectoria_par | pipeline.mecanismo |
| mart_mecanismo_contraste | mart | fct_produccion | pipeline.mecanismo |
| mart_mecanismo_contraste | mart | int_frac_hijo | pipeline.mecanismo |
| mart_mecanismo_contraste | mart | int_pozo_ubicacion | pipeline.mecanismo |
| mart_mecanismo_contraste | mart | mart_par_rama | pipeline.mecanismo |
| mart_mecanismo_contraste | mart | mart_trayectoria_cobertura | pipeline.mecanismo |
| mart_mecanismo_contraste | mart | mart_trayectoria_par | pipeline.mecanismo |
| mart_mecanismo_muestra | mart | fct_produccion | pipeline.mecanismo |
| mart_mecanismo_muestra | mart | int_frac_hijo | pipeline.mecanismo |
| mart_mecanismo_muestra | mart | int_pozo_ubicacion | pipeline.mecanismo |
| mart_mecanismo_muestra | mart | mart_par_rama | pipeline.mecanismo |
| mart_mecanismo_muestra | mart | mart_trayectoria_cobertura | pipeline.mecanismo |
| mart_mecanismo_muestra | mart | mart_trayectoria_par | pipeline.mecanismo |
| mart_mecanismo_shmax | mart | fct_produccion | pipeline.mecanismo |
| mart_mecanismo_shmax | mart | int_frac_hijo | pipeline.mecanismo |
| mart_mecanismo_shmax | mart | int_pozo_ubicacion | pipeline.mecanismo |
| mart_mecanismo_shmax | mart | mart_par_rama | pipeline.mecanismo |
| mart_mecanismo_shmax | mart | mart_trayectoria_cobertura | pipeline.mecanismo |
| mart_mecanismo_shmax | mart | mart_trayectoria_par | pipeline.mecanismo |
| mart_mecanismo_veredicto | mart | fct_produccion | pipeline.mecanismo |
| mart_mecanismo_veredicto | mart | int_frac_hijo | pipeline.mecanismo |
| mart_mecanismo_veredicto | mart | int_pozo_ubicacion | pipeline.mecanismo |
| mart_mecanismo_veredicto | mart | mart_par_rama | pipeline.mecanismo |
| mart_mecanismo_veredicto | mart | mart_trayectoria_cobertura | pipeline.mecanismo |
| mart_mecanismo_veredicto | mart | mart_trayectoria_par | pipeline.mecanismo |
| mart_par_rama | mart | dim_pozo | pipeline.trayectorias |
| mart_par_rama | mart | int_frac_hijo | pipeline.trayectorias |
| mart_par_rama | mart | int_par_padre_hijo | pipeline.trayectorias |
| mart_par_rama | mart | int_pozo_ubicacion | pipeline.trayectorias |
| mart_perdida_permanente | mart | dim_fractura_pozo | pipeline.costo |
| mart_perdida_permanente | mart | fct_produccion | pipeline.costo |
| mart_perdida_permanente | mart | int_interferencia_clase | pipeline.costo |
| mart_perdida_permanente | mart | int_interferencia_evento | pipeline.costo |
| mart_perdida_permanente | mart | int_interferencia_mes | pipeline.costo |
| mart_perdida_permanente | mart | int_pozo_ubicacion | pipeline.costo |
| mart_perdida_permanente | mart | mart_interferencia_brecha | pipeline.costo |
| mart_perdida_permanente | mart | mart_interferencia_diferida | pipeline.costo |
| mart_placebo_eje | mart | fct_produccion | pipeline.placebo |
| mart_placebo_eje | mart | int_frac_hijo | pipeline.placebo |
| mart_placebo_eje | mart | int_pozo_ubicacion | pipeline.placebo |
| mart_placebo_fechas | mart | fct_produccion | pipeline.placebo |
| mart_placebo_fechas | mart | int_frac_hijo | pipeline.placebo |
| mart_placebo_fechas | mart | int_pozo_ubicacion | pipeline.placebo |
| mart_placebo_permutacion | mart | fct_produccion | pipeline.placebo |
| mart_placebo_permutacion | mart | int_frac_hijo | pipeline.placebo |
| mart_placebo_permutacion | mart | int_pozo_ubicacion | pipeline.placebo |
| mart_placebo_pretrend | mart | fct_produccion | pipeline.placebo |
| mart_placebo_pretrend | mart | int_frac_hijo | pipeline.placebo |
| mart_placebo_pretrend | mart | int_pozo_ubicacion | pipeline.placebo |
| mart_placebo_pretrend_base_original | mart | fct_produccion | pipeline.placebo |
| mart_placebo_pretrend_base_original | mart | int_frac_hijo | pipeline.placebo |
| mart_placebo_pretrend_base_original | mart | int_pozo_ubicacion | pipeline.placebo |
| mart_placebo_pretrend_sin_previos | mart | fct_produccion | pipeline.placebo |
| mart_placebo_pretrend_sin_previos | mart | int_frac_hijo | pipeline.placebo |
| mart_placebo_pretrend_sin_previos | mart | int_pozo_ubicacion | pipeline.placebo |
| mart_potencia_dosis | mart | dim_fractura_pozo | pipeline.potencia_dosis |
| mart_potencia_dosis | mart | fct_produccion | pipeline.potencia_dosis |
| mart_potencia_dosis | mart | int_frac_hijo | pipeline.potencia_dosis |
| mart_potencia_dosis | mart | int_interferencia_evento | pipeline.potencia_dosis |
| mart_potencia_dosis | mart | int_interferencia_mes | pipeline.potencia_dosis |
| mart_potencia_dosis | mart | int_pozo_ubicacion | pipeline.potencia_dosis |
| mart_potencia_dosis | mart | mart_dosis_modelo | pipeline.potencia_dosis |
| mart_potencia_dosis | mart | mart_dosis_pad | pipeline.potencia_dosis |
| mart_potencia_dosis | mart | mart_interferencia_brecha | pipeline.potencia_dosis |
| mart_potencia_dosis | mart | stg_fractura | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | dim_fractura_pozo | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | fct_produccion | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | int_frac_hijo | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | int_interferencia_evento | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | int_interferencia_mes | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | int_pozo_ubicacion | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | mart_dosis_modelo | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | mart_dosis_pad | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | mart_interferencia_brecha | pipeline.potencia_dosis |
| mart_potencia_dosis_sim | mart | stg_fractura | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | dim_fractura_pozo | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | fct_produccion | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | int_frac_hijo | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | int_interferencia_evento | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | int_interferencia_mes | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | int_pozo_ubicacion | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | mart_dosis_modelo | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | mart_dosis_pad | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | mart_interferencia_brecha | pipeline.potencia_dosis |
| mart_potencia_dosis_veredicto | mart | stg_fractura | pipeline.potencia_dosis |
| mart_potencia_eje | mart | dim_fractura_pozo | pipeline.potencia |
| mart_potencia_eje | mart | int_interferencia_clase | pipeline.potencia |
| mart_potencia_eje | mart | int_interferencia_evento | pipeline.potencia |
| mart_potencia_eje | mart | int_interferencia_mes | pipeline.potencia |
| mart_potencia_eje | mart | int_pozo_ubicacion | pipeline.potencia |
| mart_potencia_eje | mart | mart_anisotropia_area | pipeline.potencia |
| mart_potencia_eje | mart | mart_interferencia_brecha | pipeline.potencia |
| mart_potencia_eje | mart | mart_interferencia_diferida | pipeline.potencia |
| mart_potencia_resumen | mart | dim_fractura_pozo | pipeline.potencia |
| mart_potencia_resumen | mart | int_interferencia_clase | pipeline.potencia |
| mart_potencia_resumen | mart | int_interferencia_evento | pipeline.potencia |
| mart_potencia_resumen | mart | int_interferencia_mes | pipeline.potencia |
| mart_potencia_resumen | mart | int_pozo_ubicacion | pipeline.potencia |
| mart_potencia_resumen | mart | mart_anisotropia_area | pipeline.potencia |
| mart_potencia_resumen | mart | mart_interferencia_brecha | pipeline.potencia |
| mart_potencia_resumen | mart | mart_interferencia_diferida | pipeline.potencia |
| mart_pozo_12m | mart | dim_fractura_pozo | pipeline/sql/03_marts.sql |
| mart_pozo_12m | mart | dim_pozo | pipeline/sql/03_marts.sql |
| mart_pozo_12m | mart | int_pozo_mop | pipeline/sql/03_marts.sql |
| mart_pozo_12m | mart | ultimo_mes | pipeline/sql/03_marts.sql |
| mart_riesgo_anio | mart | dim_fractura_pozo | pipeline.riesgo |
| mart_riesgo_anio | mart | fct_produccion | pipeline.riesgo |
| mart_riesgo_anio | mart | int_interferencia_evento | pipeline.riesgo |
| mart_riesgo_anio | mart | int_interferencia_mes | pipeline.riesgo |
| mart_riesgo_anio | mart | int_pozo_ubicacion | pipeline.riesgo |
| mart_riesgo_anio | mart | mart_interferencia_brecha | pipeline.riesgo |
| mart_riesgo_anio | mart | mart_par_rama | pipeline.riesgo |
| mart_riesgo_anio | mart | mart_trayectoria_cobertura | pipeline.riesgo |
| mart_riesgo_anio | mart | mart_trayectoria_par | pipeline.riesgo |
| mart_riesgo_calibracion | mart | dim_fractura_pozo | pipeline.riesgo |
| mart_riesgo_calibracion | mart | fct_produccion | pipeline.riesgo |
| mart_riesgo_calibracion | mart | int_interferencia_evento | pipeline.riesgo |
| mart_riesgo_calibracion | mart | int_interferencia_mes | pipeline.riesgo |
| mart_riesgo_calibracion | mart | int_pozo_ubicacion | pipeline.riesgo |
| mart_riesgo_calibracion | mart | mart_interferencia_brecha | pipeline.riesgo |
| mart_riesgo_calibracion | mart | mart_par_rama | pipeline.riesgo |
| mart_riesgo_calibracion | mart | mart_trayectoria_cobertura | pipeline.riesgo |
| mart_riesgo_calibracion | mart | mart_trayectoria_par | pipeline.riesgo |
| mart_riesgo_coef | mart | dim_fractura_pozo | pipeline.riesgo |
| mart_riesgo_coef | mart | fct_produccion | pipeline.riesgo |
| mart_riesgo_coef | mart | int_interferencia_evento | pipeline.riesgo |
| mart_riesgo_coef | mart | int_interferencia_mes | pipeline.riesgo |
| mart_riesgo_coef | mart | int_pozo_ubicacion | pipeline.riesgo |
| mart_riesgo_coef | mart | mart_interferencia_brecha | pipeline.riesgo |
| mart_riesgo_coef | mart | mart_par_rama | pipeline.riesgo |
| mart_riesgo_coef | mart | mart_trayectoria_cobertura | pipeline.riesgo |
| mart_riesgo_coef | mart | mart_trayectoria_par | pipeline.riesgo |
| mart_riesgo_modelo | mart | dim_fractura_pozo | pipeline.riesgo |
| mart_riesgo_modelo | mart | fct_produccion | pipeline.riesgo |
| mart_riesgo_modelo | mart | int_interferencia_evento | pipeline.riesgo |
| mart_riesgo_modelo | mart | int_interferencia_mes | pipeline.riesgo |
| mart_riesgo_modelo | mart | int_pozo_ubicacion | pipeline.riesgo |
| mart_riesgo_modelo | mart | mart_interferencia_brecha | pipeline.riesgo |
| mart_riesgo_modelo | mart | mart_par_rama | pipeline.riesgo |
| mart_riesgo_modelo | mart | mart_trayectoria_cobertura | pipeline.riesgo |
| mart_riesgo_modelo | mart | mart_trayectoria_par | pipeline.riesgo |
| mart_riesgo_prueba | mart | dim_fractura_pozo | pipeline.riesgo |
| mart_riesgo_prueba | mart | fct_produccion | pipeline.riesgo |
| mart_riesgo_prueba | mart | int_interferencia_evento | pipeline.riesgo |
| mart_riesgo_prueba | mart | int_interferencia_mes | pipeline.riesgo |
| mart_riesgo_prueba | mart | int_pozo_ubicacion | pipeline.riesgo |
| mart_riesgo_prueba | mart | mart_interferencia_brecha | pipeline.riesgo |
| mart_riesgo_prueba | mart | mart_par_rama | pipeline.riesgo |
| mart_riesgo_prueba | mart | mart_trayectoria_cobertura | pipeline.riesgo |
| mart_riesgo_prueba | mart | mart_trayectoria_par | pipeline.riesgo |
| mart_riesgo_rama | mart | dim_fractura_pozo | pipeline.riesgo |
| mart_riesgo_rama | mart | fct_produccion | pipeline.riesgo |
| mart_riesgo_rama | mart | int_interferencia_evento | pipeline.riesgo |
| mart_riesgo_rama | mart | int_interferencia_mes | pipeline.riesgo |
| mart_riesgo_rama | mart | int_pozo_ubicacion | pipeline.riesgo |
| mart_riesgo_rama | mart | mart_interferencia_brecha | pipeline.riesgo |
| mart_riesgo_rama | mart | mart_par_rama | pipeline.riesgo |
| mart_riesgo_rama | mart | mart_trayectoria_cobertura | pipeline.riesgo |
| mart_riesgo_rama | mart | mart_trayectoria_par | pipeline.riesgo |
| mart_robustez_costo | mart | dim_fractura_pozo | pipeline.robustez |
| mart_robustez_costo | mart | int_interferencia_clase | pipeline.robustez |
| mart_robustez_costo | mart | int_interferencia_evento | pipeline.robustez |
| mart_robustez_costo | mart | int_interferencia_mes | pipeline.robustez |
| mart_robustez_costo | mart | int_pozo_ubicacion | pipeline.robustez |
| mart_robustez_costo | mart | mart_anisotropia_area | pipeline.robustez |
| mart_robustez_costo | mart | mart_interferencia_brecha | pipeline.robustez |
| mart_robustez_costo | mart | mart_interferencia_diferida | pipeline.robustez |
| mart_robustez_eje | mart | dim_fractura_pozo | pipeline.robustez |
| mart_robustez_eje | mart | int_interferencia_clase | pipeline.robustez |
| mart_robustez_eje | mart | int_interferencia_evento | pipeline.robustez |
| mart_robustez_eje | mart | int_interferencia_mes | pipeline.robustez |
| mart_robustez_eje | mart | int_pozo_ubicacion | pipeline.robustez |
| mart_robustez_eje | mart | mart_anisotropia_area | pipeline.robustez |
| mart_robustez_eje | mart | mart_interferencia_brecha | pipeline.robustez |
| mart_robustez_eje | mart | mart_interferencia_diferida | pipeline.robustez |
| mart_robustez_operador | mart | fct_produccion | pipeline.robustez_operador |
| mart_robustez_operador | mart | int_frac_hijo | pipeline.robustez_operador |
| mart_robustez_operador | mart | int_pozo_ubicacion | pipeline.robustez_operador |
| mart_robustez_operador_veredicto | mart | fct_produccion | pipeline.robustez_operador |
| mart_robustez_operador_veredicto | mart | int_frac_hijo | pipeline.robustez_operador |
| mart_robustez_operador_veredicto | mart | int_pozo_ubicacion | pipeline.robustez_operador |
| mart_sincronia | mart | fct_produccion | pipeline.sincronia |
| mart_sincronia | mart | int_frac_hijo | pipeline.sincronia |
| mart_sincronia | mart | int_pozo_ubicacion | pipeline.sincronia |
| mart_sincronia | mart | stg_fractura | pipeline.sincronia |
| mart_sincronia_pendiente | mart | fct_produccion | pipeline.sincronia |
| mart_sincronia_pendiente | mart | int_frac_hijo | pipeline.sincronia |
| mart_sincronia_pendiente | mart | int_pozo_ubicacion | pipeline.sincronia |
| mart_sincronia_pendiente | mart | stg_fractura | pipeline.sincronia |
| mart_trayectoria_banda | mart | dim_pozo | pipeline.trayectorias |
| mart_trayectoria_banda | mart | int_frac_hijo | pipeline.trayectorias |
| mart_trayectoria_banda | mart | int_par_padre_hijo | pipeline.trayectorias |
| mart_trayectoria_banda | mart | int_pozo_ubicacion | pipeline.trayectorias |
| mart_trayectoria_cobertura | mart | dim_pozo | pipeline.trayectorias |
| mart_trayectoria_cobertura | mart | int_frac_hijo | pipeline.trayectorias |
| mart_trayectoria_cobertura | mart | int_par_padre_hijo | pipeline.trayectorias |
| mart_trayectoria_cobertura | mart | int_pozo_ubicacion | pipeline.trayectorias |
| mart_trayectoria_cruce | mart | dim_pozo | pipeline.trayectorias |
| mart_trayectoria_cruce | mart | int_frac_hijo | pipeline.trayectorias |
| mart_trayectoria_cruce | mart | int_par_padre_hijo | pipeline.trayectorias |
| mart_trayectoria_cruce | mart | int_pozo_ubicacion | pipeline.trayectorias |
| mart_trayectoria_par | mart | dim_pozo | pipeline.trayectorias |
| mart_trayectoria_par | mart | int_frac_hijo | pipeline.trayectorias |
| mart_trayectoria_par | mart | int_par_padre_hijo | pipeline.trayectorias |
| mart_trayectoria_par | mart | int_pozo_ubicacion | pipeline.trayectorias |
| mart_trayectoria_pozo | mart | dim_pozo | pipeline.trayectorias |
| mart_trayectoria_pozo | mart | int_frac_hijo | pipeline.trayectorias |
| mart_trayectoria_pozo | mart | int_par_padre_hijo | pipeline.trayectorias |
| mart_trayectoria_pozo | mart | int_pozo_ubicacion | pipeline.trayectorias |
| mart_trayectoria_resumen | mart | dim_pozo | pipeline.trayectorias |
| mart_trayectoria_resumen | mart | int_frac_hijo | pipeline.trayectorias |
| mart_trayectoria_resumen | mart | int_par_padre_hijo | pipeline.trayectorias |
| mart_trayectoria_resumen | mart | int_pozo_ubicacion | pipeline.trayectorias |
| mart_validacion_holdout | mart | dim_fractura_pozo | pipeline.validacion |
| mart_validacion_holdout | mart | int_interferencia_clase | pipeline.validacion |
| mart_validacion_holdout | mart | int_interferencia_evento | pipeline.validacion |
| mart_validacion_holdout | mart | int_interferencia_mes | pipeline.validacion |
| mart_validacion_holdout | mart | int_pozo_ubicacion | pipeline.validacion |
| mart_validacion_holdout | mart | int_prod_corte | pipeline.validacion |
| mart_validacion_holdout | mart | mart_interferencia_brecha | pipeline.validacion |
| mart_validacion_holdout | mart | mart_interferencia_diferida | pipeline.validacion |
| mart_validacion_resultados | mart | dim_fractura_pozo | pipeline.validacion |
| mart_validacion_resultados | mart | int_interferencia_clase | pipeline.validacion |
| mart_validacion_resultados | mart | int_interferencia_evento | pipeline.validacion |
| mart_validacion_resultados | mart | int_interferencia_mes | pipeline.validacion |
| mart_validacion_resultados | mart | int_pozo_ubicacion | pipeline.validacion |
| mart_validacion_resultados | mart | int_prod_corte | pipeline.validacion |
| mart_validacion_resultados | mart | mart_interferencia_brecha | pipeline.validacion |
| mart_validacion_resultados | mart | mart_interferencia_diferida | pipeline.validacion |
| mart_vm_mensual | mart | fct_produccion | pipeline/sql/03_marts.sql |
| operadores | auxiliar | seed:operadores | pipeline/sql/01_staging.sql |
| stg_fractura | staging | operadores | pipeline/sql/01_staging.sql |
| stg_fractura | staging | raw:fractura_adjunto_iv | pipeline/sql/01_staging.sql |
| stg_produccion | staging | operadores | pipeline/sql/01_staging.sql |
| stg_produccion | staging | raw:produccion_no_convencional | pipeline/sql/01_staging.sql |
| ultimo_mes | auxiliar | fct_produccion | pipeline/sql/02_core.sql |
