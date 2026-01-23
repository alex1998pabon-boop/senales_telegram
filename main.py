import os
import re
import asyncio
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from telethon import TelegramClient, events
import uvicorn

# Configuración
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
TARGET_GROUP = os.getenv("TARGET_GROUP", "📊 Alejandro Fintch | Señales Gratis 🚀")

# Almacenamiento en memoria
signals_storage: List[Dict] = []
MAX_SIGNALS = 50

# FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cliente de Telegram
client = None

def parse_signal(text: str) -> Dict:
    """Extrae información de la señal del mensaje"""
    try:
        # Buscar par (EURGBP-OTC, EURUSD, etc)
        pair_match = re.search(r'([A-Z]{6}(?:-OTC)?)', text)
        pair = pair_match.group(1) if pair_match else "UNKNOWN"
        
        # Buscar dirección (CALL o PUT)
        direction = "CALL" if "CALL" in text.upper() or "🟩" in text else "PUT" if "PUT" in text.upper() or "🟥" in text else "UNKNOWN"
        
        # Buscar hora (formato HH:MM)
        time_match = re.search(r'(\d{1,2}:\d{2})', text)
        time = time_match.group(1) if time_match else "N/A"
        
        # Buscar caducidad
        expiry_match = re.search(r'(\d+)\s*minutos?', text, re.IGNORECASE)
        expiry = f"{expiry_match.group(1)}m" if expiry_match else "5m"
        
        return {
            "pair": pair,
            "direction": direction,
            "time": time,
            "expiry": expiry,
            "timestamp": datetime.now().isoformat(),
            "raw_text": text[:200]
        }
    except Exception as e:
        return {
            "pair": "ERROR",
            "direction": "ERROR",
            "time": "N/A",
            "expiry": "N/A",
            "timestamp": datetime.now().isoformat(),
            "raw_text": str(e)
        }

async def start_telegram_client():
    """Inicia el cliente de Telegram y escucha mensajes"""
    global client
    
    client = TelegramClient('session_name', API_ID, API_HASH)
    await client.start()
    
    print("✅ Cliente de Telegram conectado")
    
    # Obtener la entidad del grupo
    try:
        target_entity = await client.get_entity(TARGET_GROUP)
        print(f"✅ Grupo encontrado: {TARGET_GROUP}")
    except Exception as e:
        print(f"❌ Error al encontrar el grupo: {e}")
        return
    
    @client.on(events.NewMessage(chats=target_entity))
    async def handler(event):
        """Maneja nuevos mensajes del grupo"""
        message_text = event.message.message
        
        # Filtrar solo mensajes que parezcan señales
        if any(keyword in message_text.upper() for keyword in ["CALL", "PUT", "OTC", "🟩", "🟥"]):
            signal = parse_signal(message_text)
            signals_storage.insert(0, signal)
            
            # Mantener solo las últimas señales
            if len(signals_storage) > MAX_SIGNALS:
                signals_storage.pop()
            
            print(f"📊 Nueva señal: {signal['pair']} {signal['direction']} @ {signal['time']}")
    
    print("👂 Escuchando mensajes...")
    await client.run_until_disconnected()

@app.on_event("startup")
async def startup_event():
    """Inicia el cliente de Telegram al arrancar la app"""
    asyncio.create_task(start_telegram_client())

@app.get("/")
async def root():
    """Retorna la interfaz HTML"""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/signals")
async def get_signals():
    """Endpoint para obtener las señales"""
    return {
        "status": "ok",
        "count": len(signals_storage),
        "signals": signals_storage
    }

@app.get("/health")
async def health():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "telegram_connected": client is not None and client.is_connected(),
        "signals_count": len(signals_storage)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))