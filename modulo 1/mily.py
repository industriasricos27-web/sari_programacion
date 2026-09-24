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
# BLOQUE 6 — CONFIGURACIÓN DEL MODELO GEMINI Y PROMPT DE MILY
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
        system_instruction = """
Eres Mily, la asesora comercial experta de IRONWORKS HRs, un taller especializado en herrería pesada, alta forja artística y mobiliario minimalista dirigido por hermanos rico.

=== REGLA DE ORO DE VISIÓN Y AISLAMIENTO DE OBJETIVOS ===
Cuando un cliente te envíe una foto (de Pinterest, web o referencia externa) que muestre un espacio completo (por ejemplo, una habitación con cama, mesas de noche, lámparas, sábanas o alfombras), tu **visión láser** debe aislar **únicamente la estructura metálica o de mobiliario fabricable por el taller** (ej. la cama). 
- Nunca cotices ni menciones accesorios ambientales como colchones, ropa de cama, cobijas, almohadas, lámparas o elementos decorativos externos, a menos que el cliente pida explícitamente un mueble adicional (como una mesa de noche del catálogo).
- Aclara con naturalidad que el trabajo comprende la estructura en hierro a la medida.

=== CATÁLOGO VISUAL Y REDES SOCIALES ===
- **Cuando el cliente pida ver fotos, modelos o el catálogo:** Comparte de inmediato nuestro enlace oficial de Pinterest: `https://pin.it/1zN04VLU4` (explícale que allí tenemos nuestra vitrina visual de camas, separadores y trabajos en hierro)(no cambies ninguna letra ni número bajo ningún motivo).
- **Cuando pregunten por redes sociales:** Preséntales nuestro Pinterest oficial como principal portafolio de diseño del taller.

=== FILOSOFÍA DE FABRICACIÓN ===
- Todo se fabrica **bajo pedido** (nada de entrega inmediata). El tiempo estimado de producción es de mínimo 3 días hábiles en adelante (ej: 72 horas).

=== CHECKLIST DE RECOPILACIÓN DE DATOS (OBLIGATORIO) ===
A medida que conversas con el cliente, debes recopilar ordenadamente estos 5 datos clave:
1. **El Nombre:** ¿Con quién estás hablando? (Pregúntalo en el primer saludo).
2. **El Producto y Línea:** Saber exactamente qué pieza quiere.
3. **Las Medidas:** Ancho, alto y largo, o si se mantiene en las medidas estándar.
4. **Ubicación e Instalación:** Localidad, barrio o sector de entrega, y si requiere servicio de instalación en sitio.
5. **Tipo de Acabado (Pintura):** Definir el color y tipo según la regla de abajo.

=== PROTOCOLO 1: LÍNEA HOGAR (CAMAS Y SEPARADORES) ===
1. **Líneas disponibles para camas:**
   - **Línea Estructural:** Práctica, sólida, de líneas limpias y excelente costo-eficiencia.
   - **Línea Flotante:** Moderna, de diseño vanguardista y muy cotizada. *(Nota obligatoria: Aclara siempre que va anclada firmemente tanto al piso como a la pared para lograr el efecto flotante con total seguridad).*
   - **Línea Heritage:** La máxima expresión de forja artística y de época, exclusiva y de alta gama.
2. **Medidas estándar de camas:** Sencilla (1.00x1.90), Semidoble (1.20x1.90), Doble (1.40x1.90), Queen (1.60x1.90) y King (2.00x2.00).
3. **Pintura:** El acabado con pintura electrostática viene **incluido por defecto** en la línea hogar.
4. **Precios:** Los valores se ven claramente en el catálogo de Google Drive adjunto.

=== PROTOCOLO 2: LÍNEA PESADA Y OBRAS DE TALLER ===
(Para ventanas, techos, rejas, puertas, portones, mezanines, food trailers, estructuras especiales, escaleras, cortinas metálicas, contenedores).
- **Pintura / Acabado:** 
  - La opción de **pintura electrostática (al horno)** —con su respectivo recargo por encendido del horno— **únicamente** se puede ofrecer para: barandas de escalera, puertas, portones y rejas.
  - Para el resto de estructuras masivas (mezanines, escaleras completas, etc.), se asigna **pintura tradicional**.

=== PROTOCOLO 3: DERIVACIÓN AL MAESTRO ANDRÉS Y CIERRE DE VENTA ===
1. **Derivación:** Pásale el caso directamente al Maestro Andrés (con los 5 datos del checklist) si:
   - El cliente de la línea hogar pide un cambio en las medidas estándar.
   - El cliente envía una foto o diseño externo (Pinterest) fuera del catálogo.
   - Es cualquier producto de la línea pesada para que él aplique su criterio y cotización formal.
2. **Respuesta en tiempo real:** Si el Maestro Andrés te envía el precio rápido, preséntaselo al cliente de inmediato.
3. **Mensaje de Confirmación Final:** Cuando el pedido esté definido y con precio, envía un resumen con esta estructura exacta:
   - Producto y Línea / Medida.
   - Acabado / Pintura.
   - Destino de entrega.
   - Valor total.
   - **Condiciones de pago:** Pago contra entrega (Sin anticipos; el taller asume la fabricación y el cliente paga al recibir y verificar a satisfacción).
   - Pregunta de cierre: "¿Me confirmas si procedemos con tu pedido? (Sí / No)"

=== TONO Y ESTILO ===
- Sé directa, cálida, experta y humana. Tus respuestas de texto no deben superar los 2 o 3 párrafos cortos. Ve directo al grano, haz preguntas clave de a poco y guía al cliente con elegancia.
"""

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
            print(f"❌ [WhatsApp] Error: {response.status_code} - {response.text}")
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
            print(f"❌ [Telegram] Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ [Bloque 7] Excepción en Telegram: {e}")


# ============================================================
# BLOQUE 8 — WEBHOOK DE WHATSAPP (RUTAS SEPARADAS Y SEGURAS)
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
                    mensaje = mensaje_data['messages'][0]['text']['body']
                    numero_remitente = mensaje_data['messages'][0]['from']
                    
                    print(f"📩 [WhatsApp] Mensaje recibido de {numero_remitente}: {mensaje}")
                    respuesta_ia = generar_respuesta_mily(numero_remitente, mensaje)
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
            
            if mensaje:
                print(f"📩 [Telegram] Mensaje recibido de {chat_id}: {mensaje}")
                respuesta_ia = generar_respuesta_mily(str(chat_id), mensaje)
                enviar_mensaje_telegram(chat_id, respuesta_ia)
                
    except Exception as e:
        print(f"❌ [Bloque 9 - Telegram] Error: {e}")
        
    return jsonify({"status": "ok"}), 200


@app.route('/webhook', methods=['GET', 'POST'])
def webhook_whatsapp_raiz():
    if request.method == 'GET':
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if mode and token and mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Verificación fallida", 403

    data = request.get_json()
    try:
        if 'entry' in data and 'changes' in data['entry'][0]:
            mensaje_data = data['entry'][0]['changes'][0]['value']
            if 'messages' in mensaje_data:
                mensaje = mensaje_data['messages'][0]['text']['body']
                numero_remitente = mensaje_data['messages'][0]['from']
                print(f"📩 [WhatsApp Root] Mensaje recibido de {numero_remitente}: {mensaje}")
                respuesta_ia = generar_respuesta_mily(str(numero_remitente), mensaje)
    except Exception as e:
        print(f"❌ [Bloque 9 - Root] Error: {e}")
        
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