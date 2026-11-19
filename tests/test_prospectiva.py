"""Prueba prospectiva con mundo sintetico: efecto plantado, nulo, poca muestra y archivo."""
import json

import numpy as np
import pytest

from pipeline import placebo, prospectiva

N_HIJOS = 70
N_MES = 220
REPS = 60
P1 = (-0.229, -0.287, -0.168)
FECHA = "2026-11-18"


def sintetico(efecto: float = 0.23, seed: int = 3) -> dict:
    """Como sintetico_gas pero solo petroleo: 12 cercanos y 30 controles por hijo.

    Los cercanos pierden `efecto` en los meses 0 a 2 desde la fractura del hijo.
    """
    rng = np.random.default_rng(seed)
    hijo_mes = rng.integers(100, 150, N_HIJOS).astype(np.int64)
    ph, pp, km, rumbo = [], [], [], []
    for h in range(N_HIJOS):
        for j in range(42):
            ph.append(h)
            pp.append(len(pp))
            km.append(rng.uniform(0.3, 0.9) if j < 12 else rng.uniform(2.0, 4.5))
            rumbo.append(rng.uniform(0, 180))
    n_par = len(pp)
    tasa = np.full((n_par, N_MES + 2 * placebo.PAD), np.nan)
    t = np.arange(N_MES)
    for i in range(n_par):
        h, cerca = ph[i], km[i] < 1
        y = 50 * np.exp(-0.01 * t) * (1 + rng.normal(0, 0.03, N_MES))
        if cerca:
            y[hijo_mes[h]:hijo_mes[h] + 3] *= 1 - efecto
        tasa[i, placebo.PAD:placebo.PAD + N_MES] = y
    area = np.array(["A", "B", "C"])[np.arange(n_par) % 3]
    D = {"hijo_id": np.arange(N_HIJOS) + 1000, "hijo_mes": hijo_mes, "hijo_anio": 2000 + hijo_mes // 12,
         "hijo_pad": np.arange(N_HIJOS), "primer": np.zeros(n_par, dtype=np.int64), "area": area,
         "lat": np.full(n_par, -38.5), "tasa": tasa, "bloque_5km": np.arange(N_HIJOS) // 2,
         "par_hijo": np.array(ph), "par_padre": np.array(pp),
         "par_km": np.array(km), "par_rumbo": np.array(rumbo), "n_mes": N_MES}
    D["par_real_ok"] = D["primer"][D["par_padre"]] <= hijo_mes[D["par_hijo"]] - placebo.EDAD_MIN
    return D


def truncar(D: dict, U: int) -> dict:
    """Copia de D con datos solo hasta el mes U (el mundo al congelar)."""
    T = dict(D)
    T["tasa"] = D["tasa"].copy()
    T["tasa"][:, placebo.PAD + U + 1:] = np.nan
    T["n_mes"] = U + 1
    return T


def manifest(tmp_path) -> object:
    man = {"produccion_no_convencional": {"sha256": "a" * 64}, "fractura_adjunto_iv": {"sha256": "b" * 64}}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(man), encoding="utf-8")
    return p


def congelada_rapida(D, fecha, p1, man, reps: int = REPS) -> dict:
    cong = prospectiva.congelar(D, fecha, p1, man)
    cong["parametros"]["reps"] = reps
    return cong


def test_efecto_plantado_sostiene(tmp_path):
    D = sintetico(0.23)
    cong = congelada_rapida(truncar(D, 110), FECHA, P1, manifest(tmp_path))
    out = prospectiva.puntuar(D, cong)
    assert out["estado"] == "puntuado"
    assert out["p1"]["n_near"] >= 100 and out["p1"]["bloques"] >= 15
    assert out["p1"]["veredicto"] == "sostiene"
    assert out["p2"]["veredicto"] == "sostiene"


def test_nulo_no_se_sostiene(tmp_path):
    D = sintetico(0.0)
    cong = congelada_rapida(truncar(D, 110), FECHA, P1, manifest(tmp_path))
    out = prospectiva.puntuar(D, cong)
    assert out["p1"]["veredicto"] == "no se sostiene"
    assert "por arriba" in out["p1"]["texto"]


def test_poca_muestra(tmp_path):
    D = sintetico(0.23)
    cong = congelada_rapida(truncar(D, 149), FECHA, P1, manifest(tmp_path))
    out = prospectiva.puntuar(D, cong)
    assert out["p1"]["veredicto"] == "sin muestra"


def test_archivo_manipulado(tmp_path):
    D = sintetico(0.23)
    cong = prospectiva.congelar(truncar(D, 110), FECHA, P1, manifest(tmp_path))
    p = tmp_path / "cong.json"
    sha = prospectiva.escribir_congelada(cong, p)
    assert prospectiva.leer_congelada(p, sha) == cong
    with pytest.raises(FileExistsError):
        prospectiva.escribir_congelada(cong, p)
    with pytest.raises(prospectiva.CongeladaAlterada):
        prospectiva.leer_congelada(p, None)
    raw = bytearray(p.read_bytes())
    raw[10] ^= 1
    p.write_bytes(bytes(raw))
    with pytest.raises(prospectiva.CongeladaAlterada):
        prospectiva.leer_congelada(p, sha)
    p.write_bytes(prospectiva.serializar(cong))
    p.with_name(p.name + ".sha256").write_text("0" * 64 + "  cong.json\n", encoding="utf-8")
    with pytest.raises(prospectiva.CongeladaAlterada):
        prospectiva.leer_congelada(p, sha)
    p.with_name(p.name + ".sha256").unlink()
    with pytest.raises(prospectiva.CongeladaAlterada):
        prospectiva.leer_congelada(p, sha)
    with pytest.raises(prospectiva.CongeladaAlterada):
        prospectiva.leer_congelada(tmp_path / "no_existe.json", sha)


def test_determinismo(tmp_path):
    D = sintetico(0.23)
    man = manifest(tmp_path)
    cong = congelada_rapida(truncar(D, 110), FECHA, P1, man)
    assert prospectiva.puntuar(D, cong) == prospectiva.puntuar(D, cong)
    c1 = prospectiva.congelar(truncar(D, 110), FECHA, P1, man)
    c2 = prospectiva.congelar(truncar(D, 110), FECHA, P1, man)
    assert prospectiva.serializar(c1) == prospectiva.serializar(c2)


def test_puntuar_usa_semilla_y_k_congelados(tmp_path):
    D = sintetico(0.23)
    cong = congelada_rapida(truncar(D, 110), FECHA, P1, manifest(tmp_path))
    out = prospectiva.puntuar(D, cong)
    par = cong["parametros"]
    r1 = prospectiva.medir(D, prospectiva.mes_idx(cong["p1"]["desde"]), cong["p1"]["k"],
                           par["reps"], par["semilla"] + cong["p1"]["k"])
    assert out["p1"]["ic_bajo"] == r1["ic_bajo"] and out["p1"]["ic_alto"] == r1["ic_alto"]
    cong["parametros"]["semilla"] += 7
    otro = prospectiva.puntuar(D, cong)
    assert (otro["p1"]["ic_bajo"], otro["p1"]["ic_alto"]) != (r1["ic_bajo"], r1["ic_alto"])


def test_pendiente(tmp_path):
    D = sintetico(0.23)
    T = truncar(D, 110)
    cong = prospectiva.congelar(T, FECHA, P1, manifest(tmp_path))
    out = prospectiva.puntuar(T, cong)
    assert out == {"estado": "pendiente", "ultimo_mes": prospectiva.mes_iso(110)}


def r(n_near=150, n_ctrl=150, bloques=20, brecha=-0.23, bajo=-0.28, alto=-0.17):
    return {"n_near": n_near, "n_ctrl": n_ctrl, "bloques": bloques, "brecha": brecha, "ic_bajo": bajo, "ic_alto": alto}


def test_veredictos_puros():
    assert prospectiva.veredicto_p1(r(), -0.287, -0.168)[0] == "sostiene"
    v, t = prospectiva.veredicto_p1(r(brecha=-0.02, bajo=-0.04, alto=0.01), -0.287, -0.168)
    assert v == "no se sostiene" and "por arriba" in t
    v, t = prospectiva.veredicto_p1(r(brecha=-0.40, bajo=-0.45, alto=-0.35), -0.287, -0.168)
    assert v == "no se sostiene" and "por abajo" in t
    v, t = prospectiva.veredicto_p1(r(brecha=-0.20, bajo=-0.30, alto=0.05), -0.287, -0.168)
    assert v == "no firme" and "toca" in t
    assert prospectiva.veredicto_p1(r(bajo=np.nan, alto=np.nan), -0.287, -0.168)[0] == "no firme"
    assert prospectiva.veredicto_p1(r(n_near=3), -0.287, -0.168)[0] == "sin muestra"
    assert prospectiva.veredicto_p2(r(brecha=0.02, bajo=-0.03, alto=0.05))[0] == "sostiene"
    assert prospectiva.veredicto_p2(r(brecha=0.10, bajo=0.06, alto=0.14))[0] == "no se sostiene"
    assert prospectiva.veredicto_p2(r(brecha=0.02, bajo=-0.15, alto=0.05))[0] == "no firme"
    assert prospectiva.veredicto_p2(r(bajo=np.nan, alto=np.nan))[0] == "no firme"
    assert prospectiva.mes_idx(prospectiva.mes_iso(110)) == 110
    assert prospectiva.mes_iso(0) == "2000-01-01"


def test_congelada_del_repo_verifica():
    """El archivo congelado del repo coincide con SHA_CONGELADA y su lado .sha256; cualquier cambio rompe este test."""
    c = prospectiva.leer_congelada()
    assert c["ultimo_mes"] == "2026-09-01"
    assert c["p1"]["desde"] == "2026-09-01" and c["p2"]["desde"] == "2026-04-01"


def test_pagina_pendiente_y_puntuada(tmp_path):
    D = sintetico(0.23)
    cong = congelada_rapida(truncar(D, 110), FECHA, P1, manifest(tmp_path))
    pend = prospectiva.pagina(cong, "f" * 64, prospectiva.puntuar(truncar(D, 110), cong))
    assert "**Pendiente.**" in pend
    out = prospectiva.puntuar(D, cong)
    txt = prospectiva.pagina(cong, "f" * 64, out)
    assert "**P1, brecha del mes 1: sostiene.**" in txt and "**P2, cierre al mes 6: sostiene.**" in txt
    assert "Pendiente" not in txt and "f" * 64 in txt
    assert chr(0x2013) not in txt and chr(0x2014) not in txt
