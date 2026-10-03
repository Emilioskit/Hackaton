"""Cálculo determinista del ranking de zonas. Sin LLM: misma entrada, misma salida.

Comportamiento idéntico a la versión v2 de Langflow (3 oct 2026). Diferencias solo de forma:
- los datos se leen de data/*.csv;
- acepta el perfil como dict (o Perfil) y los campos q1/q5 como lista o como texto "1b,1c";
- devuelve un dict en vez de un string JSON.
"""
from .datos import NOMBRE_BARRIO_ES, NOMBRE_ZONA_ES, cargar

DIST_BASE_M = 300
TOLERANCIA = 1.10
EMPATE_PTS = 3
TOP_N = 3
SIN_VALOR = {"", "sin_dato", "no_responde", "ninguno", None}
CAMPOS_PERFIL = ("q1_quien", "q2_movilidad", "q3_ocupacion", "q4_mascota", "q5_valora")


# ---------- utilidades ----------

def _lista(txt):
    return [x.strip() for x in str(txt).split(";") if x.strip()]


def _pesos(txt):
    return {k: float(v) for k, v in (p.split(":") for p in _lista(txt))}


def _clip(x):
    return max(0.0, min(1.0, x))


def _media(v):
    return sum(v) / len(v)


def _a_lista(v):
    """Acepta lista o texto separado por comas; quita los valores vacíos."""
    if isinstance(v, (list, tuple)):
        items = v
    elif v in SIN_VALOR:
        return []
    else:
        items = str(v).split(",")
    return [str(c).strip() for c in items if str(c).strip() not in SIN_VALOR]


def tramo(d):
    """Distancia en palabras (lo usa el agente tal cual)."""
    if d <= 100:
        return "prácticamente en la puerta"
    if d <= 300:
        return "a menos de 4 minutos andando"
    if d <= 600:
        return "a menos de 8 minutos andando"
    if d <= 1200:
        return "a menos de 15 minutos andando"
    return "a más de 15 minutos andando"


# ---------- perfil -> parámetros ----------

def _codigos(perfil):
    cods = []
    for campo in CAMPOS_PERFIL:
        cods += _a_lista(perfil.get(campo))
    return list(dict.fromkeys(cods))


def _parametros(perfil, cat, nec):
    cods = [c for c in _codigos(perfil) if c in nec]  # hijos_sin_edad no está en nec: se ignora
    base = nec["base"]
    esenciales = _lista(base["esenciales"])
    extra_serv, sobrescribe, informativo = [], {}, False
    for c in cods:
        fila = nec[c]
        esenciales += _lista(fila["esenciales"])
        extra_serv += _lista(fila["servicios_nota"])
        for eje, v in _pesos(fila["pesos"]).items():
            sobrescribe[eje] = max(sobrescribe.get(eje, 0), v)
        informativo = informativo or bool(fila["esenciales"] or fila["servicios_nota"] or fila["pesos"])
    esenciales = list(dict.fromkeys(esenciales))

    universales = [s for s, r in cat.items() if r["universal"] == "1"]
    if informativo:
        servicios = list(dict.fromkeys(_lista(base["esenciales"]) + esenciales + extra_serv))
    else:
        servicios = list(dict.fromkeys(universales + esenciales))

    pesos = {**_pesos(base["pesos"]), **sobrescribe}
    ejes = sorted({cat[s]["eje"] for s in servicios})
    piso = _pesos(base["pesos"])["salud"]
    crudos = {e: pesos.get(e, piso) for e in ejes}
    tot = sum(crudos.values())
    pesos_pct = {e: 100 * v / tot for e, v in crudos.items()}

    try:
        d_usuario = int(float(perfil.get("distancia_m") or 0))
    except (TypeError, ValueError):
        d_usuario = 0
    D = d_usuario if d_usuario > 0 else DIST_BASE_M

    avisos = []
    if d_usuario > DIST_BASE_M and ({"1e", "3d"} & set(cods)):
        avisos.append(f"Pediste {d_usuario} m; para una persona mayor el estándar de proximidad es {DIST_BASE_M} m.")
    if "5e" in cods:
        avisos.append("No hay datos de ruido: la tranquilidad no se puede medir.")
    if perfil.get("q3_destino") not in SIN_VALOR:
        avisos.append("El lugar de trabajo o estudio se tiene en cuenta en una versión futura; ahora no puntúa.")
    fuera = _a_lista(perfil.get("fuera_de_datos"))
    if fuera:
        avisos.append(f"Sin datos para: {', '.join(fuera)}.")

    return dict(codigos=cods, esenciales=esenciales, servicios=servicios, pesos=pesos_pct, D=D,
                distancia_origen="la que pediste" if d_usuario > 0 else "estándar (300 m para lo cotidiano)",
                avisos=avisos)


# ---------- puntuación ----------

def _limite(cat, s, D):
    return float(cat[s]["limite_m"]) * D / DIST_BASE_M


def _evaluar(fila, p, cat):
    por_eje, faltan, por_poco, servicios, prox = {}, [], [], [], []
    for s in p["servicios"]:
        d = float(fila[f"dist_{s}_m"])
        L = _limite(cat, s, p["D"])
        sc = _clip((1.5 * L - d) / L)          # 1 a L/2 o menos, 0,5 en L, 0 a 1,5·L
        por_eje.setdefault(cat[s]["eje"], []).append(sc)
        prox.append(0.5 ** (d / L))             # solo para desempatar
        esencial = s in p["esenciales"]
        if esencial and d > L * TOLERANCIA:
            faltan.append(s)
        elif esencial and d > L:
            por_poco.append(s)
        servicios.append({"servicio": cat[s]["nombre_es"], "dist_m": int(d),
                          "limite_m": int(round(L)), "esencial": esencial})
    ejes = {e: _media(v) for e, v in por_eje.items()}
    nota = sum(p["pesos"][e] * v for e, v in ejes.items())
    return dict(nota=round(nota, 1), prox=_media(prox), faltan=faltan, por_poco=por_poco,
                ejes={e: round(100 * v) for e, v in ejes.items()}, servicios=servicios)


def _salida_zona(fila, ev, cat, p):
    nombre = {s: cat[s]["nombre_es"] for s in cat}
    fuertes = sorted([x for x in ev["servicios"] if x["dist_m"] <= x["limite_m"] / 2],
                     key=lambda x: x["dist_m"] / x["limite_m"])[:2]
    debiles = sorted([x for x in ev["servicios"] if x["dist_m"] > x["limite_m"] / 2],
                     key=lambda x: -x["dist_m"] / x["limite_m"])[:2]
    fmt = lambda x: f'{x["servicio"]}: {tramo(x["dist_m"])} ({x["dist_m"]} m)'
    return {
        "zona": NOMBRE_ZONA_ES.get(fila["zona_es"], fila["zona_es"]),
        "barrio": NOMBRE_BARRIO_ES.get(fila["barrio"], str(fila["barrio"]).title()),
        "nota": round(ev["nota"]),
        "cumple_esenciales": not ev["faltan"],
        "faltan": [{"servicio": nombre[s], "dist_m": int(float(fila[f"dist_{s}_m"])),
                    "limite_m": int(round(_limite(cat, s, p["D"])))} for s in ev["faltan"]],
        "por_poco": [nombre[s] for s in ev["por_poco"]],
        "nota_por_eje": ev["ejes"],
        "mas_cerca": [fmt(x) for x in fuertes],
        "mas_lejos": [fmt(x) for x in debiles],
        "lo_que_necesitas": [fmt(x) for x in ev["servicios"] if x["esencial"]],
    }


# ---------- punto de entrada ----------

def ranking_zonas(perfil, incluir_rurales=False):
    """perfil: dict (o Perfil de pydantic) con los campos del formulario. Devuelve un dict."""
    if hasattr(perfil, "model_dump"):
        perfil = perfil.model_dump()
    zonas, cat, nec = cargar()
    p = _parametros(perfil, cat, nec)
    z = zonas if incluir_rurales else [r for r in zonas if r["rural"] == "0"]
    evals = [(fila, _evaluar(fila, p, cat)) for fila in z]
    pasan = [x for x in evals if not x[1]["faltan"]]
    plan_b = len(pasan) < TOP_N
    if plan_b:
        orden = sorted(evals, key=lambda x: (len(x[1]["faltan"]), -x[1]["nota"], -x[1]["prox"]))
    else:
        orden = sorted(pasan, key=lambda x: (-round(x[1]["nota"]), -x[1]["prox"]))
    top = orden[:TOP_N]
    mejor = top[0][1]["nota"]
    empatadas = [f["zona_es"] for f, ev in orden if mejor - ev["nota"] <= EMPATE_PTS]
    nombre = {s: cat[s]["nombre_es"] for s in cat}
    return {
        "perfil_aplicado": {
            "codigos": p["codigos"],
            "esenciales": [nombre[s] for s in p["esenciales"]],
            "pesos_pct": {e: round(v) for e, v in sorted(p["pesos"].items(), key=lambda x: -x[1])},
            "distancia_cotidiana_m": p["D"],
            "distancia_origen": p["distancia_origen"],
        },
        "zonas_evaluadas": len(evals),
        "zonas_que_cumplen": len(pasan),
        "plan_b": plan_b,
        "ranking": [dict(posicion=i + 1, **_salida_zona(f, ev, cat, p)) for i, (f, ev) in enumerate(top)],
        "n_empatadas_con_la_primera": len(empatadas) if len(empatadas) > 1 else 0,
        "empatadas_con_la_primera": empatadas[:8] if len(empatadas) > 1 else [],
        "avisos": p["avisos"],
        "criterio": ("Filtro: todos los esenciales dentro de su límite (+10 % de tolerancia). "
                     "Nota 0-100: cada servicio vale 1 a la mitad del límite o más cerca, 0,5 en el límite y 0 a 1,5 veces; "
                     "media por eje; ejes ponderados según el perfil. Diferencias de 3 puntos o menos = empate."),
        "limites": ["Distancias en línea recta (mediana desde los puntos habitados de la zona), no a pie por calle.",
                    "Solo cuenta si el servicio existe cerca, no su calidad, horario ni precio.",
                    "Sin datos de ruido, precio de vivienda ni seguridad."],
    }
