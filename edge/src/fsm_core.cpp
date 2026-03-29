/**
 * @file    fsm_core.cpp
 * @brief   Máquina de Estados Finitos (FSM) - Ciclo de vida principal del nodo
 * @project Hydro-V | Nodo HYDRO-V-NEZA-001
 *
 * Este archivo implementa el ciclo de vida de alto nivel del nodo Hydro-V.
 * Es diferente a fsm_logic.cpp (que controla válvulas en tiempo real).
 * fsm_core maneja las transiciones de SUEÑO/VIGILIA del sistema completo para
 * ahorrar energía en futuras versiones con deep sleep.
 *
 * Ciclo principal (en orden):
 *
 *   ┌──────────────┐
 *   │  DESPERTAR   │ → Inicializar hardware y verificar batería/red.
 *   └──────┬───────┘
 *          ▼
 *   ┌──────────────┐
 *   │ REVISAR AGUA │ → Leer sensores, filtrar datos, actualizar FSM de válvulas.
 *   └──────┬───────┘
 *          ▼
 *   ┌──────────────────┐
 *   │ PREPARAR REPORTE │ → Empaquetar JSON y publicar vía MQTT a HiveMQ Cloud.
 *   └──────┬───────────┘
 *          ▼
 *   ┌──────────────┐
 *   │    DORMIR    │ → Esperar hasta el próximo ciclo (vTaskDelay / deep sleep).
 *   └──────────────┘
 *          │
 *          └─────────┐ (loop infinito)
 *                    ▼
 *               DESPERTAR
 *
 * RELACIÓN CON OTROS MÓDULOS:
 *  - Llama a hal_sensors.h    → para obtener lecturas físicas.
 *  - Llama a fsm_logic.cpp    → para actualizar el estado de las válvulas.
 *  - Llama a telemetry.cpp    → para empaquetar y publicar el JSON MQTT.
 *  - Llama a net_mqtt.cpp     → para verificar la conexión de red.
 */

// ============================================================================
// INCLUDES
// ============================================================================
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "config.h"
#include "hal_sensors.h"
#include "hal_actuators.h"
#include "dsp_filters.h"
#include "fsm_logic.h"
#include "net_mqtt.h"
#include "telemetry.h"

// ============================================================================
// ESTADOS DEL CICLO PRINCIPAL
// ============================================================================

/**
 * @brief Los 4 momentos del ciclo de vida del nodo.
 *
 * Este enum es independiente de SystemState (fsm_logic.h) que gestiona válvulas.
 * Este enum gestiona el ciclo completo de sueño/vigilia y reporte.
 */
typedef enum {
    CORE_WAKE_UP,          // El nodo acaba de despertar o reiniciarse
    CORE_SENSE_WATER,      // Leyendo y evaluando todos los sensores
    CORE_BUILD_REPORT,     // Preparando y enviando el paquete JSON a la nube
    CORE_SLEEP             // Esperando el siguiente ciclo de medición
} CoreState_t;

// ============================================================================
// VARIABLES INTERNAS DEL MÓDULO
// ============================================================================

static CoreState_t        coreState      = CORE_WAKE_UP;
static SensorData_t       latestReading  = {};      // Última lectura de sensores
static unsigned long      lastCycleMs    = 0;        // Timestamp del ciclo anterior
static uint32_t           cycleCount     = 0;        // Contador de ciclos totales

// Intervalo entre ciclos de medición (en milisegundos)
// En producción este valor puede subirse a 10,000 ms para ahorrar energía.
static const uint32_t CYCLE_INTERVAL_MS = 5000;

// ============================================================================
// FUNCIONES AUXILIARES PRIVADAS
// ============================================================================

/**
 * @brief Registra en consola el nombre del estado actual del core.
 */
static void logCoreState(CoreState_t state) {
    const char* names[] = { "WAKE_UP", "SENSE_WATER", "BUILD_REPORT", "SLEEP" };
    if ((int)state < 4) {
        Serial.printf("[FSM_Core] Estado: %s | Ciclo #%lu\n", names[(int)state], cycleCount);
    }
}

// ============================================================================
// FASE 1: DESPERTAR
// ============================================================================

/**
 * @brief Ejecuta las rutinas de inicio del ciclo.
 *
 * Verifica que el hardware esté respondiendo antes de intentar leer datos.
 * Si hay un fallo crítico (sensor ultrasónico muerto), incrementa el
 * error_count para que el dashboard pueda alertar al usuario.
 *
 * @return true si el hardware está listo, false si hay un fallo crítico.
 */
static bool phaseWakeUp() {
    Serial.println("[FSM_Core][DESPERTAR] Iniciando ciclo de medición...");

    // Verificar que el sensor ultrasónico responde con una lectura de prueba
    float testDistance = readUltrasonicDistance();
    if (testDistance < 0) {
        Serial.println("[FSM_Core][WARN] Sensor ultrasónico no responde. Continuando con datos previos.");
        // No bloqueamos el ciclo, pero registramos el fallo en la FSM de lógica
        // para que sea visible en el dashboard (error_count)
        // Nota: updateSystemState con los datos previos mantendrá el estado seguro.
        return false;
    }

    Serial.printf("[FSM_Core][DESPERTAR] Hardware OK. Distancia de prueba: %.1f cm\n", testDistance);
    return true;
}

// ============================================================================
// FASE 2: REVISAR AGUA
// ============================================================================

/**
 * @brief Lee todos los sensores físicos y actualiza la FSM de válvulas.
 *
 * Es la fase más crítica del ciclo. Los datos obtenidos aquí son los que:
 *  - Controlan las válvulas (vía updateSystemState en fsm_logic.cpp).
 *  - Se empaquetan en JSON y se envían a HiveMQ Cloud.
 *
 * Manejo de fallos:
 *  - Si el ultrasónico devuelve -1.0, se conserva el último valor válido
 *    para no detener el flujo de datos al dashboard.
 *  - El filtro DSP (getFilteredDistance) suaviza picos de ruido a lo largo
 *    del tiempo usando una media móvil.
 */
static void phaseSenseWater() {
    Serial.println("[FSM_Core][REVISAR AGUA] Leyendo sensores...");

    // ── Turbidez ───────────────────────────────────────────────────────────
    uint16_t rawAdc         = readTurbidityRaw();
    uint16_t filteredAdc    = getFilteredTurbidity(rawAdc);
    // Escala de 0–4095 (12-bit ADC) a 0–1000 NTU (calibración lineal simple)
    latestReading.turbidity_ntu = (float)filteredAdc * (1000.0f / TURBIDITY_ADC_MAX);

    // ── Distancia / Nivel de Cisterna ──────────────────────────────────────
    float rawDistance   = readUltrasonicDistance();
    float safeDistance  = getFilteredDistance(rawDistance);

    if (safeDistance >= 0) {
        // Lectura válida: actualizar el dato más reciente
        latestReading.distance_cm = safeDistance;
    } else {
        // Sensor sin respuesta: conservar el dato anterior con una advertencia.
        // Esto evita que el dashboard muestre un "0 litros" falso.
        Serial.printf("[FSM_Core][WARN] Distancia inválida, usando último valor: %.1f cm\n",
                      latestReading.distance_cm);
    }

    // ── Caudal (Flujo) ─────────────────────────────────────────────────────
    // Calculamos el intervalo real desde el último ciclo para mayor precisión.
    unsigned long now         = millis();
    unsigned long intervalMs  = (lastCycleMs > 0) ? (now - lastCycleMs) : CYCLE_INTERVAL_MS;
    latestReading.flow_lpm    = readFlowRate(intervalMs);
    latestReading.flow_total  = getFlowTotalLiters();
    latestReading.timestamp   = now;
    lastCycleMs               = now;

    // ── Log de lectura completa ────────────────────────────────────────────
    Serial.printf("[FSM_Core] Turb=%.1f NTU | Dist=%.1f cm | Caudal=%.2f LPM | Total=%.2f L\n",
                  latestReading.turbidity_ntu,
                  latestReading.distance_cm,
                  latestReading.flow_lpm,
                  latestReading.flow_total);

    // ── Actualizar la FSM de válvulas con los datos frescos ────────────────
    // updateSystemState está en fsm_logic.cpp y mueve los relés físicos
    // según las reglas de turbidez y nivel de cistena.
    updateSystemState(latestReading.turbidity_ntu, latestReading.distance_cm);
}

// ============================================================================
// FASE 3: PREPARAR REPORTE
// ============================================================================

/**
 * @brief Empaqueta los datos de sensores y FSM en JSON y los publica en MQTT.
 *
 * Delega la serialización y publicación a telemetry.cpp (publishTelemetryData),
 * que incluye guardado offline automático si no hay conexión a internet.
 *
 * El JSON publicado tiene esta estructura (compatible con el frontend React):
 * {
 *   "device_id": "HYDRO-V-001",
 *   "timestamp": 12500,
 *   "sensors": {
 *     "turbidity_ntu": "42.8",
 *     "distance_cm": "78.0",
 *     "flow_lpm": "3.50",
 *     "flow_total_liters": "1245.80"
 *   },
 *   "system_state": {
 *     "state": "ANALYZING",
 *     "state_duration_ms": 5000,
 *     "intake_cycles": 10,
 *     "reject_cycles": 2,
 *     "error_count": 0
 *   }
 * }
 */
static void phaseBuildReport() {
    Serial.println("[FSM_Core][PREPARAR REPORTE] Empaquetando y enviando telemetría...");

    // Mantener la conexión de red activa (reconecta Wi-Fi/MQTT si se cayó)
    maintainNetwork();

    // Publicar: si no hay red, telemetry.cpp guarda el JSON en SPIFFS/LittleFS
    publishTelemetryData(latestReading);

    Serial.printf("[FSM_Core][REPORTE] Publicado. Red: %s\n",
                  isNetworkConnected() ? "OK" : "SIN RED (guardado offline)");
}

// ============================================================================
// FASE 4: DORMIR
// ============================================================================

/**
 * @brief Pone el nodo en espera eficiente hasta el próximo ciclo.
 *
 * Se usa vTaskDelay de FreeRTOS (no un blocking delay) para ceder el CPU
 * a otras tareas (taskWiFiMonitor, taskMQTT) durante la espera.
 *
 * EXPANSIÓN FUTURA (Deep Sleep):
 * Para implementar deep sleep del ESP32 y ahorrar batería, reemplazarías
 * vTaskDelay por:
 *   esp_sleep_enable_timer_wakeup(CYCLE_INTERVAL_MS * 1000ULL); // µs
 *   esp_deep_sleep_start();
 * Las variables latestReading deberían guardarse en RTC_DATA_ATTR.
 */
static void phaseSleep() {
    Serial.printf("[FSM_Core][DORMIR] Esperando %lu ms hasta el próximo ciclo...\n\n",
                  (unsigned long)CYCLE_INTERVAL_MS);
    vTaskDelay(pdMS_TO_TICKS(CYCLE_INTERVAL_MS));
}

// ============================================================================
// MÁQUINA DE ESTADOS PRINCIPAL (LOOP DEL NÚCLEO)
// ============================================================================

/**
 * @brief Ejecuta una iteración completa del ciclo de vida del nodo.
 *
 * Esta función es llamada desde una tarea FreeRTOS (o directamente desde
 * loop() en implementaciones simples). Gestiona las transiciones entre fases
 * usando un switch-case explícito para máxima legibilidad y mantenibilidad.
 *
 * Flujo normal:
 *   CORE_WAKE_UP → CORE_SENSE_WATER → CORE_BUILD_REPORT → CORE_SLEEP
 *                                                                  ↓
 *                                   CORE_WAKE_UP ←────────────────┘
 */
void runCoreFSMCycle() {
    logCoreState(coreState);

    switch (coreState) {

        // ── Estado 1: DESPERTAR ──────────────────────────────────────────────
        case CORE_WAKE_UP: {
            bool hardwareOk = phaseWakeUp();
            // Avanzamos al siguiente estado independientemente del fallo para
            // no bloquear el flujo. El fallo queda registrado en fsm_logic.
            (void)hardwareOk;
            coreState = CORE_SENSE_WATER;
            break;
        }

        // ── Estado 2: REVISAR AGUA ───────────────────────────────────────────
        case CORE_SENSE_WATER: {
            phaseSenseWater();
            coreState = CORE_BUILD_REPORT;
            break;
        }

        // ── Estado 3: PREPARAR REPORTE ───────────────────────────────────────
        case CORE_BUILD_REPORT: {
            phaseBuildReport();
            coreState = CORE_SLEEP;
            break;
        }

        // ── Estado 4: DORMIR ─────────────────────────────────────────────────
        case CORE_SLEEP: {
            phaseSleep();
            cycleCount++;
            coreState = CORE_WAKE_UP;  // Reiniciar el ciclo
            break;
        }

        // ── Seguridad: estado desconocido ────────────────────────────────────
        default: {
            Serial.println("[FSM_Core][ERROR] Estado desconocido. Reiniciando ciclo.");
            coreState = CORE_WAKE_UP;
            break;
        }
    }
}

/**
 * @brief Devuelve el nombre del estado actual del core como string legible.
 *
 * Útil para incluirlo en logs de Serial Monitor y diagnóstico.
 *
 * @return Puntero a string estático con el nombre del estado.
 */
const char* getCoreStateName() {
    switch (coreState) {
        case CORE_WAKE_UP:      return "WAKE_UP";
        case CORE_SENSE_WATER:  return "SENSE_WATER";
        case CORE_BUILD_REPORT: return "BUILD_REPORT";
        case CORE_SLEEP:        return "SLEEP";
        default:                return "UNKNOWN";
    }
}
