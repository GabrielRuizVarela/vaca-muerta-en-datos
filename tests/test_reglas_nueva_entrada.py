"""scripts/reglas_nueva_entrada.py reproduce las entradas de docs/reglas-fijadas.md byte por byte.

Las cinco entradas de la aceptación cubren los cuatro modos: sin regla (94580fd), con el tope de 60 líneas y 3 archivos
(39c7dfe), completa (06f7720, b1479a8) y los cinco archivos de pipeline/ (857d434). El historial de trabajo no está en la
copia pública, así que cada prueba se salta si falta un commit (git cat-file -e).
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import reglas_nueva_entrada as rne  # noqa: E402

ARCHIVO = REPO / "docs" / "reglas-fijadas.md"
# sha, opciones que la entrada del archivo necesita (el archivo dice cuáles en su encabezado)
CINCO = [
    ("94580fd", {}),
    ("39c7dfe", {}),
    ("06f7720", {"completa": True}),
    ("857d434", {"completa": True, "todos": True}),
    ("b1479a8", {"completa": True}),
]


def _esta(sha):
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
            cwd=REPO,
            capture_output=True,
        ).returncode
        == 0
    )


def _entrada_del_archivo(sha):
    _, entradas, _ = rne.partir(ARCHIVO.read_text(encoding="utf-8"))
    (e,) = [e for e in entradas if rne.sha_de(e) == sha]
    return e.rstrip("\n") + "\n"


@pytest.mark.parametrize(("sha", "opciones"), CINCO)
def test_la_entrada_sale_igual_que_en_el_archivo(sha, opciones):
    if not _esta(sha):
        pytest.skip(f"{sha} no está en este clon")
    _, texto = rne.armar_entrada(sha, **opciones)
    assert texto.rstrip("\n") + "\n" == _entrada_del_archivo(sha)


def test_sin_opciones_las_reglas_largas_se_cortan():
    if not _esta("06f7720"):
        pytest.skip("06f7720 no está en este clon")
    _, corta = rne.armar_entrada("06f7720")
    _, completa = rne.armar_entrada("06f7720", completa=True)
    assert "(primeras 60 de 164 líneas)" in corta
    assert "primeras" not in completa
    assert len(corta) < len(completa)


def test_recontar_imprime_la_cuenta_del_encabezado():
    if not all(_esta(s) for s, _ in CINCO):
        pytest.skip("falta el historial de trabajo")
    salida = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "reglas_nueva_entrada.py"),
            "--recontar",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    nums = tuple(int(n) for n in re.findall(r"\d+", salida))
    en_el_encabezado = re.search(
        rne.ENCABEZADO_CUENTA, ARCHIVO.read_text(encoding="utf-8")
    )
    assert nums == tuple(int(g) for g in en_el_encabezado.groups()) == (46, 36, 10)


def test_insertar_pone_la_entrada_en_su_lugar_y_no_toca_el_resto():
    texto = ARCHIVO.read_text(encoding="utf-8")
    pre, entradas, cola = rne.partir(texto)
    medio = len(entradas) // 2
    quitada = entradas[medio]
    sin = pre + "".join(entradas[:medio] + entradas[medio + 1 :]) + cola
    vuelta = rne.insertar(sin, rne.fecha_de(quitada), quitada.rstrip("\n") + "\n")
    assert vuelta == texto
    with pytest.raises(SystemExit):
        rne.insertar(texto, rne.fecha_de(quitada), quitada)


def test_insertar_al_final_queda_antes_de_la_seccion_de_uso():
    texto = ARCHIVO.read_text(encoding="utf-8")
    pre, entradas, cola = rne.partir(texto)
    assert cola.startswith("## Cómo agregar una entrada")
    nueva = "## `abcdef0` · 2999-01-01 00:00 UTC\n\n**Asunto:** x\n"
    res = rne.insertar(texto, "2999-01-01 00:00", nueva)
    assert res == pre + "".join(entradas) + nueva + "\n" + cola


def test_la_frase_de_la_cuenta_se_reescribe_sin_tocar_las_notas_a_mano():
    texto = ARCHIVO.read_text(encoding="utf-8")
    cambiado = rne.ENCABEZADO_CUENTA.sub(rne.frase_cuenta(1, 1, 0), texto, count=1)
    assert cambiado.count("**Nota agregada a mano") == texto.count(
        "**Nota agregada a mano"
    )
    assert "(1 commits; 1 se citan" in cambiado


def test_fija_regla_por_el_asunto():
    assert rne.fija_regla("Ronda 4: regla fijada antes de calcular")
    assert rne.fija_regla("Aclaración de la regla")
    assert not rne.fija_regla("Merge pull request #92 from x/y")


def _repo_chico(tmp_path, monkeypatch, archivos):
    """Un repositorio de prueba con un commit raíz que agrega ``archivos`` ({ruta: texto}); ``rne.git`` apunta a él."""
    for ruta, texto in archivos.items():
        (tmp_path / ruta).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / ruta).write_text(texto, encoding="utf-8")
    ident = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    for cmd in (["init", "-q"], ["add", "-A"], [*ident, "commit", "-q", "-m", "x"]):
        subprocess.run(["git", *cmd], cwd=tmp_path, check=True, capture_output=True)
    real = rne.git
    monkeypatch.setattr(rne, "git", lambda *a, raiz=tmp_path, check=True: real(*a, raiz=tmp_path))
    return rne.git("rev-parse", "HEAD").strip()


def test_una_linea_agregada_que_empieza_con_mas_mas_no_se_pierde(tmp_path, monkeypatch):
    sha = _repo_chico(tmp_path, monkeypatch, {"a.md": "uno\n++ x\n+++ y\n"})
    assert rne.lineas_agregadas(sha, "a.md") == ["uno", "++ x", "+++ y"]


def test_una_linea_con_salto_de_pagina_o_separador_unicode_no_se_parte(tmp_path, monkeypatch):
    sha = _repo_chico(tmp_path, monkeypatch, {"a.md": "uno\x0cdos\u2028tres\n"})
    assert rne.lineas_agregadas(sha, "a.md") == ["uno\x0cdos\u2028tres"]


def test_el_arbol_vacio_es_el_de_git():
    real = subprocess.run(
        ["git", "hash-object", "-t", "tree", "/dev/null"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert rne.ARBOL_VACIO == real


def test_los_internos_no_se_listan_ni_se_copian(tmp_path, monkeypatch):
    sha = _repo_chico(tmp_path, monkeypatch, {"AGENTS.md": "regla\n", "docs/orquestacion/x.md": "y\n", "a.md": "z\n"})
    todos = ["AGENTS.md", "REVIEW.md", "a.md", "docs/orquestacion/x.md"]
    assert rne.archivos_publicables(todos, tmp_path) == ["a.md"]
    copiado = rne.textos_agregados(sha, todos, completa=True, todos=False, raiz=tmp_path)
    assert [ruta for ruta, _ in copiado] == ["a.md"]


def test_una_ruta_absoluta_no_cuenta_el_archivo_como_citante_de_si_mismo(tmp_path, monkeypatch):
    _repo_chico(tmp_path, monkeypatch, {"reglas.md": "cita abcdef0\n"})
    for archivo in ("reglas.md", "./reglas.md", str(tmp_path / "reglas.md")):
        assert rne.citados_fuera(["abcdef0"], archivo, tmp_path) == set(), archivo
    assert rne.citados_fuera(["abcdef0"], "otro.md", tmp_path) == {"abcdef0"}
