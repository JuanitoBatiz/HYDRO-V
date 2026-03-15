#include "fsm_logic.h"
#include "hal_actuators.h" 
#include "config.h"

// AQUÍ ESTÁ LA VARIABLE QUE FALTABA (La memoria de nuestro FSM)
static FSMContext_t fsm;
static uint32_t stateStartTime = 0; // Para calcular la duración

void initFSM() {
    fsm.currentState = SYSTEM_IDLE;
    fsm.state_duration = 0;
    fsm.intake_cycles = 0;
    fsm.reject_cycles = 0;
    fsm.error_count = 0;
    stateStartTime = millis();
    stopAllValves(); 
}

void updateSystemState(float turbidity, float distanceCm) {
    SystemState nextState = fsm.currentState;

    // 1. Evaluar sensores para decidir el siguiente paso
    if (turbidity > 500.0) { 
        nextState = WATER_REJECT;
    } 
    else if (distanceCm > 100.0) { 
        nextState = WATER_INTAKE;
    } 
    else {
        nextState = SYSTEM_IDLE;
    }

    // 2. Si hay un CAMBIO de estado, hacemos la transición
    if (nextState != fsm.currentState) {
        // Aumentar contadores de telemetría para Grafana
        if (nextState == WATER_INTAKE) fsm.intake_cycles++;
        if (nextState == WATER_REJECT) fsm.reject_cycles++;
        if (nextState == SYSTEM_ERROR) fsm.error_count++;
        
        fsm.currentState = nextState;
        stateStartTime = millis(); // Reiniciar el cronómetro del estado

        // Mover los relés de las válvulas físicamente
        if (nextState == WATER_REJECT) {
            closeValveIntake();
            openValveReject();
        } 
        else if (nextState == WATER_INTAKE) {
            openValveIntake();
            closeValveReject();
        } 
        else {
            stopAllValves();
        }
    }

    // 3. Actualizar la duración en tiempo real
    fsm.state_duration = millis() - stateStartTime;
}

FSMContext_t getFSMContext() {
    return fsm;
}

const char* getStateNameString(SystemState state) {
    switch(state) {
        case SYSTEM_IDLE: return "IDLE";
        case WATER_INTAKE: return "INTAKE";
        case WATER_REJECT: return "REJECT";
        case SYSTEM_ERROR: return "ERROR";
        default: return "UNKNOWN";
    }
}

// Solución al error de "too few arguments"
const char* getStateNameString() {
    return getStateNameString(fsm.currentState);
}