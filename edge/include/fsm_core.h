#ifndef FSM_CORE_H
#define FSM_CORE_H

/**
 * @file  fsm_core.h
 * @brief Interfaz pública del módulo FSM Core (ciclo de vida del nodo).
 *
 * Expone las dos funciones que deben llamarse desde main.cpp o desde
 * una tarea FreeRTOS dedicada al ciclo principal del sistema.
 */

/**
 * @brief Ejecuta una iteración del ciclo de vida completo:
 *        WAKE_UP → SENSE_WATER → BUILD_REPORT → SLEEP → (repite)
 *
 * Llamar en un loop() o dentro de una tarea FreeRTOS con delay propio.
 */
void runCoreFSMCycle();

/**
 * @brief Devuelve el nombre del estado actual del Core FSM como string.
 *
 * Útil para telemetría de diagnóstico y logs en Serial Monitor.
 *
 * @return "WAKE_UP" | "SENSE_WATER" | "BUILD_REPORT" | "SLEEP" | "UNKNOWN"
 */
const char* getCoreStateName();

#endif // FSM_CORE_H
