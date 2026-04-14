#!/bin/bash
# ============================================================
# get_token.sh — Obtiene y exporta el JWT token para demos ante el jurado
# ============================================================
#
# Credenciales del deployment HYDRO-V:
#   Email   : admin@hydrov.mx
#   Password: admin1234
#   (definidas en hydrov-backend/tests/conftest.py — user admin de prueba)
#
# Si el usuario admin en producción tiene credenciales distintas,
# sobreescribir con variables de entorno antes de ejecutar:
#   export HYDROV_ADMIN_EMAIL=otro@email.com
#   export HYDROV_ADMIN_PASSWORD=otraPassword
#   source get_token.sh
#
# Nota: El JWT tiene TTL de 24 horas (auth.py línea 95: expires_in=86400)
# — no es necesario renovarlo entre pruebas del mismo día.
# ============================================================
#
# Uso: source get_token.sh
# Después de ejecutar, usar $TOKEN en cualquier curl:
#   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
# ============================================================

EMAIL="${HYDROV_ADMIN_EMAIL:-admin@hydrov.mx}"
PASSWORD="${HYDROV_ADMIN_PASSWORD:-admin1234}"
API_URL="${HYDROV_API_URL:-http://localhost:8000}"

echo "🔑 Obteniendo token JWT para $EMAIL..."

RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $RESPONSE | python -c "import sys,json; print(json.load(sys.stdin).get('access_token','ERROR'))" 2>/dev/null)

if [ "$TOKEN" = "ERROR" ] || [ -z "$TOKEN" ]; then
  echo "❌ Error al obtener token. Respuesta del servidor:"
  echo $RESPONSE
  return 1
fi

export TOKEN
echo "✅ Token exportado como \$TOKEN"
echo "   Válido por 24 horas (TTL configurado en auth.py)"
echo ""
echo "Prueba rápida:"
echo "  curl -H 'Authorization: Bearer \$TOKEN' $API_URL/api/v1/auth/me"
