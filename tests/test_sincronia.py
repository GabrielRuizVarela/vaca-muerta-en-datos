from datetime import date

import numpy as np

from pipeline import sincronia as sc


def _eventos(pendiente_cercano: float, n_pads: int = 120, por_pad: int = 6, semilla: int = 7, nivel: float = 0.8) -> dict:
    """Eventos sinteticos: cada pad hijo tiene un f0 y un grupo de padres cercanos y controles. El indice de un cercano es
    nivel + pendiente_cercano * f0 mas ruido; el de un control es 1 mas ruido."""
    rng = np.random.default_rng(semilla)
    f0_pad = rng.uniform(1 / 31, 1.0, n_pads)
    clave = np.repeat(np.arange(n_pads), por_pad)
    f0 = f0_pad[clave]
    banda = np.tile([0, 0, 2, 2, 2, 2], n_pads)
    ruido = rng.normal(0, 0.1, len(clave))
    y = np.where(banda == 0, nivel + pendiente_cercano * f0, 1.0) + ruido
    return {"y": np.clip(y, *sc.CLIP_INDICE), "banda": banda, "f0": f0, "clave": clave,
            "area": np.where(clave % 2 == 0, "A", "B"), "anio": 2020 + clave % 4}


def test_fraccion_en_los_bordes_del_mes():
    f = sc.fraccion_mes0([date(2026, 1, 1), date(2026, 1, 31), date(2026, 4, 1), date(2026, 4, 30), date(2026, 3, 15)])
    assert np.allclose(f, [1.0, 1 / 31, 1.0, 1 / 30, 17 / 31])


def test_fraccion_usa_los_dias_reales_del_mes():
    # ultimo dia de cada mes: un dia expuesto sobre 28, 29, 30 o 31
    f = sc.fraccion_mes0([date(2025, 2, 28), date(2024, 2, 29), date(2026, 6, 30), date(2026, 7, 31)])
    assert np.allclose(f, [1 / 28, 1 / 29, 1 / 30, 1 / 31])
    # mitad de mes: el dia 15 expone 14 dias en febrero de 28 y 16 dias en un mes de 30
    assert np.isclose(sc.fraccion_mes0([date(2025, 2, 15)])[0], 14 / 28)
    assert np.isclose(sc.fraccion_mes0([date(2026, 6, 15)])[0], 16 / 30)


def test_fraccion_esta_en_el_intervalo_unitario():
    dias = [date(2025, m, d) for m in range(1, 13) for d in (1, 10, 28)]
    f = sc.fraccion_mes0(dias)
    assert f.min() > 0 and f.max() <= 1.0


def test_dosis_en_el_tiempo_da_pendiente_negativa():
    e = _eventos(pendiente_cercano=-0.4)
    p = sc.pendiente_ic(e, 0, reps=80)
    assert -0.6 < p["pendiente"] < -0.2
    assert p["ic_alto"] < sc.UMBRAL_DOSIS
    filas = sc.tabla_grupos(e, 0, reps=60)
    # la brecha se hace mas negativa de un grupo al siguiente
    assert filas[0][4] > filas[1][4] > filas[2][4]
    assert sc.veredicto(p, {"ic_alto": 0.2}, filas) == "sostiene"


def test_efecto_parejo_no_da_pendiente():
    e = _eventos(pendiente_cercano=0.0)
    p = sc.pendiente_ic(e, 0, reps=80)
    assert abs(p["pendiente"]) < 0.15
    assert p["ic_bajo"] <= 0 <= p["ic_alto"]
    assert sc.veredicto(p, {"ic_alto": 0.2}, sc.tabla_grupos(e, 0, reps=60)) == "plana"


def test_pendiente_opuesta():
    e = _eventos(pendiente_cercano=0.5, nivel=0.4)
    p = sc.pendiente_ic(e, 0, reps=80)
    assert p["pendiente"] > 0 and p["ic_bajo"] > 0
    assert sc.veredicto(p, {"ic_alto": 0.2}, sc.tabla_grupos(e, 0, reps=60)) == "opuesta"


def test_pendiente_del_mes_previo_negativa_vuelve_no_firme():
    e = _eventos(pendiente_cercano=-0.4)
    p = sc.pendiente_ic(e, 0, reps=80)
    assert sc.veredicto(p, {"ic_alto": -0.05}, sc.tabla_grupos(e, 0, reps=60)) == "no firme"


def test_grupo_con_pocos_eventos_no_da_veredicto():
    e = _eventos(pendiente_cercano=-0.4, n_pads=6)  # 12 cercanos en total, menos de 30 por grupo
    filas = sc.tabla_grupos(e, 0, reps=20)
    assert any(f[3] < sc.MIN_EVENTOS_GRUPO for f in filas)
    p = {"ic_bajo": -0.5, "ic_alto": -0.3}
    assert sc.veredicto(p, p, filas) == "sin muestra"


def test_terciles_cubren_todos_los_eventos():
    e = _eventos(pendiente_cercano=-0.2)
    g = sc.grupo(e["f0"], sc.cortes(e["f0"]))
    assert set(np.unique(g)) == {1, 2, 3}
    filas = sc.tabla_grupos(e, 0, reps=20)
    assert sum(f[3] + f[7] for f in filas) == len(e["y"])


def test_determinista():
    e = _eventos(pendiente_cercano=-0.3)
    a, b = sc.pendiente_ic(e, 0, reps=50), sc.pendiente_ic(e, 0, reps=50)
    assert a == b
    assert sc.tabla_grupos(e, 0, reps=30) == sc.tabla_grupos(e, 0, reps=30)
