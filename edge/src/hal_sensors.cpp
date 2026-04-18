/**
 * @file    hal_sensors.cpp
 * @brief   Hardware Abstraction Layer — Implementación de lectura de sensores
 * @project Hydro-V | Nodo HYDRO-V-NEZA-001
 *
 * REGLA DE ORO C++:
 *   Este archivo es la ÚNICA unidad de compilación donde las variables
 *   volatile y las funciones del HAL existen físicamente en memoria.
 *   El .h solo las declara con "extern" para que otros .cpp puedan usarlas.
 *
 * Sensores gestionados:
 *  - HC-SR04 (Ultrasónico) → distancia en cm para calcular nivel de cisterna
 *  - YF-S201 (Flujo)       → litros por minuto y total acumulado
 *  - Analógico (Turbidez)  → valor ADC crudo para calcular NTU
 */

// ============================================================================
// INCLUDES
// ============================================================================
#include "hal_sensors.h"   // <-- Importa las declaraciones del propio módulo

// ============================================================================
// DEFINICIÓN REAL DE LAS VARIABLES GLOBALES (volatile / ISR-safe)
// ============================================================================
// Estas son las ÚNICAS definiciones reales. El .h las re-exporta con "extern"
// para que main.cpp, fsm_core.cpp, etc. las puedan leer sin re-crearlas.
volatile uint16_t currentFlowPulses = 0;
volatile uint32_t totalFlowPulses   = 0;

// ============================================================================
// FLOW SENSOR - ISR (Interrupt Service Routine)
// ============================================================================

/**
 * @brief ISR: Incrementa los contadores de pulsos del sensor YF-S201.
 *
 * IRAM_ATTR garantiza que esta función se almacene en la SRAM interna
 * del ESP32, no en la Flash. Esto es obligatorio para ISRs en Arduino/ESP-IDF.
 *
 * - currentFlowPulses: contador temporal, se resetea en cada lectura de LPM.
 * - totalFlowPulses:   historial acumulado, NUNCA se resetea al leer velocidad.
 */
void IRAM_ATTR flowPulseCounter() {
    currentFlowPulses++;
    totalFlowPulses++;
}

// ============================================================================
// SENSOR INITIALIZATION
// ============================================================================

/**
 * @brief Configura pines de todos los sensores y adjunta la ISR de flujo.
 *
 * Debe llamarse una sola vez en setup() antes de arrancar las tareas FreeRTOS.
 * FALLING es más estable que RISING para el imán del YF-S201 ya que el flanco
 * descendente es más limpio y reduce el rebote (bounce) de la señal.
 */
void initSensors() {
    // ── Turbidity sensor ────────────────────────────────────────────────────
    pinMode(PIN_TURBIDITY_SENSOR, INPUT);

    // ── Ultrasonic HC-SR04 ───────────────────────────────────────────────────
    pinMode(PIN_ULTRASONIC_TRIG, OUTPUT);
    pinMode(PIN_ULTRASONIC_ECHO, INPUT);
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);  // Asegurar estado bajo al inicio

    // ── Flow sensor YF-S201 — con interrupción hardware ─────────────────────
    pinMode(PIN_FLOW_SENSOR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_FLOW_SENSOR), flowPulseCounter, FALLING);

    Serial.println("[HAL] Sensores inicializados: Ultrasonico, Turbidez, Flujo OK.");
}

// ============================================================================
// ULTRASONIC - LECTURA ROBUSTA CON DETECCIÓN DE FALLO
// ============================================================================

/**
 * @brief Dispara el HC-SR04 y devuelve la distancia en centímetros.
 *
 * Proceso:
 *  1. Envía un pulso TRIG de 10µs para activar el transductor.
 *  2. Espera el flanco ECHO con timeout (ULTRASONIC_TIMEOUT_US).
 *  3. Si duration == 0 → sensor desconectado o fuera de rango → retorna -1.0.
 *  4. Convierte: d (cm) = (duración × 0.0343) / 2  (ida + vuelta del sonido).
 *
 * @return Distancia en cm (float ≥ 0.0) o -1.0 en caso de error.
 */
float readUltrasonicDistance() {
    // ── Paso 1: Limpiar el TRIG antes del pulso ──────────────────────────────
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
    delayMicroseconds(4);

    // ── Paso 2: Enviar pulso de disparo de 10 µs ────────────────────────────
    digitalWrite(PIN_ULTRASONIC_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);

    // ── Paso 3: Medir duración del eco con timeout de seguridad ─────────────
    // ULTRASONIC_TIMEOUT_US = 30,000 µs → ~5 metros máximo.
    unsigned long duration = pulseIn(PIN_ULTRASONIC_ECHO, HIGH, ULTRASONIC_TIMEOUT_US);

    // ── Paso 4: Validar respuesta ────────────────────────────────────────────
    if (duration == 0) {
        Serial.println("[HAL][ERROR] Ultrasonico: sin respuesta (timeout). Verificar cableado TRIG/ECHO.");
        return -1.0f;
    }

    // ── Paso 5: Convertir duración a centímetros ─────────────────────────────
    // Velocidad del sonido en aire a ~25°C ≈ 0.0343 cm/µs. Se divide entre 2
    // porque la onda recorre la distancia en ida Y vuelta.
    return (duration * 0.0343f) / 2.0f;
}

// ============================================================================
// TURBIDITY - LECTURA ADC ANALÓGICA
// ============================================================================

/**
 * @brief Lee el valor crudo del ADC del sensor de turbidez.
 *
 * ESP32 → ADC de 12 bits: valores entre 0 y 4095.
 * La conversión a NTU se realiza en capas superiores (fsm_core / telemetry)
 * para mantener este módulo desacoplado de la lógica de negocio.
 *
 * @return Valor ADC crudo (0–4095).
 */
uint16_t readTurbidityRaw() {
    return (uint16_t)analogRead(PIN_TURBIDITY_SENSOR);
}

// ============================================================================
// FLOW - CAUDAL INSTANTÁNEO
// ============================================================================

/**
 * @brief Calcula el caudal en Litros Por Minuto (LPM) en el intervalo dado.
 *
 * La interrupción flowPulseCounter() cuenta cada pulso de forma atómica.
 * Esta función lee y resetea currentFlowPulses dentro de una sección crítica
 * (noInterrupts / interrupts) para garantizar consistencia (thread-safe).
 *
 * @param intervalMs  Tiempo en milisegundos desde la última llamada.
 * @return            Caudal en LPM. 0.0 si intervalMs es 0.
 */
float readFlowRate(unsigned long intervalMs) {
    if (intervalMs == 0) return 0.0f;

    // ── Sección crítica: leer y resetear pulsos de forma atómica ────────────
    noInterrupts();
    uint16_t pulses     = currentFlowPulses;
    currentFlowPulses   = 0;  // Solo los temporales; totalFlowPulses no se toca
    interrupts();

    float liters  = (float)pulses / FLOW_PULSES_PER_LITER;
    float minutes = (float)intervalMs / 60000.0f;
    return liters / minutes;
}

// ============================================================================
// FLOW - VOLUMEN TOTAL ACUMULADO
// ============================================================================

/**
 * @brief Devuelve el total acumulado de litros desde el encendido.
 *
 * totalFlowPulses NUNCA se resetea al leer LPM, lo que permite llevar
 * un historial de consumo total independiente de la ventana de muestreo.
 *
 * @return Total de litros consumidos desde el boot del ESP32.
 */
float getFlowTotalLiters() {
    noInterrupts();
    uint32_t total = totalFlowPulses;
    interrupts();
    return (float)total / FLOW_PULSES_PER_LITER;
}

// ============================================================================
// FLOW - RESET DE CONTADORES
// ============================================================================

/**
 * @brief Resetea ambos contadores de pulsos.
 *
 * Usar con precaución: borrará también el historial total (totalFlowPulses).
 * Pensado para reinicio explícito por comando MQTT o reinicio del sistema.
 */
void resetFlowCounter() {
    noInterrupts();
    currentFlowPulses = 0;
    totalFlowPulses   = 0;
    interrupts();
}
