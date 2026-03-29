/**
 * @file    hal_sensors.cpp
 * @brief   Hardware Abstraction Layer - Implementación de lectura de sensores
 * @project Hydro-V | Nodo HYDRO-V-NEZA-001
 *
 * Este archivo contiene la lógica de bajo nivel para comunicarse con el
 * hardware físico. Las funciones aquí definidas son llamadas por las tareas
 * FreeRTOS en main.cpp (taskSensores).
 *
 * Sensores gestionados:
 *  - HC-SR04 (Ultrasónico) → distancia en cm para calcular nivel de cisterna
 *  - YF-S201 (Flujo)       → litros por minuto y total acumulado
 *  - Analógico (Turbidez)  → valor ADC crudo para calcular NTU
 *
 * NOTA DE ARQUITECTURA:
 * Las funciones de inicialización y lectura están declaradas en hal_sensors.h.
 * Este archivo (.cpp) es el complemento de compilación que permite que el
 * linker de PlatformIO resuelva los símbolos correctamente en proyectos grandes.
 * La implementación es incluida via hal_sensors.h para compatibilidad con el
 * patrón de inclusión de Arduino.
 */

// ============================================================================
// INCLUDES
// ============================================================================
#include <Arduino.h>
#include "config.h"

// ============================================================================
// ULTRASONIC - LECTURA ROBUSTA CON DETECCIÓN DE FALLO
// ============================================================================

/**
 * @brief Lee la distancia del sensor ultrasónico HC-SR04 con validación.
 *
 * Proceso:
 *  1. Envía un pulso TRIG de 10µs para activar el sensor.
 *  2. Espera el flanco ECHO con un timeout de seguridad (ULTRASONIC_TIMEOUT_US).
 *  3. Si el timeout se cumple (duration == 0), el sensor está desconectado
 *     o el objeto está fuera de rango → se devuelve -1.0 como código de error.
 *  4. Convierte la duración (µs) a distancia (cm) con la fórmula:
 *         d (cm) = (duración × velocidad_sonido) / 2
 *                = (duración × 0.0343) / 2
 *
 * @return  Distancia en centímetros (float ≥ 0.0) si la lectura es válida.
 *          -1.0 si el sensor no respondió (fallo de hardware o fuera de rango).
 */
float readUltrasonicDistanceSafe() {
    // ── Paso 1: Asegurar línea TRIG en LOW antes del pulso ──────────────────
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
    delayMicroseconds(4);

    // ── Paso 2: Emitir pulso de disparo de 10 µs ────────────────────────────
    digitalWrite(PIN_ULTRASONIC_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);

    // ── Paso 3: Medir duración del eco con timeout de seguridad ─────────────
    // ULTRASONIC_TIMEOUT_US = 30,000 µs → equivale a ~5 metros máximo.
    // Si el pulso nunca llega (sensor desconectado o cable roto), pulseIn()
    // devuelve 0 después del timeout en lugar de bloquearse para siempre.
    unsigned long duration = pulseIn(PIN_ULTRASONIC_ECHO, HIGH, ULTRASONIC_TIMEOUT_US);

    // ── Paso 4: Validar respuesta ────────────────────────────────────────────
    if (duration == 0) {
        // Sensor desconectado, cable dañado, o objeto fuera de rango.
        // Devolver centinela de error (-1.0) para que el filtro DSP y la
        // FSM puedan ignorar esta lectura y no tomar decisiones erróneas.
        Serial.println("[HAL][ERROR] Ultrasonico: sin respuesta (timeout). Verificar cableado TRIG/ECHO.");
        return -1.0f;
    }

    // ── Paso 5: Convertir duración a centímetros ─────────────────────────────
    // El sonido viaja ida y vuelta, por eso se divide entre 2.
    // Velocidad del sonido en aire a ~25°C ≈ 343 m/s = 0.0343 cm/µs
    float distance_cm = (duration * 0.0343f) / 2.0f;

    return distance_cm;
}

// ============================================================================
// TURBIDITY - LECTURA ADC ANALÓGICA
// ============================================================================

/**
 * @brief Lee el valor crudo del ADC del sensor de turbidez.
 *
 * El ESP32 tiene un ADC de 12 bits → valores entre 0 y 4095 (TURBIDITY_ADC_MAX).
 * La conversión a NTU se realiza en taskSensores (main.cpp) para mantener
 * este módulo desacoplado de la lógica de negocio.
 *
 * @return  Valor ADC crudo entre 0 y 4095.
 */
uint16_t readTurbidityRawValue() {
    return (uint16_t)analogRead(PIN_TURBIDITY_SENSOR);
}

// ============================================================================
// FLOW - CAUDAL INSTANTÁNEO Y VOLUMEN TOTAL
// ============================================================================

/**
 * @brief Calcula el caudal en Litros Por Minuto (LPM) en el intervalo dado.
 *
 * El sensor YF-S201 genera pulsos magnéticos al pasar agua.
 * La interrupción flowPulseCounter() (definida en hal_sensors.h) cuenta cada
 * pulso de forma atómica. Esta función:
 *  1. Desactiva interrupciones brevemente para leer y limpiar el contador
 *     de pulsos temporales (currentFlowPulses) de forma segura (thread-safe).
 *  2. Calcula litros = pulsos / FLOW_PULSES_PER_LITER (calibración YF-S201 = 450).
 *  3. Convierte a LPM dividiendo entre el intervalo de tiempo.
 *
 * @param intervalMs  Tiempo en milisegundos desde la última llamada.
 * @return            Caudal en litros por minuto. 0.0 si intervalMs es 0.
 */
float readFlowRateLPM(unsigned long intervalMs) {
    if (intervalMs == 0) return 0.0f;

    // Sección crítica: leer y resetear pulsos de forma atómica
    noInterrupts();
    extern volatile uint16_t currentFlowPulses;
    uint16_t pulses = currentFlowPulses;
    currentFlowPulses = 0;
    interrupts();

    float liters  = (float)pulses / FLOW_PULSES_PER_LITER;
    float minutes = (float)intervalMs / 60000.0f;
    return liters / minutes;
}

/**
 * @brief Devuelve el total acumulado de litros desde el encendido.
 *
 * A diferencia de readFlowRateLPM(), este contador (totalFlowPulses) NUNCA
 * se resetea al leer, lo que permite llevar un historial de consumo total.
 *
 * @return Total de litros consumidos desde el boot del ESP32.
 */
float readFlowTotalLiters() {
    noInterrupts();
    extern volatile uint32_t totalFlowPulses;
    uint32_t total = totalFlowPulses;
    interrupts();
    return (float)total / FLOW_PULSES_PER_LITER;
}
