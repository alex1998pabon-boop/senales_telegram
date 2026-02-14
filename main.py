import os
import re
import asyncio
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn


# Configuración
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
TARGET_GROUP_RAW = os.getenv("TARGET_GROUP", "alejandrosinalesgratis")

# Limpiar TARGET_GROUP si viene como URL
if "t.me/" in TARGET_GROUP_RAW:
    TARGET_GROUP = TARGET_GROUP_RAW.split("t.me/")[-1]
else:
    TARGET_GROUP = TARGET_GROUP_RAW

SESSION_STRING = os.getenv("TELEGRAM_SESSION", "")

# Estadísticas de filtrado
signals_stats = {
    "total_received": 0,
    "total_accepted": 0,
    "total_rejected_otc": 0,
    "total_rejected_market_closed": 0
}

# Almacenamiento en memoria
signals_storage = []
MAX_SIGNALS = 50

# Cliente de Telegram
telegram_client = None


class TradingSignal:
    """Modelo de señal de trading"""
    def __init__(self, pair: str, market_type: str, direction: str, 
                 entry_time: str, expiration: str, raw_message: str):
        self.pair = pair
        self.market_type = market_type
        self.direction = direction
        self.entry_time = entry_time
        self.expiration = expiration
        self.timestamp = datetime.now().isoformat()
        self.raw_message = raw_message
    
    def to_dict(self):
        return {
            "pair": self.pair,
            "market_type": self.market_type,
            "direction": self.direction,
            "entry_time": self.entry_time,
            "expiration": self.expiration,
            "timestamp": self.timestamp,
            "raw_message": self.raw_message
        }


def parse_signal(message_text: str) -> Optional[TradingSignal]:
    """
    Extrae información de la señal del mensaje de Telegram.
    
    FILTRO ACTIVO: Solo señales de MERCADO REAL (ignora OTC)
    
    Ejemplo:
    ✅ EURGBP - PUT 🟥 - 18:10         (ACEPTADA - Mercado Real)
    ❌ EURGBP-OTC - CALL 🟩 - 09:45   (RECHAZADA - OTC)
    • Caducidad: 5 minutos (M5)
    """
    try:
        lines = message_text.strip().split('\n')
        
        # Buscar línea con el par y dirección
        signal_line = None
        expiration_line = None
        
        for line in lines:
            # Línea principal con par, dirección y hora
            if re.search(r'(CALL|PUT)', line, re.IGNORECASE):
                signal_line = line
            # Línea de caducidad
            if 'caducidad' in line.lower() or 'M5' in line or 'M1' in line or 'M15' in line:
                expiration_line = line
        
        if not signal_line:
            return None
        
        # Extraer par (ahora más flexible - busca cualquier par de 6 letras mayúsculas)
        # Soporta: EURGBP, NZDUSD, etc., con o sin -OTC
        pair_match = re.search(r'([A-Z]{6})(-OTC)?', signal_line)
        if not pair_match:
            return None
        
        pair_base = pair_match.group(1)
        is_otc = bool(pair_match.group(2))
        
        # 🔥 FILTRO: Rechazar señales OTC
        if is_otc:
            print(f"\n{'='*60}")
            print(f"⚠️  SEÑAL OTC DETECTADA Y RECHAZADA")
            print(f"{'='*60}")
            print(f"Par: {pair_base}-OTC")
            print(f"Razón: Solo se procesan señales de MERCADO REAL")
            print(f"")
            print(f"💡 ¿Por qué rechazamos OTC?")
            print(f"   - Precios OTC son sintéticos (no reales)")
            print(f"   - Varían mucho entre brokers")
            print(f"   - Win rate es menor en OTC")
            print(f"   - Mercado real es más confiable")
            print(f"{'='*60}\n")
            return None
        
        market_type = "Regular"  # Solo aceptamos mercado regular
        
        # Extraer dirección (CALL o PUT)
        direction_match = re.search(r'(CALL|PUT)', signal_line, re.IGNORECASE)
        direction = direction_match.group(1).upper() if direction_match else "UNKNOWN"
        
        # Extraer hora (formato HH:MM, ahora acepta también 00:15)
        time_match = re.search(r'(\d{1,2}:\d{2})', signal_line)
        entry_time = time_match.group(1) if time_match else "N/A"
        
        # Extraer expiración
        expiration = "M5"  # Default
        if expiration_line:
            exp_match = re.search(r'(M\d+)', expiration_line)
            if exp_match:
                expiration = exp_match.group(1)
            elif re.search(r'(\d+)\s*minut', expiration_line, re.IGNORECASE):
                minutes = re.search(r'(\d+)\s*minut', expiration_line, re.IGNORECASE).group(1)
                expiration = f"M{minutes}"
        
        # 🎯 VALIDACIÓN ADICIONAL: Verificar horario de mercado
        if not is_market_open(pair_base):
            print(f"\n⚠️  Señal rechazada: {pair_base} - Mercado cerrado")
            print(f"   Solo se ejecutan señales durante horario de mercado\n")
            return None
        
        return TradingSignal(
            pair=pair_base,
            market_type=market_type,
            direction=direction,
            entry_time=entry_time,
            expiration=expiration,
            raw_message=message_text
        )
    
    except Exception as e:
        print(f"Error parsing signal: {e}")
        return None


def is_market_open(pair: str) -> bool:
    """
    Verificar si el mercado está abierto para el par dado
    
    Forex abre: Domingo 22:00 UTC - Viernes 22:00 UTC
    (24 horas durante la semana)
    """
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    weekday = now.weekday()  # 0=Lunes, 6=Domingo
    hour = now.hour
    
    # Viernes después de las 22:00 UTC - Mercado cerrado
    if weekday == 4 and hour >= 22:
        return False
    
    # Sábado - Mercado cerrado
    if weekday == 5:
        return False
    
    # Domingo antes de las 22:00 UTC - Mercado cerrado
    if weekday == 6 and hour < 22:
        return False
    
    # Resto del tiempo - Mercado abierto
    return True


async def init_telegram():
    """Inicializa el cliente de Telegram"""
    global telegram_client
    
    if not API_ID or not API_HASH:
        print("ERROR: TELEGRAM_API_ID y TELEGRAM_API_HASH son requeridos")
        return
    
    # Usar StringSession para persistir la sesión
    session = StringSession(SESSION_STRING)
    
    telegram_client = TelegramClient(session, int(API_ID), API_HASH)
    await telegram_client.start()
    
    print("✓ Cliente de Telegram conectado")
    
    # Si es la primera vez, guardar la sesión
    if not SESSION_STRING:
        session_string = telegram_client.session.save()
        print(f"\n⚠️  IMPORTANTE: Guarda esta sesión en la variable TELEGRAM_SESSION:")
        print(f"TELEGRAM_SESSION={session_string}\n")
    
    # Registrar handler para mensajes nuevos del grupo
    @telegram_client.on(events.NewMessage(chats=TARGET_GROUP))
    async def handler(event):
        message_text = event.message.message
        
        # Incrementar contador de mensajes recibidos
        signals_stats["total_received"] += 1
        
        print(f"\n{'='*60}")
        print(f"📨 Nuevo mensaje recibido del grupo: {TARGET_GROUP}")
        print(f"{'='*60}")
        print(f"Contenido completo:")
        print(message_text)
        print(f"{'='*60}")
        
        signal = parse_signal(message_text)
        
        if signal:
            # Señal aceptada (pasó todos los filtros)
            signals_stats["total_accepted"] += 1
            
            signals_storage.insert(0, signal.to_dict())
            # Mantener solo las últimas MAX_SIGNALS
            if len(signals_storage) > MAX_SIGNALS:
                signals_storage.pop()
            
            print(f"✅ Señal ACEPTADA y procesada exitosamente:")
            print(f"   Par: {signal.pair}")
            print(f"   Mercado: {signal.market_type}")
            print(f"   Dirección: {signal.direction}")
            print(f"   Hora: {signal.entry_time}")
            print(f"   Expiración: {signal.expiration}")
            print(f"\n📊 Estadísticas:")
            print(f"   Total recibidas: {signals_stats['total_received']}")
            print(f"   Aceptadas: {signals_stats['total_accepted']}")
            print(f"   Rechazadas (OTC): {signals_stats['total_rejected_otc']}")
            print(f"   Rechazadas (Mercado cerrado): {signals_stats['total_rejected_market_closed']}")
            print(f"{'='*60}\n")
        else:
            # Señal rechazada por filtros
            # Verificar el motivo
            if "-OTC" in message_text:
                signals_stats["total_rejected_otc"] += 1
            elif "CALL" in message_text or "PUT" in message_text:
                # Es una señal pero rechazada por otro motivo (mercado cerrado)
                signals_stats["total_rejected_market_closed"] += 1
            
            print(f"❌ Señal rechazada o mensaje no procesable")
            print(f"   Revisar logs arriba para más detalles")
            print(f"{'='*60}\n")
    
    print(f"✓ Escuchando mensajes del grupo: {TARGET_GROUP}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación"""
    # Startup
    await init_telegram()
    yield
    # Shutdown
    if telegram_client:
        await telegram_client.disconnect()


# FastAPI App
app = FastAPI(
    title="Trading Signals API",
    description="API para capturar señales de trading desde Telegram",
    version="1.0.0",
    lifespan=lifespan
)

# Montar archivos estáticos (crear directorio si no existe)
import os
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Sirve el frontend"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        # Si no existe el archivo, mostrar una página simple
        return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Signals API</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        .endpoint {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }
        code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .status {
            display: inline-block;
            padding: 5px 10px;
            background: #28a745;
            color: white;
            border-radius: 15px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Trading Signals API</h1>
        <p><span class="status">✅ Online</span></p>
        
        <h2>Endpoints Disponibles:</h2>
        
        <div class="endpoint">
            <strong>GET /api/signals</strong><br>
            Obtiene todas las señales capturadas
        </div>
        
        <div class="endpoint">
            <strong>GET /api/health</strong><br>
            Verifica el estado del sistema
        </div>
        
        <div class="endpoint">
            <strong>POST /api/test-parse</strong><br>
            Prueba el parser de señales
        </div>
        
        <h2>Ejemplo de uso:</h2>
        <p>Obtener señales:</p>
        <pre><code>fetch('/api/signals').then(r => r.json()).then(console.log)</code></pre>
        
        <p><em>Para ver la interfaz web completa, sube el archivo <code>static/index.html</code> a tu repositorio.</em></p>
    </div>
</body>
</html>
        """, status_code=200)


@app.get("/api/signals")
async def get_signals():
    """
    Retorna las señales almacenadas en memoria.
    SOLO señales de MERCADO REAL (sin OTC)
    
    Response:
    {
        "count": 10,
        "signals": [...],
        "filter_info": {
            "mode": "REAL_MARKET_ONLY",
            "description": "Solo se muestran señales de mercado real"
        }
    }
    """
    return {
        "count": len(signals_storage),
        "signals": signals_storage,
        "filter_info": {
            "mode": "REAL_MARKET_ONLY",
            "description": "Solo señales de mercado regular (sin OTC)",
            "reason": "Mayor precisión y win rate con precios de mercado real"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint con estadísticas de filtrado"""
    acceptance_rate = 0
    if signals_stats["total_received"] > 0:
        acceptance_rate = (signals_stats["total_accepted"] / signals_stats["total_received"]) * 100
    
    return {
        "status": "ok",
        "telegram_connected": telegram_client is not None and telegram_client.is_connected(),
        "signals_count": len(signals_storage),
        "target_group": TARGET_GROUP,
        "filter_mode": "REAL_MARKET_ONLY",
        "statistics": {
            "total_messages_received": signals_stats["total_received"],
            "signals_accepted": signals_stats["total_accepted"],
            "signals_rejected_otc": signals_stats["total_rejected_otc"],
            "signals_rejected_market_closed": signals_stats["total_rejected_market_closed"],
            "acceptance_rate": f"{acceptance_rate:.1f}%"
        }
    }


@app.post("/api/test-parse")
async def test_parse(message: dict):
    """
    Endpoint para probar el parser de señales.
    
    Body: {"text": "mensaje de prueba"}
    """
    signal = parse_signal(message.get("text", ""))
    if signal:
        return {"success": True, "signal": signal.to_dict()}
    return {"success": False, "error": "No se pudo parsear el mensaje"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
