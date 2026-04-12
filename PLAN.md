# SAPA Stats — Plan de Producto

## Visión

App de análisis táctico de handball en tiempo real.
Objetivo: usable desde el celular en cancha, escalable para vender a múltiples clubes.

## Distribución (mismo código, tres canales)

```
React + TypeScript (Vite)
    ├── Vercel          → browser (web, desktop, demo)
    ├── Capacitor APK   → Google Play Store (Android)
    └── Capacitor IPA   → Apple App Store (iOS)
```

No hay elección entre uno u otro: Capacitor envuelve el mismo frontend React
en una WebView nativa. Un solo codebase, tres formas de acceso.

## Stack tecnológico

| Capa | Tecnología | Hosting |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite + TailwindCSS | Vercel (gratis) |
| Mobile wrapper | Capacitor | APK → Play Store / IPA → App Store |
| Backend | FastAPI + Python | Railway (gratis hasta ~$5/mes) |
| Base de datos | PostgreSQL | Supabase (gratis hasta 500 MB) |

**Costo operativo inicial: $0/mes**
**Play Store (único pago): $25**
**App Store (anual): $99/año** — solo cuando se avance a iOS

---

## Fase 1 — Fundación mobile (prioridad máxima)

> Objetivo: app funcional en el celular con login, sin bugs críticos en pantalla.

### Backend
- [x] Agregar modelo `User` (email, password hash, role)
- [x] Endpoints `/auth/login`, `/auth/me`, `/auth/change-password`, `/auth/users` con JWT
- [x] Middleware que protege todos los endpoints existentes (27 endpoints)
- [ ] Persistir el timer del partido en la DB (campo `timer_seconds` en `Match`)
- [x] Variable de entorno `SECRET_KEY` para firmar tokens
- [x] Agregar `python-jose`, `passlib[bcrypt]`, `gunicorn` a `requirements.txt`

### Frontend
- [x] Pantalla de login (email + contraseña)
- [x] Guardar JWT en `localStorage`, adjuntarlo en cada request (`axios` interceptor)
- [x] Redirect a login si el token expira (401 → `/login`)
- [x] Botón de logout en el header
- [ ] Arreglar zonas de toque del `ScoreBoard` (botones +/− de 28px → mínimo 44px)
- [x] Agregar `viewport-fit=cover` en index.html para notch
- [ ] `inputmode="numeric"` en campos de número de camiseta
- [ ] Arreglar tabla de estadísticas en mobile (7 columnas → layout alternativo en xs)
- [x] `VITE_API_URL` environment variable

### Deploy
- [ ] DB en Supabase (crear proyecto, obtener connection string)
- [ ] Backend en Railway (conectar repo, configurar env vars)
- [x] Frontend configurado para GitHub Pages (workflow CI/CD + SPA routing)
- [ ] Migración inicial de tablas en Supabase

**Resultado de Fase 1:** URL pública con login. Vos y quien quieras pueden usarlo desde el browser del celu.

---

## Fase 2 — APK Android en Play Store

> Objetivo: app instalable en Android, publicada en Play Store (internal testing primero).

- [x] Instalar y configurar Capacitor 6 en el proyecto frontend
- [x] Agregar plataforma Android (`npx cap add android`)
- [x] Configurar `capacitor.config.ts` (app ID, nombre, plugins)
- [ ] Diseñar ícono (1024x1024) y splash screen
- [ ] Generar APK firmado (keystore)
- [ ] Crear cuenta Google Play Developer ($25 único pago)
- [ ] Subir a internal testing → probar en dispositivos reales
- [ ] Completar ficha de Play Store (descripción, capturas de pantalla, categoría: Deportes)
- [ ] Publicar en producción

**Resultado de Fase 2:** app descargable desde Play Store en Android.

---

## Fase 3 — Multi-tenant (listo para vender)

> Objetivo: poder crear un nuevo club, darle credenciales, y que solo vea sus datos.

### Backend
- [ ] Modelo `Club` (nombre, slug, activo)
- [ ] Vincular `User` a `Club` con `role` (superadmin / admin / analista)
- [ ] Vincular `Tournament`, `Team`, `Player`, `Match` a `Club`
- [ ] Todos los endpoints filtran automáticamente por el club del token JWT
- [ ] Un club nunca puede ver ni modificar datos de otro
- [ ] Endpoint de superadmin para crear clubes y usuarios iniciales

### Frontend
- [ ] El header muestra el nombre del club del usuario logueado
- [ ] Superadmin: panel simple para listar clubes y crear nuevos

### Negocio
- [ ] Definir precio por club (ej: suscripción mensual)
- [ ] Proceso manual de alta: superadmin crea club + usuario admin
- [ ] Script para migrar datos del club SAPA al nuevo modelo

**Resultado de Fase 3:** producto vendible. Cada club paga y accede solo a sus datos.

---

## Fase 4 — iOS / App Store

> Requiere Mac o servicio de build en la nube (ej: Codemagic).

- [ ] Agregar plataforma iOS a Capacitor (`npx cap add ios`)
- [ ] Ajustes específicos de iOS (gestos, notch, status bar)
- [ ] Crear cuenta Apple Developer ($99/año)
- [ ] Generar certificados y provisioning profiles
- [ ] Build con Xcode (o Codemagic si no tenés Mac)
- [ ] Subir a TestFlight → probar
- [ ] Completar ficha App Store (más estricta que Google Play)
- [ ] Publicar

**Resultado de Fase 4:** app en ambas tiendas, cubre Android + iPhone.

---

## Deuda técnica conocida (no bloquea pero hay que resolver)

| Problema | Impacto | Cuándo resolver |
|---|---|---|
| Timer solo clientside — se pierde si cerrás la app | Alto en cancha | Fase 1 |
| Sin `offline support` — requiere internet permanente | Medio | Fase 3+ |
| Botones de eliminar sin confirmación | Bajo | Fase 1 o 2 |
| Sin paginación en listas | Bajo hasta ~200 registros | Fase 3 |
| La versión Streamlit (`app/`) quedó obsoleta | Sin impacto | Borrar cuando se confirme Fase 1 |

---

## Estado actual del código

| Área | Estado |
|---|---|
| API REST (27 endpoints) | ✅ Completa, protegida con JWT |
| Autenticación backend | ✅ JWT + modelo User + roles (superadmin/admin/analyst) |
| Login frontend | ✅ LoginPage + AuthContext + rutas protegidas + logout |
| Capacitor Android | ✅ Inicializado, proyecto Android generado |
| GitHub Pages config | ✅ Workflow CI/CD + SPA routing |
| Backend deploy-ready | ✅ Procfile + gunicorn + railway.toml |
| Multi-tenant / Clubs | No existe |
| Deploy en producción | Pendiente (necesita cuentas Supabase + Railway) |
| Tests automatizados | No existen |

---

## Próximo paso: deploy

### Paso 1 — Crear cuentas (manual)
1. **Supabase**: https://supabase.com → crear proyecto → copiar connection string
2. **Railway**: https://railway.app → conectar repo GitHub → configurar env vars
3. **GitHub Pages**: Settings → Pages → Source: GitHub Actions

### Paso 2 — Configurar variables de entorno

**Railway (backend):**
- `DATABASE_URL` = la connection string de Supabase
- `SECRET_KEY` = un string random largo (ej: `openssl rand -hex 32`)
- `SUPERADMIN_EMAIL` = tu email
- `SUPERADMIN_PASSWORD` = contraseña segura
- `ALLOWED_ORIGINS` = `https://TU-USUARIO.github.io`

**GitHub repo → Settings → Variables (Actions):**
- `VITE_API_URL` = URL del backend en Railway (ej: `https://sapa-backend.up.railway.app`)
- `VITE_BASE` = `/analisis-handball/` (o `/` si usás dominio propio)

### Paso 3 — APK de prueba
```bash
cd frontend
npm run cap:android   # abre Android Studio
# Build → Build APK → instalar en celular
```
