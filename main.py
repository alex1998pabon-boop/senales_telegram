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
TARGET_GROUP = os.getenv("TARGET_GROUP", "alejandrosinalesgratis")
SESSION_STRING = os.getenv("TELEGRAM_SESSION", "")

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
    
    Ejemplo:
    • EURGBP - PUT 🟥 - 18:10
    • EURGBP-OTC - CALL 🟩 - 09:45
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
        
        # Extraer par (puede tener -OTC)
        pair_match = re.search(r'([A-Z]{6})(-OTC)?', signal_line)
        if not pair_match:
            return None
        
        pair_base = pair_match.group(1)
        is_otc = bool(pair_match.group(2))
        market_type = "OTC" if is_otc else "Regular"
        
        # Extraer dirección (CALL o PUT)
        direction_match = re.search(r'(CALL|PUT)', signal_line, re.IGNORECASE)
        direction = direction_match.group(1).upper() if direction_match else "UNKNOWN"
        
        # Extraer hora (formato HH:MM)
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
        print(f"\n📨 Nuevo mensaje recibido:")
        print(f"   {message_text[:100]}...")
        
        signal = parse_signal(message_text)
        
        if signal:
            signals_storage.insert(0, signal.to_dict())
            # Mantener solo las últimas MAX_SIGNALS
            if len(signals_storage) > MAX_SIGNALS:
                signals_storage.pop()
            
            print(f"✓ Señal procesada: {signal.pair} {signal.direction} @ {signal.entry_time}")
        else:
            print("✗ No se pudo extraer señal del mensaje")
    
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

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Sirve el frontend"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/api/signals")
async def get_signals():
    """
    Retorna las señales almacenadas en memoria.
    
    Response:
    {
        "count": 10,
        "signals": [...]
    }
    """
    return {
        "count": len(signals_storage),
        "signals": signals_storage
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "telegram_connected": telegram_client is not None and telegram_client.is_connected(),
        "signals_count": len(signals_storage),
        "target_group": TARGET_GROUP
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
