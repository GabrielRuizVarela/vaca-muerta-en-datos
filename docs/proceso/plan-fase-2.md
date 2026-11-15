# Fase 2: eventos, memoria que se acumula, repetición temporal y costo de interferencia

Plan escrito el 2026-11-15 a partir de la fase de investigación. Lo ejecuta un orquestador que delega cada tramo.
Datos a 2026-09. Todas las cifras de "Evidencia" salen de consultas de solo lectura sobre `data/warehouse.duckdb`
y sobre el CSV crudo de producción; cada tramo debe reproducirlas (con tolerancia) en sus tests o en su informe.

## Reglas del proyecto (no negociables)

- Repo privado. Nada de push, PR ni merge a `main` sin aprobación de vg. Commits locales en ramas de tramo sí.
- Nunca guiones largos (em dash, en dash) en texto que salga del repo (README, sitio, wiki, mensajes).
- Python 3.13 con uv. DuckDB 2.x: `con.execute(sql).fetchall()` y `cur.description`. Tests con pytest (hoy 19).
- Interfaz y textos del sitio en español, como `site/index.html`. Código y comentarios pueden ir en inglés.
- El warehouse se reconstruye con `uv run python -m pipeline.build`; `data/raw` ya está. Reconstrucción completa,
  idempotente (`create or replace`).

## Evidencia que motiva el plan

1. Agua en los padres. Tras la fractura de un hijo a menos de 1 km, el corte de agua mediano del padre pasa de 14,5%
   a 28% en el mes 2; los controles (2-5 km) quedan en 13%. Salto de más de 15 puntos en meses 0-1: 31,7% de los
   eventos cercanos, 21,5% intermedios (1-2 km), 13,0% controles.
2. Cierre declarado. `tipoestado = 'Parado Transitoriamente'` en el mes 0: 10,7% de los padres cercanos (5,5% en el
   mes -1) contra 3,6% de los controles. TEF medio cae de 0,85 a 0,70 en el mes 0.
3. Diferimiento, no pérdida. Brecha cercano menos control: -0,19 en el mes 1, 0,00 en el 6, -0,02 en el 18.
4. Anisotropía. Entre 0,3 y 1 km, padres en el eje ENE-OSO del hijo (sector 67,5°) retienen 0,50 del caudal
   previo (53% con corte de agua > 0,4); en el eje N-S (sector 0°) retienen 0,80 (24%). Entre 1 y 2 km se invierte.
   SHmax publicado: OSO-ENE (RAGA 2024, https://revista.geologica.org.ar/raga/article/view/1793). No encontramos
   publicaciones que infieran la dirección de SHmax desde producción.
5. Sin penalidad medible del hijo con coordenadas de superficie: con efectos fijos de área y cohorte, el petróleo ya
   producido a menos de 1 km no mueve el petróleo por metro del hijo (+1,7% ± 1,8%).
6. Pads. Distancia al vecino más cercano: mediana 10 m. El redondeo a 3 decimales parte pads reales. 489 de 528 pads
   con 3 o más pozos se completaron en menos de 3 meses: la decisión real es entre pads.
7. Columnas crudas sin usar (CSV de producción): `tipoestado`, `tipoextraccion` (1.830 pozos cambian de sistema),
   `profundidad`, `observaciones`. CSV de fractura: `presion_maxima_psi`, `potencia_equipos_fractura_hp`.

## Tramos

Dependencias: T1 y T2 en paralelo. T3 y T5 después de T1. T4 en paralelo con T3 contra el contrato de datos de abajo
(con un generador de datos de prueba). T6 al final.

### T1. Registro de eventos y clasificación de la interferencia

- `pipeline/sql/01_staging.sql`: llevar `tipoestado` y `tipoextraccion` a `stg_produccion` (y a `fct_produccion` si
  conviene); `presion_maxima_psi` a `stg_fractura`.
- Pads por cercanía: agrupar pozos cuya superficie esté a menos de 50 m (componentes conexas, enlace simple).
  `pad_id` estable entre versiones (por ejemplo, el `pozo_id` mínimo del grupo). Reemplaza el redondeo en
  `int_pozo_ubicacion`. Informar cuántos pads cambian.
- Nuevo `pipeline/sql/05_eventos.sql` con `fct_evento` (pozo_id, fecha, mes, tipo, atributos como columnas o JSON,
  fuente). Tipos mínimos: `fractura` (fecha diaria), `primera_produccion`, `cambio_estado` (transiciones de
  `tipoestado`), `cambio_extraccion`, `cierre` (mes sin petróleo o TEF 0 después de producir), `salto_agua`
  (corte de agua sube más de 15 puntos contra la media de los 3 meses previos), `quiebre_caudal` (prueba de quiebre
  en las fechas conocidas de fractura vecina; no hace falta detección ciega).
- `int_interferencia_clase`: cada evento padre/hijo de `int_interferencia_evento` con `clase` en
  {`golpe`, `cierre_preventivo`, `ambos`, `sin_efecto`} a partir de salto de agua, estado declarado y TEF del mes 0-1,
  más `rumbo_eje` (0-180°, del hijo al padre) y `km`.
- Controles en `pipeline/checks.py` (avisos) para eventos sin pozo o fechas fuera de rango.
- Tests sobre fixtures chicos. Informe con las cifras 1, 2 y 4 recalculadas.

### T2. Libro de hallazgos y grafo bitemporal

- `pipeline/hallazgos.py`: cada hallazgo es una hipótesis en código (id, enunciado, consulta u operación tipada,
  expectativa con umbral). En cada build se re-evalúa y se agrega una fila a la tabla `hallazgos_ledger`
  (id, hash de datos del manifiesto, mes de datos, valor, estado `confirmado` / `debilitado` / `refutado`,
  fecha de evaluación). Sembrar con las evidencias 1 a 5.
- Persistir el libro entre builds en `data/hallazgos_ledger.parquet` o CSV versionado (el warehouse se reconstruye
  entero), y renderizarlo en el wiki (`wiki/hallazgos/`), reemplazando el historial ad hoc actual.
- `wiki/grafo.json`: aristas con `valido_desde`, `valido_hasta`, `registrado_en`, `hash_datos` (estilo Graphiti:
  se invalidan, no se borran).
- Lint del wiki: páginas huérfanas, hallazgos refutados citados como vigentes, enlaces rotos. Sale como aviso.

### T3. Exportación para la repetición temporal

`pipeline/replay.py` lee el warehouse y escribe `site/replay.html` autocontenido (datos embebidos, abre con doble
clic como `site/index.html`). Contrato de datos (lo usa T4):

- `meta`: `{meses: ["2010-01", ...], n_pozos, hash_datos, mes_datos, generado}`.
- `pozos`: lista `{id, op, area, pad, lon, lat, mes0, frac}` (solo Vaca Muerta shale con ubicación, unos 3.450).
- `caudal`: Uint16 base64, matriz pozos × meses, petróleo en bbl/d redondeado.
- `agua`: Uint8 base64, corte de agua × 255.
- `estado`: Uint8 base64, bits: 1 produciendo, 2 parado declarado, 4 cambio de extracción ese mes.
- `eventos`: lista `{f: "AAAA-MM-DD", t: tipo, p: pozo, h: hijo, km, rumbo, clase, bbl}` (clase y bbl solo en
  interferencia).
- `cuenca`: serie mensual por operador en kbbl/d (de `mart_vm_mensual`).
- Presupuesto: archivo final menor a 8 MB.

### T4. Repetición temporal (frontend)

Una página, sin paso de build, JS plano y canvas 2D (o una librería por CDN con versión fija). Español.

- Mapa sin teselas: proyección equirectangular ajustada a la caja de los pozos. Puntos con radio según raíz del
  caudal; color por operadora (YPF destacada) o por estado (modo conmutable). Pozo parado: atenuado.
- Fracturas: anillo que se expande en la fecha diaria (animación dentro del mes).
- Interferencia: arco hijo a padre, color por clase, se desvanece en 6 meses.
- Línea de tiempo: reproducir / pausa, velocidad, arrastre; debajo, área apilada de producción por operadora con
  cursor y barras de eventos por mes.
- Feed de eventos con frases generadas ("mar 2025 · YPF fractura 4 pozos en el pad X, La Amarga Chica · 3 padres
  afectados, 1 cerrado preventivamente").
- Rosa de rumbos: interferencia acumulada por sector de 22,5° hasta la fecha actual, filtrable por área, con el eje
  SHmax publicado superpuesto.
- Contador de barriles diferidos acumulados.
- Clic en pozo o pad: panel con caudal y corte de agua en el tiempo, eventos marcados, enlace a su página del wiki.
- Filtros por operadora y área; estado en la URL (mes, filtros); teclado (espacio, flechas).
- Rendimiento: 60 fps con 3.500 pozos en una laptop. Tema claro y oscuro. Usable a 390 px de ancho.

### T5. Anisotropía por área y costo de la interferencia

- Por área con datos suficientes: estimar el eje de máxima interferencia (ajuste de un núcleo coseno sobre rumbo,
  con distancia y edad del padre) con intervalo por bootstrap. Comparar con el SHmax publicado y con la rotación
  regional sur-norte. Mapa simple en el wiki.
- Modelo de costo por evento: barriles diferidos meses 0-6 en función de distancia, rumbo relativo al eje,
  edad y caudal base del padre, número de hijos, tamaño de la fractura del hijo (arena, etapas), cierre preventivo,
  área y operadora. Estudio de eventos escalonado con controles de la misma edad (ya existe) y regresión o DML para
  la dosis-respuesta. Fracción de padres que no se recuperan a los 12 meses (cola de pérdida permanente).
- Operación tipada nueva para el agente: `costo_interferencia(pad_o_coordenadas, fecha)` que devuelve barriles
  diferidos esperados para los padres vecinos y los factores que más pesan. Ser explícito en lo que no se puede
  identificar (pérdida del hijo, espaciamiento entre ramas).

### T6. Agente, evaluación y documentación

- Operaciones tipadas para eventos, clases de interferencia y el libro de hallazgos. Preguntas nuevas en
  `agente/eval/` (dev y reservadas), incluidas preguntas que combinan dos operaciones.
- README: secciones nuevas (eventos, hallazgos, repetición, anisotropía) y límites. Sin guiones largos.

## Criterios de aceptación de cada tramo

- `uv run pytest -q` en verde, y `uv run python -m pipeline.build` sin errores bloqueantes.
- Informe final del tramo con las cifras que reproduce y cualquier diferencia contra este plan.
- Commit en su rama local. Sin push.
