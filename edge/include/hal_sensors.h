/**
 * @file    hal_sensors.h
 * @brief   HAL Sensors — Declaraciones públicas (SOLO firmas, sin implementación)
 * @project Hydro-V | Nodo HYDRO-V-NEZA-001
 *
 * REGLA DE ORO C++:
 *   Los archivos .h DECLARAN (qué existe).
 *   Los archivos .cpp DEFINEN (cómo funciona).
 *
 * Si defines variables o implementas funciones en un .h y ese .h
 * es incluido en más de una unidad de compilación (.cpp), el linker
 * verá múltiples definiciones del mismo símbolo → error "multiple definition".
 */

#ifndef HAL_SENSORS_H
#define HAL_SENSORS_H

#include <Arduino.h>
#include "config.h"

// ============================================
// FLOW SENSOR - VARIABLES GLOBALES (ISR-safe)
// ============================================
// "extern" le dice al compilador: "esta variable existe, pero está
// definida en hal_sensors.cpp — no la crees de nuevo aquí".
extern volatile uint16_t currentFlowPulses;
extern volatile uint32_t totalFlowPulses;

// ============================================
// FUNCTION PROTOTYPES
// ============================================

/** ISR: Cuenta cada pulso del sensor de flujo YF-S201. Debe ser IRAM_ATTR. */
void IRAM_ATTR flowPulseCounter();

/** Inicializa pines y adjunta la interrupción del sensor de flujo. */
void initSensors();

/**
 * @brief Dispara el HC-SR04 y devuelve la distancia en centímetros.
 * @return Distancia en cm (float ≥ 0.0) o -1.0 si hay timeout/error.
 */
float readUltrasonicDistance();

/**
 * @brief Lee el ADC del sensor de turbidez (0–4095).
 * @return Valor crudo del ADC de 12 bits.
 */
uint16_t readTurbidityRaw();

/**
 * @brief Calcula el caudal instantáneo en Litros Por Minuto.
 * @param intervalMs Milisegundos transcurridos desde la última llamada.
 * @return Caudal en LPM. 0.0 si intervalMs es 0.
 */
float readFlowRate(unsigned long intervalMs);

/**
 * @brief Devuelve el volumen total acumulado desde el encendido.
 * @return Litros totales (nunca se resetea al leer).
 */
float getFlowTotalLiters();

/** Resetea ambos contadores de pulsos (currentFlowPulses y totalFlowPulses). */
void resetFlowCounter();

#endif // HAL_SENSORS_H