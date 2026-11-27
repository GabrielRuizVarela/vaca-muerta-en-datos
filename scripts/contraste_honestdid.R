# Contraste de la cota condicional con HonestDiD 0.2.8 (ronda 4, S1). Las cuatro lecturas estan en el docstring de
# pipeline/cota_rr_contraste.py. Uso: Rscript contraste_honestdid.R <entradas.json> <salida.json>
suppressPackageStartupMessages({library(HonestDiD); library(jsonlite); library(parallel)})
args <- commandArgs(trailingOnly = TRUE)
ent_path <- args[1]; sal_path <- args[2]
t0 <- Sys.time()
ENT <- fromJSON(ent_path, simplifyVector = FALSE)
sha <- strsplit(system2("sha256sum", ent_path, stdout = TRUE), " ")[[1]][1]
P <- ENT$parametros
ALFA <- P$alfa; KAPPA <- P$kappa; GRID_PUNTOS <- as.integer(P$grid_puntos); GRID_SD <- P$grid_sd
SEMILLA <- P$semilla_r; TOL_BIS <- P$tol_biseccion; MBAR_MAX <- P$mbar_max; CERO <- unlist(P$cero_grilla)
GRILLA_MBAR <- unlist(P$grilla_mbar); NPRE <- as.integer(P$num_previos); NPOST <- as.integer(P$num_posteriores)
NCORES <- 4L
LECTURAS <- c("L1", "L1p", "L2", "L3")

mat <- function(rows) do.call(rbind, lapply(rows, function(r) as.numeric(unlist(r))))
num <- function(x) if (is.null(x)) NA_real_ else as.numeric(x)

# Si el paquete falla con un error en un theta (p. ej. solve() de una matriz singular en una grilla que cae justo en un empate), esa
# prueba no rechaza, igual que cuando el programa lineal no converge; se cuenta aparte y se publica. Solo cambia eso del paquete.
.wrapper_original <- HonestDiD:::.test_delta_lp_fn_wrapper
.wrapper_con_error <- function(...) {
  r <- try(.wrapper_original(...), silent = TRUE)
  if (inherits(r, "try-error")) { warning("ERROR_PAQUETE: ", conditionMessage(attr(r, "condition"))); return(0) }
  r
}
assignInNamespace(".test_delta_lp_fn_wrapper", .wrapper_con_error, ns = "HonestDiD")

# cuenta las veces que el programa lineal no convergio (el paquete no rechaza ese theta), los errores del paquete y otras advertencias
contar <- function(expr) {
  n <- 0L; err <- 0L; otras <- 0L
  val <- withCallingHandlers(expr, warning = function(w) {
    m <- conditionMessage(w)
    if (grepl("did not converge", m, fixed = TRUE)) n <<- n + 1L
    else if (grepl("ERROR_PAQUETE", m, fixed = TRUE)) err <<- err + 1L
    else if (!grepl("CI is open", m, fixed = TRUE)) otras <<- otras + 1L
    invokeRestart("muffleWarning")
  })
  list(val = val, lp = n, err = err, otras = otras)
}

ests <- lapply(ENT$estimandos, function(e) {
  list(nombre = e$nombre, l = as.numeric(unlist(e$l_vec)), bh = as.numeric(unlist(e$beta_h)), sh = mat(e$Sigma_h),
       sd = e$sd, mbars_quiebre = as.numeric(unlist(e$mbars_quiebre)),
       por_mbar = lapply(e$por_mbar, function(m) list(mbar = m$mbar, pol = lapply(m$poliedros, function(p)
         list(j = p$j, sg = p$sg, A = mat(p$A), lf = if (is.null(p$c_lf)) Inf else p$c_lf)))))
})
names(ests) <- vapply(ests, function(e) e$nombre, "")
for (e in names(ests)) {
  E <- ests[[e]]
  center <- sum(E$l * E$bh[(NPRE + 1):(NPRE + NPOST)])
  sdh <- sqrt(c(t(E$l) %*% E$sh[(NPRE + 1):(NPRE + NPOST), (NPRE + 1):(NPRE + NPOST)] %*% E$l))
  ests[[e]]$sdh <- sdh
  ests[[e]]$lb <- center - GRID_SD * sdh
  ests[[e]]$ub <- center + GRID_SD * sdh
  ests[[e]]$grid <- seq(center - GRID_SD * sdh, center + GRID_SD * sdh, length.out = GRID_PUNTOS)
  stopifnot(abs(sdh - E$sd) < 1e-9)
}

polis_de <- function(E, mbar) {   # poliedros de la entrada con ese Mbar, o interpolados (A es lineal en Mbar) con los de 0 y 1
  for (m in E$por_mbar) if (abs(m$mbar - mbar) < 1e-12) return(m$pol)
  m0 <- Filter(function(m) m$mbar == 0, E$por_mbar)[[1]]$pol
  m1 <- Filter(function(m) m$mbar == 1, E$por_mbar)[[1]]$pol
  Map(function(p0, p1) list(j = p0$j, sg = p0$sg, A = p0$A + mbar * (p1$A - p0$A), lf = NA_real_), m0, m1)
}

# L1: el cuerpo de .ARP_computeCI sin la linea que vuelve a calcular lf_cv, que es el del modulo
acepta_l1 <- function(E, p, thetas) {
  A <- p$A
  Gamma <- HonestDiD:::.construct_Gamma(E$l)
  AGammaInv <- A[, (NPRE + 1):(NPRE + NPOST)] %*% base::solve(Gamma)
  AGammaInv_one <- AGammaInv[, 1]
  AGammaInv_minusOne <- AGammaInv[, -1]
  Y <- base::c(A %*% E$bh - 0)
  sigmaY <- A %*% E$sh %*% base::t(A)
  hl <- list(hybrid_kappa = KAPPA, lf_cv = p$lf)
  vapply(thetas, function(theta) 1 - HonestDiD:::.test_delta_lp_fn_wrapper(theta = theta,
    y_T = Y - AGammaInv_one * theta, X_T = AGammaInv_minusOne, sigma = sigmaY, alpha = ALFA, hybrid_flag = "LF",
    hybrid_list = hl, rowsForARP = 1:nrow(A)), numeric(1))
}
acepta_l1p <- function(E, p, thetas) {   # .ARP_computeCI tal cual
  HonestDiD:::.ARP_computeCI(betahat = E$bh, sigma = E$sh, numPrePeriods = NPRE, numPostPeriods = NPOST, A = p$A,
    d = rep(0, nrow(p$A)), l_vec = E$l, alpha = ALFA, hybrid_flag = "LF", hybrid_list = list(hybrid_kappa = KAPPA),
    returnLength = FALSE, grid.lb = min(thetas), grid.ub = max(thetas), gridPoints = length(thetas),
    rowsForARP = 1:nrow(p$A))$accept
}
acepta_l23 <- function(E, mbar, thetas, solo_post) {
  computeConditionalCS_DeltaRM(betahat = E$bh, sigma = E$sh, numPrePeriods = NPRE, numPostPeriods = NPOST, l_vec = E$l,
    Mbar = mbar, alpha = ALFA, hybrid_flag = "LF", hybrid_kappa = KAPPA, returnLength = FALSE,
    postPeriodMomentsOnly = solo_post, gridPoints = length(thetas), grid.ub = max(thetas), grid.lb = min(thetas),
    seed = SEMILLA)$accept
}
acepta <- function(E, lectura, mbar, thetas) {
  if (lectura == "L2") return(acepta_l23(E, mbar, thetas, FALSE))
  if (lectura == "L3") return(acepta_l23(E, mbar, thetas, TRUE))
  acc <- rep(0, length(thetas))
  for (p in polis_de(E, mbar)) {
    a <- if (lectura == "L1") acepta_l1(E, p, thetas) else acepta_l1p(E, p, thetas)
    acc <- pmax(acc, a)
  }
  acc
}

resumen <- function(grid, acc, mbar, lp, otras, err) {
  idx <- which(acc == 1)
  paso <- grid[2] - grid[1]
  if (!length(idx)) return(list(mbar = mbar, bajo = NA_real_, alto = NA_real_, abierto = NA_character_, con_huecos = FALSE,
                                n_aceptados = 0L, paso = paso, lp_fallos = lp, errores_paquete = err, otras_advertencias = otras))
  ab_lo <- acc[1] == 1; ab_hi <- acc[length(acc)] == 1
  list(mbar = mbar, bajo = grid[min(idx)], alto = grid[max(idx)],
       abierto = if (ab_lo && ab_hi) "ambos" else if (ab_lo) "bajo" else if (ab_hi) "alto" else NA_character_,
       con_huecos = (max(idx) - min(idx) + 1L) != length(idx), n_aceptados = length(idx), paso = paso,
       lp_fallos = lp, errores_paquete = err, otras_advertencias = otras)
}

tarea <- function(t) {
  E <- ests[[t$est]]
  ini <- Sys.time()
  if (t$tipo == "set") {
    r <- contar(acepta(E, t$lectura, t$mbar, E$grid))
    out <- list(resumen = resumen(E$grid, r$val, t$mbar, r$lp, r$otras, r$err), lp = r$lp, err = r$err)
  } else if (t$lectura == "L1") {
    r <- contar(acepta(E, "L1", t$mbar, CERO))
    out <- list(prueba = list(mbar = t$mbar, acepta_cero = r$val[2] == 1), lp = r$lp, err = r$err)
  } else {   # biseccion de L1p, L2 o L3
    lp <- 0L; err <- 0L
    contiene <- function(m) { r <- contar(acepta(E, t$lectura, m, CERO)); lp <<- lp + r$lp; err <<- err + r$err; r$val[2] == 1 }
    q <- if (contiene(0)) 0 else if (!contiene(MBAR_MAX)) NA_real_ else {
      lo <- 0; hi <- MBAR_MAX
      while (hi - lo > TOL_BIS) { mid <- (lo + hi) / 2; if (contiene(mid)) hi <- mid else lo <- mid }
      hi
    }
    out <- list(quiebre = q, lp = lp, err = err)
  }
  message(sprintf("%s %s %s %s: %.1f s", t$est, t$lectura, t$tipo, format(t$mbar), as.numeric(Sys.time() - ini, units = "secs")))
  c(t[c("est", "lectura", "tipo", "mbar")], out)
}

tareas <- list()
for (e in names(ests)) for (l in LECTURAS) {
  for (m in GRILLA_MBAR) tareas[[length(tareas) + 1]] <- list(est = e, lectura = l, tipo = "set", mbar = m)
  if (l == "L1") for (m in ests[[e]]$mbars_quiebre) tareas[[length(tareas) + 1]] <- list(est = e, lectura = l, tipo = "quiebre", mbar = m)
  else tareas[[length(tareas) + 1]] <- list(est = e, lectura = l, tipo = "biseccion", mbar = NA_real_)
}
res <- mclapply(tareas, tarea, mc.cores = NCORES, mc.preschedule = FALSE)
for (r in res) if (inherits(r, "try-error") || is.null(r)) stop("fallo una tarea: ", paste(as.character(r), collapse = " "))

salida_est <- list()
for (e in names(ests)) {
  E <- ests[[e]]
  s <- list(paso_r = E$grid[2] - E$grid[1], sd = E$sdh, grid_lb = E$lb, grid_ub = E$ub)
  for (l in LECTURAS) {
    mis <- Filter(function(r) r$est == e && r$lectura == l, res)
    sets <- Filter(function(r) r$tipo == "set", mis)
    sets <- sets[order(vapply(sets, function(r) r$mbar, 0))]
    entrada <- list(sets = lapply(sets, function(r) r$resumen), lp_fallos = sum(vapply(mis, function(r) r$lp, 0L)),
                    errores_paquete = sum(vapply(mis, function(r) r$err, 0L)))
    if (l == "L1") {
      qs <- Filter(function(r) r$tipo == "quiebre", mis)
      entrada$quiebre_prueba <- lapply(qs, function(r) r$prueba)
      entrada$quiebre <- NA_real_
    } else {
      entrada$quiebre <- Filter(function(r) r$tipo == "biseccion", mis)[[1]]$quiebre
    }
    s[[l]] <- entrada
  }
  salida_est[[e]] <- s
}
out <- list(sha256_entradas = sha, r = R.version.string, honestdid = as.character(packageVersion("HonestDiD")),
            parametros = P, seed = SEMILLA, nucleos = NCORES,
            segundos = as.numeric(Sys.time() - t0, units = "secs"), estimandos = salida_est)
write_json(out, sal_path, auto_unbox = TRUE, digits = NA, na = "null", pretty = TRUE)
message("listo: ", sal_path, " en ", round(out$segundos), " s")
