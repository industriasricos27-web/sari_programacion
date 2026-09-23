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

# 1.1 — IDENTIDAD DEL SISTEMA
MILY_NOMBRE = "Mily"
MILY_VERSION = "3.0"
EMPRESA_NOMBRE = "IRONWORKS HR"
EMPRESA_DESCRIPCION = "Hermanos Rico Diseño y Estructura"

# 1.2 — CONFIGURACIÓN DEL SERVIDOR
HOST = "0.0.0.0"
PUERTO = int(os.environ.get("PORT", 5000))

# 1.3 — CREACIÓN DE LA APLICACIÓN
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

GOOGLE_FOLDER_ID = os.environ.get("GOOGLE_FOLDER_ID", "13DTk5zWfh31fb0gt6otHhLKau72tubzT")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

ADMINES_AUTORIZADOS = [
    admin.strip() 
    for admin in os.environ.get("ADMINES_AUTORIZADOS", "").split(",") 
    if admin.strip()
]


# ============================================================
# BLOQUE 3 — CEREBRO COMERCIAL E INSTRUCCIONES DE SISTEMA (MILY)
# ============================================================

SYSTEM_PROMPT_MILY = """
PROMPT DE SISTEMA Y CEREBRO — MILY
ASESORA COMERCIAL, EXPERTA EN TALLER Y PRECALIFICADORA DE IRONWORKS HRs

1. IDENTIDAD Y TONO
Eres Mily, la asesora comercial y experta de taller de IRONWORKS HRs — Hermanos Rico Diseño y Estructura. 
Hablas con la cercanía, naturalidad y seguridad de quien vive el metalwork todos los días: cálida, profesional, experta y apasionada por el diseño minimalista y la herrería pesada. 
No suenes robótica ni corporativa. Ve directo al grano con párrafos cortos y humanos (máximo 2 a 3 oraciones). 
Tu función principal es atender clientes, detectar necesidades, orientar, precalificar proyectos y guiar con maestría hacia la venta directa, la cotización formal o la visita técnica.

2. VITRINA VISUAL Y FUENTE DE INSPIRACIÓN (PINTEREST)
- Nuestra vitrina oficial de diseños, proyectos previos y fuente principal de inspiración es nuestro perfil de Pinterest: https://pin.it/12ojB0iY6.
- Cuando los clientes te compartan fotos o te pidan referencias visuales (como rejas, separadores o muebles minimalistas), utilízalo y recuérdalo con orgullo para mostrarles de lo que somos capaces en el taller.

3. REGLA FUNDAMENTAL DE PRECIOS Y CATÁLOGOS (FUENTE DINÁMICA DE DRIVE)
- CONSULTA DE PRODUCTOS: Debes basarte estrictamente en la información técnica y de catálogos obtenida dinámicamente desde la carpeta oficial de Google Drive vinculada al sistema.
- PROHIBICIÓN DE COTIZAR A CIEGAS: Si el cliente solicita una modificación, diseño personalizado, escalera, reja o proyecto sobre fotografía que no esté cubierto o estandarizado en los documentos de Drive, Mily NO debe inventar ni calcular un precio. Debe recopilar datos y solicitar evaluación técnica.

4. PROTOCOLO PARA PROYECTOS PERSONALIZADOS
PASO 1 — Recibir y confirmar imagen/solicitud.
PASO 2 — Recopilar: Producto, medidas aproximadas, ubicación, uso y si desea réplica exacta o modificación.
PASO 3 — Solicitar evaluación al equipo técnico interno (Maestro Andrés y Alexa) con el formato estructurado.
PASO 4 — Informar al cliente que el equipo técnico está evaluando la referencia.

5. UBICACIONES Y CONTACTO
- Bosa / El Porvenir: Calle 61A Sur #87B-36
- Fontibón Centro: Calle 17A #102-67

6. REGLA DE CIERRE
Toda conversación debe finalizar con una pregunta clara para avanzar (Ejemplo: "*¿Para qué sector o barrio de la ciudad necesitas el separador, señor?*").
"""

SYSTEM_PROMPT_INTERNO = """
PROMPT DE SISTEMA — MILY (MODO INTERNO Y ACADEMIA DEL TALLER)
Estás interactuando con un miembro del equipo de IRONWORKS HRs (Alexa, Maestro Andrés o un nuevo colaborador en entrenamiento).
- Asiste con reportes de estado, recepción de requerimientos técnicos y coordinación de cotizaciones personalizadas.
- Actúa también como tutora y guía de oratoria comercial para entrenar a los nuevos empleados o maestros colaboradores en la forma correcta de hablar, estructurar ofertas y mantener los estándares verbales del taller.
- Mantén un tono operativo, profesional, claro y enfocado en la excelencia de la marca.
"""


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

DRIVE_FOLDER_ID = "13DTk5zWfh31fb0gt6otHhLKau72tubzT"

def listar_archivos_catalogo():
    servicio = obtener_servicio_drive()
    if not servicio:
        return []
        
    try:
        query = f"'{DRIVE_FOLDER_ID}' in parents and trashed = false"
        resultados = servicio.files().list(
            q=query,
            pageSize=10,
            fields="files(id, name, mimeType)"
        ).execute()
        
        archivos = resultados.get('files', [])
        if archivos:
            print(f"✓ [Bloque 4] Se encontraron {len(archivos)} archivos en la subcarpeta de catálogos.")
        return archivos
    except Exception as e:
        print(f"❌ [Bloque 4] Error al listar archivos de la subcarpeta: {e}")
        return []

listar_archivos_catalogo()


# ============================================================
# BLOQUE 5 — MEMORIA Y GESTIÓN DE CONVERSACIONES
# ============================================================

HISTORIALES_CONVERSACION = {}
LIMITE_HISTORIAL = 10

def obtener_historial_usuario(user_id):
    if user_id not in HISTORIALES_CONVERSACION:
        HISTORIALES_CONVERSACION[user_id] = []
    return HISTORIALES_CONVERSACION[user_id]

def registrar_mensaje_historial(user_id, rol, texto):
    historial = obtener_historial_usuario(user_id)
    historial.append({
        "role": rol,
        "parts": [{"text": texto}]
    })
    if len(historial) > (LIMITE_HISTORIAL * 2):
        HISTORIALES_CONVERSACION[user_id] = historial[-(LIMITE_HISTORIAL * 2):]

def limpiar_historial_usuario(user_id):
    if user_id in HISTORIALES_CONVERSACION:
        HISTORIALES_CONVERSACION[user_id] = []
        print(f"✓ [Bloque 5] Historial reiniciado para el usuario: {user_id}")


# ============================================================
# BLOQUE 6 — CONFIGURACIÓN DEL MODELO GEMINI
# ============================================================

from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
MODELO_GEMINI = "gemini-2.5-flash"

def generar_respuesta_mily(user_id, mensaje_usuario, contexto_drive=""):
    if not api_key:
        return "Lo siento, en este momento tengo un problema temporal de configuración con mi inteligencia artificial."

    try:
        system_instruction = (
            "Eres Mily, la asistente virtual  de IRONWORKS HRs, experta en ventas, "
            "atención al cliente y asesoría en proyectos pesados, metalwork y muebles de diseño minimalista. "
            "Utiliza la información técnica y de catálogos proporcionada para responder de forma amable, "
            "profesional y orientada a concretar ventas o agendar asesorías."
        )

        historial = obtener_historial_usuario(user_id)

        prompt_completo = mensaje_usuario
        if contexto_drive:
            prompt_completo = f"[Información de catálogos de Drive]: {contexto_drive}\n\n[Mensaje del cliente]: {mensaje_usuario}"

        respuesta = client.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt_completo,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        
        texto_respuesta = respuesta.text

        registrar_mensaje_historial(user_id, "user", mensaje_usuario)
        registrar_mensaje_historial(user_id, "model", texto_respuesta)

        return texto_respuesta

    except Exception as e:
        print(f"❌ [Bloque 6] Error al generar respuesta con Gemini: {e}")
        return "Disculpa, ocurrió un error procesando tu solicitud en este momento. Por favor, intenta de nuevo más tarde."
    

# ============================================================
# BLOQUE 7 — ENVÍO DE MENSAJES A WHATSAPP (META API)
# ============================================================

def enviar_mensaje_whatsapp(numero_destino, texto_respuesta):
    """
    Envía una respuesta de texto al número de WhatsApp del cliente usando la API oficial de Meta.
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("⚠ [Bloque 7] Faltan credenciales de WhatsApp (WHATSAPP_TOKEN o PHONE_NUMBER_ID).")
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
        "text": {
            "body": texto_respuesta
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"✅ [WhatsApp] Mensaje enviado con éxito a {numero_destino}")
        else:
            print(f"❌ [WhatsApp] Error al enviar mensaje: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ [Bloque 7] Excepción al enviar mensaje a WhatsApp: {e}")


# ============================================================
# BLOQUE 8 — RUTAS Y WEBHOOKS DE COMUNICACIÓN (WHATSAPP)
# ============================================================

@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def webhook_whatsapp_bloque8():
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
                    mensaje = mensaje_data['messages'][0]['text']['body']
                    numero_remitente = mensaje_data['messages'][0]['from']
                    
                    print(f"📩 [WhatsApp] Mensaje recibido de {numero_remitente}: {mensaje}" if 'numero_remitente' in locals() else f"📩 [WhatsApp] Mensaje recibido de {numero_remitente}: {mensaje}")
                    
                    contexto_actual = ""
                    
                    # Generamos la respuesta con la IA de Mily
                    respuesta_ia = generar_respuesta_mily(numero_remitente, mensaje, contexto_drive=contexto_actual)
                    print(f"🤖 [Mily Respuesta]: {respuesta_ia}")
                    
                    # Enviamos la respuesta de vuelta al cliente
                    enviar_mensaje_whatsapp(numero_remitente, respuesta_ia)
                    
        except Exception as e:
            print(f"❌ [Bloque 8] Error procesando mensaje de WhatsApp: {e}")
            
        return jsonify({"status": "success"}), 200


# ============================================================
# BLOQUE 9 — RUTAS Y WEBHOOKS DE TELEGRAM
# ============================================================

# --- 1. RUTA PARA TELEGRAM ---
@app.route('/webhook/telegram', methods=['POST'])
def webhook_telegram():
    data = request.get_json()
    try:
        if "message" in data:
            message_data = data["message"]
            chat_id = message_data["chat"]["id"]
            mensaje = message_data.get("text", message_data.get("caption", ""))
            
            if mensaje:
                print(f"📩 [Telegram] Mensaje recibido de {chat_id}: {mensaje}")
                respuesta_ia = generar_respuesta_mily(str(chat_id), mensaje)
                print(f"🤖 [Mily Respuesta]: {respuesta_ia}")
                enviar_mensaje_telegram(chat_id, respuesta_ia)
    except Exception as e:
        print(f"❌ [Bloque 9 - Telegram] Error: {e}")
        
    return jsonify({"status": "ok"}), 200


# --- 2. RUTA PARA WHATSAPP / META (Futuro) ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook_whatsapp_meta():  # <--- Nombre único para evitar choques
    if request.method == 'GET':
        verify_token = os.environ.get("VERIFY_TOKEN", "tu_token_secreto")
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if mode and token and mode == "subscribe" and token == verify_token:
            return challenge, 200
        return "Verificación fallida", 403

    data = request.get_json()
    try:
        if 'entry' in data and 'changes' in data['entry'][0]:
            mensaje_data = data['entry'][0]['changes'][0]['value']
            if 'messages' in mensaje_data:
                mensaje = mensaje_data['messages'][0]['text']['body']
                numero_remitiente = mensaje_data['messages'][0]['from']
                print(f"📩 [WhatsApp] Mensaje recibido de {numero_remitiente}: {mensaje}")
                respuesta_ia = generar_respuesta_mily(str(numero_remitiente), mensaje)
                print(f"🤖 [Mily Respuesta]: {respuesta_ia}")
    except Exception as e:
        print(f"❌ [Bloque 9 - WhatsApp] Error: {e}")
        
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
