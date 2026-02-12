"""
Script para generar el TELEGRAM_SESSION string.
Ejecutar SOLO UNA VEZ desde tu computadora local antes de desplegar en Render.

IMPORTANTE: Si no tienes Telethon instalado, ejecuta primero:
    python -m pip install telethon

O si estás en Windows y tienes Python 3:
    py -m pip install telethon
"""

import asyncio
import sys

# Fix para Windows - configurar event loop policy
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("\n" + "=" * 60)
    print("   ❌ ERROR: Telethon no está instalado")
    print("=" * 60)
    print()
    print("Por favor, instala Telethon primero ejecutando:")
    print()
    print("   python -m pip install telethon")
    print()
    print("O si estás en Windows:")
    print()
    print("   py -m pip install telethon")
    print()
    print("Luego vuelve a ejecutar este script.")
    print()
    input("Presiona Enter para salir...")
    exit(1)

print("=" * 60)
print("   GENERADOR DE SESSION STRING PARA TELEGRAM")
print("=" * 60)
print()
print("Este script te ayudará a generar tu TELEGRAM_SESSION")
print("que necesitarás configurar en Render.com")
print()

API_ID = input("1️⃣  Ingresa tu TELEGRAM_API_ID: ").strip()
API_HASH = input("2️⃣  Ingresa tu TELEGRAM_API_HASH: ").strip()

if not API_ID or not API_HASH:
    print("\n❌ Error: API_ID y API_HASH son requeridos")
    input("Presiona Enter para salir...")
    exit(1)

print("\n🔄 Conectando a Telegram...")
print("   Te llegará un código de verificación a tu app de Telegram\n")


async def main():
    """Función principal asíncrona"""
    try:
        client = TelegramClient(StringSession(), int(API_ID), API_HASH)
        
        await client.connect()
        
        if not await client.is_user_authorized():
            phone = input("📱 Ingresa tu número de teléfono (ej: +573001234567): ").strip()
            await client.send_code_request(phone)
            code = input("🔐 Ingresa el código de verificación: ").strip()
            
            try:
                await client.sign_in(phone, code)
            except Exception as e:
                if 'password' in str(e).lower() or '2FA' in str(e) or 'SessionPasswordNeededError' in str(type(e).__name__):
                    password = input("🔑 Ingresa tu contraseña 2FA: ").strip()
                    await client.sign_in(password=password)
                else:
                    raise
        
        print("\n✅ ¡Autenticación exitosa!")
        
        session_string = client.session.save()
        
        print("\n" + "=" * 60)
        print("   TU SESSION STRING")
        print("=" * 60)
        print()
        print(session_string)
        print()
        print("=" * 60)
        print()
        print("⚠️  IMPORTANTE:")
        print("   1. Copia el texto de arriba COMPLETO")
        print("   2. Guárdalo de forma segura")
        print("   3. Lo necesitarás en Render como TELEGRAM_SESSION")
        print("   4. NUNCA lo compartas con nadie")
        print()
        print("✅ Ahora puedes cerrar este script y continuar con el")
        print("   despliegue en Render.com")
        print()
        
        # Guardar en archivo para facilitar copia
        try:
            with open("session_string.txt", "w") as f:
                f.write(session_string)
            print("💾 También se guardó en: session_string.txt")
            print("   (elimina este archivo después de copiarlo)")
            print()
        except:
            pass
        
        await client.disconnect()
        
    except Exception as e:
        print(f"\n❌ Error durante la autenticación: {e}")
        print("\nVerifica que:")
        print("   - Tu API_ID y API_HASH sean correctos")
        print("   - Tengas conexión a internet")
        print("   - Hayas ingresado el código de verificación correcto")
        print()


# Ejecutar la función asíncrona
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\n\n⚠️  Proceso cancelado por el usuario")
except Exception as e:
    print(f"\n❌ Error inesperado: {e}")

input("\nPresiona Enter para salir...")
