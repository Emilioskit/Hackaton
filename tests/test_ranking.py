"""Tests del cálculo. Fijan el comportamiento actual (v2 de Langflow, 3 oct 2026).
Si cambias la puntuación a propósito, actualiza los valores esperados aquí."""
from hiria.ranking import ranking_zonas

FAMILIA = dict(q1_quien=["1c"], q2_movilidad="2a", q3_ocupacion="3b", q4_mascota="4b", q5_valora=["5c"])


def test_ejemplo_documentado_familia_6_12():
    r = ranking_zonas(FAMILIA)
    assert r["zonas_evaluadas"] == 103
    assert r["zonas_que_cumplen"] == 21
    assert [(z["zona"], z["nota"]) for z in r["ranking"]] == [("Matia", 100), ("Atotxa", 99), ("Amarazarra", 99)]
    assert r["empatadas_con_la_primera"] == ["Matia", "Atotxa", "Amarazarra", "Aldakoenea"]
    assert r["perfil_aplicado"]["pesos_pct"] == {"movilidad": 31, "educacion": 21, "verde": 19,
                                                  "deporte": 13, "compra": 10, "salud": 6}


def test_texto_y_lista_dan_lo_mismo():
    assert ranking_zonas(dict(FAMILIA, q1_quien="1b,1e")) == ranking_zonas(dict(FAMILIA, q1_quien=["1b", "1e"]))


def test_determinista():
    assert ranking_zonas(FAMILIA) == ranking_zonas(FAMILIA)


def test_sin_perfil_usa_servicios_universales():
    r = ranking_zonas({})
    assert r["perfil_aplicado"]["esenciales"] == [
        "Supermercado o tienda de alimentación", "Farmacia", "Parada de bus", "Parque o zona verde"]


def test_distancia_muy_corta_activa_plan_b():
    r = ranking_zonas(dict(FAMILIA, distancia_m=100))
    assert r["plan_b"] is True
    assert len(r["ranking"]) == 3


def test_rurales_excluidas_por_defecto():
    assert ranking_zonas({}, incluir_rurales=True)["zonas_evaluadas"] == 105
