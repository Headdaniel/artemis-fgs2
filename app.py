"""
Backend del Tablero — Ruta de Emprendimientos de Base (Comuna 6, Cartagena)
============================================================================
Versión para Hugging Face Spaces con SDK **Gradio** (gratis).

Mantiene EXACTAMENTE la misma lógica que la versión Flask:
  1. Sirve el tablero (index.html) y sus archivos (logos, etc.) en "/".
  2. /api/datos  → lee la hoja "Agregados" del Google Sheet y la reenvía.
  3. /api/lectura → arma el resumen y pide a Groq la interpretación.

La diferencia es sólo el "envoltorio": en vez de Flask, usamos FastAPI y
montamos una app Gradio mínima encima, porque HF Spaces gratis corre Gradio.
Tu index.html NO cambia: sigue llamando a /api/datos y /api/lectura.

La clave de Groq NUNCA va en el código: se lee de las variables de entorno.
En HF Spaces se configura en  Settings → Variables and secrets → New secret:
    GROQ_API_KEY = tu_clave_gsk_...
    (opcional) GROQ_MODELO = openai/gpt-oss-120b
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, FileResponse

# ----------------------------------------------------------------------------
# CONFIGURACIÓN (se lee de variables de entorno; en local puede usar .env)
# ----------------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # opcional en local; en HF no hace falta
    load_dotenv()
except Exception:
    pass

SHEET_CSV_URL = os.getenv(
    "SHEET_CSV_URL",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNF5FC6bM-aPr9iJ5WnV04EPTNUNQ_uHpW6rZGOUUTT22gw2jQG_e-i88nlQQzejFsQKUbWLYtqj1s/pub?gid=793554120&single=true&output=csv",
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODELO = os.getenv("GROQ_MODELO", "openai/gpt-oss-120b")
PORT = int(os.getenv("PORT", "7860"))

BASE_DIR = Path(__file__).parent.resolve()

# ----------------------------------------------------------------------------
# App FastAPI (es la que realmente sirve el tablero y las rutas /api/*)
# ----------------------------------------------------------------------------
app = FastAPI()


# ---- RUTA 2: proxy del Google Sheet ----------------------------------------
@app.get("/api/datos")
def api_datos():
    try:
        with urllib.request.urlopen(SHEET_CSV_URL, timeout=15) as resp:
            csv_text = resp.read().decode("utf-8")
        return Response(content=csv_text, media_type="text/csv")
    except Exception as e:
        return JSONResponse({"error": f"No se pudo leer la hoja: {e}"}, status_code=502)


# ---- RUTA 3: interpretación con Groq ---------------------------------------
@app.post("/api/lectura")
async def api_lectura(request: Request):
    if not GROQ_API_KEY:
        return JSONResponse(
            {"error": "Falta GROQ_API_KEY en las variables/secrets del Space."},
            status_code=500,
        )

    try:
        datos = await request.json()
    except Exception:
        datos = {}
    resumen = datos.get("resumen", {})
    saludo = datos.get("saludo", "Hola, equipo")

    sistema = (
        "Eres Artemis, el analista de datos que acompaña esta evaluación de impacto de la Ruta de "
        "Emprendimientos de Base en la Comuna 6 de Cartagena. Te diriges con calidez a los gestores de la "
        "Fundación Grupo Social y la Fundación Santo Domingo. Escribe un RESUMEN breve (máx. 6 líneas), "
        "amigable y motivador, en español, que comience con el saludo indicado. Reconoce el avance, señala "
        "con tono positivo dónde conviene reforzar, menciona si el ritmo acerca a la meta, y cierra con un "
        "aliento. Usa frases cortas. No inventes datos fuera del resumen."
    )
    usuario = (
        f'Saludo a usar: "{saludo}".\n'
        f"Datos actuales del tablero:\n{json.dumps(resumen, ensure_ascii=False, indent=2)}"
    )

    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=GROQ_MODELO,
            temperature=0.6,
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
        )
        texto = completion.choices[0].message.content
        return JSONResponse({
            "texto": texto or "El modelo no devolvió texto.",
            "generado": datetime.now().isoformat(timespec="minutes"),
        })
    except Exception as e:
        print("\n===== ERROR DE GROQ =====")
        print("Detalle:", repr(e))
        print("Modelo usado:", GROQ_MODELO)
        print("=========================\n")
        return JSONResponse({"error": f"No se pudo generar la lectura: {e}"}, status_code=502)


# ---- RUTA 1: servir el tablero y sus archivos (logos, etc.) ----------------
# Servimos index.html en "/" y cualquier archivo (PNG de logos) por su nombre.
@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/{filename}")
def archivo(filename: str):
    # sólo sirve archivos que existan en la carpeta del proyecto (logos, etc.)
    f = (BASE_DIR / filename).resolve()
    if f.is_file() and str(f).startswith(str(BASE_DIR)):
        return FileResponse(f)
    return JSONResponse({"error": "no encontrado"}, status_code=404)


# ----------------------------------------------------------------------------
# Gradio: HF Spaces (SDK Gradio) necesita una app Gradio presente.
# Montamos una app Gradio mínima e invisible en /_panel; el tablero real vive en "/".
# ----------------------------------------------------------------------------
with gr.Blocks() as panel:
    gr.Markdown("Servicio del tablero activo. Abre la raíz del sitio para verlo.")

app = gr.mount_gradio_app(app, panel, path="/_panel")


# ----------------------------------------------------------------------------
# Arranque
# ----------------------------------------------------------------------------
# En Hugging Face Spaces (SDK Gradio) NO se debe llamar a uvicorn.run():
# la plataforma detecta la variable `app` y la sirve automáticamente en el
# puerto 7860. Arrancarla aquí de nuevo choca el puerto ("address already in use").
#
# Para correr en LOCAL, usa este comando en la terminal (no ejecutes este archivo
# directamente con `python app.py` en local si quieres el mismo comportamiento):
#     uvicorn app:app --host 0.0.0.0 --port 7860
#
# Dejamos el print informativo, pero sin arrancar el servidor a mano.
print(f"App lista. Groq {'configurado ✓' if GROQ_API_KEY else 'SIN clave ✗'}")
