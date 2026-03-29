#include "net_mqtt.h"

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "config.h"

namespace {
WiFiClientSecure espClient;
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

void initNetwork() {
	setupWiFi();

	if (MQTT_USE_TLS) {
		espClient.setInsecure();
	}
	mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
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
}

bool isNetworkConnected() {
	return wifiConnected && mqttConnected;
}
