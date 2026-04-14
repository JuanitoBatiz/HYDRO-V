#ifndef CONFIG_H
#define CONFIG_H

// ============================================
// PIN DEFINITIONS - SENSORS
// ============================================
#define PIN_TURBIDITY_SENSOR    34  // ADC1 - Sensor de turbidez analógico
#define PIN_FLOW_SENSOR         27  // GPIO con interrupción para pulsos de flujo
#define PIN_ULTRASONIC_TRIG     5   // Trigger del sensor ultrasónico 
#define PIN_ULTRASONIC_ECHO     18  // Echo del sensor ultrasónico 

// ============================================
// PIN DEFINITIONS - ACTUATORS (VALVES)
// ============================================
#define PIN_VALVE_REJECT        26  // Válvula de rechazo (normalmente cerrada)
#define PIN_VALVE_INTAKE        14  // Válvula de admisión (normalmente abierta)

// ============================================
// WIFI & MQTT CONFIGURATION - HiveMQ Cloud
// ============================================
#define WIFI_SSID               "FCP-1"
#define WIFI_PASSWORD           "FCP2430290431"

#define MQTT_BROKER             "56e39f9776c14953958f63d9c18ae8ef.s1.eu.hivemq.cloud"
#define MQTT_PORT               8883
#define MQTT_USERNAME           "hydrov_esp32_01"
#define MQTT_PASSWORD           "Emmamiamor1"
#define MQTT_CLIENT_ID          "HYDRO-V-001"
#define MQTT_USE_TLS            true

// MQTT Topics
#define MQTT_TOPIC_TELEMETRY    "hydrov/neza/001/telemetry"
#define MQTT_TOPIC_COMMANDS     "hydrov/HYDRO-V-001/commands"

// ============================================
// SENSOR CALIBRATION CONSTANTS
// ============================================
#define TURBIDITY_ADC_MAX       4095    // 12-bit ADC resolution
#define FLOW_PULSES_PER_LITER   450     // Calibración YF-S201
#define ULTRASONIC_TIMEOUT_US   30000   // Timeout para lectura (aprox 5 metros máximo)

// ============================================
// DERIVATIVE ALGORITHM CONSTANTS (dT/dt)
// ============================================
#define DTDT_WINDOW_SIZE 5           // Tamaño del buffer para calcular la derivada
#define DTDT_REJECT_THRESHOLD -8.0f  // NTU/s: umbral negativo fuerte (agua aclarándose)
#define TURBIDITY_INITIAL_FLOOR 80.0f // NTU mínimo para considerar presencia de sedimentos
#define TURBIDITY_ACCEPT_HARD 15.0f   // NTU: agua cristalina, admitir siempre

#endif // CONFIG_H