# Trading Signals Monitor

Sistema de captura y visualización de señales de trading desde Telegram, ejecutándose 24/7 en la nube.

## 🎯 Características

- ✅ Captura automática de señales desde grupo público de Telegram
- ✅ Conexión como usuario (sin necesidad de ser admin o agregar bots)
- ✅ Ejecución 24/7 en la nube (Render.com)
- ✅ API REST para consumir señales
- ✅ Interfaz web moderna con actualización automática
- ✅ Parsing inteligente de mensajes de trading
- ✅ Almacenamiento en memoria de últimas 50 señales

## 📋 Pre-requisitos

### 1. Obtener credenciales de Telegram API

1. Ir a https://my.telegram.org
2. Iniciar sesión con tu número de teléfono
3. Ir a "API development tools"
4. Crear una nueva aplicación:
   - **App title**: Trading Signals Monitor
   - **Short name**: trading-signals
   - **Platform**: Other
5. Copiar `api_id` y `api_hash`

### 2. Generar Session String (Primera vez)

**IMPORTANTE**: Este paso solo se hace UNA VEZ desde tu computadora local.

```bash
# Instalar dependencias
pip install telethon

# Ejecutar script de autenticación
python generate_session.py
```

Código para `generate_session.py`:

```python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = input("Ingresa tu API_ID: ")
API_HASH = input("Ingresa tu API_HASH: ")

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\n✓ Autenticación exitosa!")
    session_string = client.session.save()
    print(f"\n📋 Tu SESSION STRING (cópialo completo):")
    print(f"{session_string}\n")
    print("⚠️  GUARDA ESTO DE FORMA SEGURA - Lo necesitarás para Render")
```

Te pedirá:
- Número de teléfono (formato internacional, ej: +57...)
- Código de verificación (llegará a Telegram)
- Contraseña 2FA (si la tienes configurada)

**Guarda el SESSION STRING generado**

## 🚀 Despliegue en Render.com

### Paso 1: Preparar repositorio

1. Sube estos archivos a un repositorio de GitHub:
   ```
   trading-signals/
   ├── main.py
   ├── requirements.txt
   ├── static/
   │   └── index.html
   └── README.md
   ```

### Paso 2: Crear Web Service en Render

1. Ir a https://render.com
2. Conectar tu cuenta de GitHub
3. Click en "New +" → "Web Service"
4. Seleccionar tu repositorio
5. Configurar:

   **Configuración básica:**
   - **Name**: trading-signals
   - **Region**: Oregon (US West) o más cercano
   - **Branch**: main
   - **Root Directory**: (dejar vacío o poner directorio raíz)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`

   **Plan:**
   - Seleccionar **Free** ($0/mes)

### Paso 3: Variables de entorno

En la sección "Environment Variables", agregar:

| Key | Value | Ejemplo |
|-----|-------|---------|
| `TELEGRAM_API_ID` | Tu API ID | `12345678` |
| `TELEGRAM_API_HASH` | Tu API Hash | `abcdef1234567890abcdef` |
| `TELEGRAM_SESSION` | Tu Session String | `1ApWapzMBu1h...` (muy largo) |
| `TARGET_GROUP` | Nombre del grupo | `alejandrosinalesgratis` |
| `PORT` | Puerto (opcional) | `8000` |

**IMPORTANTE**: 
- No incluyas comillas en los valores
- El `TELEGRAM_SESSION` es muy largo (300+ caracteres), cópialo completo
- `TARGET_GROUP` es solo el nombre, sin `https://t.me/`

### Paso 4: Deploy

1. Click en "Create Web Service"
2. Render automáticamente:
   - Instalará dependencias
   - Iniciará la aplicación
   - Asignará una URL pública

**Tu app estará disponible en**: `https://trading-signals-xxx.onrender.com`

## 📡 Endpoints de la API

### GET `/`
Interfaz web principal

### GET `/api/signals`
Retorna todas las señales almacenadas

**Response:**
```json
{
  "count": 5,
  "signals": [
    {
      "pair": "EURGBP",
      "market_type": "Regular",
      "direction": "PUT",
      "entry_time": "18:10",
      "expiration": "M5",
      "timestamp": "2026-01-27T15:30:45.123456",
      "raw_message": "• EURGBP - PUT 🟥 - 18:10\n• Caducidad: 5 minutos (M5)"
    }
  ]
}
```

### GET `/api/health`
Health check del sistema

**Response:**
```json
{
  "status": "ok",
  "telegram_connected": true,
  "signals_count": 5,
  "target_group": "alejandrosinalesgratis"
}
```

### POST `/api/test-parse`
Probar el parser de señales

**Request:**
```json
{
  "text": "• EURGBP-OTC - CALL 🟩 - 09:45\n• Caducidad: 5 minutos (M5)"
}
```

## 🎨 Interfaz Web

La interfaz web muestra:
- ✅ Estado de conexión en tiempo real
- ✅ Contador de señales activas
- ✅ Grid responsive de tarjetas de señales
- ✅ Actualización automática cada 5 segundos
- ✅ Diseño moderno con gradientes y animaciones
- ✅ Diferenciación visual CALL (verde) vs PUT (rojo)
- ✅ Identificación OTC vs Regular

## 🔍 Monitoreo

### Ver logs en Render:
1. Dashboard → Tu servicio → Logs
2. Ver mensajes en tiempo real:
   - `✓ Cliente de Telegram conectado`
   - `📨 Nuevo mensaje recibido`
   - `✓ Señal procesada: EURGBP PUT @ 18:10`

### Verificar que funciona:
```bash
# Health check
curl https://tu-app.onrender.com/api/health

# Ver señales
curl https://tu-app.onrender.com/api/signals
```

## 🛠️ Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export TELEGRAM_API_ID="tu_api_id"
export TELEGRAM_API_HASH="tu_api_hash"
export TELEGRAM_SESSION="tu_session_string"
export TARGET_GROUP="alejandrosinalesgratis"

# Ejecutar
python main.py
```

Abrir navegador en: `http://localhost:8000`

## 📝 Formato de Señales Soportado

El sistema reconoce estos formatos:

```
• EURGBP - PUT 🟥 - 18:10
• Caducidad: 5 minutos (M5)
```

```
• EURGBP-OTC - CALL 🟩 - 09:45
• Caducidad: 5 minutos (M5)
```

**Extrae:**
- Par de divisas (ej: EURGBP)
- Tipo de mercado (OTC / Regular)
- Dirección (CALL / PUT)
- Hora de entrada (ej: 18:10)
- Expiración (ej: M5, M1, M15)

## ⚠️ Limitaciones de Render Free Tier

- El servicio puede dormir después de 15 minutos de inactividad
- Se despierta automáticamente al recibir una request
- Puede tardar ~30 segundos en despertar
- 750 horas/mes gratuitas (suficiente para 24/7)

**Solución**: Configurar un cron job externo para hacer ping cada 14 minutos:
```bash
# Cron job (crontab -e)
*/14 * * * * curl https://tu-app.onrender.com/api/health
```

O usar servicios como UptimeRobot (gratis) para hacer ping automático.

## 🔐 Seguridad

- ✅ Las credenciales están en variables de entorno (no en código)
- ✅ El Session String es privado y encriptado
- ✅ No se expone información sensible en la API
- ⚠️ No compartas tu Session String con nadie
- ⚠️ Regenera el Session String si lo comprometes

## 🐛 Troubleshooting

### "Error: TELEGRAM_API_ID y TELEGRAM_API_HASH son requeridos"
→ Verifica que las variables de entorno estén configuradas en Render

### "No se pudo conectar a Telegram"
→ Verifica que el `TELEGRAM_SESSION` sea correcto y completo

### "No se reciben señales"
→ Verifica:
1. Que el grupo sea correcto: `TARGET_GROUP=alejandrosinalesgratis`
2. Que tu cuenta de Telegram esté en el grupo
3. Que el grupo tenga mensajes nuevos
4. Los logs en Render para ver errores

### "Service is sleeping"
→ Normal en Render Free. Se despierta solo o configura ping automático.

## 📞 Soporte

Para reportar bugs o solicitar features, crear un issue en el repositorio.

## 📄 Licencia

MIT License - Libre para uso personal y comercial.
