"""
Backend del Tablero — Ruta de Emprendimientos de Base (Comuna 6, Cartagena)
============================================================================
Versión Flask para desplegar en Render (plan Web Service Free).

  1. Sirve el tablero (index.html) y sus archivos (logos, etc.) en "/".
  2. /api/datos   → lee la hoja "Agregados" del Google Sheet y la reenvía.
  3. /api/lectura → arma el resumen y pide a Groq la interpretación.

La clave de Groq NUNCA va en el código: se lee de las variables de entorno.
En Render se configura en:  Environment → Add Environment Variable
    GROQ_API_KEY = tu_clave_gsk_...
    GROQ_MODELO  = openai/gpt-oss-120b

Render asigna el puerto por la variable PORT (este código ya la lee).
Comandos de despliegue en Render:
    Build:  pip install -r requirements.txt
    Start:  python app.py
"""

import os
import json
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
import urllib.request

# .env es opcional (solo local); en Render no hace falta
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__, static_folder=".", static_url_path="")

# ----------------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------------
SHEET_CSV_URL = os.getenv(
    "SHEET_CSV_URL",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNF5FC6bM-aPr9iJ5WnV04EPTNUNQ_uHpW6rZGOUUTT22gw2jQG_e-i88nlQQzejFsQKUbWLYtqj1s/pub?gid=793554120&single=true&output=csv",
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODELO = os.getenv("GROQ_MODELO", "openai/gpt-oss-120b")
PORT = int(os.getenv("PORT", "8000"))  # Render inyecta PORT automáticamente


# ---- RUTA 1: servir el tablero ---------------------------------------------
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


# ---- RUTA 2: proxy del Google Sheet ----------------------------------------
@app.route("/api/datos")
def api_datos():
    try:
        with urllib.request.urlopen(SHEET_CSV_URL, timeout=15) as resp:
            csv_text = resp.read().decode("utf-8")
        return app.response_class(csv_text, mimetype="text/csv")
    except Exception as e:
        return jsonify({"error": f"No se pudo leer la hoja: {e}"}), 502


# ---- RUTA 3: interpretación con Groq ---------------------------------------
@app.route("/api/lectura", methods=["POST"])
def api_lectura():
    if not GROQ_API_KEY:
        return jsonify({"error": "Falta GROQ_API_KEY en las variables de entorno."}), 500

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
    print(f"Tablero corriendo en el puerto {PORT}")
    print(f"Groq {'configurado ✓' if GROQ_API_KEY else 'SIN clave (configura la variable de entorno) ✗'}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
