"""Tests del modo con datos propios (pipeline/local.py)."""
from __future__ import annotations

import csv
import json
import math
import subprocess
from calendar import monthrange
from pathlib import Path

import numpy as np
import pytest

from pipeline import local
from pipeline.dosis import NOMBRES
from pipeline.ingest import ROOT


def sintetico(base, brecha=0.25, pendiente=0.08, seed=1, n_clusters=60):
    """Escribe pozos.csv y mensual.csv sintéticos fuera del repo y devuelve sus rutas.

    Cada cluster tiene 1 hijo con fractura en 2020 (marzo a octubre), 2 padres cercanos (0,4 a 0,9 km) y 2
    padres control (2,5 a 4 km). Los padres producen desde 2018-01 con decaimiento de 1% mensual y ruido de 1%;
    en los meses 0, 1 y 2 desde la fractura, el caudal de cada padre cercano se multiplica por (1 - g) con
    g = brecha + pendiente * z, z la arena por etapa logarítmica estandarizada entre clusters.
    """
    rng = np.random.default_rng(seed)
    base = Path(base)
    pozos_csv, mensual_csv = base / "pozos.csv", base / "mensual.csv"
    cols, lat0, lon0 = 8, -38.9, -68.1
    hijos = []
    for i in range(n_clusters):
        lat_c = lat0 + (i // cols) * 0.3
        lon_c = lon0 + (i % cols) * 0.3
        hijos.append({"id": 1000 + i, "lat": lat_c, "lon": lon_c, "mes": int(rng.integers(3, 11)),
                      "dia": int(rng.integers(1, 29)),
                      "arena": 8000.0 * float(np.exp(rng.normal(0, 0.3))),
                      "etapas": max(1, int(round(40.0 * float(np.exp(rng.normal(0, 0.5)))))),
                      "rama": 2500.0 * float(np.exp(rng.normal(0, 0.5))),
                      "presion": min(19000.0, max(1000.0, 9000.0 * float(np.exp(rng.normal(0, 0.15)))))})
    x = np.array([math.log(h["arena"] / h["etapas"]) for h in hijos])
    z = (x - x.mean()) / x.std()
    filas_p, filas_m = [], []
    for i, h in enumerate(hijos):
        g = brecha + pendiente * float(z[i])
        filas_p.append([h["id"], f"pad-{h['id']}", repr(h["lon"]), repr(h["lat"]),
                        f"2020-{h['mes']:02d}-{h['dia']:02d}", repr(h["arena"]), h["etapas"],
                        repr(h["rama"]), repr(h["presion"])])
        t2 = 0
        for yy in (2020, 2021):
            for mm in range(1, 13):
                if yy == 2020 and mm <= h["mes"]:
                    continue
                dias = monthrange(yy, mm)[1]
                q = 30.0 * 0.99 ** t2 * (1 + 0.01 * float(rng.normal()))
                filas_m.append([h["id"], f"{yy}-{mm:02d}", repr(q * dias), "99"])
                t2 += 1
        for j in range(4):
            dist = float(rng.uniform(0.4, 0.9)) if j < 2 else float(rng.uniform(2.5, 4.0))
            tet = j * math.pi / 2 + float(rng.uniform(-0.3, 0.3))
            plat = h["lat"] + dist * math.cos(tet) / 111.32
            plon = h["lon"] + dist * math.sin(tet) / (111.32 * math.cos(math.radians(h["lat"])))
            pid = 10000 + i * 4 + j
            filas_p.append([pid, f"pad-{pid}", repr(plon), repr(plat), "", "", "", "2000", ""])
            q0 = float(rng.uniform(20, 40))
            for yy in (2018, 2019, 2020, 2021):
                for mm in range(1, 13):
                    t = (yy - 2018) * 12 + mm - 1
                    q = q0 * 0.99 ** t * (1 + 0.01 * float(rng.normal()))
                    k = (yy - 2020) * 12 + (mm - h["mes"])
                    if j < 2 and k in (0, 1, 2):
                        q *= (1 - g)
                    dias = monthrange(yy, mm)[1]
                    filas_m.append([pid, f"{yy}-{mm:02d}", repr(q * dias), str(dias)])
    for mm in range(1, 6):
        filas_m.append([999999, f"2020-{mm:02d}", "100.0", "28"])
    with open(pozos_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pozo_id", "pad_id", "lon", "lat", "fecha_fractura", "arena_tn", "etapas", "rama_m",
                    "presion_max_psi"])
        w.writerows(filas_p)
    with open(mensual_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pozo_id", "mes", "petroleo_m3", "dias_produccion"])
        w.writerows(filas_m)
    return pozos_csv, mensual_csv


def _corre(pozos, mensual, out, reps=200):
    assert local.main(["--wells", str(pozos), "--monthly", str(mensual), "--out", str(out), "--reps",
                       str(reps)]) == 0
    return json.loads((out / "resumen.json").read_text())


def test_comprobar_rutas_repo_temporal(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "tracked.csv").write_text("a\n1\n")
    (repo / ".gitignore").write_text("ignored.csv\n")
    (repo / "ignored.csv").write_text("a\n2\n")
    (repo / "untracked_noignored.csv").write_text("a\n3\n")
    subprocess.run(["git", "add", "tracked.csv", ".gitignore"], cwd=repo, check=True, capture_output=True)
    with pytest.raises(SystemExit) as e:
        local.comprobar_rutas([repo / "tracked.csv"], raiz=repo)
    assert e.value.code == 2
    assert "repositorio" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:
        local.comprobar_rutas([repo / "untracked_noignored.csv"], raiz=repo)
    assert e.value.code == 2
    assert "repositorio" in capsys.readouterr().err
    local.comprobar_rutas([repo / "ignored.csv", tmp_path / "fuera"], raiz=repo)


def test_main_rehusa_ruta_versionada(tmp_path):
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as e:
        local.main(["--wells", str(ROOT / "README.md"), "--monthly", str(tmp_path / "m.csv"), "--out",
                    str(out)])
    assert e.value.code == 2
    assert not out.exists()


def test_error_columna_faltante(tmp_path, capsys):
    pozos = tmp_path / "pozos.csv"
    mensual = tmp_path / "mensual.csv"
    pozos.write_text("pozo_id,pad_id,lon,fecha_fractura,arena_tn,etapas,rama_m,presion_max_psi\n"
                     "7,pad-siete,12.345678,2020-05-10,87654.321,40,2500,9000\n")
    mensual.write_text("pozo_id,mes,petroleo_m3\n7,2020-01,100\n")
    with pytest.raises(SystemExit) as e:
        local.main(["--wells", str(pozos), "--monthly", str(mensual), "--out", str(tmp_path / "out"),
                    "--reps", "100"])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert "lat" in err
    assert "12.345678" not in err and "pad-siete" not in err and "87654.321" not in err


def test_planta_y_recupera(tmp_path):
    pozos, mensual = sintetico(tmp_path, brecha=0.25, pendiente=0.08, seed=1, n_clusters=60)
    out = tmp_path / "out"
    res = _corre(pozos, mensual, out)
    k1, k6 = res["brecha"]["k1"], res["brecha"]["k6"]
    assert -0.31 <= k1["brecha"] <= -0.19
    assert not (k1["ic_bajo"] <= 0 <= k1["ic_alto"])
    assert -0.06 <= k6["brecha"] <= 0.06
    dz = res["dosis"]
    assert dz["corrio"] and dz["n"] >= 100
    var = next(v for v in dz["variables"] if v["nombre"] == NOMBRES["arena_etapa"])
    assert 0.00 <= var["coef"] <= 0.18
    assert var["ic_bajo"] > -0.05
    md = (out / "resumen.md").read_text()
    assert "Qué no prueba" in md and "queda descartado" not in md and "—" not in md and "–" not in md
    ev = (out / "eventos.csv").read_text().splitlines()
    assert ev[0] == "padre,hijo_cercano,mes_frac,km_min,edad_meses,caida,v1,v2,v3,v4"
    assert len(ev) > 100


def test_sin_pendiente(tmp_path):
    pozos, mensual = sintetico(tmp_path, brecha=0.25, pendiente=0, seed=1, n_clusters=60)
    res = _corre(pozos, mensual, tmp_path / "out")
    var = next(v for v in res["dosis"]["variables"] if v["nombre"] == NOMBRES["arena_etapa"])
    assert abs(var["coef_sd"]) < 0.2
    assert var["ic_bajo_sd"] <= 0 <= var["ic_alto_sd"]


def test_determinismo(tmp_path):
    pozos, mensual = sintetico(tmp_path, brecha=0.25, pendiente=0.08, seed=1, n_clusters=60)
    _corre(pozos, mensual, tmp_path / "o1")
    _corre(pozos, mensual, tmp_path / "o2")
    assert (tmp_path / "o1" / "resumen.json").read_bytes() == (tmp_path / "o2" / "resumen.json").read_bytes()


def test_solo_escribe_en_salida(tmp_path):
    try:
        antes = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True,
                               timeout=60).stdout
    except Exception:
        antes = None
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    out = tmp_path / "out"
    _corre(pozos, mensual, out)
    if antes is not None:
        despues = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True,
                                 timeout=60).stdout
        assert antes == despues
    todos = {p for p in tmp_path.rglob("*") if p.is_file()}
    resto = todos - {pozos, mensual}
    assert resto <= {out / "resumen.json", out / "resumen.md", out / "eventos.csv"}


def test_dosis_salteada_por_muestra_chica(tmp_path):
    pozos, mensual = sintetico(tmp_path, n_clusters=12)
    res = _corre(pozos, mensual, tmp_path / "out")
    assert res["dosis"]["corrio"] is False
    assert "nimo" in res["dosis"]["motivo"]
    assert res["brecha"]["k1"]["aviso_muestra_chica"] is True
    assert res["brecha"]["k1"]["n_cercanos"] == 24
