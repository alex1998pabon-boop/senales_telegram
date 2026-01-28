# 📝 INSTRUCCIONES PARA ARCHIVOS OCULTOS

Los archivos con punto inicial (.) son archivos ocultos en sistemas Unix/Linux.
Debido a las limitaciones de descarga, estos archivos están disponibles con nombres alternativos:

## Archivos incluidos:

### 1. gitignore.txt
**Renombrar a:** `.gitignore`

Este archivo indica a Git qué archivos NO debe rastrear (como credenciales, archivos temporales, etc.)

**Cómo usar:**
```bash
# En tu proyecto local, renombra:
mv gitignore.txt .gitignore

# O en Windows:
rename gitignore.txt .gitignore
```

### 2. env-example.txt
**Renombrar a:** `.env.example`

Este archivo es una plantilla para tus variables de entorno.

**Cómo usar:**
```bash
# En tu proyecto local, renombra:
mv env-example.txt .env.example

# O en Windows:
rename env-example.txt .env.example
```

## ⚠️ Importante:

- El archivo `.gitignore` es **opcional pero recomendado** si vas a usar Git
- El archivo `.env.example` es **solo una referencia**, las variables reales se configuran en Render.com
- NUNCA crees un archivo `.env` con valores reales y lo subas a GitHub

## 🚀 Para GitHub:

Antes de hacer tu primer commit:
```bash
mv gitignore.txt .gitignore
mv env-example.txt .env.example
git add .
git commit -m "Initial commit"
git push
```

## 📦 Estructura final del proyecto:

```
trading-signals/
├── .gitignore              ← Renombrado de gitignore.txt
├── .env.example            ← Renombrado de env-example.txt
├── main.py
├── requirements.txt
├── generate_session.py
├── README.md
├── DEPLOY.md
└── static/
    └── index.html
```

---

**Nota:** Si no usas Git, puedes ignorar estos archivos. La aplicación funcionará perfectamente sin ellos.
