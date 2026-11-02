# ============================================================
# MILY — IRONWORKS HR
# SISTEMA COMERCIAL Y ASISTENTE VIRTUAL
# Versión 4.1 — Corregida y optimizada para google-genai
# ============================================================

import os
import json
import sqlite3
import threading
import requests
from flask import Flask, jsonify, request

# ============================================================
# BLOQUE 1 — CONFIGURACIÓN GENERAL
# ============================================================

MILY_NOMBRE = "Mily"
MILY_VERSION = "4.1"
EMPRESA_NOMBRE = "IRONWORKS HR"
EMPRESA_DESCRIPCION = "Hermanos Rico Diseño y Estructura"

HOST = "0.0.0.0"
PUERTO = int(os.environ.get("PORT", 5000))

app = Flask(__name__)

# ============================================================
# INFORMACIÓN OFICIAL — NO SE INVENTA
# ============================================================

SEDES = {
    "bosa": "Cl. 61A Sur #87B-36, Bosa, Bogotá, Cundinamarca",
    "fontibon": "Cl. 17A #102-33, Local 1, Fontibón, Bogotá, Cundinamarca",
}

CONTACTOS_PUBLICOS = {
    "alexa": {
        "nombre": "Alexa",
        "telefono": "+57 323 960 3473",
        "whatsapp": "3239603473",
    },
    "andres": {
        "nombre": "Andrés",
        "telefono": "+57 322 457 9894",
        "whatsapp": "3224579894",
    },
}

ENLACES_OFICIALES = {
    "facebook": "https://www.facebook.com/profile.php?id=61591255868048&rdid=8HYcG90i2o1409yk",
    "instagram": "https://www.instagram.com/industriasrico_s/?hl=es",
    "pinterest": "https://co.pinterest.com/industriasricos/_profile/",
    "tiktok": "https://www.tiktok.com/@ironworkshrs",
}

CATALOGO_CANVA_PUBLICO = os.environ.get("CATALOGO_CANVA_PUBLICO", "")

TELEGRAM_MAESTRO_ANDRES = os.environ.get("TELEGRAM_MAESTRO_ANDRES", "")
TELEGRAM_ALEXA = os.environ.get("TELEGRAM_ALEXA", "")

# ============================================================
# RUTAS BÁSICAS
# ============================================================

@app.route("/", methods=["GET"])
def inicio():
    return jsonify({
        "status": "online",
        "sistema": MILY_NOMBRE,
        "version": MILY_VERSION,
        "empresa": EMPRESA_NOMBRE,
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "health": "ok",
        "mily": MILY_NOMBRE,
        "version": MILY_VERSION,
    })


# ============================================================
# BLOQUE 2 — CREDENCIALES Y CONEXIONES
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ironworks_mily_token_2026")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    if TELEGRAM_BOT_TOKEN else None
)

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
DRIVE_FOLDER_ID = os.environ.get(
    "GOOGLE_FOLDER_ID",
    "1qWEAo8wv7bWTXWX272SsQVVZpgtkLjbe",
)

# Cliente Gemini (Nuevo SDK)
CLIENTE_GEMINI = None

if GEMINI_API_KEY:
    try:
        from google import genai
        CLIENTE_GEMINI = genai.Client(api_key=GEMINI_API_KEY)
        print("✔ [Bloque 2] Conexión con Gemini inicializada.")
    except Exception as e:
        print(f"✖ [Bloque 2] Error inicializando Gemini: {e}")
else:
    print("⚠ [Bloque 2] Falta GEMINI_API_KEY.")

# ============================================================
# BLOQUE 3 — GOOGLE DRIVE / FUENTES DE VERDAD
# ============================================================

try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
except Exception as e:
    build = None
    service_account = None
    print(f"⚠ [Bloque 3] Librerías de Google Drive no disponibles: {e}")


def _cargar_credenciales_google():
    if not GOOGLE_SERVICE_ACCOUNT_JSON or not service_account:
        return None
    try:
        if os.path.exists(GOOGLE_SERVICE_ACCOUNT_JSON):
            return service_account.Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_JSON,
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )
        info_cred = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        return service_account.Credentials.from_service_account_info(
            info_cred,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
    except Exception as e:
        print(f"✖ [Bloque 3] Error leyendo credenciales de Google: {e}")
        return None


def obtener_servicio_drive():
    credenciales = _cargar_credenciales_google()
    if not credenciales or not build:
        return None
    try:
        return build("drive", "v3", credentials=credenciales, cache_discovery=False)
    except Exception as e:
        print(f"✖ [Bloque 3] Error conectando Google Drive: {e}")
        return None


def obtener_contexto_archivos_drive():
    servicio = obtener_servicio_drive()
    if not servicio:
        return "FUENTE DRIVE: no disponible en este momento. No inventes precios ni fichas técnicas."
    try:
        query = f"'{DRIVE_FOLDER_ID}' in parents and trashed = false"
        resultados = servicio.files().list(
            q=query,
            pageSize=100,
            orderBy="name",
            fields="files(id,name,mimeType,webViewLink)",
        ).execute()
        archivos = resultados.get("files", [])
        if not archivos:
            return "FUENTE DRIVE: no se encontraron archivos en la carpeta oficial."

        lineas = []
        for archivo in archivos:
            nombre = archivo.get("name", "Sin nombre")
            mime = archivo.get("mimeType", "")
            link = archivo.get("webViewLink", "")
            if link:
                lineas.append(f"- {nombre} | tipo: {mime} | enlace: {link}")
            else:
                lineas.append(f"- {nombre} | tipo: {mime}")
        return "ARCHIVOS OFICIALES REGISTRADOS EN GOOGLE DRIVE:\n" + "\n".join(lineas)
    except Exception as e:
        print(f"⚠ [Bloque 3] Error consultando Google Drive: {e}")
        return "FUENTE DRIVE: error temporal."


# ============================================================
# BLOQUE 4 — MEMORIA UNIFICADA (SQLite)
# ============================================================

DATA_DIR = os.environ.get("MILY_DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.environ.get(
    "MILY_DB_PATH",
    os.path.join(DATA_DIR, "mily_memory.db"),
)

LIMITE_HISTORIAL = 30
DB_LOCK = threading.RLock()


def obtener_conexion_db():
    conexion = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA journal_mode=WAL")
    return conexion


def inicializar_memoria():
    with DB_LOCK:
        conexion = obtener_conexion_db()
        try:
            conexion.execute("""
                CREATE TABLE IF NOT EXISTS mensajes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conexion.execute("""
                CREATE TABLE IF NOT EXISTS perfiles (
                    user_id TEXT PRIMARY KEY,
                    nombre TEXT,
                    telefono TEXT,
                    ultima_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conexion.commit()
        finally:
            conexion.close()
    print(f"✔ [Bloque 4] Memoria SQLite activa en: {DB_PATH}")


def guardar_mensaje(user_id, role, text):
    if not text:
        return
    with DB_LOCK:
        conexion = obtener_conexion_db()
        try:
            conexion.execute(
                "INSERT INTO mensajes (user_id, role, text) VALUES (?, ?, ?)",
                (str(user_id), role, str(text)),
            )
            conexion.execute("""
                DELETE FROM mensajes
                WHERE user_id = ?
                  AND id NOT IN (
                      SELECT id FROM mensajes
                      WHERE user_id = ?
                      ORDER BY id DESC
                      LIMIT ?
                  )
            """, (str(user_id), str(user_id), LIMITE_HISTORIAL))
            conexion.commit()
        finally:
            conexion.close()


def obtener_historial(user_id):
    from google.genai import types

    with DB_LOCK:
        conexion = obtener_conexion_db()
        try:
            filas = conexion.execute("""
                SELECT role, text
                FROM mensajes
                WHERE user_id = ?
                ORDER BY id ASC
                LIMIT ?
            """, (str(user_id), LIMITE_HISTORIAL)).fetchall()
        finally:
            conexion.close()

    historial = []

    for fila in filas:
        rol = "user" if fila["role"] == "user" else "model"

        historial.append(
            types.Content(
                role=rol,
                parts=[
                    types.Part.from_text(text=fila["text"])
                ]
            )
        )

    return historial


def guardar_nombre_si_aparece(user_id, mensaje):
    if not mensaje:
        return
    import re
    patrones = [
        r"\bme llamo\s+([A-Za-zÁÉÍÓÚáéíóúÑñÜü]{2,40})",
        r"\bsoy\s+([A-Za-zÁÉÍÓÚáéíóúÑñÜü]{2,40})",
        r"\bmi nombre es\s+([A-Za-zÁÉÍÓÚáéíóúÑñÜü]{2,40})",
        r"\ble habla\s+([A-Za-zÁÉÍÓÚáéíóúÑñÜü]{2,40})",
    ]
    nombre = None
    for patron in patrones:
        coincidencia = re.search(patron, mensaje, flags=re.IGNORECASE)
        if coincidencia:
            nombre = coincidencia.group(1).strip()
            break

    if not nombre:
        return

    with DB_LOCK:
        conexion = obtener_conexion_db()
        try:
            conexion.execute("""
                INSERT INTO perfiles(user_id, nombre)
                VALUES (?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET nombre=excluded.nombre,
                              ultima_actualizacion=CURRENT_TIMESTAMP
            """, (str(user_id), nombre))
            conexion.commit()
        finally:
            conexion.close()


def obtener_perfil(user_id):
    with DB_LOCK:
        conexion = obtener_conexion_db()
        try:
            fila = conexion.execute(
                "SELECT nombre, telefono FROM perfiles WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
        finally:
            conexion.close()
    if not fila:
        return {}
    return {"nombre": fila["nombre"], "telefono": fila["telefono"]}


inicializar_memoria()

# ============================================================
# BLOQUE 5 — PROMPT OFICIAL DE MILY
# ============================================================

MODELO_GEMINI = os.environ.get("MODELO_GEMINI", "gemini-2.5-flash")

def construir_system_instruction(contexto_drive):
    return f"""
Eres Mily, la asesora comercial virtual de {EMPRESA_NOMBRE}, {EMPRESA_DESCRIPCION}.
- Ciudad principal: Bogotá, Colombia. Fabricación bajo pedido.
- No inventes productos, precios, medidas, materiales ni tiempos de entrega.

FUENTES OFICIALES:
{contexto_drive}

SEDES:
- Bosa: 
{SEDES["bosa"]}
- Fontibón: 
{SEDES["fontibon"]}

CONTACTOS:
- Alexa: 
{CONTACTOS_PUBLICOS["alexa"]["telefono"]}
- Andrés: 
{CONTACTOS_PUBLICOS["andres"]["telefono"]}

REGLAS:
1. Mantén continuidad si ya hay historial.
2. Si el cliente ya dio su nombre, úsalo y no lo vuelvas a pedir.
3. Para diseños especiales, recopila datos (medidas, cantidad, fotos) y escala con Andrés.
4. Tono profesional, cálido y comercial.
"""

def construir_perfil_contexto(user_id):
    perfil = obtener_perfil(user_id)
    if not perfil:
        return "No hay datos de perfil guardados todavía."
    datos = []
    if perfil.get("nombre"):
        datos.append(f"- Nombre conocido: {perfil['nombre']}")
    return "\n".join(datos)

# ============================================================
# BLOQUE 6 — GENERACIÓN DE RESPUESTA
# ============================================================

def generar_respuesta_mily(user_id, mensaje_usuario, imagen_bytes=None):
    if not CLIENTE_GEMINI:
        return "En este momento tengo un problema temporal de conexión. Por favor intenta nuevamente."

    user_id = str(user_id)

    try:
        if mensaje_usuario:
            guardar_nombre_si_aparece(user_id, mensaje_usuario)

        historial = obtener_historial(user_id)
        contexto_drive = obtener_contexto_archivos_drive()
        perfil = construir_perfil_contexto(user_id)

        system_instruction = construir_system_instruction(contexto_drive) + f"\n\nPERFIL DEL CLIENTE:\n{perfil}"

        from google.genai import types

        contenidos = list(historial)
        partes_actuales = []

        if mensaje_usuario:
            partes_actuales.append(
                types.Part.from_text(text=mensaje_usuario)
            )

        if imagen_bytes:
            partes_actuales.append(
                types.Part.from_bytes(
                    data=imagen_bytes,
                    mime_type="image/jpeg"
                )
            )

        if partes_actuales:
            contenidos.append(
                types.Content(
                    role="user",
                    parts=partes_actuales
                )
            )

        if not contenidos:
            return "Hola. Soy Mily, asesora comercial de IRONWORKS HR. ¿En qué proyecto te puedo ayudar?"

        response = CLIENTE_GEMINI.models.generate_content(
            model=MODELO_GEMINI,
            contents=contenidos,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            ),
        )

        respuesta_texto = (response.text or "").strip()
        if not respuesta_texto:
            respuesta_texto = "Quiero ayudarte con tu proyecto. Cuéntame qué producto necesitas y las medidas aproximadas."

        # Guardar en base de datos
        if mensaje_usuario:
            guardar_mensaje(user_id, "user", mensaje_usuario)
        if imagen_bytes:
            guardar_mensaje(user_id, "user", "[El cliente envió una imagen de referencia.]")
        
        guardar_mensaje(user_id, "model", respuesta_texto)

        # Alerta a Telegram si es cotización formal o diseño especial
        if any(w in respuesta_texto.lower() for w in ["cotización formal", "diseño a medida", "proyecto especial"]):
            if TELEGRAM_MAESTRO_ANDRES:
                alerta = f"🔔 [Mily - Aviso al Taller]\nCliente ID: {user_id}\nMensaje: {mensaje_usuario or '[imagen]'}\nRespuesta: {respuesta_texto[:300]}"
                enviar_mensaje_telegram(TELEGRAM_MAESTRO_ANDRES, alerta)

        return respuesta_texto

    except Exception as e:
        print(f"❌ [Bloque 6] Error detallado en Gemini: {e}")
        return "Recibí tu mensaje. Para darte un valor exacto o una especificación técnica correcta, prefiero revisarlo directamente con el taller. Ya te atendemos."


# ============================================================
# BLOQUE 7, 8, 9, 10 Y ARRANQUE (Se mantienen estables)
# ============================================================

def enviar_mensaje_whatsapp(numero_destino, texto_respuesta):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        return False
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": numero_destino, "type": "text", "text": {"body": texto_respuesta}}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        return response.ok
    except Exception as e:
        print(f"❌ [WhatsApp] Excepción: {e}")
        return False


def enviar_mensaje_telegram(chat_id, texto_respuesta):
    if not TELEGRAM_API_URL:
        return False
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto_respuesta}
    try:
        response = requests.post(url, json=payload, timeout=20)
        return response.ok
    except Exception as e:
        print(f"❌ [Telegram] Excepción: {e}")
        return False


@app.route("/webhook/whatsapp", methods=["GET", "POST"])
def webhook_whatsapp_meta():
    if request.method == "GET":
        hub_mode = request.args.get("hub.mode")
        hub_verify_token = request.args.get("hub.verify_token")
        hub_challenge = request.args.get("hub.challenge")
        if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
            return hub_challenge, 200
        return "Token inválido", 403

    data = request.get_json(silent=True) or {}
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                for msg_obj in change.get("value", {}).get("messages", []):
                    numero_remitente = msg_obj.get("from")
                    if not numero_remitente:
                        continue
                    
                    mensaje, imagen_bytes = "", None
                    if msg_obj.get("type") == "text":
                        mensaje = msg_obj.get("text", {}).get("body", "")
                    elif msg_obj.get("type") == "image":
                        mensaje = msg_obj.get("image", {}).get("caption", "Imagen de referencia.")
                        image_id = msg_obj.get("image", {}).get("id")
                        if image_id:
                            imagen_bytes = descargar_imagen_whatsapp(image_id)

                    if not mensaje and not imagen_bytes:
                        continue

                    respuesta = generar_respuesta_mily(numero_remitente, mensaje, imagen_bytes)
                    enviar_mensaje_whatsapp(numero_remitente, respuesta)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"❌ [WhatsApp] Error: {e}")
        return jsonify({"status": "error"}), 200


def descargar_imagen_whatsapp(media_id):
    if not WHATSAPP_TOKEN or not media_id:
        return None
    try:
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        info_res = requests.get(f"https://graph.facebook.com/v18.0/{media_id}", headers=headers, timeout=20)
        if not info_res.ok: return None
        media_url = info_res.json().get("url")
        if not media_url: return None
        media_res = requests.get(media_url, headers=headers, timeout=30)
        return media_res.content if media_res.ok else None
    except Exception:
        return None


@app.route("/webhook/telegram", methods=["POST"])
def webhook_telegram():
    data = request.get_json(silent=True) or {}
    try:
        message_data = data.get("message")
        if not message_data: return jsonify({"status": "ok"}), 200
        chat_id = message_data.get("chat", {}).get("id")
        if not chat_id: return jsonify({"status": "ok"}), 200
        
        mensaje = message_data.get("text", message_data.get("caption", ""))
        imagen_bytes = None
        if message_data.get("photo"):
            imagen_bytes = descargar_imagen_telegram(message_data["photo"][-1].get("file_id"))

        if not mensaje and not imagen_bytes: return jsonify({"status": "ok"}), 200

        respuesta = generar_respuesta_mily(str(chat_id), mensaje, imagen_bytes)
        enviar_mensaje_telegram(chat_id, respuesta)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ [Telegram] Error: {e}")
        return jsonify({"status": "ok"}), 200


def descargar_imagen_telegram(file_id):
    if not TELEGRAM_API_URL or not TELEGRAM_BOT_TOKEN or not file_id: return None
    try:
        info_res = requests.get(f"{TELEGRAM_API_URL}/getFile", params={"file_id": file_id}, timeout=20)
        if not info_res.ok: return None
        file_path = info_res.json().get("result", {}).get("file_path")
        if not file_path: return None
        img_res = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}", timeout=30)
        return img_res.content if img_res.ok else None
    except Exception:
        return None


@app.route("/debug/memory/<path:user_id>", methods=["GET"])
def debug_memory(user_id):
    return jsonify({
        "user_id": user_id,
        "mensajes": obtener_historial(user_id),
        "perfil": obtener_perfil(user_id),
    })


if __name__ == "__main__":
    print(f"=== {MILY_NOMBRE} {MILY_VERSION} INICIANDO ===")
    app.run(host=HOST, port=PUERTO, debug=False)