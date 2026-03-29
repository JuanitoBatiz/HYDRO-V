#include "telemetry.h"

#include <ArduinoJson.h>

#include "config.h"
#include "net_mqtt.h"
#include "fsm_logic.h"
#include "storage_fs.h"

void publishTelemetryData(SensorData_t currentSensors) {
	StaticJsonDocument<512> doc;

	doc["device_id"] = MQTT_CLIENT_ID;
	doc["timestamp"] = currentSensors.timestamp;

	JsonObject sensors = doc.createNestedObject("sensors");
	sensors["turbidity_ntu"] = serialized(String(currentSensors.turbidity_ntu, 1));
	sensors["distance_cm"] = serialized(String(currentSensors.distance_cm, 1));
	sensors["flow_lpm"] = serialized(String(currentSensors.flow_lpm, 2));
	sensors["flow_total_liters"] = serialized(String(currentSensors.flow_total, 2));

	FSMContext_t fsmState = getFSMContext();
	JsonObject systemState = doc.createNestedObject("system_state");
	systemState["state"] = getStateNameString();
	systemState["state_duration_ms"] = fsmState.state_duration;
	systemState["intake_cycles"] = fsmState.intake_cycles;
	systemState["reject_cycles"] = fsmState.reject_cycles;
	systemState["error_count"] = fsmState.error_count;

	char jsonBuffer[512];
	serializeJson(doc, jsonBuffer, sizeof(jsonBuffer));

	if (isNetworkConnected()) {
		bool published = mqttClient.publish(MQTT_TOPIC_TELEMETRY, jsonBuffer);
		if (published) {
			Serial.printf("[Telemetry] Publicado (%d bytes)\n", strlen(jsonBuffer));
		} else {
			Serial.println("[Telemetry] Error al publicar, guardando offline");
			if (!saveTelemetryOffline(String(jsonBuffer))) {
				Serial.println("[Telemetry] Error guardando offline");
			}
		}
	} else {
		if (!saveTelemetryOffline(String(jsonBuffer))) {
			Serial.println("[Telemetry] Error guardando offline");
		} else {
			Serial.println("[Telemetry] Sin red, guardado offline");
		}
	}
}
