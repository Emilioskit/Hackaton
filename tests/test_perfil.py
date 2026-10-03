from hiria.agente import calcular_ranking
from hiria.perfil import Perfil, pendientes


def test_1a_nunca_junto_a_hijos():
    assert Perfil(q1_quien=["1a", "1c"]).q1_quien == ["1c"]


def test_edades_sustituyen_a_hijos_sin_edad():
    assert Perfil(q1_quien=["hijos_sin_edad", "1b", "1c"]).q1_quien == ["1b", "1c"]


def test_pendientes_se_calculan_por_codigo():
    p = Perfil(q1_quien=["1a"], q2_movilidad="2a", q4_mascota="4a")
    assert pendientes(p) == ["q3", "q5"]
    assert "q1" in pendientes(Perfil(q1_quien=["hijos_sin_edad"]))


def test_no_responde_no_es_pendiente():
    assert "q3" not in pendientes(Perfil(q3_ocupacion="no_responde"))


def test_herramienta_pide_formulario_sin_datos_basicos():
    assert calcular_ranking(Perfil())["estado"] == "pedir_formulario"


def test_herramienta_pregunta_edad_de_hijos():
    assert calcular_ranking(Perfil(q1_quien=["hijos_sin_edad"], q2_movilidad="2a"))["estado"] == "preguntar_edad_hijos"


def test_dime_ya_calcula_aunque_falte_la_edad():
    r = calcular_ranking(Perfil(q1_quien=["hijos_sin_edad"], pide_resultados_ya=True))
    assert r["estado"] == "ok" and "q1" not in r["pendientes"]


def test_herramienta_ok():
    r = calcular_ranking(Perfil(q1_quien=["1c"], q2_movilidad="2a", q3_ocupacion="3b", q4_mascota="4b", q5_valora=["5c"]))
    assert r["estado"] == "ok" and r["pendientes"] == [] and r["zonas_que_cumplen"] == 21
