#include <Arduino.h>
#include <WiFi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

#include "config.h"
#include "hal_sensors.h"
#include "dsp_filters.h"
#include "hal_actuators.h"
#include "fsm_logic.h"
#include "fsm_core.h"
#include "net_mqtt.h"
#include "telemetry.h"
#include "storage_fs.h"

// ============================================================================
// DEFINICIONES GLOBALES
// ============================================================================
static QueueHandle_t sensorDataQueue = nullptr;

// ============================================================================
// TAREAS FREERTOS
// ============================================================================

/**
 * @brief Tarea de lectura de sensores (2 segundos)
 * Lee los sensores y alimenta la máquina de estados con los datos frescos
 */
void taskSensores(void* pvParameters) {
  TickType_t xLastWakeTime = xTaskGetTickCount();
  const TickType_t xFrequency = pdMS_TO_TICKS(2000); // 2 segundos

  Serial.println("[TaskSensores] Iniciada");

  while (1) {
    // ===== LECTURA DE SENSORES =====
    SensorData_t sensorData;
    
    // Leer turbidez (ADC), filtrar y convertir a NTU
    uint16_t turbidityRaw = readTurbidityRaw();
    uint16_t turbidityFiltered = getFilteredTurbidity(turbidityRaw);
    // Conversión simple: escalar de 0-4095 a 0-1000 NTU
    sensorData.turbidity_ntu = (float)turbidityFiltered * (1000.0 / TURBIDITY_ADC_MAX);
    
    // Leer distancia del ultrasónico y filtrar ruido
    float distanceRaw = readUltrasonicDistance();
    sensorData.distance_cm = getFilteredDistance(distanceRaw);
    
    // Leer caudal (flujo LPM en 2 segundos)
    sensorData.flow_lpm = readFlowRate(2000);
    
    // Leer acumulado total de flujo
    sensorData.flow_total = getFlowTotalLiters();
    
    sensorData.timestamp = millis();

    // Log de lecturas
    Serial.printf("[TaskSensores] T=%.1f NTU | D=%.1f cm | F=%.1f LPM | Total=%.2f L\n",
                  sensorData.turbidity_ntu, sensorData.distance_cm,
                  sensorData.flow_lpm, sensorData.flow_total);

    // ===== ALIMENTAR COLA DE DATOS =====
    if (sensorDataQueue != nullptr) {
      if (xQueueSend(sensorDataQueue, &sensorData, pdMS_TO_TICKS(100)) != pdPASS) {
        Serial.println("[TaskSensores] Error: Cola llena, datos descartados");
      }
    }

    // ===== ACTUALIZAR MÁQUINA DE ESTADOS (PUNTO CRÍTICO) =====
    // La FSM evalúa turbidez y distancia en TIEMPO REAL
    // y ejecuta acciones sobre las válvulas inmediatamente
    updateSystemState(sensorData.turbidity_ntu, sensorData.distance_cm);

    // Esperar hasta el siguiente ciclo (2 segundos)
    vTaskDelayUntil(&xLastWakeTime, xFrequency);
  }
}

/**
 * @brief Tarea de publicación MQTT (5 segundos)
 * Empaqueta los datos en JSON y los publica en HiveMQ
 */
void taskMQTT(void* pvParameters) {
  TickType_t xLastWakeTime = xTaskGetTickCount();
  const TickType_t xFrequency = pdMS_TO_TICKS(2000); // 2 segundos
  
  SensorData_t sensorData;

  Serial.println("[TaskMQTT] Iniciada");

  while (1) {
    // Mantener conexion WiFi/MQTT activa y reconectar si se cae
    maintainNetwork();

    // Intentar recibir datos de la cola de sensores
    if (sensorDataQueue != nullptr) {
      if (xQueueReceive(sensorDataQueue, &sensorData, pdMS_TO_TICKS(100)) == pdPASS) {
        publishTelemetryData(sensorData);
      }
    }

    // Esperar hasta el siguiente ciclo (5 segundos)
    vTaskDelayUntil(&xLastWakeTime, xFrequency);
  }
}

/**
 * @brief Tarea de monitoreo WiFi/MQTT (10 segundos)
 */
void taskWiFiMonitor(void* pvParameters) {
  TickType_t xLastWakeTime = xTaskGetTickCount();
  const TickType_t xFrequency = pdMS_TO_TICKS(10000); // 10 segundos

  Serial.println("[TaskWiFiMonitor] Iniciada");

  while (1) {
    maintainNetwork();

    // Verificar estado WiFi
    bool currentWiFi = (WiFi.status() == WL_CONNECTED);
    if (currentWiFi) {
      Serial.print("[WiFi] IP: ");
      Serial.println(WiFi.localIP());
    }

    // Log de estado general
    Serial.printf("[Status] WiFi=%s | NET=%s | Heap=%u bytes\n",
                  currentWiFi ? "OK" : "FAIL",
                  isNetworkConnected() ? "OK" : "FAIL",
                  ESP.getFreeHeap());

    vTaskDelayUntil(&xLastWakeTime, xFrequency);
  }
}

// ============================================================================
// SETUP
// ============================================================================
void setup() {
  Serial.begin(115200);
  initFS();
  delay(2000);

  // --- PRUEBA VALVULA ---
  Serial.println("[SISTEMA] CERRANDO VÁLVULA");
  pinMode(4, OUTPUT_OPEN_DRAIN);
  digitalWrite(4, HIGH);
  delay(4000);
  Serial.println("[SISTEMA] INTENTANDO ABRIR VÁLVULA");
  digitalWrite(4, LOW);
  delay(1000);
  Serial.println("[SISTEMA] CERRANDO VÁLVULA");
  digitalWrite(4, HIGH);
  // --- PRUEBA VALVULA ---
  
  Serial.println("\n");
  Serial.println("================================");
  Serial.println("   HYDRO-V Sistema Principal");
  Serial.println("================================\n");

  // Inicializar sensores
  Serial.println("[Setup] Inicializando sensores...");
  initSensors();
  initFilters();

  // Inicializar actuadores (NUEVO)
  Serial.println("[Setup] Inicializando actuadores (válvulas)...");
  initActuators();

  // Inicializar máquina de estados (NUEVO)
  Serial.println("[Setup] Inicializando FSM...");
  initFSM();

  // Prueba rápida de válvula antes de red/MQTT
  openValveIntake();
  delay(3000);
  closeValveIntake();
  Serial.println("[PRUEBA] Válvula probada con éxito.");

  // Configurar red WiFi + MQTT
  Serial.println("[Setup] Configurando red (WiFi/MQTT)...");
  initNetwork();

  // Crear cola FreeRTOS
  sensorDataQueue = xQueueCreate(10, sizeof(SensorData_t));
  if (sensorDataQueue == nullptr) {
    Serial.println("[ERROR] Fallo al crear cola de sensores");
    while (1) { vTaskDelay(pdMS_TO_TICKS(1000)); }
  }

  Serial.println("[Setup] Creando tareas FreeRTOS...");

  // Crear tarea de lectura de sensores (Core 1, Prioridad 2)
  xTaskCreatePinnedToCore(
    taskSensores,
    "TaskSensores",
    4096,
    nullptr,
    2,
    nullptr,
    1
  );

  // Crear tarea MQTT (Core 1, Prioridad 2)
  xTaskCreatePinnedToCore(
    taskMQTT,
    
    "TaskMQTT",
    8192,
    nullptr,
    2,
    nullptr,
    1
  );

  // Crear tarea de monitoreo (Core 0, Prioridad 1)
  xTaskCreatePinnedToCore(
    taskWiFiMonitor,
    "TaskWiFiMonitor",
    4096, // <-- INCREMENTADO PARA EVITAR STACK OVERFLOW
    nullptr,
    1,
    nullptr,
    0
  );

  Serial.println("[Setup] Sistema listo!\n");
}

// ============================================================================
// LOOP
// ============================================================================
void loop() {
  static uint32_t iterationCount = 0;

  // Ciclo principal de la máquina de estados
  runCoreFSMCycle();

  // Auditoría visual (Heartbeat FSM) cada 5 iteraciones
  iterationCount++;
  if (iterationCount % 5 == 0) {
    Serial.println("[FSM] Ciclo core ejecutado");
  }

  // Safety: delay no bloqueante para ceder CPU al WDT y FreeRTOS scheduler
  vTaskDelay(pdMS_TO_TICKS(2000));
}