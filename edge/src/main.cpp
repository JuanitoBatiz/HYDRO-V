#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>

#include "config.h"
#include "hal_sensors.h"
#include "hal_actuators.h"
#include "fsm_logic.h"

// ============================================================================
// DEFINICIONES GLOBALES
// ============================================================================
static QueueHandle_t sensorDataQueue = nullptr;
static WiFiClientSecure espClient;
static PubSubClient mqttClient(espClient);

static volatile bool wifiConnected = false;
static volatile bool mqttConnected = false;

// Estructura de datos de sensores
typedef struct {
  float turbidity_ntu;
  float distance_cm;
  float flow_lpm;
  float flow_total;
  uint32_t timestamp;
} SensorData_t;

// ============================================================================
// FUNCIONES DE RED
// ============================================================================
void setupWiFi() {
  Serial.println("[WiFi] Iniciando conexión...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  const int maxAttempts = 20;
  
  while ((WiFi.status() != WL_CONNECTED) && (attempts < maxAttempts)) {
    vTaskDelay(pdMS_TO_TICKS(500));
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println("\n[WiFi] Conectado!");
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());
  } else {
    wifiConnected = false;
    Serial.println("\n[WiFi] Fallo en conexión");
  }
}

void reconnectMQTT() {
  int attempts = 0;
  const int maxAttempts = 5;
  
  while (!mqttClient.connected() && (attempts < maxAttempts)) {
    Serial.print("[MQTT] Intentando conectar... ");
    
    if (mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
      Serial.println("Conectado!");
      mqttConnected = true;
      return;
    } else {
      Serial.print("Código de error: ");
      Serial.println(mqttClient.state());
      vTaskDelay(pdMS_TO_TICKS(2000));
      attempts++;
    }
  }
  
  if (attempts >= maxAttempts) {
    mqttConnected = false;
    Serial.println("[MQTT] No se pudo conectar después de intentos");
  }
}

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
    
    // Leer turbidez (ADC, convertir a NTU)
    uint16_t turbidityRaw = readTurbidityRaw();
    // Conversión simple: escalar de 0-4095 a 0-1000 NTU
    sensorData.turbidity_ntu = (float)turbidityRaw * (1000.0 / TURBIDITY_ADC_MAX);
    
    // Leer distancia del ultrasónico
    sensorData.distance_cm = readUltrasonicDistance();
    
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
  const TickType_t xFrequency = pdMS_TO_TICKS(5000); // 5 segundos
  
  SensorData_t sensorData;
  StaticJsonDocument<512> doc;

  Serial.println("[TaskMQTT] Iniciada");

  while (1) {
    // Asegurar conexión MQTT
    if (!mqttConnected) {
      if (wifiConnected) {
        reconnectMQTT();
      }
    }

    // Mantener la conexión MQTT activa
    if (mqttConnected) {
      mqttClient.loop();
    }

    // Intentar recibir datos de la cola de sensores
    if (sensorDataQueue != nullptr) {
      if (xQueueReceive(sensorDataQueue, &sensorData, pdMS_TO_TICKS(100)) == pdPASS) {
        
        // Crear JSON con los datos de sensores
        doc.clear();
        doc["device_id"] = MQTT_CLIENT_ID;
        doc["timestamp"] = sensorData.timestamp;
        
        // Sección de turbidez
        JsonObject turbidity = doc.createNestedObject("turbidity");
        turbidity["ntu"] = serialized(String(sensorData.turbidity_ntu, 1));
        
        // Sección de nivel del tanque
        JsonObject level = doc.createNestedObject("level");
        level["distance_cm"] = serialized(String(sensorData.distance_cm, 1));
        
        // Sección de flujo
        JsonObject flow = doc.createNestedObject("flow");
        flow["rate_lpm"] = serialized(String(sensorData.flow_lpm, 2));
        flow["total_liters"] = serialized(String(sensorData.flow_total, 2));
        
        // Sección de estado de válvulas
        ActuatorState_t actuatorState = getActuatorState();
        JsonObject valves = doc.createNestedObject("valves");
        valves["reject_open"] = actuatorState.valve_reject_open;
        valves["intake_open"] = actuatorState.valve_intake_open;
        
        // Sección de estado FSM
        FSMContext_t fsmState = getFSMContext();
        JsonObject fsm = doc.createNestedObject("system");
        fsm["state"] = getStateNameString();
        fsm["state_duration_ms"] = fsmState.state_duration;
        fsm["intake_cycles"] = fsmState.intake_cycles;
        fsm["reject_cycles"] = fsmState.reject_cycles;
        fsm["error_count"] = fsmState.error_count;

        // Serializar JSON a string
        char jsonBuffer[512];
        serializeJson(doc, jsonBuffer, sizeof(jsonBuffer));

        // Publicar en MQTT si está conectado
        if (mqttConnected) {
          bool published = mqttClient.publish(MQTT_TOPIC_TELEMETRY, jsonBuffer);
          if (published) {
            Serial.printf("[TaskMQTT] Publicado telemetría (%d bytes)\n", strlen(jsonBuffer));
          } else {
            Serial.println("[TaskMQTT] Error al publicar");
            mqttConnected = false;
          }
        } else {
          Serial.println("[TaskMQTT] MQTT no conectado, datos no publicados");
        }
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
    // Verificar estado WiFi
    bool currentWiFi = (WiFi.status() == WL_CONNECTED);
    if (currentWiFi != wifiConnected) {
      wifiConnected = currentWiFi;
      Serial.printf("[WiFi] Estado cambió a: %s\n", 
                    wifiConnected ? "CONECTADO" : "DESCONECTADO");
      
      if (wifiConnected) {
        Serial.print("[WiFi] IP: ");
        Serial.println(WiFi.localIP());
      }
    }

    // Log de estado general
    Serial.printf("[Status] WiFi=%s | MQTT=%s | Heap=%u bytes\n",
                  wifiConnected ? "OK" : "FAIL",
                  mqttConnected ? "OK" : "FAIL",
                  ESP.getFreeHeap());

    vTaskDelayUntil(&xLastWakeTime, xFrequency);
  }
}

// ============================================================================
// SETUP
// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n");
  Serial.println("================================");
  Serial.println("   HYDRO-V Sistema Principal");
  Serial.println("================================\n");

  // Inicializar sensores
  Serial.println("[Setup] Inicializando sensores...");
  initSensors();

  // Inicializar actuadores (NUEVO)
  Serial.println("[Setup] Inicializando actuadores (válvulas)...");
  initActuators();

  // Inicializar máquina de estados (NUEVO)
  Serial.println("[Setup] Inicializando FSM...");
  initFSM();

  // Configurar WiFi
  Serial.println("[Setup] Configurando WiFi...");
  setupWiFi();

  // Configurar MQTT
  Serial.println("[Setup] Configurando MQTT...");
  if (MQTT_USE_TLS) {
    espClient.setInsecure();
  }
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);

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
    4096,
    nullptr,
    2,
    nullptr,
    1
  );

  // Crear tarea de monitoreo (Core 0, Prioridad 1)
  xTaskCreatePinnedToCore(
    taskWiFiMonitor,
    "TaskWiFiMonitor",
    2048,
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
  // El scheduler de FreeRTOS se encarga de todo
  vTaskDelay(pdMS_TO_TICKS(10000));
}