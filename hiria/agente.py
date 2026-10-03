"""Agente Hir.ia: un solo LLM + una herramienta determinista.

El perfil es el argumento tipado de la herramienta, así que extraer el perfil y decidir
calcular ocurre en la misma llamada. El historial (con las llamadas a herramientas) es la memoria.
"""
import os

from pydantic_ai import Agent

from .perfil import Perfil, pendientes
from .prompts import INSTRUCCIONES
from .ranking import ranking_zonas

MODELO = os.getenv("HIRIA_MODELO", "anthropic:claude-sonnet-5-5")

agente = Agent(
    MODELO,
    instructions=INSTRUCCIONES,
    model_settings={"temperature": 0},
    defer_model_check=True,  # no exige la API key hasta la primera llamada (útil en tests)
    retries=2,  # si el LLM manda un código no permitido, se le devuelve el error y reintenta
)


@agente.tool_plain
def calcular_ranking(perfil: Perfil) -> dict:
    """Calcula las 3 mejores zonas de Donostia para el perfil.

    Llámala cada vez que el usuario dé datos de su vida, corrija algo o plantee un "¿y si...?".
    Pasa siempre el perfil completo (lo anterior + lo nuevo). Lee el campo "estado" del resultado.
    """
    falta = pendientes(perfil)

    if not perfil.pide_resultados_ya:
        if perfil.q1_quien == ["sin_dato"] and perfil.q2_movilidad == "sin_dato":
            return {"estado": "pedir_formulario", "pendientes": falta}
        if "hijos_sin_edad" in perfil.q1_quien:
            return {"estado": "preguntar_edad_hijos", "pendientes": falta}

    resultado = ranking_zonas(perfil)
    if "hijos_sin_edad" in perfil.q1_quien:
        resultado["avisos"].append("No sé la edad de los hijos: calculo sin colegios ni parque infantil.")
    return {"estado": "ok", "pendientes": [q for q in falta if q != "q1" or "hijos_sin_edad" not in perfil.q1_quien],
            **resultado}
