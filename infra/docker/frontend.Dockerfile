# infra/docker/frontend.Dockerfile
# ─────────────────────────────────────────────────────────────────
#  Multi-stage build para el frontend React/Vite de Hydro-V
#  Stage 1 (builder): npm install + vite build
#  Stage 2 (runtime): Nginx sirviendo los archivos estáticos
# ─────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar manifests primero (layer cache)
COPY package.json package-lock.json* ./

RUN npm ci --prefer-offline

# Copiar el resto del código y compilar
COPY . .

# Build de producción — genera /app/dist
RUN npm run build


# ── Stage 2: Runtime con Nginx ────────────────────────────────────
FROM nginx:alpine AS runtime

# Copiar el build de Vite al directorio de Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Configuración de Nginx para SPA (React Router)
# Redirige todas las rutas al index.html
RUN echo 'server { \
    listen 5173; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
    location /health { return 200 "ok"; add_header Content-Type text/plain; } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s \
    CMD wget -qO- http://localhost:5173/health || exit 1
