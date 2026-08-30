# Tablero Comuna 6 — Cómo ponerlo a funcionar con la IA

Este tablero ahora usa un pequeño backend (`app.py`) que hace dos cosas:
lee el Google Sheet y genera la lectura de IA con Groq (la clave queda protegida).

## Archivos
- `index.html` — el tablero.
- `app.py` — el backend.
- `requirements.txt` — dependencias.
- `.env.example` — plantilla para tu clave (crea tu propio `.env`).
- Los 7 logos `.png`.

## Pasos (en la terminal de Cursor, dentro de la carpeta del proyecto)

**1. Instala las dependencias (una sola vez):**
```
pip3 install -r requirements.txt
```

**2. Crea tu archivo de clave.**
Copia la plantilla y edítala:
```
cp .env.example .env
```
Abre `.env` en Cursor y reemplaza `pega_aqui_tu_clave_de_groq` por tu clave real
de Groq (empieza por `gsk_...`). Guarda.

**3. Detén el servidor de Python anterior** si lo tienes corriendo (Ctrl + C),
y levanta el backend:
```
python3 app.py
```
Verás: `Tablero corriendo en http://localhost:8000` y si Groq quedó configurado.

**4. Abre en el navegador:**
```
http://localhost:8000
```

## Cómo probar la IA ahora mismo
La lectura se genera sola a las 6:00 a. m. y 12:00 m., pero para probarla en
cualquier momento hay un botón **"Generar ahora"** en el panel de Artemis.

## Notas
- El archivo `.env` NO debe compartirse ni subirse a repositorios públicos.
- Si cambias la hoja publicada, actualiza `SHEET_CSV_URL` en `.env` (o en `app.py`).
- Este backend es también la base para el despliegue con enlace público.
