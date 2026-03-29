# HYDRO-V: Sistema IoT de Predicción de Autonomía Hídrica 💧

Bienvenido al repositorio central de **HYDRO-V**. Este proyecto gestiona la telemetría, inferencia ML (fugas y autonomía) y centros de control para una amplia red de captación comunitaria basada en ESP32.

---

## 🛠️ Stack Tecnológico
- **Cloud Backend:** FastAPI (Python), PostgreSQL, InfluxDB, Redis
- **Infraestructura ML:** PyTorch, NetworkX (GNN Leak Detection), scikit-learn (Autonomía)
- **Frontend / Dashboard:** React, TypeScript, TailwindCSS
- **Control Mission:** Grafana + Alertas Automáticas
- **IoT & Edge:** ESP32, MQTT (HiveMQ), Sensores Físicos
- **DevOps:** Docker Compose, GitHub Actions CI/CD

---

## 🚀 Despliegue y CI/CD (GitHub Actions)

El proyecto cuenta con un flujo completo de automatización que:
1. Valida el código (Python Pytest/Ruff y Frontend ESLint/TSC)
2. Construye imágenes de Docker (Frontend / Backend)
3. Las publica en `ghcr.io` y despliega en entorno local/servidor VPS.

### 🔐 Variables y Secrets de Entorno (GitHub Secrets)

Para que los contenedores y el despliegue automático por GitHub Actions funcione correctamente, debes configurar los siguientes secretos en **Settings > Secrets and variables > Actions** de este repositorio:

| Nombre del Secret | Descripción |
|-------------------|-------------|
| `GITHUB_TOKEN` | Generado automáticamente. Necesario para escribir imágenes en GHCR. |
| `STAGING_HOST` | Dirección IP o hostname del servidor donde se hace el deploy. |
| `STAGING_USER` | Usuario SSH para la conexión (ej. `ubuntu`, `root`). |
| `STAGING_SSH_KEY` | Clave privada RSA/Ed25519 con acceso al servidor de staging. |

Para el backend (`hydrov-backend/.env`), debes crear los `.env` y asegurarte de tener la conectividad correcta a tu broker HiveMQ, PostgreSQL y bases InfluxDB tal cual está definido en el archivo `docker-compose.yml`.

---

> Hecho con 💙 para la innovación social del agua.
