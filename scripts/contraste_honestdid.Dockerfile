# Contenedor del contraste con HonestDiD (ronda 4, S1): R 4.4.2 y HonestDiD 0.2.8 de CRAN, de una foto fechada de Posit Package Manager.
FROM rocker/r-ver:4.4.2
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends libglpk40 && rm -rf /var/lib/apt/lists/*
RUN Rscript -e 'options(repos = c(CRAN = "https://p3m.dev/cran/__linux__/noble/2026-11-26")); install.packages(c("HonestDiD", "jsonlite"), Ncpus = 2); stopifnot(as.character(packageVersion("HonestDiD")) == "0.2.8"); library(jsonlite); cat("HonestDiD", as.character(packageVersion("HonestDiD")), "\n")'
