#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <Arduino.h>

typedef struct {
	float turbidity_ntu;
	float distance_cm;
	float flow_lpm;
	float flow_total;
	uint32_t timestamp;
} SensorData_t;

void publishTelemetryData(SensorData_t currentSensors);

#endif // TELEMETRY_H
