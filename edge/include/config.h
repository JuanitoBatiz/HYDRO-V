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
#define WIFI_SSID               "TU_WIFI_AQUI"
#define WIFI_PASSWORD           "TU_PASS_AQUI"

#define MQTT_BROKER             "56e39f9776c14953958f63d9c18ae8ef.s1.eu.hivemq.cloud"
#define MQTT_PORT               8883
#define MQTT_USERNAME           "TU_USUARIO"
#define MQTT_PASSWORD           "TU_PASS"
#define MQTT_CLIENT_ID          "HYDRO-V-001"
#define MQTT_USE_TLS            true

// MQTT Topics
#define MQTT_TOPIC_TELEMETRY    "hydrov/HYDRO-V-001/telemetry"
#define MQTT_TOPIC_COMMANDS     "hydrov/HYDRO-V-001/commands"

// ============================================
// SENSOR CALIBRATION CONSTANTS
// ============================================
#define TURBIDITY_ADC_MAX       4095    // 12-bit ADC resolution
#define FLOW_PULSES_PER_LITER   450     // Calibración YF-S201
#define ULTRASONIC_TIMEOUT_US   30000   // Timeout para lectura (aprox 5 metros máximo)

#endif // CONFIG_H