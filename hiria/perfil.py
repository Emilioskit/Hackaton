"""Perfil del usuario. Sustituye a la 'Salida estructurada' del extractor de Langflow.

El LLM rellena este modelo como argumento de la herramienta, así que solo puede usar
los códigos permitidos. Lo que antes calculaba el modelo (pendientes) ahora se calcula aquí.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SinDato = Literal["sin_dato", "no_responde"]
Q1 = Literal["1a", "1b", "1c", "1d", "1e", "hijos_sin_edad", "sin_dato", "no_responde"]
Q5 = Literal["5a", "5b", "5c", "5d", "5e", "sin_dato", "no_responde"]


class Perfil(BaseModel):
    q1_quien: list[Q1] = Field(
        default=["sin_dato"],
        description=("Con quién vivirá. 1a solo o en pareja (solo si no aplica otro código; compañeros de piso = 1a), "
                     "1b hijos 0-5, 1c hijos 6-12, 1d hijos 13-18, 1e persona mayor. Un código por tramo de edad. "
                     "hijos_sin_edad si tiene hijos y no se sabe la edad. Hijos de 18 o más = adultos."),
    )
    q2_movilidad: Literal["2a", "2b", "2c"] | SinDato = Field(
        default="sin_dato", description="Medio habitual: 2a a pie y transporte público, 2b bici, 2c coche.")
    q3_ocupacion: Literal["3a", "3b", "3c", "3d", "3e"] | SinDato = Field(
        default="sin_dato", description="3a estudio, 3b trabajo fuera de casa, 3c teletrabajo, 3d jubilado/a, 3e otro.")
    q3_destino: str = Field(
        default="sin_dato", description="Lugar al que va a diario si lo nombra (p. ej. TECNUN). No puntúa en v1.")
    q4_mascota: Literal["4a", "4b"] | SinDato = Field(default="sin_dato", description="4a sí, 4b no.")
    q5_valora: list[Q5] = Field(
        default=["sin_dato"], max_length=2,
        description="Hasta 2: 5a vida social y ocio, 5b deporte, 5c playa, 5d cultura, 5e tranquilidad.",
    )
    distancia_m: int = Field(default=0, ge=0, description="Metros máximos que pide (80 m por minuto). 0 si no lo dice.")
    pide_resultados_ya: bool = Field(
        default=False, description="True SOLO si rechaza contestar más preguntas ('dime ya'). Pedir una recomendación no cuenta.")
    fuera_de_datos: list[str] = Field(
        default_factory=list, description="Lo que pide y no se puede medir: ruido, precio, alquiler, seguridad, horarios, plazas...")

    @field_validator("q1_quien")
    @classmethod
    def _limpiar_q1(cls, v):
        """Reglas del extractor que ahora se aplican por código, no por prompt."""
        v = list(dict.fromkeys(v))
        reales = [c for c in v if c not in ("sin_dato", "no_responde")]
        if not reales:
            return v[:1] or ["sin_dato"]
        if any(c in reales for c in ("1b", "1c", "1d")):
            reales = [c for c in reales if c != "hijos_sin_edad"]   # ya hay edades
        if len(reales) > 1:
            reales = [c for c in reales if c != "1a"]               # 1a nunca junto a otros
        return reales

    @field_validator("q5_valora")
    @classmethod
    def _limpiar_q5(cls, v):
        v = list(dict.fromkeys(v))
        reales = [c for c in v if c not in ("sin_dato", "no_responde")]
        return reales or v[:1] or ["sin_dato"]


def pendientes(p: Perfil) -> list[str]:
    """Preguntas sin responder (antes lo calculaba el LLM y falló una vez)."""
    falta = []
    if p.q1_quien == ["sin_dato"] or "hijos_sin_edad" in p.q1_quien:
        falta.append("q1")
    for q, v in (("q2", p.q2_movilidad), ("q3", p.q3_ocupacion), ("q4", p.q4_mascota)):
        if v == "sin_dato":
            falta.append(q)
    if p.q5_valora == ["sin_dato"]:
        falta.append("q5")
    return falta
