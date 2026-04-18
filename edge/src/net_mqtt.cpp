#include "net_mqtt.h"

#include <Arduino.h>
#include <WiFi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <ArduinoJson.h>

#include "config.h"
#include "storage_fs.h"
#include "fsm_logic.h"

namespace {
WiFiClient espClient;
volatile bool wifiConnected = false;
volatile bool mqttConnected = false;

void setupWiFi() {
	Serial.println("[WiFi] Iniciando conexion...");
	WiFi.mode(WIFI_STA);
	WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

	int attempts = 0;
	const int maxAttempts = 20;
	while ((WiFi.status() != WL_CONNECTED) && (attempts < maxAttempts)) {
		vTaskDelay(pdMS_TO_TICKS(500));
		Serial.print(".");
		attempts++;
	}

	wifiConnected = (WiFi.status() == WL_CONNECTED);
	if (wifiConnected) {
		Serial.println("\n[WiFi] Conectado!");
		Serial.print("[WiFi] IP: ");
		Serial.println(WiFi.localIP());
	} else {
		Serial.println("\n[WiFi] Fallo en conexion");
	}
}

void reconnectMQTT() {
	int attempts = 0;
	const int maxAttempts = 5;

	while (!mqttClient.connected() && (attempts < maxAttempts)) {
		Serial.print("[MQTT] Intentando conectar... ");
		if (mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
			Serial.println("Conectado!");
			mqttConnected = true;
			mqttClient.subscribe(MQTT_TOPIC_COMMANDS);
			return;
		}

		Serial.print("Codigo de error: ");
		Serial.println(mqttClient.state());
		vTaskDelay(pdMS_TO_TICKS(2000));
		attempts++;
	}

	mqttConnected = false;
	if (attempts >= maxAttempts) {
		Serial.println("[MQTT] No se pudo conectar despues de intentos");
	}
}
} // namespace

PubSubClient mqttClient(espClient);

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
	String message;
	for (unsigned int i = 0; i < length; i++) {
		message += (char)payload[i];
	}

	StaticJsonDocument<256> doc;
	DeserializationError error = deserializeJson(doc, message);

	if (error) {
		Serial.print("[MQTT] Error parseando JSON de comando: ");
		Serial.println(error.c_str());
		return;
	}

	if (!doc.containsKey("command")) return;

	String command = doc["command"].as<String>();
	String status = "executed";

	if (command == "FORCE_HARVEST") {
		forceHarvestMode = true;
		forceIdleMode = false;
	} 
	else if (command == "FORCE_IDLE") {
		forceIdleMode = true;
		forceHarvestMode = false;
	} 
	else if (command == "AUTO_MODE") {
		forceHarvestMode = false;
		forceIdleMode = false;
	} 
	else if (command == "RESET_ERRORS") {
		resetFsmErrors();
	} 
	else if (command == "REBOOT") {
		Serial.println("[MQTT] Reiniciando ESP32 vía Comando...");
		delay(2000);
		ESP.restart();
	} 
	else {
		status = "unknown_command";
	}

	if (status == "executed") {
		StaticJsonDocument<128> ackDoc;
		ackDoc["ack"] = command;
		ackDoc["status"] = status;

		char ackBuffer[128];
		serializeJson(ackDoc, ackBuffer);

		String ackTopic = String(MQTT_TOPIC_TELEMETRY) + "/ack";
		mqttClient.publish(ackTopic.c_str(), ackBuffer);
	}
}

void initNetwork() {
	setupWiFi();

	mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
	mqttClient.setCallback(onMqttMessage);
	mqttClient.setBufferSize(512);

	if (wifiConnected) {
		reconnectMQTT();
	}
}

void maintainNetwork() {
	wifiConnected = (WiFi.status() == WL_CONNECTED);
	if (!wifiConnected) {
		mqttConnected = false;
		setupWiFi();
	}

	if (wifiConnected && !mqttClient.connected()) {
		reconnectMQTT();
	}

	if (mqttClient.connected()) {
		mqttClient.loop();
		mqttConnected = true;
	} else {
		mqttConnected = false;
	}

	if (wifiConnected && mqttConnected) {
		syncOfflineBuffer();
	}
}

bool isNetworkConnected() {
	return wifiConnected && mqttConnected;
}
