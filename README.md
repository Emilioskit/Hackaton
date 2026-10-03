# Hir.ia

Agente que ayuda a elegir zona para vivir en Donostia según los servicios que hay cerca andando.
Migración a Python de la versión de Langflow (Gipuzkoa AI Hackathon 2026 · Urban Challenge).

## Arrancar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # y pon tu ANTHROPIC_API_KEY
python main.py              # chat en la terminal
pytest                      # tests (no necesitan API key)
```

## Estructura

```
data/
  zonas.csv          105 zonas × distancia (m) a 22 servicios
  categorias.csv     22 servicios: eje, límite, fuente
  necesidades.csv    respuestas del formulario → esenciales, servicios y pesos
hiria/
  datos.py           carga y valida los CSV
  ranking.py         cálculo determinista (sin LLM)
  perfil.py          perfil tipado (sustituye al extractor) + pendientes
  prompts.py         instrucciones del agente
  agente.py          agente Pydantic AI con la herramienta calcular_ranking
tests/               tests del cálculo y del perfil
main.py              chat en la terminal
```

## Qué cambia respecto a Langflow

- Un solo LLM: el perfil es el argumento tipado de la herramienta, así que extraer y calcular va en la misma llamada.
- Sin línea `Perfil:`: el historial de Pydantic AI guarda las llamadas a herramientas.
- Por código, no por prompt: pendientes, `1a` nunca junto a hijos, edades que sustituyen a `hijos_sin_edad`,
  y las decisiones "enviar formulario" / "preguntar edad".
- El cálculo da exactamente el mismo resultado que la v2 de Langflow (comprobado en 16.128 perfiles).
- Se quitó del cierre la oferta de contar qué tiene cerca una zona (no existe `detalle_zona`).
