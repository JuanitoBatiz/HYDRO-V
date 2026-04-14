#ifndef FSM_LOGIC_H
#define FSM_LOGIC_H

#include <Arduino.h>

// Los estados posibles de nuestra planta de agua
enum SystemState {
    SYSTEM_IDLE,
    WATER_INTAKE,
    WATER_REJECT,
    SYSTEM_ERROR
};

// ¡La estructura versión NASA! Con telemetría para Grafana
struct FSMContext_t {
    SystemState currentState;
    uint32_t state_duration; // Milisegundos que lleva en el estado actual
    uint32_t intake_cycles;  // Contador de veces que ha entrado agua
    uint32_t reject_cycles;  // Contador de veces que ha rechazado agua
    uint32_t error_count;    // Contador de errores
};

void initFSM();
void updateSystemState(float turbidity, float distanceCm);
FSMContext_t getFSMContext();
void resetFsmErrors();

extern bool forceHarvestMode;
extern bool forceIdleMode;

// Dos versiones para evitar que el main se confunda
const char* getStateNameString(SystemState state);
const char* getStateNameString(); // Devuelve el estado actual automáticamente

#endif // FSM_LOGIC_H