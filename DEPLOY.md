# 🚀 GUÍA RÁPIDA DE DESPLIEGUE

## Pasos para poner en producción (15 minutos)

### 1️⃣ Obtener credenciales de Telegram (5 min)

1. Ir a: https://my.telegram.org
2. Login con tu teléfono
3. "API development tools" → Crear app
4. Copiar `api_id` y `api_hash`

### 2️⃣ Generar Session String (5 min)

**En tu computadora local:**

```bash
pip install telethon
python generate_session.py
```

- Ingresar API_ID y API_HASH
- Ingresar código de verificación de Telegram
- Copiar el SESSION STRING generado (¡es muy largo!)

### 3️⃣ Subir a GitHub (2 min)

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/trading-signals.git
git push -u origin main
```

### 4️⃣ Desplegar en Render.com (3 min)

1. Ir a: https://render.com
2. New + → Web Service
3. Conectar repositorio de GitHub
4. Configurar:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free

5. Agregar Environment Variables:
   ```
   TELEGRAM_API_ID = (tu api_id)
   TELEGRAM_API_HASH = (tu api_hash)
   TELEGRAM_SESSION = (tu session string completo)
   TARGET_GROUP = alejandrosinalesgratis
   ```

6. Click "Create Web Service"

### 5️⃣ ¡Listo! 🎉

Tu app estará en: `https://tu-app.onrender.com`

---

## 📊 Verificar que funciona

```bash
# Health check
curl https://tu-app.onrender.com/api/health

# Ver señales
curl https://tu-app.onrender.com/api/signals
```

## 🔍 Ver logs

Render Dashboard → Tu servicio → Logs

Buscar:
- ✓ Cliente de Telegram conectado
- ✓ Escuchando mensajes del grupo
- 📨 Nuevo mensaje recibido

---

## ⚡ Mantener activo 24/7

Render Free duerme después de 15 min de inactividad.

**Solución**: Usar UptimeRobot (gratis)

1. Ir a: https://uptimerobot.com
2. Add New Monitor
3. Monitor Type: HTTP(s)
4. URL: `https://tu-app.onrender.com/api/health`
5. Interval: 5 minutos

---

## 🆘 Problemas comunes

**No recibo señales:**
- Verifica que estés en el grupo de Telegram
- Revisa los logs en Render
- Espera a que haya mensajes nuevos en el grupo

**"Service is sleeping":**
- Normal en Free tier
- Se despierta automáticamente
- Configura UptimeRobot para evitarlo

**"Telegram connection failed":**
- Verifica TELEGRAM_SESSION completo en variables
- Regenera el session string si es necesario

---

## 📱 Acceder a la interfaz

Abre en tu navegador:
```
https://tu-app.onrender.com
```

Verás:
- Estado de conexión
- Número de señales
- Grid con todas las señales
- Actualización automática cada 5 segundos

---

## 🔗 Integrar con otras apps

**Ejemplo con JavaScript:**
```javascript
fetch('https://tu-app.onrender.com/api/signals')
  .then(res => res.json())
  .then(data => {
    console.log('Señales:', data.signals);
  });
```

**Ejemplo con Python:**
```python
import requests

response = requests.get('https://tu-app.onrender.com/api/signals')
signals = response.json()['signals']

for signal in signals:
    print(f"{signal['pair']} {signal['direction']} @ {signal['entry_time']}")
```

---

**¿Dudas?** Revisa el README.md completo para más detalles.
