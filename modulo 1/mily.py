
# ============================================================
# MILY — IRONWORKS HRs
# SISTEMA COMERCIAL Y ASISTENTE VIRTUAL
# ============================================================

# ============================================================
# BLOQUE 1 — CONFIGURACIÓN GENERAL
# ============================================================

import os
import requests
from flask import Flask, jsonify, request

MILY_NOMBRE = "Mily"
MILY_VERSION = "3.2"
EMPRESA_NOMBRE = "IRONWORKS HR"
EMPRESA_DESCRIPCION = "Hermanos Rico Diseño y Estructura"

HOST = "0.0.0.0"
PUERTO = int(os.environ.get("PORT", 5000))

app = Flask(__name__)

@app.route("/", methods=["GET"])
def inicio():
    return jsonify({
        "status": "online",
        "sistema": MILY_NOMBRE,
        "version": MILY_VERSION,
        "empresa": EMPRESA_NOMBRE
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "health": "ok",
        "mily": MILY_NOMBRE,
        "version": MILY_VERSION
    })


# ============================================================
# BLOQUE 2 — CREDENCIALES Y CONEXIONES
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CLIENTE_GEMINI = None

if GEMINI_API_KEY:
    try:
        from google import genai
        CLIENTE_GEMINI = genai.Client(api_key=GEMINI_API_KEY)
        print("✔ [Bloque 2] Conexión con Gemini inicializada correctamente.")
    except Exception as e:
        print(f"✖ [Bloque 2] Error al inicializar el cliente de Gemini: {e}")
else:
    print("⚠ [Bloque 2] Advertencia: No se encontró GEMINI_API_KEY en las variables de entorno.")

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ironworks_mily_token_2026")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None

GOOGLE_FOLDER_ID = os.environ.get("GOOGLE_FOLDER_ID", "14CWV4pxiOfNhpsQ7unNORpK3h9f7xSeU")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

ADMINES_AUTORIZADOS = [
    admin.strip() 
    for admin in os.environ.get("ADMINES_AUTORIZADOS", "").split(",") 
    if admin.strip()
]

# ------------------------------------------------------------
# CHAT IDs DE TELEGRAM PARA LOS MAESTROS / TALLER
# ------------------------------------------------------------
TELEGRAM_MAESTRO_ANDRES = os.environ.get("TELEGRAM_MAESTRO_ANDRES", "")
TELEGRAM_ALEXA = os.environ.get("TELEGRAM_ALEXA", "")


# ============================================================
# BLOQUE 4 — CATÁLOGO Y FUENTES DE VERDAD (GOOGLE DRIVE)
# ============================================================

import io
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

def obtener_servicio_drive():
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        print("⚠ [Bloque 4] Advertencia: No se encontró GOOGLE_SERVICE_ACCOUNT_JSON en el entorno.")
        return None
    
    try:
        if os.path.exists(GOOGLE_SERVICE_ACCOUNT_JSON):
            credenciales = service_account.Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_JSON,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
        else:
            info_cred = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
            credenciales = service_account.Credentials.from_service_account_info(
                info_cred,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
        servicio = build('drive', 'v3', credentials=credenciales)
        print("✓ [Bloque 4] Conexión con Google Drive inicializada correctamente.")
        return servicio
    except Exception as e:
        print(f"✖ [Bloque 4] Error al conectar con Google Drive: {e}")
        return None

DRIVE_FOLDER_ID = "1qWEAo8wv7bWTXWX272SsQVVZpgtkLjbe"

def obtener_contexto_archivos_drive():
    servicio = obtener_servicio_drive()
    if not servicio:
        return "No hay conexión con Google Drive en este momento."
        
    try:
        query = f"'{DRIVE_FOLDER_ID}' in parents and trashed = false"
        resultados = servicio.files().list(
            q=query,
            pageSize=50,
            fields="files(id, name, mimeType)"
        ).execute()
        
        archivos = resultados.get('files', [])
        if not archivos:
            return "No se encontraron archivos en la carpeta de inventario."
            
        lista_nombres = [f"- {archivo['name']}" for archivo in archivos]
        contexto = "FOTOS Y FICHAS TÉCNICAS OFICIALES REGISTRADAS EN GOOGLE DRIVE:\n" + "\n".join(lista_nombres)
        print(f"✓ [Bloque 4] Se cargaron {len(archivos)} referencias de fotos y fichas de Google Drive para Mily.")
        return contexto
    except Exception as e:
        print(f"❌ [Bloque 4] Error al listar archivos de la subcarpeta: {e}")
        return "Error al recuperar las referencias de Google Drive."



# ============================================================
# BLOQUE 5 y 6 — MEMORIA PERSISTENTE Y MODELO GEMINI
# ============================================================

from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
MODELO_GEMINI = "gemini-2.5-flash"

# Diccionario global robusto para almacenar el historial de mensajes por usuario
HISTORIALES_CONVERSACION = {}
LIMITE_HISTORIAL = 12  # Mantiene los últimos mensajes para no perder el hilo

def generar_respuesta_mily(user_id, mensaje_usuario, imagen_bytes=None, contexto_drive=""):
    if not client:
        return "Lo siento, en este momento tengo un problema temporal de configuración con mi inteligencia artificial."

    try:
        contexto_drive_actual = obtener_contexto_archivos_drive()

        system_instruction = f"""
Eres Mily, la asesora comercial experta de IRONWORKS HRs, un taller especializado en herrería pesada, alta forja artística, portones, rejas, separadores y mobiliario minimalista dirigido por los hermanos Rico.

{contexto_drive_actual}

=== REGLAS DE ORO DE IDENTIDAD Y MEMORIA (ESTRICTAS) ===
1. **Cero redundancias y Cero amnesias:** Ya conoces al cliente si su nombre ya apareció antes en la conversación. NUNCA vuelvas a decir "Soy Mily, la asesora..." si ya lo dijiste en los mensajes anteriores. Salúdalo por su nombre directamente (ej: "¡Hola, Óscar!"). 
2. **Respuestas cortas y conversacionales:** No mandes Testamentos ni bloques de texto largos. Responde de forma natural, directa y humana, como un chat real de WhatsApp o Telegram. Ve paso a paso.
3. **Memoria absoluta del hilo:** Recuerda lo que hablaron en los mensajes anteriores (nombre, tipo de producto, medidas, ubicación). No vuelvas a preguntar lo que ya te dijeron.

=== PROTOCOLO DE VISIÓN Y FOTOS ===
- Si envían una foto de producto estándar, indícale su código, precio base y medida estándar.
- Si piden medidas personalizadas o diseños especiales, recaba los datos y dile que le avisarás al Maestro Andrés de inmediato.

=== FILOSOFÍA DE FABRICACIÓN Y PAGOS ===
- Todo se fabrica bajo pedido. 
- Pago contra entrega (sin anticipos).
"""

        # Inicializar historial del usuario si no existe
        if user_id not in HISTORIALES_CONVERSACION:
            HISTORIALES_CONVERSACION[user_id] = []

        # Agregar el mensaje actual del usuario al historial
        if mensaje_usuario:
            HISTORIALES_CONVERSACION[user_id].append({"role": "user", "parts": [mensaje_usuario]})
        elif imagen_bytes:
            HISTORIALES_CONVERSACION[user_id].append({
                "role": "user", 
                "parts": [
                    "Te envío esta referencia visual de mi proyecto en hierro:",
                    types.Part.from_bytes(data=imagen_bytes, mime_type="image/jpeg")
                ]
            })

        # Limitar el historial para que no crezca infinitamente
        if len(HISTORIALES_CONVERSACION[user_id]) > LIMITE_HISTORIAL:
            HISTORIALES_CONVERSACION[user_id] = HISTORIALES_CONVERSACION[user_id][-LIMITE_HISTORIAL:]

        # Construir el contenido completo con el historial para enviárselo a Gemini
        response = client.models.generate_content(
            model=MODELO_GEMINI,
            contents=HISTORIALES_CONVERSACION[user_id],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            )
        )

        respuesta_texto = response.text

        # Guardar la respuesta de Mily en el historial del usuario para mantener la memoria
        HISTORIALES_CONVERSACION[user_id].append({"role": "model", "parts": [respuesta_texto]})

        # Detector de avisos al taller por Telegram
        if any(palabra in respuesta_texto.lower() for palabra in ["maestro andrés", "le avisaré", "revisar el caso", "cotización formal", "con el maestro"]):
            if TELEGRAM_MAESTRO_ANDRES:
                alerta_taller = f"🔔 [Mily - Aviso al Taller]\nUn cliente (ID: {user_id}) requiere atención personalizada.\nÚltimo mensaje: '{mensaje_usuario}'\nMily respondió: '{respuesta_texto[:200]}...'"
                enviar_mensaje_telegram(TELEGRAM_MAESTRO_ANDRES, alerta_taller)

        return respuesta_texto

    except Exception as e:
        print(f"❌ [Bloque 6] Error generando respuesta con Mily: {e}")
        return "¡Hola! Entiendo tu solicitud. Por favor dime las medidas aproximadas de tu proyecto para ayudarte."
        

# ============================================================
# BLOQUE 7 — ENVÍO DE MENSAJES (WHATSAPP Y TELEGRAM)
# ============================================================

def enviar_mensaje_whatsapp(numero_destino, texto_respuesta):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("⚠ [Bloque 7] Faltan credenciales de WhatsApp.")
        return

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto_respuesta}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"✅ [WhatsApp] Mensaje enviado a {numero_destino}")
        else:
            print(f"❌ [WhatsApp] Error: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ [Bloque 7] Excepción en WhatsApp: {e}")


def enviar_mensaje_telegram(chat_id, texto_respuesta):
    if not TELEGRAM_API_URL:
        print("⚠ [Bloque 7] Falta TELEGRAM_TOKEN.")
        return
    
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto_respuesta,
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"✅ [Telegram] Mensaje enviado a {chat_id}")
        else:
            print(f"❌ [Telegram] Error: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ [Bloque 7] Excepción en Telegram: {e}")


# ============================================================
# BLOQUE 8 — WEBHOOK DE WHATSAPP
# ============================================================

@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def webhook_whatsapp_meta():
    if request.method == 'GET':
        hub_mode = request.args.get('hub.mode')
        hub_verify_token = request.args.get('hub.verify_token')
        hub_challenge = request.args.get('hub.challenge')
        
        if hub_mode == 'subscribe' and hub_verify_token == VERIFY_TOKEN:
            print("✅ [Bloque 8] Webhook de Meta verificado correctamente.")
            return hub_challenge, 200
        return "Token de verificación inválido", 403

    if request.method == 'POST':
        data = request.get_json()
        try:
            if 'entry' in data and 'changes' in data['entry'][0]:
                mensaje_data = data['entry'][0]['changes'][0]['value']
                if 'messages' in mensaje_data:
                    msg_obj = mensaje_data['messages']
                    numero_remitente = msg_obj['from']
                    
                    mensaje = ""
                    imagen_bytes = None
                    
                    if 'text' in msg_obj:
                        mensaje = msg_obj['text']['body']
                    elif 'image' in msg_obj:
                        mensaje = msg_obj.get('caption', "Te envío esta imagen de referencia")
                    
                    print(f"📩 [WhatsApp] Mensaje recibido de {numero_remitente}: {mensaje}")
                    respuesta_ia = generar_respuesta_mily(numero_remitente, mensaje, imagen_bytes)
                    enviar_mensaje_whatsapp(numero_remitente, respuesta_ia)
        except Exception as e:
            print(f"❌ [Bloque 8] Error procesando mensaje de WhatsApp: {e}")
            
        return jsonify({"status": "success"}), 200


# ============================================================
# BLOQUE 9 — WEBHOOK DE TELEGRAM Y RUTA ALTERNATIVA
# ============================================================

@app.route('/webhook/telegram', methods=['POST'])
def webhook_telegram():
    data = request.get_json()
    try:
        if "message" in data:
            message_data = data["message"]
            chat_id = message_data["chat"]["id"]
            mensaje = message_data.get("text", message_data.get("caption", ""))
            
            imagen_bytes = None
            if "photo" in message_data:
                try:
                    file_id = message_data["photo"][-1]["file_id"]
                    file_info_url = f"{TELEGRAM_API_URL}/getFile?file_id={file_id}"
                    file_info_res = requests.get(file_info_url).json()
                    if file_info_res.get("ok"):
                        file_path = file_info_res["result"]["file_path"]
                        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                        img_res = requests.get(download_url)
                        if img_res.status_code == 200:
                            imagen_bytes = img_res.content
                except Exception as img_err:
                    print(f"⚠ [Telegram] No se pudo descargar la foto adjunta: {img_err}")

            if mensaje or imagen_bytes:
                print(f"📩 [Telegram] Mensaje recibido de {chat_id}: {mensaje or '[Foto sin texto]'}")
                respuesta_ia = generar_respuesta_mily(str(chat_id), mensaje, imagen_bytes)
                enviar_mensaje_telegram(chat_id, respuesta_ia)
                
    except Exception as e:
        print(f"❌ [Bloque 9 - Telegram] Error: {e}")
        
    return jsonify({"status": "ok"}), 200


# ============================================================
# ARRANQUE DEL SERVIDOR
# ============================================================

if __name__ == "__main__":
    print("==============================================")
    print(f"{MILY_NOMBRE} {MILY_VERSION}")
    print(f"Empresa: {EMPRESA_NOMBRE}")
    print("Servidor iniciando...")
    print("==============================================")

    app.run(
        host=HOST,
        port=PUERTO,
        debug=True
    )