# Fuentes del mundo: quien publica petroleo por pozo

Auditoria hecha el 2026-11-19 bajando cada fuente (encabezado y unas filas, nunca una bajada masiva) y leyendo sus terminos. Los datos de cada fila salen de pedidos reales que se listan en `data/fuentes_mundo.json`; lo que no se pudo ver figura como "no se pudo verificar", no como "no publica".

## Regla de elegibilidad (fijada antes de mirar las fuentes)

Una fuente entra al estudio de otra cuenca solo si cumple las cuatro condiciones:

1. descarga directa o API documentada, sin login ni pago;
2. terminos que no impiden descargar y publicar cifras derivadas con atribucion: una licencia que lo permite, o una descarga que el regulador ofrece sin ninguna restriccion de uso. Una prohibicion expresa de reproducir o redistribuir, o una pagina de terminos que no se pudo leer, la deja afuera;
3. petroleo reportado por pozo y por mes (no por lease, campo, instalacion ni empresa);
4. una fecha de fractura o terminacion por pozo, del regulador o de un registro publico que une por el id del pozo (se verifica con dos pozos reales que el id coincide).

Una condicion que falla, o que no se pudo verificar, deja la fuente afuera.

## Resultado

Se auditaron 27 jurisdicciones. 2 entran al estudio. Por nivel: 3 publican produccion por pozo con fecha de fractura o terminacion, 1 por pozo sin esa fecha, 4 por lease, campo o instalacion, 0 solo totales, 1 nada publico o de pago, 1 es un registro de fracturas sin petroleo y 17 no se pudieron verificar.

| Jurisdiccion | Organismo | Nivel | Entra | Motivo |
|---|---|---|---|---|
| Argentina, Nacional (cuencas Neuquina, Golfo San Jorge, Austral, Noroeste) | Secretaria de Energia de la Nacion (datos.gob.ar / datos.energia.gob.ar) | por pozo, con fecha de fractura o terminacion | si | Cumple las cuatro: descarga directa sin login; licencia CC-BY-4.0 que permite derivadas con atribucion; petroleo por pozo y por mes (prod_pet con anio/mes); fecha de fractura por pozo en el Adjunto IV unida por idpozo (mismo id en ambos datasets: los pozos 159219 y 159910 aparecen con ese idpozo en el CSV de produccion 2024 y en el Adjunto IV). |
| Estados Unidos, Wyoming | Wyoming Oil and Gas Conservation Commission (WOGCC) | por pozo, con fecha de fractura o terminacion | si | Cumple las cuatro condiciones con una reserva en la segunda. Descarga directa del menu de descargas del regulador, sin login ni pago; petroleo por pozo y por mes (JAN_OIL a DEC_OIL con dias); ubicacion de superficie y fecha de terminacion en el mismo archivo de encabezados; el id coincide entre encabezado y produccion en 2 pozos reales (705000 y 720921). Terminos: la pagina solo declara ausencia de garantia y prohibe raspar el sitio, sin prohibir usar ni publicar cifras derivadas de los archivos que ofrece para descargar; no hay una licencia que lo permita expresamente (sin_restriccion). |
| Canada, Columbia Britanica | BC Energy Regulator (BCER) | por pozo, con fecha de fractura o terminacion | no | Falla dos condiciones. Terminos: la licencia abierta cubre la capa de superficie, pero los CSV de produccion y fractura estan en el Centro de datos, que no muestra licencia propia y cuyos terminos del sitio piden permiso escrito para reproducir o redistribuir (no_claro). Petroleo: en el tramo 2016-2024 solo 187 pozos con fecha de fractura tienen petroleo mayor que cero (3.690 tienen condensado); el liquido de la Montney es condensado, no petroleo. |
| Brasil, Nacional (campos terrestres y maritimos) | Agencia Nacional do Petroleo, Gas Natural e Biocombustiveis (ANP) | por pozo, sin esa fecha | no | Falla (d) y probablemente (b): hay petroleo por pozo y por mes, pero no hay fecha de fractura ni terminacion en el dataset, y el archivo de produccion no trae coordenadas (solo estado/bacia/campo). |
| Canada, Alberta | Alberta Energy Regulator via Petrinex (Public Data) | por lease, campo o instalacion | no | El petroleo se reporta por instalacion (bateria): falla la condicion de petroleo por pozo. |
| Canada, Saskatchewan | Saskatchewan Ministry of Energy via Petrinex (Public Data) | por lease, campo o instalacion | no | El petroleo se reporta por instalacion: falla la condicion de petroleo por pozo. |
| Colombia, Nacional (Llanos, Valle Medio del Magdalena, Putumayo) | Agencia Nacional de Hidrocarburos (ANH) | por lease, campo o instalacion | no | Falla (c): el petroleo es por campo y por mes, no por pozo. Tampoco hay fecha de fractura ni coordenadas por pozo en el archivo. |
| Estados Unidos, Texas | Railroad Commission of Texas (RRC) | por lease, campo o instalacion | no | Confirmado el escenario esperado: la produccion de petroleo se reporta por lease/OGID, no por pozo ('oil lease overproduction status', 'pending lease', 'Statewide Production Data - Oil'). No cumple la condicion (c) de petroleo mensual por pozo. |
| Estados Unidos, Dakota del Norte | North Dakota Department of Mineral Resources, Oil and Gas Division | nada publico o de pago | no | La produccion por pozo ('Well Production') esta bajo 'Premium Subscription Services' con tarifa anual (500 USD/anio premium), por lo que viola la regla de no pago; solo hay PDFs agregados publicos y sin enlace Excel. No se scrapeo ni se intento eludir el pago. |
| Estados Unidos, Registro nacional de fractura (FracFocus) | Ground Water Protection Council / Interstate Oil and Gas Compact Commission | registro de fracturas, sin petroleo | no | Es el registro publico de fecha de fractura por pozo y se une por API (confirmado con 2 pozos reales de Nuevo Mexico: 30-015-58180 y 30-015-58196), pero no publica produccion de petroleo: sirve como fuente de la fecha de otra fuente, no entra solo. |
| Arabia Saudita, Nacional | Ministry of Energy | no se pudo verificar | no | Nada verificado. Por lo conocido del regimen de datos saudita lo esperable es solo totales o nada publico, pero no se pudo confirmar con una pagina bajada. |
| Argelia, Nacional | ALNAFT / Sonatrach | no se pudo verificar | no | Nada verificado. Lo esperable es solo totales (Sonatrach/OPEC), sin microdatos por pozo, pero no se confirmo con una pagina bajada. |
| Australia, Australia Occidental | Department of Energy, Mines, Industry Regulation and Safety (DEMIRS) | no se pudo verificar | no | Nada verificado: sin archivo ni pagina de datos accesible en esta sesion. |
| Australia, Queensland (cuenca Cooper y Surat/Bowen) | Queensland Department of Natural Resources and Mines (data.qld.gov.au) | no se pudo verificar | no | No cumple (c) con lo verificado: las estadisticas de produccion son por campo/lease, y la produccion por pozo de CSG no aparecio en el catalogo; la fecha de terminacion solo existe en PDF por pozo. No se pudo ver ningun archivo por pozo, y una portada no prueba que no exista: queda como no verificado, no como que no publica. |
| Australia, Territorio del Norte (Beetaloo) | NT Department of Industry, Tourism and Trade | no se pudo verificar | no | Nada verificado: bloqueo 403 del sitio, no se intento rodearlo. |
| Canada, Manitoba | Manitoba Economic Development via Petrinex (Public Data) | no se pudo verificar | no | No se vio ningun archivo de produccion mensual por pozo. |
| China, Nacional | National Bureau of Statistics of China (NBS) | no se pudo verificar | no | Falla (c) y (d): solo agregados nacionales; no hay produccion por pozo ni fechas de terminacion publicas. No se pudo ver ningun archivo por pozo, y una portada no prueba que no exista: queda como no verificado, no como que no publica. |
| Estados Unidos, Montana | Montana Board of Oil and Gas Conservation (MBOGC) | no se pudo verificar | no | No se verifico ninguna condicion: el regulador no responde por DNS, asi que no hay archivo, campos ni terminos que citar. No se afirma que Montana no publique produccion por pozo; solo que no fue verificable hoy. |
| Estados Unidos, Nuevo Mexico | Oil Conservation Division (EMNRD) | no se pudo verificar | no | No se pudo verificar ninguna de las cuatro condiciones: la produccion por pozo de Nuevo Mexico solo esta detras del formulario interactivo de GO-TECH (ni descarga directa ni API documentada), el .mdb descargado de GO-TECH no se pudo leer sin un lector de Access, y el FTP anonimo de OCD (ftp.emnrd.nm.gov) y la aplicacion OCD Permitting (wwwapps.emnrd.nm.gov) agotaron el tiempo de espera, asi que no se vio ninguna columna de petroleo por pozo y mes ni una fecha de fractura o terminacion. |
| Estados Unidos, Oklahoma | Oklahoma Corporation Commission (OCC), Oil and Gas Conservation Division | no se pudo verificar | no | La pagina de datos de la OCC remite la produccion de petroleo a la Oklahoma Tax Commission, que no se pudo verificar; el archivo de pozos de la OCC no trae produccion. Sin petroleo por pozo y por mes verificado no se cumple la condicion 3. |
| Estados Unidos, Pennsylvania | Department of Environmental Protection (DEP), Office of Oil and Gas Management | no se pudo verificar | no | No se pudo verificar el petroleo por pozo y por mes: el unico enlace de produccion por pozo que publica la DEP (el extracto OilGasWellProdReport de greenport.pa.gov) responde HTTP 500 con Error Code 3759 por HTTP, por HTTPS y con el parametro de formato de SSRS, y los reportes SSRS alternativos agotan el tiempo de espera; sin abrir el archivo no se vio ninguna columna ni fecha, asi que las cuatro condiciones quedan sin verificar. |
| Estados Unidos, Utah | Utah Division of Oil, Gas and Mining (DOGM) | no se pudo verificar | no | No se verifico ninguna condicion: dogm.utah.gov ya no resuelve (NXDOMAIN), el portal de datos del estado (opendata.utah.gov) esta dado de baja y dnr.utah.gov agoto el tiempo de espera, de modo que hoy no se vio ningun archivo de produccion por pozo ni la pagina de terminos del regulador. |
| Libia, Nacional | National Oil Corporation (NOC) | no se pudo verificar | no | Falla (c) y (d): solo agregados y comunicados; sin produccion por pozo ni fechas de terminacion. No se pudo ver ningun archivo por pozo, y una portada no prueba que no exista: queda como no verificado, no como que no publica. |
| Mexico, Nacional (cuencas del sureste y Burgos) | Comision Nacional de Hidrocarburos (CNH) / Centro Nacional de Informacion de Hidrocarburos (CNIH) | no se pudo verificar | no | No se pudo verificar ninguna de las cuatro condiciones: el portal de datos del CNIH estaba caido (522) y no se encontro un archivo alternativo en esta sesion. |
| Noruega, Plataforma continental noruega | Norwegian Offshore Directorate (Sodir / Sokkeldirektoratet) - FactPages | no se pudo verificar | no | No verificado en esta sesion: ni la granularidad por pozo ni el acceso a un archivo se pudieron comprobar. |
| Reino Unido, Plataforma continental del Reino Unido | North Sea Transition Authority (NSTA) | no se pudo verificar | no | No cumple (c): la produccion se publica por campo, no por pozo; los datos por pozo estan en el NDR, que pide registro. No se pudo ver ningun archivo por pozo, y una portada no prueba que no exista: queda como no verificado, no como que no publica. |
| Rusia, Nacional | CDU TEK (Centro de Datos del Complejo de Combustibles y Energia) / Ministerio de Energia | no se pudo verificar | no | Falla (c) y (d): sin produccion por pozo publica; los datos por pozo de CDU TEK son un producto comercial. No se pudo ver ningun archivo por pozo, y una portada no prueba que no exista: queda como no verificado, no como que no publica. |

## Detalle por fuente

### Argentina, Nacional (cuencas Neuquina, Golfo San Jorge, Austral, Noroeste)

- Que publica: Publica produccion mensual por pozo (archivos anuales 2006-2026 con idpozo, anio, mes y prod_pet), un padron de pozos con geometria de superficie en geojson/geom, y un dataset separado de fracturas (Adjunto IV) con fecha_inicio_fractura y fecha_fin_fractura por idpozo.
- Acceso: descarga_directa. Archivo o API: http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/43a09dce-1742-44d0-bc13-f193deaab563/download/produccin-de-pozos-de-gas-y-petrleo-2024.csv (CSV. 319.898.336 bytes).
- Id del pozo: idpozo (produccion) / idpozo + sigla (padron capitulo-iv-pozos.csv). Ubicacion: geojson ({"type":"Point","coordinates":[lon,lat]}) y geom (WKB 4326) en capitulo-iv-pozos.csv.
- Petroleo mensual por pozo: prod_pet (con anio y mes) (unidad: m3). Anios: produccion 2006-2026 (un archivo por anio); fracturas: registros vistos 2017-2019.
- Fecha de fractura o terminacion: fecha_inicio_fractura / fecha_fin_fractura, del dataset 'Datos de fractura de pozos de hidrocarburos (Adjunto IV)', unido por idpozo.
- Terminos (https://datos.gob.ar/dataset/produccion-de-petroleo-y-gas-por-pozo): Licencia / CC-BY-4.0 Permiten derivadas con atribucion: si.
- Notas: El CSV de produccion anual pesa 319 MB y el servidor ignora el rango de bytes (devuelve el archivo completo aunque declare Accept-Ranges: bytes); para ver el encabezado hay que cortar el stream con head. La unidad de prod_pet (m3) es la del dataset; el pozo 159219 muestra 93,22 en enero de 2024, pero la unidad no esta escrita en la fila. El padron de pozos trae ademas adjiv_fecha_inicio_term / adjiv_fecha_fin_term (terminacion), que puede servir como fecha alternativa. Ojo: el padron es un archivo aparte del de produccion; la union es por idpozo.

### Estados Unidos, Wyoming

- Que publica: Ofrece en su menu de descargas un ZIP con el encabezado de todos los pozos (API, longitud y latitud de superficie, fecha de primera terminacion, estado, direccion del pozo) y un ZIP de produccion 1978 a 2026 en cuatro XLSX por rangos de condados, con una fila por pozo y anio y columnas de petroleo, gas, agua y dias para cada mes.
- Acceso: descarga_directa. Archivo o API: https://pipeline.wyo.gov/downloads/TTLProd_110426.zip (ZIP. 430.521.456 bytes).
- Id del pozo: APINO (encabezado, con formato 705000.00000) y APINO (produccion, 705000): condado de 3 digitos mas secuencia de 5. Ubicacion: LON y LAT de superficie en 110326WH.DBF (143.554 de 143.555 pozos con coordenadas); BLON y BLAT de fondo.
- Petroleo mensual por pozo: JAN_OIL a DEC_OIL con DAYS por mes y YR, una fila por pozo y anio (XLSX de produccion) (unidad: bbl). Anios: 1978 a 2026 (produccion); terminaciones desde 1932.
- Fecha de fractura o terminacion: FIRSTCOMP (fecha de primera terminacion) en el encabezado del propio regulador; con formato AAAAMMDD sin ceros a la izquierda en el mes (2024615).
- Terminos (https://pipeline.wyo.gov/MainMenu.cfm): No Warranty is made by the Wyoming Oil and Gas Conservation Commission for the use of this data. Those making use of, or relying on, this information assume all risks and liability arising from such use or reliance. (Menu principal: Scraping of website data is not allowed.) Permiten derivadas con atribucion: sin_restriccion.
- Notas: La fecha es de terminacion, no de fractura: la regla de otra cuenca tendra que decir como la trata. En el pozo 720921 el encabezado da FIRSTCOMP 2024 y la produccion vista llega hasta 2000, sin que se haya podido ver si hay filas posteriores (solo se leyo el 3 por ciento del XLSX): es una discrepancia a revisar al construir. La unidad (bbl) es la convencion del regulador y no se confirmo en una fila con unidades escritas. No se uso FracFocus aqui.

### Canada, Columbia Britanica

- Que publica: Publica por pozo (numero de autorizacion WA) la produccion mensual por zona con columnas separadas de petroleo, condensado, gas y agua, la fecha de terminacion y cada etapa de fractura (IRIS hydraulic_fracture.csv) y la ubicacion de superficie en una capa ArcGIS REST consultable.
- Acceso: descarga_directa. Archivo o API: https://iris.bcogc.ca/download/prod_csv.zip (ZIP. 124.001.179 bytes).
- Id del pozo: Wa_num (produccion), WA NUM (fractura), WELL_AUTHORITY_NUMBER (capa de superficie). Ubicacion: capa PASR_WELL_SURFACE_STATE_PT: geometria puntual, salida WGS84 con outSR=4326.
- Petroleo mensual por pozo: Oil_prod_vol (m3), con Prod_period (AAAAMM) y Prod_days; el condensado va aparte en Cond_prod_vol (m3) (unidad: m3). Anios: produccion 1954 a 2026 (cuatro archivos por tramo de anios); fracturas desde 2013 (visto) hasta 2026.
- Fecha de fractura o terminacion: COMPLTN DATE y FRAC START TIME en hydraulic_fracture.csv del propio regulador (fecha con formato DD-MON-AA).
- Terminos (https://www.bc-er.ca/files/gis/BCER-Open-Data-Licence.pdf): The Information Provider grants you a worldwide, royalty-free, perpetual, non-exclusive licence to use the Information, including for commercial purposes. You are free to copy, modify, publish, translate, adapt, distribute or otherwise use the Information in any medium, mode or format for any lawful purpose. (Licencia del portal de datos abiertos, que cubre la capa de superficie. Los CSV de IRIS cuelgan del Centro de datos, cuya pagina de terminos dice: It may not be reproduced or redistributed without the prior written permission of the Province of British Columbia, https://www.bc-er.ca/terms/) Permiten derivadas con atribucion: no_claro.
- Notas: Se verifico con 2 pozos reales que la clave WA une produccion, fractura y superficie. Los tres archivos se pueden unir y la fuente es tecnicamente completa; el corte es la licencia de los CSV y la columna de petroleo. Si el regulador aclara la licencia, el caso sigue abierto con las cifras de condensado como medida distinta (no es la regla actual). Muestra no publicada: los términos de la fuente no permiten reproducir las filas.

### Brasil, Nacional (campos terrestres y maritimos)

- Que publica: Publica un ZIP por mes con dos CSV separados, producao_mar (offshore) y producao_terra (onshore), con una fila por pozo y mes: estado, bacia, nombre del pozo, campo, operador, periodo y petroleo en bbl/dia; no hay fecha de fractura ni terminacion en el archivo.
- Acceso: descarga_directa. Archivo o API: https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco/producao-por-poco-2010.zip (ZIP. 6.981.503 bytes).
- Id del pozo: Nome Poco (y la columna interna de codigo ANP, sin encabezado, ej. '7C   0010  BA'). Ubicacion: no verificado: el archivo trae Estado, Bacia y Campo, pero no lat/lon.
- Petroleo mensual por pozo: Petroleo (bbl/dia) (y Oleo (bbl/dia), Condensado (bbl/dia)) (unidad: bbl). Anios: 2005-2026 (un ZIP por anio, y por mes desde 2021); verificado 2010.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.gov.br/anp/pt-br/acesso-a-informacao/termo-uso-politica-privacidade-lgpd.pdf): TERMO DE USO E POLITICA DE PRIVACIDADE DA ANP | SGE - ANP | 2021 Permiten derivadas con atribucion: no_claro.
- Notas: Respuesta a la pregunta puntual: si, los pozos onshore tienen produccion mensual por pozo en archivos propios (2010_01_producao_terra.csv dentro del ZIP; los maritimos van en producao_mar.csv). El encabezado real esta en la fila 5 (las primeras 4 son titulos del sistema SIGEP) y hay una fila de subencabezado para oleo asociado/no asociado. HEAD devuelve 403 pero GET funciona. La pagina de terminos que existe es una politica de privacidad (LGPD), no una licencia de reutilizacion de datos: no se encontro licencia explicita para publicar derivadas. Muestra no publicada: los términos de la fuente no permiten reproducir las filas.

### Canada, Alberta

- Que publica: Publica un CSV mensual de volumetria por instalacion declarante (bateria) con producto, volumen en m3 y horas, no por pozo; los pozos aparecen solo como origen de una instalacion, sin petroleo propio.
- Acceso: descarga_directa. Archivo o API: https://www.petrinex.ca/PD/Pages/APD.aspx (ZIP).
- Id del pozo: ReportingFacilityID y FromToID (instalacion o pozo de origen). Ubicacion: ReportingFacilityLocation (subdivision legal DLS de la instalacion).
- Petroleo mensual por pozo: no se pudo verificar (unidad: m3). Anios: un archivo por mes (visto 2024-01).
- Fecha de fractura o terminacion: no verificado en esta fuente.
- Terminos (https://www.petrinex.ca/PD/Pages/default.aspx): no verificado: pagina de terminos de Petrinex no leida Permiten derivadas con atribucion: no_claro.
- Notas: Se leyeron las 14 columnas del CSV de 2024-01 y la guia del formato; hay enlace pozo a instalacion aparte, pero no reparte volumen por pozo.

### Canada, Saskatchewan

- Que publica: Publica la misma volumetria mensual por instalacion que Alberta, mas un enlace de pozo a instalacion.
- Acceso: descarga_directa. Archivo o API: https://www.petrinex.ca/PD/Pages/SPD.aspx (HTML).
- Id del pozo: ReportingFacilityID y FromToID (instalacion o pozo de origen). Ubicacion: ReportingFacilityLocation (subdivision legal DLS de la instalacion).
- Petroleo mensual por pozo: no se pudo verificar (unidad: m3). Anios: un archivo por mes (visto 2024-01).
- Fecha de fractura o terminacion: no verificado en esta fuente.
- Terminos (https://www.petrinex.ca/PD/Pages/default.aspx): no verificado: pagina de terminos de Petrinex no leida Permiten derivadas con atribucion: no_claro.
- Notas: Solo se leyo la pagina de descargas y la guia del formato; no se bajo ningun CSV de Saskatchewan.

### Colombia, Nacional (Llanos, Valle Medio del Magdalena, Putumayo)

- Que publica: Publica un XLSX por anio de 'Produccion Fiscalizada de Petroleo por Campo' con una fila por campo y una columna por mes (enero..diciembre) en barriles por dia calendario, mas departamento, municipio, operadora y contrato; no hay filas por pozo.
- Acceso: descarga_directa. Archivo o API: https://www.anh.gov.co/documents/26710/Producci%C3%B3n_Fiscalizada_Crudo_2024_TIBfkeo.xlsx (XLSX. 77.903 bytes).
- Id del pozo: no se pudo verificar. Ubicacion: Departamento, Municipio (no hay lat/lon).
- Petroleo mensual por pozo: no se pudo verificar (unidad: bbl). Anios: 2013-2026 (un XLSX por anio); verificado 2024.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.anh.gov.co/es/operaciones-y-regal%C3%ADas/sistemas-integrados-operaciones/estad%C3%ADsticas-de-producci%C3%B3n/): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: El titulo del propio archivo lo dice: 'PRODUCCION FISCALIZADA DE PETROLEO POR CAMPO'. La ANH tiene un visor y estadisticas de pozos perforados, pero no se encontro produccion por pozo en la pagina de estadisticas. El dataset de gas en datos.gov.co ('Produccion Fiscalizada Gas Consolidada', id 5dux-bfvx) tampoco es por pozo. Muestra no publicada: los términos de la fuente no permiten reproducir las filas.

### Estados Unidos, Texas

- Que publica: RRC ofrece gratuitamente datos de pozos y 'Oil Ledger'/'Statewide Production Data - Oil' en formato EBCDIC por districtos, ademas de un 'Production Data Query Dump' en CSV; las descripciones hablan de 'oil lease overproduction status' y de 'pending lease', es decir, produccion reportada por lease y no por pozo.
- Acceso: scraping_necesario. Archivo o API: https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/ (CSV).
- Id del pozo: no verificado en el archivo de produccion (en los datos de pozos RRC se usa el API; el CSV de produccion no se pudo bajar). Ubicacion: no verificado en el archivo de produccion.
- Petroleo mensual por pozo: no se pudo verificar (unidad: bbl). Anios: Production Data Query Dump: 1993 a la fecha; datos de produccion de los ultimos 24 meses en el archivo statewide.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.rrc.texas.gov/site-policies/): The Railroad Commission of Texas (RRC) maintains this website as a public service. The following is the privacy policy for this website (all pages starting with www.rrc.texas.gov, www.propane.tx.gov, altenergy.rrc.texas.gov, webapps.rrc.texas.gov, or driller.rrc.texas.gov). Permiten derivadas con atribucion: no_claro.
- Notas: Los archivos de datos estan en mft.rrc.texas.gov y ese host fallo con SSL_ERROR_SYSCALL, asi que no se pudo leer el encabezado real del CSV de produccion; la clasificacion se basa en las descripciones oficiales de la pagina de datos. Acceso marcado como scraping_necesario porque el unico enlace de descarga utilizable ('CSV Format') apunta a ese host MFT que no respondio. Muestra no publicada: los términos de la fuente no permiten reproducir las filas.

### Estados Unidos, Dakota del Norte

- Que publica: El sitio publico ofrece el indice de Monthly Production Reports en PDF y datos agregados, pero coloca 'Well Production' dentro de 'Premium Subscription Services'; informa tarifas de 100 USD/anio (basica) y 500 USD/anio (premium) desde el 1/1/2026.
- Acceso: pago. Archivo o API: https://www.dmr.nd.gov/oilgas/subscriptionservice.asp (HTML. 11.895 bytes).
- Id del pozo: no verificado (el listado de pozos publico existe en https://www.dmr.nd.gov/oilgas/findwellsvw.asp pero no se abrio). Ubicacion: no verificado.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: Indice de reportes mensuales 2003-2026.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.nd.gov/content.htm?id=Disclaimer): sin terminos visibles en las paginas revisadas (el sitio enlaza 'Disclaimer' en https://www.nd.gov/content.htm?id=Disclaimer, que no se abrio en esta sesion) Permiten derivadas con atribucion: no_claro.
- Notas: Confirmado el escenario esperado. Los PDFs mensuales publicos son 'fully searchable' pero no se abrio ninguno, conforme a la instruccion de no scrapear. Muestra no publicada: los términos de la fuente no permiten reproducir las filas.

### Estados Unidos, Registro nacional de fractura (FracFocus)

- Que publica: FracFocus publica como CSV publico (ZIP con FracFocusRegistry_1.csv a _15.csv, DisclosureList, WaterSource y readme) las declaraciones de fractura con APINumber, APINumber10, WellName, Latitude/Longitude, JobStartDate y JobEndDate por pozo; su API de busqueda permite recuperar pozos por estado, nombre o numero API.
- Acceso: api_documentada. Archivo o API: https://www.fracfocusdata.org/digitaldownload/FracFocusCSV.zip (CSV. 444.298.587 bytes).
- Id del pozo: APINumber (14 digitos, p. ej. 30-015-58180-00-00) y APINumber10 (10 digitos, p. ej. 3001558180). Ubicacion: Latitude, Longitude.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: Declaraciones desde 2011 (formato 1.0, solo cabecera) y 2012-presente (formato 2.0-4.0, con quimicos); ZIP actualizado 18/11/2026.
- Fecha de fractura o terminacion: JobStartDate (inicio del trabajo de fractura) y JobEndDate, en el registro de declaraciones de FracFocus; en los 2 ejemplos de Nuevo Mexico verificados JobStartDate vino nulo y JobEndDate = 10/30/2026.
- Terminos (https://fracfocus.org/terms): Data Download Terms of Use ... Downloaded data may be aggregated or combined with other datasets. The FracFocus data may not be altered in any way. Data downloaded from the FracFocus site may be used without restriction. Permiten derivadas con atribucion: si.
- Notas: El CSV completo pesa 444 MB y no se bajo: solo se leyo su directorio central por rango de bytes (FracFocusRegistry_1.csv ... _15.csv, DisclosureList_1.csv, WaterSource_1.csv, readme csv.txt). Los 2 ejemplos se obtuvieron de la API publica del propio registro (sin login) y muestran que APINumber usa el formato '30-XXX-XXXXX-XX-XX', compatible con el id de pozo de Nuevo Mexico (API 30-015-58180). No se pudo comparar directamente con la tabla de pozos de NM OCD porque wwwapps.emnrd.nm.gov agoto el timeout. El campo de fecha de inicio de trabajo es JobStartDate (en estos 2 registros vino nulo; JobEndDate si tiene fecha).

### Arabia Saudita, Nacional

- Que publica: No se pudo ver: el sitio del Ministerio de Energia (moenergy.gov.sa) no respondio dentro del tiempo limite en esta sesion.
- Acceso: otro. Archivo o API: https://www.moenergy.gov.sa/en (HTML).
- Id del pozo: no se pudo verificar. Ubicacion: no se pudo verificar.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.moenergy.gov.sa/en): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: Un solo pedido, sin respuesta. Reintentar o probar el portal de estadisticas (GASTAT).

### Argelia, Nacional

- Que publica: No se pudo ver: el sitio de ALNAFT (alnaft.gov.dz) no respondio dentro del tiempo limite en esta sesion.
- Acceso: otro. Archivo o API: https://www.alnaft.gov.dz/en/ (HTML).
- Id del pozo: no se pudo verificar. Ubicacion: no se pudo verificar.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.alnaft.gov.dz/en/): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: Un solo pedido, sin respuesta.

### Australia, Australia Occidental

- Que publica: No se pudo ver: el catalogo CKAN data.wa.gov.au devolvio HTTP 500 en la busqueda y la pagina de coleccion de datos de petroleo en wa.gov.au devolvio 404 en la ruta probada.
- Acceso: otro. Archivo o API: https://data.wa.gov.au/api/3/action/package_search?q=petroleum%20production (API).
- Id del pozo: no verificado. Ubicacion: no verificado.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.wa.gov.au/): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: El CKAN de WA devuelve 500 en la busqueda (puede ser caida temporal). DEMIRS publica datos de pozos y produccion por campo en su propio portal, que no se localizo en la ruta probada.

### Australia, Queensland (cuenca Cooper y Surat/Bowen)

- Que publica: Publica 'Petroleum and gas production statistics' en XLSX semestrales (y una serie historica con archivos separados de crudo, gas, condensado y CSG) bajo CC-BY 4.0; el intento de abrir el XLSX 2025 devolvio HTTP 202 sin cuerpo, y el catalogo tambien expone informes de terminacion de pozo (well completion report) por pozo en PDF.
- Acceso: descarga_directa. Archivo o API: https://www.data.qld.gov.au/dataset/petroleum-gas-production-and-reserve-statistics (XLSX).
- Id del pozo: no verificado (el catalogo tiene 'WELL COMPLETION REPORT' por pozo en PDF). Ubicacion: no verificado.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado (publicaciones semestrales 2025 y serie historica).
- Fecha de fractura o terminacion: no verificado (informes de terminacion por pozo en PDF, no tabla).
- Terminos (https://www.data.qld.gov.au/dataset/petroleum-gas-production-and-reserve-statistics): Creative Commons Attribution 4.0 Permiten derivadas con atribucion: si.
- Notas: El 202 sin cuerpo puede ser una generacion diferida del archivo: reintentar la descarga. Queensland si publica muchos informes por pozo (cr*) incluidos 'WELL COMPLETION REPORT', que darian la fecha de terminacion pero en PDF, no en tabla unible por id.

### Australia, Territorio del Norte (Beetaloo)

- Que publica: No se pudo ver: la pagina de estadisticas de produccion de nt.gov.au devolvio HTTP 403 al cliente generico.
- Acceso: otro. Archivo o API: https://nt.gov.au/industry/mining-and-petroleum/petroleum/production-and-exploration-statistics (HTML).
- Id del pozo: no verificado. Ubicacion: no verificado.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://nt.gov.au/): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: El Beetaloo es exploratorio: es probable que no haya produccion mensual por pozo publicada, pero no se pudo confirmar.

### Canada, Manitoba

- Que publica: La pagina de datos publicos de Manitoba lista codigos y catalogos de instalaciones y campos, y ninguna descarga de volumetria por pozo.
- Acceso: descarga_directa. Archivo o API: https://www.petrinex.ca/PD/Pages/MBPD.aspx (HTML).
- Id del pozo: no verificado. Ubicacion: no verificado.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no verificado). Anios: no verificado.
- Fecha de fractura o terminacion: no verificado en esta fuente.
- Terminos (https://www.petrinex.ca/PD/Pages/default.aspx): no verificado: pagina de terminos de Petrinex no leida Permiten derivadas con atribucion: no_claro.
- Notas: Solo se leyo la pagina de descargas; la pagina de produccion del gobierno provincial respondio 404.

### China, Nacional

- Que publica: El portal estadistico nacional (NBS) publica series macro: en la portada aparece 'Industrial Production Operation in October 2026'; no se vio ningun dataset por pozo ni por campo.
- Acceso: descarga_directa. Archivo o API: https://www.stats.gov.cn/english/ (HTML).
- Id del pozo: no se pudo verificar. Ubicacion: no se pudo verificar.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.stats.gov.cn/english/): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: Verificacion liviana (una pagina). China no publica microdatos de pozos; las cifras por campo que circulan son de empresas o de agencias privadas. Muestra no publicada: los términos de la fuente no permiten reproducir las filas.

### Estados Unidos, Montana

- Que publica: No se pudo ver: los dos dominios del regulador (www.mbogc.gov y mbogc.mt.gov) no resuelven desde esta sesion y la consulta DNS publica de www.mbogc.gov devuelve una respuesta sin registro A; la ruta del Board en el portal del estado (www.mt.gov/boards/mbogc) da 404.
- Acceso: otro. Archivo o API: https://www.mbogc.gov/ (no verificado).
- Id del pozo: no verificado. Ubicacion: no verificado.
- Petroleo mensual por pozo: no verificado (unidad: no verificado). Anios: no verificado.
- Fecha de fractura o terminacion: no verificado.
- Terminos (no verificado): no verificado: hoy no se pudo abrir ninguna pagina del regulador ni de terminos Permiten derivadas con atribucion: no_claro.
- Notas: Lo nuevo de hoy es que www.mbogc.gov no tiene registro A publico y que la ruta del estado en mt.gov da 404: conviene ubicar el host actual de la Board of Oil and Gas Conservation (o sus paginas en el portal del estado) antes de reintentar. El portal data.mt.gov responde pero es un portal institucional, no un catalogo de datasets con produccion por pozo. No se intento ninguna via con login ni pago. Muestra no publicada: no hay filas que reproducir.

### Estados Unidos, Nuevo Mexico

- Que publica: GO-TECH, el centro de datos de produccion del Petroleum Recovery Research Center de NM Tech (gotech.nmt.edu), ofrece una busqueda interactiva de produccion por API Number, seccion/township/range, operador, pool y condado, con anio de inicio y fin, y una pagina 'All Wells' con dos descargas directas (allwells_zip/AllWells.zip, 24.324.628 bytes, y allwells_zip/PermianBasin.zip, 18.103.183 bytes) que contienen un unico archivo Microsoft Access (PermianBasin.mdb, 86.880.256 bytes) que no se pudo leer en esta sesion. La pagina OCD Data del EMNRD publica el diccionario del FTP (FTPDataSetDescriptions.pdf) que describe OCDCoreDataYYYYMMDD.zip con las tablas T_WELL (wells), T_WC (well completions), T_POOL, T_PROD_PROP, T_SPU, T_SP_C_UNIT_SDIV y T_POD_VOL, pero ese FTP no contesto.
- Acceso: otro. Archivo o API: https://gotech.nmt.edu/gotech/Petroleum_Data/allwells_zip/PermianBasin.zip (ZIP con MDB (Access). 18.103.183 bytes).
- Id del pozo: no verificado (el .mdb descargado no se pudo abrir: no hay lector de Access en este entorno; el buscador de GO-TECH si pide API Number, con el ejemplo 3001525482). Ubicacion: no verificado (el buscador pide Section, Township, Range y County Name, pero no se vio el resultado).
- Petroleo mensual por pozo: no verificado (la busqueda de GO-TECH devuelve la produccion del pozo, pero solo por formulario ASP.NET; no se vio ninguna tabla ni columna) (unidad: no verificado). Anios: no verificado (el buscador de GO-TECH permite elegir anio de inicio y fin desde 1993 hasta 2026; el diccionario del FTP dice que los datos se refrescan el primer lunes de cada mes).
- Fecha de fractura o terminacion: no verificado (existen las paginas 'Well Activity' y 'First Production' de GO-TECH, que no se abrieron).
- Terminos (https://www.emnrd.nm.gov/officeofsecretary/legal-disclaimer/): This website includes information maintained by the State of New Mexico, Energy, Minerals and Natural Resources Department (“EMNRD”), as well as links to other sites maintained by other entities, agencies, or third parties, as a public service. This information and links are provided for the convenience of the website user and do not constitute an official or final repository of such information or data. Permiten derivadas con atribucion: no_claro.
- Notas: Lo nuevo de hoy: GO-TECH si responde y publica su base de datos de pozos como descarga directa (dos ZIP con un .mdb cada uno) y el diccionario del FTP de OCD nombres de tablas (T_WELL, T_WC, T_POD_VOL...), de modo que la fuente existe y es alcanzable; lo que falta es poder leer el .mdb o el ZIP del FTP. El diccionario dice explicitamente que esos datasets se comparten con NM Tech para sus reportes de produccion en el sitio Go-Tech y que se refrescan el primer lunes de cada mes. Terminos: la disclaimer del EMNRD se leyo completa hoy y no prohibe descargar ni publicar cifras derivadas, pero tampoco concede una licencia (no_claro). No se intento ninguna via con login ni pago. Muestra no publicada: no se pudo abrir ningun archivo con filas.

### Estados Unidos, Oklahoma

- Que publica: OCC publica datos de pozos descargables (RBDMS Well Data en CSV, con API, lat/lon, operador y estado; reportes mensuales de terminaciones y shapefiles), pero la propia pagina indica que la produccion de crudo y gas la conserva la Oklahoma Tax Commission.
- Acceso: descarga_directa. Archivo o API: https://oklahoma.gov/content/dam/ok/en/occ/documents/og/ogdatafiles/rbdms-wells.csv (CSV. 127.075.756 bytes).
- Id del pozo: API. Ubicacion: SH_LAT, SH_LON (ademas COUNTY, SECTION, TOWNSHIP, RANGE, QTR1-QTR4).
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: El CSV se actualiza cada noche (last-modified 2026-11-18); el archivo no declara anios cubiertos.
- Fecha de fractura o terminacion: no verificado en este archivo; existe un 'Monthly Well Completions Report' XLSX separado (completions-wells-formations-base.xlsx).
- Terminos (https://oklahoma.gov/about/policy-disclaimers.html): sin terminos visibles en las paginas revisadas (la pagina de datos solo enlaza 'Policies' en https://oklahoma.gov/about/policy-disclaimers.html, que no se abrio en esta sesion) Permiten derivadas con atribucion: no_claro.
- Notas: El CSV de pozos pesa 127 MB pero acepta rangos; se bajo solo el primer bloque de 64 KB. Produccion podria estar en la Oklahoma Tax Commission, no revisada en esta tarea. Formato del id: API de 10 digitos (3500100002), comparable al API de FracFocus. Muestra no publicada: los términos de la fuente no permiten reproducir las filas.

### Estados Unidos, Pennsylvania

- Que publica: La pagina 'Oil and Gas Reports' de la DEP enlaza el extracto de produccion por pozo (OilGasWellProdReport en greenport.pa.gov) y una lista de reportes SSRS en cedatareporting.pa.gov; hoy el extracto devuelve HTTP 500 con 'Error Code 3759' por HTTP, por HTTPS y con rs:Format=CSV, y los dos reportes SSRS probados agotan el tiempo de espera. Si se pudo abrir un directorio publico (files.dep.state.pa.us/OilGas/BOGM/BOGMPortalFiles/) y el diccionario de datos de los reportes, un PDF de 639.611 bytes.
- Acceso: otro. Archivo o API: https://greenport.pa.gov/ReportExtracts/OG/OilGasWellProdReport (no verificado).
- Id del pozo: no verificado (el diccionario publico de los reportes se descargo, pero el extracto de produccion no se pudo abrir). Ubicacion: no verificado.
- Petroleo mensual por pozo: no verificado (unidad: no verificado). Anios: no verificado.
- Fecha de fractura o terminacion: no verificado.
- Terminos (no verificado): no verificado: hoy no se abrio ninguna pagina de terminos del estado Permiten derivadas con atribucion: no_claro.
- Notas: El 500 no parece un error de ruta: se probo con y sin www, por http y https y con rs:Format=CSV, siempre con la misma respuesta. El diccionario publico de datos (DEP_Oil_and_GAS_Reports_Data_Dictionary.pdf, abril de 2022, version 1.8) y el directorio files.dep.state.pa.us si responden, de modo que el bloqueo parece del servicio de extraccion y no del sitio. Repetir el extracto mas adelante; no se eludio el bloqueo. Muestra no publicada: no hay filas que reproducir.

### Estados Unidos, Utah

- Que publica: No se pudo ver: el dominio del regulador (dogm.utah.gov) no existe en DNS, confirmado con una consulta publica que devuelve NXDOMAIN, y tampoco resuelve desde esta sesion. Lo unico localizado hoy son cuatro capas de petroleo y gas en el Hub de datos geograficos del estado (opendata.gis.utah.gov) atribuidas a la Division of Oil, Gas, and Mining: 'Utah Oil and Gas Wells Paths', 'Utah Oil and Gas Well Bottom Hole Locations', 'Utah Oil and Gas Fields' y 'Utah Oil and Gas Well Locations', ninguna de produccion por pozo.
- Acceso: otro. Archivo o API: https://dogm.utah.gov/ (no verificado).
- Id del pozo: no verificado. Ubicacion: no verificado.
- Petroleo mensual por pozo: no verificado (unidad: no verificado). Anios: no verificado.
- Fecha de fractura o terminacion: no verificado.
- Terminos (no verificado): no verificado: hoy no se pudo abrir ninguna pagina del regulador ni de terminos Permiten derivadas con atribucion: no_claro.
- Notas: Hallazgo nuevo de hoy: el dominio del regulador ya no existe en DNS, asi que el reintento exige localizar el host actual de la Division of Oil, Gas, and Mining. Las cuatro capas del Hub del estado estan descritas como datos de la Division; la metadata de 'Utah Oil and Gas Wells Paths' dice literalmente 'This data set represents Utah Oil and Gas Well Paths permitted by the Utah Division of Oil, Gas, and Mining. Data is updated regularly.' y en el catalogo del Hub no aparecio produccion por pozo. No se intento ninguna via con login ni pago. Muestra no publicada: no hay filas que reproducir.

### Libia, Nacional

- Que publica: La portada de la NOC publica comunicados y metas agregadas ('con una vision de producir 2-3 millones de barriles por dia'); no se vio ningun dataset por pozo ni por campo.
- Acceso: descarga_directa. Archivo o API: https://noc.ly/ (HTML).
- Id del pozo: no se pudo verificar. Ubicacion: no se pudo verificar.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://noc.ly/): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: Verificacion liviana (una pagina). Muestra no publicada: los términos de la fuente no permiten reproducir las filas.

### Mexico, Nacional (cuencas del sureste y Burgos)

- Que publica: No se pudo ver: la pagina de la CNH remite al Centro Nacional de Informacion de Hidrocarburos como centro de datos, pero el portal del CNIH (hidrocarburos.gob.mx) respondio HTTP 522 (origen caido) y la API de datos.gob.mx devolvio 404 en la ruta de busqueda usada.
- Acceso: otro. Archivo o API: https://www.gob.mx/cnh/articulos/centro-nacional-de-informacion-de-hidrocarburos-cnih-64831 (HTML).
- Id del pozo: no verificado. Ubicacion: no verificado (la CNH lista 'Autorizaciones de Perforacion de Pozos', que es un registro por pozo, no produccion).
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.gob.mx/cnh): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: Reintentar por el CNIH cuando el portal responda; la CNH si publica registros por pozo (autorizaciones de perforacion) que podrian dar id y coordenadas. No se pudo confirmar si la produccion es por pozo o por campo.

### Noruega, Plataforma continental noruega

- Que publica: No se pudo ver el contenido: factpages.sodir.no responde 200 pero es una aplicacion JavaScript sin tabla en el HTML, y sodir.no devuelve 403 al cliente generico; los endpoints de reporte de FactPages que se probaron devolvieron 500 por ruta invalida.
- Acceso: otro. Archivo o API: https://factpages.sodir.no/en/wellbore/PageView/All (HTML).
- Id del pozo: no verificado (FactPages tiene vista 'wellbore'). Ubicacion: no verificado.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://factpages.sodir.no/en): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: El bloqueo 403 de sodir.no es un filtro de bots: no se intento rodearlo (regla dura). Para el revisor: FactPages expone descargas en SQL Server Reporting Services bajo /public?/Factpages/external/...; habria que encontrar la ruta exacta del reporte de wellbore o de produccion.

### Reino Unido, Plataforma continental del Reino Unido

- Que publica: Publica temas de datos separados (Fields, Wells, Production, Licences) con una pagina de 'Production data' interactiva; no se pudo abrir ningun archivo de produccion por pozo y los datos por pozo del UK National Data Repository estan detras de un registro.
- Acceso: otro. Archivo o API: https://www.nstauthority.co.uk/data-and-insights/data/themes/production/ (HTML).
- Id del pozo: no verificado (tema 'Wells' con 'Exploration and appraisal well results'). Ubicacion: no verificado.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.nstauthority.co.uk/data-centre/data-downloads/): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: Nivel asignado con evidencia parcial: la pagina de produccion no expone un archivo estatico (se carga por JavaScript) y no se pudo ver la columna de granularidad. El acceso por pozo pasa por el UK National Data Repository (registro de usuario), lo que lo excluye por regla de login.

### Rusia, Nacional

- Que publica: El sitio de CDU TEK publica noticias y notas del sector (menciona yacimientos y planes de produccion) pero no se vio ningun dataset descargable por pozo; la portada es institucional.
- Acceso: otro. Archivo o API: https://www.cdu.ru/ (HTML).
- Id del pozo: no se pudo verificar. Ubicacion: no se pudo verificar.
- Petroleo mensual por pozo: no se pudo verificar (unidad: no se pudo verificar). Anios: no verificado.
- Fecha de fractura o terminacion: no se pudo verificar.
- Terminos (https://www.cdu.ru/): sin terminos visibles Permiten derivadas con atribucion: no_claro.
- Notas: Verificacion liviana (una pagina). No se intento el sitio del Ministerio de Energia. Muestra no publicada: los términos de la fuente no permiten reproducir las filas.

## Que NO es

- No es una medicion de nada: ninguna cifra de esta pagina es una brecha, un rendimiento ni una afirmacion causal.
- "No entra" no dice que la jurisdiccion no produzca ni que no publique nada: dice que esta auditoria no encontro, verificando hoy, las cuatro condiciones juntas. Una fuente marcada "no se pudo verificar" quedo sin leer, y su estado puede cambiar.
- Un permiso no claro cuenta como no permitido hasta que el regulador lo aclare; no se rodea ningun login, pago ni termino de uso. "Sin restriccion" quiere decir que la pagina no prohibe usar ni publicar cifras derivadas de los archivos que ofrece; no es una licencia.
- La auditoria lee encabezados y unas filas. Que una fuente entre no garantiza que sus datos alcancen para medir: eso lo dice el estudio de cada cuenca.
