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
        # Buscar par con múltiples patrones
        # Patrón 1: USDJPY-OTC, EURGBP-OTC
        pair_match = re.search(r'[•\-\*]\s*([A-Z]{6,7}(?:-OTC)?)', text)
        if not pair_match:
            # Patrón 2: Solo el par sin prefijo
            pair_match = re.search(r'\b([A-Z]{6,7})(?:-OTC)?\b', text)
        
        pair = pair_match.group(1) if pair_match else "UNKNOWN"
        
        # Buscar dirección con múltiples indicadores
        text_upper = text.upper()
        if "CALL" in text_upper or "🟩" in text or "⬆️" in text or "UP" in text_upper:
            direction = "CALL"
        elif "PUT" in text_upper or "🟥" in text or "⬇️" in text or "DOWN" in text_upper:
            direction = "PUT"
        else:
            direction = "UNKNOWN"
        
        # Buscar hora (formato HH:MM con posible guión)
        time_match = re.search(r'(\d{1,2}:\d{2})', text)
        time = time_match.group(1) if time_match else "N/A"
        
        # Buscar caducidad con múltiples formatos
        expiry_match = re.search(r'(\d+)\s*minutos?|M(\d+)', text, re.IGNORECASE)
        if expiry_match:
            expiry_value = expiry_match.group(1) or expiry_match.group(2)
            expiry = f"{expiry_value}m"
        else:
            expiry = "5m"  # Default
        
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
        
        # Filtrar mensajes que contengan señales con patrones flexibles
        signal_indicators = [
            "CALL", "PUT", "OTC", "🟩", "🟥", 
            "SEÑALE", "SEÑAL", "SIGNAL",
            "-", "•", "minutos", "M5", "M1", "M15"
        ]
        
        # Verificar si el mensaje contiene al menos 2 indicadores
        matches = sum(1 for indicator in signal_indicators if indicator in message_text.upper())
        
        if matches >= 2:
            signal = parse_signal(message_text)
            
            # Solo agregar si se detectó par y dirección válidos
            if signal["pair"] != "UNKNOWN" and signal["direction"] != "UNKNOWN":
                signals_storage.insert(0, signal)
                
                # Mantener solo las últimas señales
                if len(signals_storage) > MAX_SIGNALS:
                    signals_storage.pop()
                
                print(f"📊 Nueva señal: {signal['pair']} {signal['direction']} @ {signal['time']}")
            else:
                print(f"⚠️ Mensaje detectado pero sin datos válidos: {message_text[:50]}...")
    
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
