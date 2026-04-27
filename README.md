<div align="center">

<img src="https://img.shields.io/badge/IPN-CECyT_9_Juan_de_Dios_Bátiz-900000?style=for-the-badge&logo=academia&logoColor=white"/>
<img src="https://img.shields.io/badge/Premio_Nacional_Juvenil_del_Agua-2026-1a73e8?style=for-the-badge&logo=water&logoColor=white"/>

# 💧 HYDRO-V
### Sistema Ciber-Físico de Gestión Hídrica Inteligente

**Discriminación Adaptativa basada en IA · Datos Satelitales NASA · Resiliencia Urbana**

*Hydro-V: Cyber-Physical Smart Water Management System with AI-Driven Adaptive Discrimination and Satellite Data for Urban Resilience*

---

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![ESP32](https://img.shields.io/badge/ESP32-PlatformIO-E7352C?style=flat-square&logo=espressif&logoColor=white)](https://platformio.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2+-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![TRL](https://img.shields.io/badge/TRL-4_(Validado)-green?style=flat-square)](https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Shaping_the_Future/Technology_Readiness_Levels)
[![ODS](https://img.shields.io/badge/ODS-6_%7C_11_%7C_13-blue?style=flat-square)](https://sdgs.un.org/goals)
[![Licencia](https://img.shields.io/badge/Licencia-MIT-yellow?style=flat-square)](./LICENSE)

</div>

---

## 📑 Índice

1. [Sobre el Proyecto](#-sobre-el-proyecto)
2. [La Problemática: Una Crisis Multidimensional](#-la-problemática-una-crisis-multidimensional)
3. [Solución: Arquitectura Ciber-Física](#-solución-arquitectura-ciber-física)
4. [Características e Innovaciones Clave](#-características-e-innovaciones-clave)
5. [Arquitectura del Sistema](#-arquitectura-del-sistema)
   - [Diagrama de Flujo de Datos](#diagrama-de-flujo-de-datos)
   - [Stack Tecnológico](#stack-tecnológico)
6. [Estructura del Repositorio](#-estructura-del-repositorio)
7. [Módulos del Sistema](#-módulos-del-sistema)
   - [Edge — Firmware ESP32](#1-edge--firmware-esp32)
   - [Backend — FastAPI](#2-backend--fastapi)
   - [Frontend — React/Vite](#3-frontend--reactvite)
   - [ML — Modelos de IA](#4-ml--modelos-de-ia)
   - [Infraestructura](#5-infraestructura)
8. [Primeros Pasos](#-primeros-pasos)
   - [Prerrequisitos](#prerrequisitos)
   - [Configuración de Variables de Entorno](#configuración-de-variables-de-entorno)
   - [Despliegue con Docker](#despliegue-con-docker)
   - [Desarrollo Local](#desarrollo-local)
   - [Flasheo del Firmware ESP32](#flasheo-del-firmware-esp32)
9. [API Reference](#-api-reference)
10. [Algoritmos Core](#-algoritmos-core)
    - [Discriminación Adaptativa dT/dt](#discriminación-adaptativa-dtdt)
    - [Máquina de Estados Finitos (FSM)](#máquina-de-estados-finitos-fsm)
    - [Predicción de Autonomía Hídrica](#predicción-de-autonomía-hídrica)
    - [Detección de Fugas con GNN](#detección-de-fugas-con-gnn)
11. [Hardware y Prototipo](#-hardware-y-prototipo)
12. [Resultados y Validación](#-resultados-y-validación)
13. [Alineación con los ODS](#-alineación-con-los-ods)
14. [Trabajo Futuro](#-trabajo-futuro)
15. [Presupuesto del Prototipo](#-presupuesto-del-prototipo)
16. [Contacto y Equipo](#-contacto-y-equipo)
17. [Referencias](#-referencias)
18. [Licencia](#-licencia)

---

## 🌊 Sobre el Proyecto

**Hydro-V** es un sistema ciber-físico (Cyber-Physical System, CPS) de gestión hídrica domiciliaria diseñado específicamente para mitigar la crisis multidimensional del agua en zonas urbanas de alta vulnerabilidad. Desarrollado en el **CECyT 9 "Juan de Dios Bátiz" del IPN** como candidato al **Premio Nacional Juvenil del Agua 2026**, el proyecto representa la aplicación de tecnologías de la Industria 4.0 a uno de los problemas sociales más urgentes de las megaciudades latinoamericanas.

El sistema transforma cada vivienda en un **nodo activo de gestión hídrica**, capaz de:

- **Discriminar inteligentemente** entre agua de calidad apta para almacenamiento y agua de primer arrastre (turbidez alta), usando un algoritmo propio de derivada temporal.
- **Captar y filtrar** agua pluvial y de red en tiempo real, con una mejora del **40% en eficiencia** respecto a sistemas tradicionales de desecho fijo.
- **Predecir la autonomía hídrica** del hogar (en días) integrando datos satelitales de precipitación de la **NASA POWER API**.
- **Detectar fugas** en la red hídrica local mediante una Red Neuronal de Grafos (GNN/GraphSAGE).
- **Emitir alertas** y permitir **control remoto** del nodo desde un dashboard web en tiempo real.

> **Presupuesto del prototipo (TRL 4): $3,200 MXN · ROI estimado: ~8 meses**

---

## ⚠️ La Problemática: Una Crisis Multidimensional

La crisis hídrica de la Zona Metropolitana del Valle de México (ZMVM) opera en cuatro dimensiones críticas que se manifiestan de forma escalonada:

| Nivel | Indicador | Cifra |
|-------|-----------|-------|
| 🌍 **Global** | Personas sin agua potable segura | 2,200 millones |
| 🌍 **Global** | Personas con escasez severa (≥1 mes/año) | ~4,000 millones |
| 🇲🇽 **México (2024)** | Territorio con algún grado de sequía | 75% |
| 🇲🇽 **México (2024)** | Embalses principales promedio | ~37% de capacidad |
| 🏙️ **ZMVM** | Presión hídrica de la Región XIII | **128.5%** |
| 🏙️ **ZMVM** | Sistema Cutzamala (máx. crisis 2024) | ~34.7% de capacidad |
| 🏙️ **ZMVM** | Habitantes con agua por tandeo (estrato bajo) | **80% en CDMX** |
| 📍 **Nezahualcóyotl** | Reducción en suministro Cutzamala | De 650 → 200 L/s (**-70%**) |
| 📍 **Nezahualcóyotl** | Costo del agua por pipa vs. red | **Hasta 15× más caro** |

### El Fenómeno del "Primer Arrastre" (*First Flush*)

Cuando inicia una lluvia, las superficies urbanas liberan la carga contaminante acumulada durante el período seco: sedimentos, metales pesados, hidrocarburos y bacterias. La turbidez del agua pluvial inicial puede alcanzar **50–200 NTU**, muy por encima del límite de 5 NTU de la NOM-127-SSA1-1994. Los sistemas tradicionales desechan un volumen fijo (ej. 5 minutos de agua) sin importar la intensidad real de la lluvia, desperdiciando hasta un **40% del agua recuperable**.

Hydro-V resuelve exactamente esto: analiza la *tasa de cambio de la turbidez* (dT/dt) para detectar matemáticamente el instante preciso en que el flujo es apto para almacenamiento.

---

## 🔬 Solución: Arquitectura Ciber-Física

Hydro-V implementa una arquitectura de **"Doble Barrera"** para garantizar la calidad del agua almacenada:

```
Lluvia / Red Municipal
         │
         ▼
 ┌───────────────┐
 │  Sensor de    │  ← Turbidímetro nefelométrico (0–3000 NTU)
 │  Turbidez     │     Caudalímetro (YF-S201, efecto Hall)
 │  (ADC 12-bit) │     Sensor ultrasónico de nivel (JSN-SR04T)
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │  ESP32 FSM    │  ← Filtro DSP media móvil (N=10 muestras)
 │  dT/dt Algo   │     Cálculo de derivada discreta
 │  (Edge Layer) │     Máquina de estados: IDLE/REJECT/INTAKE/ERROR
 └───────┬───────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  V_reject  V_intake  ← Válvulas solenoides 12V NC (fail-safe)
  (drenaje)   │
              ▼
     ┌─────────────────┐
     │  FILTRO PRO-V   │  ← BARRERA 2: Filtración físico-química
     │  ① Fibra 50µm   │     ① Pre-filtro mecánico
     │  ② Zeolita 2kg  │     ② Intercambio catiónico (metales)
     │  ③ Carbón 1kg   │     ③ Adsorción orgánica (olor/sabor)
     └────────┬────────┘
              │  < 5 NTU (NOM-127 ✓)
              ▼
           CISTERNA
```

---

## ✨ Características e Innovaciones Clave

### 🧠 Algoritmo de Discriminación Adaptativa (dT/dt)
La innovación central. En lugar de desechar un volumen fijo de agua, el firmware calcula la **derivada temporal de la turbidez** en tiempo real usando diferencias finitas sobre una ventana deslizante. Esto permite identificar con precisión cuándo el flujo *se está aclarando activamente*, no solo cuándo ya está limpio.

```
dT/dt ≈ (T_n - T_{n-1}) / Δt
```

- `dT/dt << 0` → Turbidez cayendo rápido → **CAPTACIÓN** ✅
- `dT/dt ≈ 0` y `T < umbral` → Agua estable y limpia → **CAPTACIÓN** ✅
- `dT/dt > 0` → Turbidez aumentando → **RECHAZO** 🚫

### 🤖 IA en el Edge y en la Nube
- **Edge (ESP32):** FSM determinista en tiempo real con filtros DSP (media móvil de 10 muestras para turbidez, 5 para ultrasonido).
- **Nube (Python/PyTorch):** GNN GraphSAGE de 3 capas para detección de fugas al correlacionar múltiples nodos vecinos. MLP de fallback para inferencia individual.
- **Regresión lineal supervisada:** Predicción de días de autonomía hídrica con features de NASA POWER.

### 🛰️ Integración NASA POWER
El backend consulta automáticamente (via APScheduler) la [NASA POWER API](https://power.larc.nasa.gov/) para obtener pronósticos de precipitación locales en Ciudad Nezahualcóyotl, integrándolos como feature en el modelo de autonomía.

### 📡 Telemetría en Tiempo Real
Pipeline completo: `ESP32 → MQTT/HiveMQ Cloud → FastAPI → InfluxDB → Redis (caché) → WebSocket → Dashboard React`.

### 🔐 Seguridad por Diseño
- JWT HS256 para autenticación de usuarios.
- Válvulas solenoides **Normalmente Cerradas (NC)**: ante fallo eléctrico, el sistema cae en modo seguro (no capta agua).
- Control remoto con auditoría de comandos (quién envió qué acción y cuándo).

### 📊 Dashboard Operacional
Interfaz React/TypeScript con paneles de: nivel de cisterna, turbidez en vivo, histórico (Recharts), estado FSM, predicción de autonomía, score de fugas y alertas.

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Flujo de Datos

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CAPA FÍSICA (EDGE)                          │
│   Sensores ─► ESP32 (FreeRTOS) ─► FSM dT/dt ─► Válvulas Rele      │
│                    │                                                 │
│                    └─── MQTT (HiveMQ Cloud TLS) ──────────┐         │
└─────────────────────────────────────────────────────────────────────┘
                                                             │
┌────────────────────────────────────────────────────────────▼────────┐
│                       CAPA BACKEND (FastAPI)                        │
│                                                                     │
│  MQTT Listener ─► Parser JSON ─► InfluxDB (serie temporal)         │
│                              └─► PostgreSQL (catálogos/alertas)     │
│                              └─► Redis (caché último estado)         │
│                                                                     │
│  APScheduler ─► NASA POWER API ─► PostgreSQL (clima)               │
│                                                                     │
│  ML Service ─► GNN (fugas) / LinearRegression (autonomía)          │
│                                                                     │
│  REST API v1 ─────────────────────────────────────────────────┐    │
│  WebSocket ───────────────────────────────────────────────────┤    │
└───────────────────────────────────────────────────────────────│────┘
                                                                │
┌───────────────────────────────────────────────────────────────▼────┐
│                      CAPA FRONTEND (React/Vite)                     │
│                                                                     │
│  Dashboard │ Control │ Alertas │ Historial │ Configuración          │
│                                                                     │
│  Recharts │ Framer Motion │ MQTT Client (WS) │ Lucide Icons        │
└────────────────────────────────────────────────────────────────────┘

                          ↕  Grafana (monitoreo técnico)
```

### Stack Tecnológico

| Capa | Tecnología | Versión | Rol |
|------|-----------|---------|-----|
| **Firmware** | ESP32 / PlatformIO | Framework Arduino | Microcontrolador de 32 bits, dual-core |
| **Firmware** | FreeRTOS | integrado | Multitarea: sensores, MQTT, monitor WiFi |
| **Firmware** | C++17 / ArduinoJson | 6.21.5 | Serialización JSON para MQTT |
| **Firmware** | PubSubClient | 2.8.0 | Cliente MQTT con TLS |
| **Backend** | Python | 3.11+ | Lenguaje principal del servidor |
| **Backend** | FastAPI | 0.110+ | Framework REST + WebSocket |
| **Backend** | SQLAlchemy (async) | 2.0+ | ORM para PostgreSQL |
| **Backend** | Alembic | 1.13+ | Migraciones de base de datos |
| **Backend** | aiomqtt | 1.2+ | Suscripción MQTT asíncrona |
| **Backend** | APScheduler | 3.10+ | Ingesta periódica NASA POWER |
| **Base de datos** | PostgreSQL | 15 | Catálogos: dispositivos, zonas, alertas |
| **Base de datos** | InfluxDB | 2.7 | Serie temporal de telemetría |
| **Base de datos** | Redis | 7.2 | Caché de últimos estados (TTL 60s) |
| **ML** | PyTorch | 2.2+ | GNN GraphSAGE para detección de fugas |
| **ML** | PyTorch Geometric | latest | Capas SAGEConv |
| **ML** | scikit-learn | 1.4+ | Regresión lineal de autonomía |
| **Frontend** | React | 18.3 | UI del dashboard |
| **Frontend** | TypeScript | 5.4 | Tipado estático |
| **Frontend** | Vite | 5.2 | Bundler ultra-rápido |
| **Frontend** | Recharts | 2.12 | Gráficas de telemetría |
| **Frontend** | Framer Motion | 11.0 | Animaciones de UI |
| **Frontend** | Tailwind CSS | 3.4 | Estilos utility-first |
| **Infra** | Docker Compose | latest | Orquestación de servicios |
| **Infra** | Nginx | Alpine | Reverse proxy + SPA server (integrado en frontend container) |
| **Infra** | Grafana | 10.4.0 | Dashboard técnico de monitoreo |
| **Broker** | HiveMQ Cloud | TLS 8883 | Broker MQTT en la nube |
| **Seguridad** | bcrypt | 3.1.7 (pinned) | Hashing de contraseñas (compatibilidad passlib) |

---

## 📁 Estructura del Repositorio

```
HYDRO-V/
│
├── 📁 edge/                          # Firmware para ESP32 (PlatformIO)
│   ├── platformio.ini                # Configuración del entorno y dependencias
│   └── src/
│       ├── main.cpp                  # Punto de entrada; tareas FreeRTOS
│       ├── fsm_core.cpp              # FSM ciclo de vida: Despertar→Leer→Reportar→Dormir
│       ├── fsm_logic.cpp             # FSM de válvulas: lógica dT/dt y estados hídricos
│       ├── dsp_filters.cpp           # Filtros media móvil (turbidez N=10, ultrasonido N=5)
│       ├── hal_sensors.cpp           # HAL: lectura de turbidímetro, caudalímetro, ultrasonido
│       ├── hal_actuators.cpp         # HAL: control de válvulas solenoides
│       ├── net_mqtt.cpp              # Cliente MQTT: pub/sub y reconexión automática
│       ├── telemetry.cpp             # Serialización JSON y guardado offline (SPIFFS)
│       └── storage_fs.cpp            # Sistema de archivos para persistencia offline
│
├── 📁 hydrov-backend/                # Backend Python / FastAPI
│   ├── requirements.txt              # Dependencias principales
│   ├── requirements-dev.txt          # Dependencias de desarrollo y testing
│   ├── requirements-extra.txt        # Extras opcionales (ML pesado)
│   ├── alembic.ini                   # Configuración de migraciones DB
│   ├── alembic/                      # Scripts de migración de PostgreSQL
│   ├── app/
│   │   ├── main.py                   # Startup, lifespan, CORS manual, health check
│   │   ├── config.py                 # Pydantic Settings (variables de entorno)
│   │   ├── api/v1/
│   │   │   ├── router.py             # Agrupación de todos los sub-routers
│   │   │   └── endpoints/
│   │   │       ├── auth.py           # Login/logout JWT
│   │   │       ├── devices.py        # CRUD de dispositivos ESP32
│   │   │       ├── zones.py          # Gestión de zonas geográficas
│   │   │       ├── telemetry.py      # Consulta de datos de sensores
│   │   │       ├── alerts.py         # Listado y gestión de alertas
│   │   │       ├── control.py        # Comandos remotos al ESP32 via MQTT
│   │   │       └── predictions.py    # Autonomía hídrica + detección de fugas (ML)
│   │   ├── core/
│   │   │   ├── security.py           # JWT (HS256), bcrypt, OAuth2
│   │   │   └── logger.py             # Logger estructurado
│   │   ├── models/                   # ORM SQLAlchemy (12 modelos)
│   │   │   ├── device.py             # Nodo IoT (device_code, lat, lon, zonas)
│   │   │   ├── zone.py               # Zona geográfica / colonia
│   │   │   ├── alert.py              # Alertas generadas por la FSM o el ML
│   │   │   ├── alert_type.py         # Catálogo de tipos de alertas
│   │   │   ├── sensor.py             # Catálogo de sensores por dispositivo
│   │   │   ├── sensor_type.py        # Catálogo de tipos de sensor ← nuevo
│   │   │   ├── user.py               # Usuarios del dashboard
│   │   │   ├── role.py               # Roles de usuario (RBAC) ← nuevo
│   │   │   ├── valve.py              # Estado de válvulas registrado
│   │   │   ├── valve_type.py         # Catálogo de tipos de válvula ← nuevo
│   │   │   └── audit_log.py          # Log de auditoría de comandos
│   │   ├── services/
│   │   │   ├── mqtt_service.py       # Listener aiomqtt → InfluxDB + PG + Redis
│   │   │   ├── influx_service.py     # Lectura/escritura InfluxDB (2 measurements)
│   │   │   ├── redis_service.py      # Caché Redis (estado nodo, throttle 60s)
│   │   │   ├── ml_service.py         # Puente backend ↔ hydrov-ml (autonomía + fugas)
│   │   │   ├── nasa_service.py       # Cliente NASA POWER API
│   │   │   ├── nasa_ingestion.py     # Ingesta periódica (APScheduler 3 jobs)
│   │   │   ├── nasa_parser.py        # Parseo de respuestas NASA
│   │   │   ├── websocketservice.py   # Broadcast WebSocket al frontend
│   │   │   └── device_cache.py       # Caché de metadatos de dispositivos
│   │   ├── schemas/                  # Pydantic v2 schemas (validación I/O REST)
│   │   │   ├── mqtt.py               # ESP32PayloadSchema, SensorsSchema, SystemStateSchema
│   │   │   ├── telemetry.py          # TelemetryResponseSchema, TelemetryListSchema
│   │   │   ├── alert.py              # AlertResponseSchema, AlertListSchema
│   │   │   ├── device.py             # DeviceCreateSchema, DeviceResponseSchema
│   │   │   ├── prediction.py         # AutonomyResponseSchema, LeakResponseSchema
│   │   │   └── user.py               # UserCreateSchema, TokenSchema
│   │   ├── db/
│   │   │   ├── init_db.py            # Inicialización de tablas
│   │   │   └── influx_client.py      # Singleton async InfluxDB client
│   │   └── seed.py                   # Datos iniciales de catálogos (v2.0)
│   ├── scripts/
│   │   └── deploy.sh                 # Script de despliegue automatizado
│   └── tests/                        # Suite de pruebas pytest
│       ├── conftest.py               # Fixtures globales (DB, auth, mocks)
│       ├── tests_api/
│       │   └── test_alerts.py        # Tests de endpoint /alerts
│       └── tests_services/
│           ├── test_influx_service.py
│           ├── test_ml_service.py
│           ├── test_mqtt_service.py
│           ├── test_nasa_service.py
│           └── test_websocket_service.py
│
├── 📁 hydrov-frontend/               # Frontend React + TypeScript + Vite
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── default.conf                  # Nginx config integrada (SPA + proxy /api/)
│   └── src/
│       ├── App.tsx                   # Shell principal: auth guard + SPA routing
│       ├── pages/                    # Rutas de alto nivel
│       │   ├── DashboardPage.tsx     # Panel principal con telemetría en vivo
│       │   ├── AlertsPage.tsx        # Historial de alertas
│       │   ├── ControlPage.tsx       # Control remoto de válvulas
│       │   ├── HistoryPage.tsx       # Histórico de datos (gráficas)
│       │   ├── SettingsPage.tsx      # Configuración del sistema
│       │   └── LoginPage.tsx         # Autenticación JWT
│       ├── views/                    # Sub-vistas del AppShell (sin re-render de layout)
│       │   ├── HistoryView.tsx       # Gráficas históricas
│       │   ├── AnalyticsView.tsx     # Inteligencia hídrica (ML insights)
│       │   └── SettingsView.tsx      # Ajustes del sistema
│       ├── components/               # Componentes reutilizables
│       │   ├── Login.tsx             # Componente de autenticación con device code
│       │   ├── dashboard/            # Widgets del panel principal
│       │   │   ├── WaterLevelGauge.tsx
│       │   │   ├── AutonomyCard.tsx
│       │   │   ├── RainPredictorWidget.tsx
│       │   │   ├── ClimatologyChart.tsx
│       │   │   ├── WeatherWidget.tsx
│       │   │   ├── LocationWidget.tsx
│       │   │   ├── TurbidityChart.tsx
│       │   │   ├── FlowRateChart.tsx
│       │   │   └── LeakAlertBanner.tsx
│       │   ├── control/              # Botones de comando remoto
│       │   ├── maps/                 # Visualización de nodos en mapa
│       │   └── common/               # Navbar, Sidebar (hamburger), NotificationsPanel
│       ├── services/                 # Clientes HTTP y WebSocket
│       ├── store/                    # Estado global
│       ├── hooks/
│       │   ├── useTelemetry.ts       # useHydroData: polling + WebSocket
│       │   ├── useAuth.ts
│       │   ├── useDeviceControl.ts
│       │   └── useWebSocket.ts
│       ├── styles/
│       │   └── global.css            # Estilos globales + tokens de diseño
│       ├── types/                    # Interfaces TypeScript
│       └── utils/                    # Helpers y formateadores
│
├── 📁 hydrov-ml/                     # Módulo de Machine Learning
│   ├── requirements.txt
│   └── src/
│       ├── models/
│       │   ├── gnn_leak_detection.py # HydroGNN (GraphSAGE) + MLP fallback
│       │   ├── linear_autonomy.py    # AutonomyPredictor (sklearn LinearRegression)
│       │   └── gan_synthetic.py      # GAN para generación de datos sintéticos
│       ├── training/                 # Scripts de entrenamiento
│       ├── inference/                # Pipelines de inferencia
│       ├── data/                     # Datasets y scripts de preprocesamiento
│       └── utils/                    # Utilidades: normalización, features, etc.
│
├── 📁 infra/                         # Infraestructura y DevOps
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   ├── frontend.Dockerfile
│   │   └── nginx.conf
│   ├── db/
│   │   ├── init_postgres.sql         # Schema inicial de PostgreSQL
│   │   └── init_influxdb.sh          # Inicialización de InfluxDB
│   ├── grafana/
│   │   ├── provisioning/             # Datasources y dashboards auto-provisionados
│   │   └── dashboards/               # JSONs de dashboards Grafana
│   ├── ci-cd/                        # Pipelines de CI/CD (GitHub Actions)
│   └── scripts/                      # Scripts de mantenimiento
│
├── 📁 docs/                          # Documentación técnica del proyecto
│   ├── architecture/                 # Diagramas de arquitectura
│   ├── hardware/                     # Esquemáticos del circuito y lista de materiales
│   ├── hydraulic/                    # Diagramas hidráulicos (P&ID)
│   ├── IA-ML/                        # Documentación de modelos ML
│   ├── manuals/                      # Manuales de instalación y uso
│   └── reports/                      # Reportes de validación experimental
│
├── 📁 scripts/                       # Scripts de utilidad raíz
│   ├── seed_redis_gnn.py             # Sembrar datos de prueba en Redis para GNN
│   ├── build_models.py               # Entrenamiento y exportación de modelos ML
│   ├── test_mqtt.py                  # Test de publicación MQTT
│   ├── test_gate4.py                 # Test del pipeline completo (Gate 4)
│   └── get_token.sh                  # Obtiene JWT para pruebas de API
│
├── docker-compose.yml                # Orquestación: Postgres, InfluxDB, Redis,
│                                     # Backend, Frontend, Nginx, Grafana
├── .env                              # Variables de entorno (NO subir a Git)
└── README.md                         # Este archivo
```

---

## 🔧 Módulos del Sistema

### 1. Edge — Firmware ESP32

El firmware está desarrollado en **C++17** sobre el framework Arduino con **PlatformIO** y utiliza **FreeRTOS** para multitarea real.

**Tareas FreeRTOS:**
| Tarea | Core | Prioridad | Período | Función |
|-------|------|-----------|---------|---------|
| `taskSensores` | 1 | 2 | 2s | Lee sensores, filtra con DSP, actualiza FSM de válvulas |
| `taskMQTT` | 1 | 2 | 2s | Publica telemetría JSON al broker HiveMQ |
| `taskWiFiMonitor` | 0 | 1 | 10s | Monitorea y reconecta WiFi/MQTT |

**FSM de Válvulas — Estados:**
```
SYSTEM_IDLE   → Sin flujo, o cisterna llena, o modo manual IDLE
WATER_REJECT  → Agua turbia (primer arrastre), válvula de rechazo abierta
WATER_INTAKE  → Agua validada por dT/dt, válvula de captación abierta
SYSTEM_ERROR  → Sensor fuera de rango, cierre total de seguridad
```

**Sensores integrados:**
- Turbidímetro analógico Gravity (ADC 12-bit, 0–3000 NTU)
- Caudalímetro de efecto Hall YF-S201 (~450 pulsos/L)
- Sensor ultrasónico impermeable JSN-SR04T (20–450 cm, ±1 cm)

### 2. Backend — FastAPI

API REST + WebSocket con arquitectura de servicios desacoplados.

**Endpoints principales (API v1):**
```
POST   /api/v1/auth/login              → Obtiene JWT
GET    /api/v1/devices                 → Lista dispositivos registrados
GET    /api/v1/devices/{id}            → Detalles de un nodo
GET    /api/v1/telemetry/{node_id}     → Último estado del sensor
GET    /api/v1/alerts                  → Historial de alertas
POST   /api/v1/control/{node_id}/command → Envía comando al ESP32
GET    /api/v1/predictions/{node_id}/autonomy → Días de autonomía hídrica
GET    /api/v1/predictions/{node_id}/leaks    → Score de detección de fuga
GET    /api/v1/predictions/{node_id}/full     → Autonomía + fugas combinado
GET    /health                         → Health check del sistema
```

**Servicios en background:**
- **MQTT Listener:** Suscripción continua a `hydrov/+/telemetry`, escribe en InfluxDB y PostgreSQL.
- **NASA Scheduler:** Ingesta horaria, diaria y mensual de datos meteorológicos.
- **WebSocket Broadcast:** Empuja actualizaciones en tiempo real al dashboard.

### 3. Frontend — React/Vite

SPA (Single Page Application) con TypeScript y Tailwind CSS. La navegación principal se gestiona en `App.tsx` mediante un `AppShell` con `Sidebar` + `Navbar` responsivos (hamburger menu en móvil) y `AnimatePresence` de Framer Motion para transiciones suaves entre vistas.

**Vistas del AppShell:**
| Vista / Sección | Descripción |
|-----------------|-------------|
| `dashboard` | Telemetría en vivo: `WaterLevelGauge`, `AutonomyCard`, `RainPredictorWidget`, stats rápidas |
| `history` → `HistoryView` | Gráficas históricas de turbidez, nivel y caudal (Recharts) |
| `analytics` → `AnalyticsView` | Inteligencia hídrica: climatología, predicciones ML, mapa de nodos |
| `settings` → `SettingsView` | Configuración de umbrales, preferencias y control remoto |

**Componentes del Dashboard:**
| Componente | Función |
|------------|--------|
| `WaterLevelGauge` | Gauge animado del nivel de cisterna (%) |
| `AutonomyCard` | Días de autonomía hídrica predichos por ML |
| `RainPredictorWidget` | Pronóstico de precipitaciones NASA + gráfica |
| `ClimatologyChart` | Histórico climatológico (temperatura, humedad) |
| `WeatherWidget` | Estado climático actual integrado NASA POWER |
| `LocationWidget` | Mapa de ubicación del nodo activo |
| `TurbidityChart` | Gráfica de turbidez en tiempo real |
| `FlowRateChart` | Gráfica de caudal (L/min) |
| `LeakAlertBanner` | Banner de alerta de fuga (warning / danger) |

**Common:**
- `Sidebar` — Navegación lateral con collapse en desktop y drawer en móvil
- `Navbar` — Barra superior con estado de conexión, badge de notificaciones y menú hamburger
- `NotificationsPanel` — Panel slide-over de notificaciones

### 4. ML — Modelos de IA

#### `HydroGNN` — Detección de Fugas
```python
# Arquitectura GraphSAGE (3 capas convolucionales)
SAGEConv(8 → 64) → ReLU → Dropout(0.3)
SAGEConv(64 → 32) → ReLU → Dropout(0.3)
SAGEConv(32 → 16) → ReLU
Linear(16 → 8) → ReLU
Linear(8 → 2)  → log_softmax  # {normal, fuga}
```
Cada nodo del grafo representa un sensor Hydro-V con 8 features: `[turbidez_norm, flujo_norm, nivel_norm, presion_est, delta_turbidez, delta_flujo, hora_sin, hora_cos]`.

#### `LeakDetectorMLP` — Fallback Individual
MLP de 3 capas para cuando el grafo completo no está disponible. Retorna probabilidad de fuga ∈ [0, 1].

#### `AutonomyPredictor` — Predicción de Autonomía
Regresión lineal múltiple (con StandardScaler) entrenada con:
- `nivel_actual_litros`, `consumo_7d_lpm` (desde InfluxDB últimos 7 días)
- `forecast_precip_mm` (NASA POWER próximas 72h), `temperatura_c`, `humedad_pct`
- `days_without_rain` (calculado desde InfluxDB), `mes`

El pipeline de inferencia vive en `hydrov-ml/src/inference/predict_autonomy.py`. Modo fallback físico disponible si no hay modelo entrenado.

### 5. Infraestructura

El sistema se despliega completo con `docker-compose up` levantando **6 servicios** (Nginx ya no es un servicio separado — está integrado en el container del frontend):

```yaml
services:
  postgres    # Catálogos y alertas (PostgreSQL 15)
  influxdb    # Telemetría de series temporales (InfluxDB 2.7)
  redis       # Caché de estado (TTL 60s, maxmemory 256mb LRU)
  backend     # FastAPI (puerto 8000)
  frontend    # React/Vite + Nginx integrado (puerto 80)
  grafana     # Dashboard técnico (puerto 3000)
```

> **Nota:** El container `frontend` sirve la SPA compilada **y** hace proxy inverso de `/api/` → backend. El servicio `nginx` independiente está desactivado en `docker-compose.yml`.

---

## 🚀 Primeros Pasos

### Prerrequisitos

| Herramienta | Versión mínima | Uso |
|-------------|---------------|-----|
| Docker Desktop | 24+ | Contenedores |
| Docker Compose | 2.20+ | Orquestación |
| PlatformIO Core | 6.x | Flasheo de firmware |
| Node.js + npm | 18+ | Desarrollo frontend |
| Python | 3.11+ | Desarrollo backend |
| Git | 2.x | Control de versiones |

### Configuración de Variables de Entorno

Copia y configura el archivo de variables de entorno:

```bash
cp .env.example .env
```

**Variables críticas a configurar:**

```env
# ── PostgreSQL ──────────────────────────────────────────────
POSTGRES_USER=hydrov
POSTGRES_PASSWORD=tu_password_seguro
POSTGRES_DB=hydrov

# ── InfluxDB ────────────────────────────────────────────────
INFLUX_TOKEN=tu_token_influxdb
INFLUX_ORG=hydrov
INFLUX_BUCKET=sensor_telemetry

# ── Redis ───────────────────────────────────────────────────
REDIS_PASSWORD=tu_password_redis

# ── Seguridad / JWT ─────────────────────────────────────────
SECRET_KEY=clave_secreta_min_32_chars
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── MQTT (HiveMQ Cloud) ─────────────────────────────────────
MQTT_HOST=tu-cluster.hivemq.cloud
MQTT_PORT=8883
MQTT_USER=tu_usuario_mqtt
MQTT_PASSWORD=tu_password_mqtt

# ── NASA POWER ──────────────────────────────────────────────
NASA_LAT=19.4066        # Latitud Ciudad Nezahualcóyotl
NASA_LON=-99.0131       # Longitud Ciudad Nezahualcóyotl

# ── Grafana ─────────────────────────────────────────────────
GRAFANA_PASSWORD=tu_password_grafana
```

### Despliegue con Docker

```bash
# 1. Clonar el repositorio
git clone https://github.com/TuUsuario/HYDRO-V.git
cd HYDRO-V

# 2. Configurar variables de entorno
cp .env.example .env
# Edita .env con tus credenciales

# 3. Levantar todos los servicios
docker compose up -d

# 4. Verificar que todos los servicios están sanos
docker compose ps

# 5. Ver logs en tiempo real
docker compose logs -f backend
```

**URLs de acceso:**
| Servicio | URL | Descripción |
|----------|-----|-------------|
| Dashboard | http://localhost | Interfaz principal (puerto 80, Nginx integrado) |
| Dashboard (red local) | http://\<IP-LAN\> | Acceso desde móvil en la misma red |
| API REST | http://localhost:8000/docs | Swagger UI (solo cuando `DEBUG=true`) |
| Grafana | http://localhost:3000 | Dashboard técnico de monitoreo |
| InfluxDB | http://localhost:8086 | Administración de datos |
| Health | http://localhost:8000/health | Estado de servicios |

### Desarrollo Local

**Backend:**
```bash
cd hydrov-backend
python -m venv .venv
.venv\Scripts\activate         # Windows
source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dependencias de testing
uvicorn app.main:app --reload --port 8000
```

**Ejecutar tests:**
```bash
cd hydrov-backend
pytest tests/ -v

# Tests por módulo
pytest tests/tests_services/test_mqtt_service.py -v
pytest tests/tests_services/test_ml_service.py -v
pytest tests/tests_api/test_alerts.py -v
```

**Frontend:**
```bash
cd hydrov-frontend
npm install
npm run dev   # Puerto 5173 (desarrollo)
```

**Modelos ML:**
```bash
cd hydrov-ml
pip install -r requirements.txt

# Entrenar modelo de autonomía
python src/training/train_autonomy.py

# Probar pipeline de inferencia directamente
python src/inference/predict_autonomy.py
python src/inference/detect_leaks.py
```

### Flasheo del Firmware ESP32

```bash
# 1. Instalar PlatformIO CLI
pip install platformio

# 2. Ir al directorio del firmware
cd edge

# 3. Configurar credenciales WiFi y MQTT en include/config.h
# (ver include/config.h para las constantes a modificar)

# 4. Compilar y cargar al ESP32
pio run --target upload

# 5. Monitor serial para verificar operación
pio device monitor --baud 115200
```

**Configuración mínima en `edge/include/config.h`:**
```cpp
// WiFi
#define WIFI_SSID       "tu_red_wifi"
#define WIFI_PASSWORD   "tu_password_wifi"

// MQTT
#define MQTT_HOST       "tu-cluster.hivemq.cloud"
#define MQTT_USER       "tu_usuario_mqtt"
#define MQTT_PASSWORD   "tu_password_mqtt"

// Identificador del nodo
#define DEVICE_ID       "HYDRO-V-001"

// Umbrales de turbidez (NTU)
#define TURBIDITY_ACCEPT_HARD    15.0f   // Captación directa
#define TURBIDITY_INITIAL_FLOOR  80.0f   // Umbral para análisis dT/dt
#define DTDT_REJECT_THRESHOLD   -2.0f    // Tasa de cambio mínima para captación
#define DTDT_WINDOW_SIZE         5        // Ventana de la derivada
```

---

## 📖 API Reference

### Autenticación

Todos los endpoints (excepto `/health`) requieren JWT Bearer token.

```bash
# Obtener token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=tu_password"
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Predicción de Autonomía Hídrica

```bash
GET /api/v1/predictions/{node_id}/autonomy?level_pct=65.0
Authorization: Bearer <token>
```

```json
{
  "node_id": "HYDRO-V-001",
  "days_autonomy": 4.3,
  "confidence": 0.85,
  "alert": false
}
```

### Detección de Fugas

```bash
GET /api/v1/predictions/{node_id}/leaks?flow_lpm=3.5&level_pct=60.0
Authorization: Bearer <token>
```

```json
{
  "node_id": "HYDRO-V-001",
  "leak_detected": false,
  "anomaly_score": 0.12,
  "confidence": 0.80
}
```

> Un `anomaly_score > 0.75` indica fuga probable.

### Control Remoto del ESP32

```bash
POST /api/v1/control/{node_id}/command
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "FORCE_HARVEST",
  "notes": "Captación manual activada por operador"
}
```

**Acciones disponibles:**
| Acción | Efecto en el ESP32 |
|--------|--------------------|
| `FORCE_HARVEST` | Fuerza apertura de válvula de captación |
| `FORCE_IDLE` | Detiene todas las operaciones del nodo |
| `RESET_ERRORS` | Limpia el contador de errores del FSM |
| `REQUEST_TELEMETRY` | Solicita telemetría inmediata fuera de ciclo |
| `REBOOT` | ⚠️ Reinicia el microcontrolador remotamente |

### Health Check

```bash
GET /health
```

```json
{
  "status": "ok",
  "version": "2.0.0",
  "environment": "production",
  "services": {
    "postgres": "up",
    "influxdb": "up",
    "mqtt": "up",
    "scheduler": "up"
  }
}
```

> `status` es `"ok"` si PostgreSQL e InfluxDB están disponibles; `"degraded"` en caso contrario. El campo `mqtt` verifica que el asyncio Task del listener esté activo; `scheduler` que el APScheduler esté corriendo.

---

## 🧮 Algoritmos Core

### Discriminación Adaptativa dT/dt

La innovación principal del proyecto. El algoritmo calcula la **derivada temporal discreta** de la turbidez usando una ventana circular de `DTDT_WINDOW_SIZE` muestras:

```cpp
float computeDtDt(float newReading) {
    // Guardar lectura y timestamp en ventana circular
    turbidityHistory[historyIndex] = newReading;
    timeHistory[historyIndex]      = millis();
    historyIndex = (historyIndex + 1) % DTDT_WINDOW_SIZE;

    // Calcular tasa de cambio entre la muestra más nueva y la más antigua
    float deltaT       = newReading - turbidityHistory[oldestIndex];
    float deltaSeconds = (now - timeHistory[oldestIndex]) / 1000.0f;

    return deltaT / deltaSeconds;   // NTU/s
}
```

**Lógica de decisión de la FSM:**
```cpp
if      (distanceCm <= 100.0)                             → SYSTEM_IDLE   // Cisterna llena
else if (turbidity < TURBIDITY_ACCEPT_HARD)               → WATER_INTAKE  // Agua cristalina
else if (turbidity < TURBIDITY_INITIAL_FLOOR
         && current_dtdt < DTDT_REJECT_THRESHOLD)         → WATER_INTAKE  // Aclarándose rápido
else                                                       → WATER_REJECT  // Turbidez alta
```

Esto permite que en lluvias intensas (donde el agua se limpia en <3 minutos), el sistema inicie la captación **hasta 2 minutos antes** que un temporizador fijo de 5 minutos, recuperando ~20 litros adicionales por evento.

### Máquina de Estados Finitos (FSM)

El sistema implementa una FSM de dos niveles:

**FSM Core** (ciclo de vida del nodo, 5 segundos):
```
CORE_WAKE_UP → CORE_SENSE_WATER → CORE_BUILD_REPORT → CORE_SLEEP → (repetir)
```

**FSM Logic** (control de válvulas, en tiempo real cada 2 segundos):
```
SYSTEM_IDLE ⟷ WATER_REJECT ⟷ WATER_INTAKE
                   ↓
             SYSTEM_ERROR (fail-safe)
```

**Telemetría JSON publicada por MQTT:**
```json
{
  "device_id": "HYDRO-V-001",
  "timestamp": 125000,
  "sensors": {
    "turbidity_ntu": "42.8",
    "distance_cm": "78.0",
    "flow_lpm": "3.50",
    "flow_total_liters": "1245.80"
  },
  "system_state": {
    "state": "ANALYZING",
    "state_duration_ms": 5000,
    "intake_cycles": 10,
    "reject_cycles": 2,
    "error_count": 0
  }
}
```

### Predicción de Autonomía Hídrica

Modelo de **regresión lineal múltiple** (scikit-learn) con normalización StandardScaler. El pipeline completo (`hydrov-ml/src/inference/predict_autonomy.py`) integra tres fuentes de datos en tiempo real:

```python
# Features del modelo
Y_pred = f(
    level_pct,            # Nivel actual cisterna (%)
    avg_consumption_lpd,  # Consumo promedio últimos 7 días (InfluxDB)
    forecast_precip_mm,   # Precipitación NASA POWER próximas 72h
    temperature_c,        # Temperatura promedio (NASA POWER)
    humidity_pct,         # Humedad relativa (NASA POWER)
    days_without_rain,    # Días sin flujo pluvial (InfluxDB)
    month,                # Mes actual (estacionalidad)
)
```

Con **fallback físico** cuando no hay modelo entrenado:
```python
PHYSICAL_COEFFICIENTS = [0.002, -0.5, -0.3, 0.05, 0.01, 0.02]
# coef de: nivel, consumo_7d, consumo_30d, lluvia, dia_semana, mes
```

El backend (`ml_service.py`) orquesta automáticamente la consulta a NASA POWER e InfluxDB antes de llamar a `predict_autonomy()`. Si NASA POWER no está disponible, usa defaults seguros (precipitación=0, temperatura=20°C, humedad=50%).

### Detección de Fugas con GNN

**HydroGNN** es una red neuronal de grafos basada en **GraphSAGE** para detección de anomalías de flujo al correlacionar múltiples nodos vecinos:

```
Cada nodo → 8 features: [turbidez, flujo, nivel, presión_est,
                          Δturbidez, Δflujo, sin(hora), cos(hora)]

SAGEConv(8→64) → ReLU → Dropout(0.3)
SAGEConv(64→32) → ReLU → Dropout(0.3)
SAGEConv(32→16) → ReLU
FC(16→8) → ReLU
FC(8→2) → log_softmax   →  {NORMAL, FUGA}
```

Un `anomaly_score > 0.75` activa una alerta de fuga. Cuando el grafo completo no está disponible (nodo aislado), el sistema usa el **LeakDetectorMLP** de fallback, un perceptrón de 3 capas que evalúa individualmente el nodo.

---

## 🔩 Hardware y Prototipo

### Lista de Materiales (BOM — TRL 4)

| Componente | Modelo | Quantity | Función |
|-----------|--------|----------|---------|
| Microcontrolador | ESP32 DevKit V1 (dual-core 240MHz) | 1 | Cerebro del sistema |
| Turbidímetro | Gravity Analog Turbidity Sensor | 1 | Calidad del agua (0-3000 NTU) |
| Caudalímetro | YF-S201 (efecto Hall) | 1 | Flujo volumétrico (~450 pulsos/L) |
| Sensor de nivel | JSN-SR04T (ultrasónico impermeable) | 1 | Nivel de cisterna (20-450cm) |
| Válvula de captación | Solenoide 1/2" latón 12V NC | 1 | Admisión de agua validada |
| Válvula de rechazo | Solenoide 1/2" latón 12V NC | 1 | Purga del primer arrastre |
| Etapa de potencia | Relé 12V / Optoacoplador | 2 | Protección del ESP32 |
| Fuente | Conmutada 12V 2A | 1 | Alimentación del sistema |
| Gabinete | IP65 plástico | 1 | Protección contra el clima |
| Filtro Pro-V | Columna PVC 4" × 50cm | 1 | Filtración físico-química |
| Zeolita | Clinoptilolita 3-5mm | 2 kg | Intercambio catiónico |
| Carbón activado | Granular cáscara de coco | 1 kg | Adsorción orgánica |
| Pre-filtro | Guata poliéster 50µm | - | Filtración mecánica |

### Diseño del Filtro Pro-V

```
       Entrada validada (< 15 NTU digital)
              │
    ┌─────────▼─────────┐
    │  ① GUATA 50µm     │  ← Arena, sedimentos visibles
    ├───────────────────┤
    │  ② ZEOLITA 2kg    │  ← Metales pesados, NH4+, turbidez 5µm
    │  (Clinoptilolita) │     Intercambio catiónico (CIC alta)
    ├───────────────────┤
    │  ③ CARBÓN 1kg     │  ← COVs, cloro residual, olor/sabor
    │  (Cáscara coco)   │     Adsorción (500-1500 m²/g)
    └─────────┬─────────┘
              │  < 5 NTU (NOM-127 ✓)
              ▼
          CISTERNA
```

**Capacidad de filtrado:** El filtro está dimensionado para eventos de lluvia típicos del Valle de México (intensidad 5-30 mm/h). Las tapas roscadas permiten reemplazo fácil de medios filtrantes cada 6-12 meses.

---

## 📊 Resultados y Validación

El prototipo fue validado bajo protocolo experimental TRL 4 (laboratorio + campo controlado):

### Eficiencia del Algoritmo dT/dt

| Métrica | Sistema Tradicional (5 min fijos) | Hydro-V (dT/dt) |
|---------|----------------------------------|-----------------|
| Agua descartada (lluvia intensa) | 50 litros | 30 litros |
| Agua captada adicional | — | +20 litros (+**40%**) |
| Tiempo hasta captación | 5 min (fijo) | ~3 min (adaptativo) |

### Calidad del Agua Post-Filtro Pro-V

| Punto de medición | Turbidez | Norma NOM-127 |
|------------------|---------|---------------|
| Red municipal (turbia) | 85 NTU | — |
| Salida Filtro Pro-V | **3.2 NTU** | ≤ 5 NTU ✅ |
| Agua pluvial (primer arrastre) | 150–200 NTU | — |
| Salida después de dT/dt + filtro | **< 5 NTU** | ≤ 5 NTU ✅ |

### Análisis Financiero

| Concepto | Valor |
|----------|-------|
| Costo del prototipo | **$3,200 MXN** |
| Gasto anual en pipas (vivienda promedio) | ~$6,400 MXN/año |
| Ahorro estimado con Hydro-V | ~$4,800 MXN/año |
| **ROI Simple** | **~8 meses** |

---

## 🌱 Alineación con los ODS

Hydro-V contribuye directamente a tres Objetivos de Desarrollo Sostenible de la Agenda 2030:

| ODS | Meta | Contribución |
|-----|------|-------------|
| **ODS 6** — Agua Limpia y Saneamiento | 6.1, 6.3, 6.4 | Acceso universal al agua limpia, mejora de calidad (< 5 NTU), eficiencia hídrica (+40%) |
| **ODS 11** — Ciudades Sostenibles | 11.5 | Reducción de impacto de inundaciones al usar cisternas domésticas como vasos reguladores |
| **ODS 13** — Acción por el Clima | 13.1 | Resiliencia climática: predicción de lluvias (NASA) para preparación ante eventos extremos |

---

## 🔭 Trabajo Futuro

El roadmap hacia **TRL 7-9** incluye:

| Fase | Objetivo | Tecnología |
|------|---------|-----------|
| **TRL 5-6** | Validación en 10 viviendas reales en Nezahualcóyotl | Despliegue en campo |
| **TRL 7** | Red de 50+ nodos con GNN completo activo | GraphSAGE en producción |
| **TRL 7** | Alimentación solar + baterías LiPo | Autonomía energética total |
| **TRL 8** | Certificación COFEPRIS para el proceso de filtración | Aprobación sanitaria |
| **TRL 9** | Manufactura a escala, distribución municipal | Política pública hídrica |

**Logros recientes (v2.x):**
- ✅ **Suite de tests completa:** 6 módulos de prueba (MQTT, ML, NASA, InfluxDB, WebSocket, Alerts) con fixtures y mocks en `conftest.py`.
- ✅ **CORS middleware manual** implementado para compatibilidad con acceso LAN desde dispositivos móviles.
- ✅ **Nginx integrado** en el container del frontend, eliminando el servicio proxy separado.
- ✅ **RBAC inicial:** Modelos `Role`, `SensorType` y `ValveType` añadidos al ORM.
- ✅ **Pipeline ML en producción:** `hydrov-ml/src/inference/` con `predict_autonomy.py` y `detect_leaks.py` conectados al backend.
- ✅ **UI responsiva con hamburger menu:** `Sidebar` y `Navbar` adaptados para móvil; `NotificationsPanel` como slide-over.

**Líneas de investigación abiertas:**
- **Redes Neuronales de Grafos (GNN) a escala:** Entrenar la GNN con datos reales de 50+ nodos para detección de fugas en la red municipal de distribución.
- **Calibración automática del turbidímetro:** Autoajuste de la curva de conversión ADC→NTU con muestras periódicas de referencia.
- **GAN para datos sintéticos:** El módulo `gan_synthetic.py` permite generar datos de entrenamiento realistas cuando no hay suficientes eventos de lluvia reales.
- **Optimización energética con deep sleep:** El firmware ya tiene la arquitectura preparada (`RTC_DATA_ATTR`) para agregar `esp_deep_sleep_start()` sin cambios de diseño.
- **RBAC completo:** Expandir el modelo `Role` para control de acceso granular por zona geográfica.

---

## 💰 Presupuesto del Prototipo

| Concepto | Componente | Costo (MXN) |
|---------|-----------|-------------|
| Control | ESP32 DevKit V1 + PCB | $180 |
| Sensórica | Turbidez Gravity + Flujo YF-S201 + Nivel JSN-SR04T | $1,000 |
| Actuadores | 2× Válvulas Solenoides 1/2" Latón 12V NC | $560 |
| Filtración | Filtro Pro-V (PVC 4" + Zeolita 2kg + Carbón 1kg) | $380 |
| Infraestructura | Gabinete IP65 + Fuente 12V/2A + Conectores | $1,080 |
| **TOTAL** | | **$3,200 MXN** |

> *El costo puede reducirse ~15% en producción en serie debido a economías de escala en materiales de filtración.*

---

## 👥 Contacto y Equipo

**Institución:** Instituto Politécnico Nacional — CECyT 9 "Juan de Dios Bátiz"
**Ubicación:** Ciudad Nezahualcóyotl, Estado de México, México
**Concurso:** Premio Nacional Juvenil del Agua 2026

| Rol | Nombre | Contacto |
|-----|--------|---------|
| **Autores / Desarrolladores** | Cruz Pérez Jesús Emmanuel<br>Curiel García Juan Jesús | emmancruz0831@gmail.com<br>curielgarciajuanjesus@gmail.com |
| **Asesor** | Pérez Montes Rubén Enain | +52 55 2296 1094 |

---

**¿Tienes preguntas sobre el proyecto?**  
Abre un [Issue](../../issues) en GitHub o contacta directamente al equipo.

---

## 📚 Referencias

1. UNESCO / UN-Water. (2024). *World Water Development Report 2024: Valuing Water*. UNESCO Publishing.
2. CONAGUA. (2024). *Estadísticas del Agua en México 2024*. Comisión Nacional del Agua / SEMARNAT.
3. NASA POWER Project. (2025). *NASA Prediction Of Worldwide Energy Resources*. https://power.larc.nasa.gov/
4. Espressif Systems. (2024). *ESP32 Technical Reference Manual v4.8*. Espressif Systems.
5. Secretaría de Salud. (1995). *NOM-127-SSA1-1994: Agua para uso y consumo humano - Límites permisibles de calidad*. Diario Oficial de la Federación.
6. Mekonnen, M. M. & Hoekstra, A. Y. (2016). Four billion people facing severe water scarcity. *Science Advances*, 2(2), e1500323.
7. Martinson, D. B. & Thomas, T. (2005). Quantifying the first-flush phenomenon. *12th International Rainwater Catchment Systems Conference*. New Delhi, India.
8. SACMEX. (2024). *Reporte del Sistema de Aguas de la Ciudad de México 2024*. Gobierno de la CDMX.
9. Tchobanoglous, G., et al. (2003). *Wastewater Engineering: Treatment and Reuse*. Metcalf & Eddy, McGraw-Hill.
10. Hamilton, W., Ying, Z. & Leskovec, J. (2017). Inductive Representation Learning on Large Graphs (GraphSAGE). *NeurIPS 2017*.
11. Ethos Laboratorio de Políticas Públicas. (2019). *Corrupción en el sector agua: ¿quién es responsable de la crisis?*. Ethos A.C.
12. BBVA Research. (2024). *La crisis hídrica en México: situación actual y perspectivas*. BBVA México.

---

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT**. Consulta el archivo [LICENSE](./LICENSE) para más detalles.

---

<div align="center">

**Hydro-V** — *Transformando la crisis hídrica en soberanía del agua para las familias vulnerables*

Desarrollado con ❤️ en Ciudad Nezahualcóyotl, Estado de México

*"La alta tecnología, cuando se aplica con enfoque social, es la clave para la resiliencia urbana."*

[![IPN](https://img.shields.io/badge/IPN-Instituto_Politécnico_Nacional-900000?style=flat-square)](https://www.ipn.mx)
[![CECyT 9](https://img.shields.io/badge/CECyT_9-Juan_de_Dios_Bátiz-1a73e8?style=flat-square)](https://www.cecyt9.ipn.mx)

</div>
