"""Carga de las tablas de datos (data/*.csv). Se leen una sola vez."""
import csv
from functools import cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Nombres que se muestran al usuario en castellano
NOMBRE_ZONA_ES = {
    "Parte Zaharra": "Parte Vieja",
    "Gune Erromantikoa": "Área Romántica",
}
NOMBRE_BARRIO_ES = {
    "ANTIGUA": "Antiguo",
    "ERDIALDEA": "Centro",
    "AMARABERRI": "Amara Berri",
    "MIRAKRUZ - BIDEBIETA": "Miracruz - Bidebieta",
}


def _leer(nombre):
    with open(DATA / nombre, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _validar(zonas, cat, nec):
    columnas = set(zonas[0])
    for s in cat:
        if f"dist_{s}_m" not in columnas:
            raise ValueError(f"zonas.csv no tiene la columna dist_{s}_m")
    for z in zonas:
        if any(v in ("", None) for v in z.values()):
            raise ValueError(f"Zona con datos vacíos: {z.get('zona_es')}")
    if "base" not in nec:
        raise ValueError("necesidades.csv necesita la fila 'base'")
    for cod, fila in nec.items():
        for campo in ("esenciales", "servicios_nota"):
            for s in filter(None, fila[campo].split(";")):
                if s.strip() not in cat:
                    raise ValueError(f"necesidades.csv ({cod}): servicio desconocido '{s}'")


@cache
def cargar():
    """Devuelve (zonas, categorias, necesidades). Se cachea tras la primera llamada."""
    zonas = _leer("zonas.csv")
    cat = {r["servicio"]: r for r in _leer("categorias.csv")}
    nec = {r["codigo"]: r for r in _leer("necesidades.csv")}
    _validar(zonas, cat, nec)
    return zonas, cat, nec
