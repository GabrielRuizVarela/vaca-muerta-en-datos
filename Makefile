# Atajos del proyecto. Cada objetivo es un comando de uv; no hace falta nada mas que uv.
.PHONY: test demo full ingest

# Tests (no necesitan datos).
test:
	uv run pytest -q

# Demo: construye con la muestra de data/muestra, sin descargar nada (menos de 3 minutos).
# La pagina queda en site/muestra/index.html y dice MUESTRA: no son las cifras de la cuenca.
demo:
	uv sync
	uv run python -m pipeline.run_all --muestra
	@echo "Listo: abri site/muestra/index.html en el navegador (muestra, no son las cifras de la cuenca)."

# Cadena completa sobre la capa raw (necesita data/raw: bajala con `make ingest`).
full:
	uv run python -m pipeline.run_all

# Descarga los datos de la Secretaria de Energia y corre todo.
# Necesita una red argentina: el servidor de datos.energia.gob.ar no responde desde otros paises.
ingest:
	uv run python -m pipeline.run_all --with-ingest
