# ============================================================
# MILY — IRONWORKS HR
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
# BLOQUE 5 — MEMORIA Y GESTIÓN DE CONVERSACIONES
# ============================================================

HISTORIALES_CONVERSACION = {}
LIMITE_HISTORIAL = 10

def obtener_historial_usuario(user_id):
    if user_id not in HISTORIALES_CONVERSACION:
        HISTORIALES_CONVERSACION[user_id] = []
    return HISTORIALES_CONVERSACION[user_id]


# ============================================================
# BLOQUE 6 — CONFIGURACIÓN DEL MODELO GEMINI Y PROMPT DE MILY
# ============================================================

from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
MODELO_GEMINI = "gemini-2.5-flash"

sesiones_chat = {}

def generar_respuesta_mily(user_id, mensaje_usuario, imagen_bytes=None, contexto_drive=""):
    if not client:
        return "Lo siento, en este momento tengo un problema temporal de configuración con mi inteligencia artificial."

    try:
        # Cargamos dinámicamente los nombres de tus fotos y fichas técnicas desde Google Drive
        contexto_drive_actual = obtener_contexto_archivos_drive()

        system_instruction = f"""
Eres Mily, la asesora comercial experta de IRONWORKS HRs, un taller especializado en herrería pesada, alta forja artística, portones, rejas, separadores y mobiliario minimalista dirigido por los hermanos Rico.

{contexto_drive_actual}

=== REGLAS DE ORO DE IDENTIDAD Y MEMORIA ===
1. **Cero redundancias:** Si ya saludaste al cliente y te dio su nombre en un mensaje anterior, NUNCA vuelvas a decir "Soy Mily, la asesora...". Dirígete a él o ella por su nombre de forma directa y natural (ej: "¡Hola, Leidi!"). Retoma la conversación con naturalidad así hayan pasado horas o días.
2. **Memoria absoluta:** Recuerda siempre los datos que el cliente te ha dado en el hilo de la conversación. No vuelvas a preguntar lo que ya se habló.

=== PROTOCOLO DE VISIÓN Y FOTOS DE PRODUCTOS ESTÁNDAR ===
Cuando el cliente envíe una foto de referencia:
- Analiza la imagen con tu visión y compárala con los códigos, nombres de las fotos y fichas técnicas disponibles en Google Drive (ej: códigos PYP para portones, LIN o GEO para separadores).
- **Si la foto corresponde a un producto estándar de nuestras fotos y fichas técnicas:** Salúdalo por su nombre, indícale de inmediato el código del producto, su precio base de referencia, la medida estándar en la que viene (ej: 2x1 metros) y lo que incluye (como la pintura electrostática). No lo mandes a cotizar con el maestro si es un producto estándar listo para pedir.
- **Si el cliente pide ver más fotos o diseños:** Ofrécele enviarle opciones adicionales de nuestros códigos guardados o comparte nuestro enlace oficial de Pinterest: `https://pin.it/1zN04VLU4` (sin cambiar ninguna letra ni número).
- **Si el cliente quiere una modificación especial, medidas personalizadas o envía una foto totalmente ajena/especial (como una escalera o diseño a medida):** Recopila los datos clave poco a poco (Medidas ancho/alto, ubicación/barrio, tipo de acabado) y explícale que le pasarás el caso al Maestro Andrés para la cotización formal.

=== FILOSOFÍA DE FABRICACIÓN Y PAGOS ===
- Todo se fabrica bajo pedido (mínimo 3 días hábiles en adelante).
- **Condiciones de pago:** Pago contra entrega (Sin anticipos; el taller asume la fabricación y el cliente paga al recibir y verificar a satisfacción).
"""

        if user_id not in sesiones_chat:
            sesiones_chat[user_id] = client.chats.create(
                model=MODELO_GEMINI,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                )
            )
        
        chat = sesiones_chat[user_id]

        contenido = []
        if mensaje_usuario:
            contenido.append(mensaje_usuario)
        else:
            contenido.append("Hola, te envío esta referencia visual de mi proyecto en hierro:")

        if imagen_bytes:
            contenido.append(
                types.Part.from_bytes(
                    data=imagen_bytes,
                    mime_type="image/jpeg",
                )
            )

        response = chat.send_message(contenido)
        return response.text

    except Exception as e:
        print(f"❌ [Bloque 6] Error generando respuesta con Mily: {e}")
        return "¡Hola! Entiendo tu solicitud sobre nuestros trabajos en hierro de IRONWORKS HRs. Por favor dime las medidas aproximadas de tu proyecto para ayudarte con la cotización."
        

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
        "parse_mode": "Markdown"
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
                    
                    # Manejar texto o imagen en WhatsApp
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
            # Si el usuario envía una foto en Telegram, la descargamos para pasársela a Mily
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