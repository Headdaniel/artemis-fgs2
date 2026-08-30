"""
Backend del Tablero — Ruta de Emprendimientos de Base (Comuna 6, Cartagena)
============================================================================
Qué hace:
  1. Sirve el tablero (index.html) y sus archivos (logos, etc.).
  2. Expone /api/datos: lee la hoja "Agregados" del Google Sheet y la reenvía
     al tablero (evita cualquier bloqueo del navegador al leer Google directamente).
  3. Expone /api/lectura: arma un resumen agregado y pide a Groq la interpretación
     en lenguaje natural. La clave de Groq vive en .env y NUNCA llega al navegador.

Cómo correrlo (ver también el README):
  1. pip install -r requirements.txt
  2. crea un archivo .env con tu clave (ver .env.example)
  3. python app.py
  4. abre http://localhost:8000
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

# carga las variables del archivo .env (GROQ_API_KEY, etc.)
load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")

# ----------------------------------------------------------------------------
# CONFIGURACIÓN (se puede sobreescribir desde .env)
# ----------------------------------------------------------------------------
SHEET_CSV_URL = os.getenv(
    "SHEET_CSV_URL",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNF5FC6bM-aPr9iJ5WnV04EPTNUNQ_uHpW6rZGOUUTT22gw2jQG_e-i88nlQQzejFsQKUbWLYtqj1s/pub?gid=793554120&single=true&output=csv",
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELO = os.getenv("GROQ_MODELO", "openai/gpt-oss-120b")
PORT = int(os.getenv("PORT", "8000"))


# ----------------------------------------------------------------------------
# RUTA 1: servir el tablero
# ----------------------------------------------------------------------------
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


# ----------------------------------------------------------------------------
# RUTA 2: proxy del Google Sheet (el tablero pide aquí en vez de a Google)
# ----------------------------------------------------------------------------
@app.route("/api/datos")
def api_datos():
    try:
        with urllib.request.urlopen(SHEET_CSV_URL, timeout=15) as resp:
            csv_text = resp.read().decode("utf-8")
        return app.response_class(csv_text, mimetype="text/csv")
    except Exception as e:
        return jsonify({"error": f"No se pudo leer la hoja: {e}"}), 502


# ----------------------------------------------------------------------------
# RUTA 3: interpretación con Groq (clave protegida en el servidor)
# El tablero envía el resumen agregado ya calculado; aquí solo se reenvía a Groq.
# ----------------------------------------------------------------------------
@app.route("/api/lectura", methods=["POST"])
def api_lectura():
    if not GROQ_API_KEY:
        return jsonify({"error": "Falta GROQ_API_KEY en el archivo .env del servidor."}), 500

    datos = request.get_json(force=True, silent=True) or {}
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
        # Usamos la librería oficial de Groq (evita el bloqueo 1010 de Cloudflare que
        # ocurre al llamar el endpoint con urllib crudo).
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
        return jsonify({
            "texto": texto or "El modelo no devolvió texto.",
            "generado": datetime.now().isoformat(timespec="minutes"),
        })
    except Exception as e:
        print("\n===== ERROR DE GROQ =====")
        print("Detalle:", repr(e))
        print("Modelo usado:", GROQ_MODELO)
        print("=========================\n")
        return jsonify({"error": f"No se pudo generar la lectura: {e}"}), 502


if __name__ == "__main__":
    print(f"Tablero corriendo en http://localhost:{PORT}")
    print(f"Groq {'configurado ✓' if GROQ_API_KEY else 'SIN clave (configura .env) ✗'}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
