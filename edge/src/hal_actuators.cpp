#include "hal_actuators.h"

// Variables privadas de estado para reflejar el estado fisico de las valvulas.
static volatile bool valveRejectOpen = false;
static volatile bool valveIntakeOpen = false;
static volatile uint32_t lastStateChange = 0;

void initActuators() {
	pinMode(PIN_VALVE_REJECT, OUTPUT);
	pinMode(PIN_VALVE_INTAKE, OUTPUT);
	stopAllValves();
}

void openValveReject() {
	digitalWrite(PIN_VALVE_REJECT, HIGH);
	valveRejectOpen = true;
	lastStateChange = millis();
}

void closeValveReject() {
	digitalWrite(PIN_VALVE_REJECT, LOW);
	valveRejectOpen = false;
	lastStateChange = millis();
}

bool isValveRejectOpen() {
	return valveRejectOpen;
}

void openValveIntake() {
	digitalWrite(PIN_VALVE_INTAKE, HIGH);
	valveIntakeOpen = true;
	lastStateChange = millis();
}

void closeValveIntake() {
	digitalWrite(PIN_VALVE_INTAKE, LOW);
	valveIntakeOpen = false;
	lastStateChange = millis();
}

bool isValveIntakeOpen() {
	return valveIntakeOpen;
}

void stopAllValves() {
	digitalWrite(PIN_VALVE_REJECT, LOW);
	digitalWrite(PIN_VALVE_INTAKE, LOW);
	valveRejectOpen = false;
	valveIntakeOpen = false;
	lastStateChange = millis();
}

ActuatorState_t getActuatorState() {
	ActuatorState_t state;
	state.valve_reject_open = valveRejectOpen;
	state.valve_intake_open = valveIntakeOpen;
	state.last_state_change = lastStateChange;
	return state;
}
