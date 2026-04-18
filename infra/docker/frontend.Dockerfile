# infra/docker/frontend.Dockerfile
# ─────────────────────────────────────────────────────────────────
#  Multi-stage build para el frontend React/Vite de Hydro-V
#  Stage 1 (builder) : npm ci + vite build
#  Stage 2 (runtime) : Nginx sirviendo la SPA + proxy inverso a backend
# ─────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Instalar dependencias (aprovecha caché de capas)
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline --legacy-peer-deps

# Copiar el resto del código y compilar
COPY . .

# Build de producción — genera /app/dist
# El plugin basicSsl sólo aplica en dev; en build se ignora automáticamente
RUN npm run build


# ── Stage 2: Runtime con Nginx ────────────────────────────────────
FROM nginx:stable-alpine AS runtime

# Copiar el build de Vite al directorio público de Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Sobreescribir la config por defecto de Nginx con la nuestra
# El archivo default.conf está en la raíz de hydrov-frontend/
COPY default.conf /etc/nginx/conf.d/default.conf

# Puerto estándar HTTP (Nginx escucha en 80 según nuestro default.conf)
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s \
    CMD wget -qO- http://localhost/health || exit 1
