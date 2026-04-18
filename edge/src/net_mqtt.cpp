#include "net_mqtt.h"

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <ArduinoJson.h>
#include <time.h>

#include "config.h"
#include "storage_fs.h"
#include "fsm_logic.h"

namespace {
WiFiClientSecure espClient;
volatile bool wifiConnected = false;
volatile bool mqttConnected = false;
volatile bool timeSynced = false;
bool ntpConfigured = false;
bool sslReady = false;
bool tlsInsecureMode = false;
bool mqttConnectInProgress = false;

const char *root_ca = R"EOF(
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
)EOF";


bool hasValidTime() {
	time_t now = time(nullptr);
	return now > 1000000000;
}

void applyTlsPolicyForCurrentTime() {
	time_t now = time(nullptr);

	if (now < 1000000000) {
		if (!tlsInsecureMode) {
			espClient.setInsecure();
			tlsInsecureMode = true;
			sslReady = false;
			Serial.println("[SSL][WARN] Hora invalida: usando modo inseguro temporal");
		}
		return;
	}

	if (!sslReady || tlsInsecureMode) {
		espClient.setCACert(root_ca);
		sslReady = true;
		tlsInsecureMode = false;
		Serial.println("[SSL] Root CA cargado correctamente");
	}
}

void configureNtp() {
	if (ntpConfigured) {
		return;
	}

	configTime(NTP_TIME_OFFSET_SECONDS, 0,
	           NTP_SERVER_PRIMARY,
	           NTP_SERVER_SECONDARY,
	           NTP_SERVER_TERTIARY);
	ntpConfigured = true;
	Serial.println("[NTP] SNTP configurado con pool.ntp.org, time.google.com y time.windows.com");
}

bool refreshTimeSyncState() {
	if (hasValidTime()) {
		if (!timeSynced) {
			struct tm timeinfo;
			if (getLocalTime(&timeinfo, 1000)) {
				Serial.printf("[NTP] OK -> %04d-%02d-%02d %02d:%02d:%02d\n",
				              timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
				              timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
			}
		}
		timeSynced = true;
		return true;
	}

	return false;
}

} // namespace

bool waitForValidTime(uint32_t timeoutMs) {
	configureNtp();

	unsigned long start = millis();
	while ((millis() - start) < timeoutMs) {
		if (refreshTimeSyncState()) {
			return true;
		}
		vTaskDelay(pdMS_TO_TICKS(500));
	}

	refreshTimeSyncState();
	if (!timeSynced) {
		Serial.println("[NTP][ERROR] Timeout de sincronizacion: continuando sin hora valida");
	}

	return timeSynced;
}

bool isTimeSynced() {
	return timeSynced;
}

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
    if (mqttClient.connected()) {
        mqttConnected = true;
        return;
    }

    if (mqttConnectInProgress) {
        Serial.println("[MQTT] Conexion en progreso, evitando intento duplicado");
        return;
    }

	mqttConnectInProgress = true;
	refreshTimeSyncState();
	applyTlsPolicyForCurrentTime();

	int attempts = 0;
	const int maxAttempts = 5;

	while (!mqttClient.connected() && (attempts < maxAttempts)) {
		if (espClient.connected()) {
			Serial.println("[MQTT] Socket previo detectado, cerrando antes de reconectar");
			espClient.stop();
		}

		Serial.print("[MQTT] Intentando conectar... ");
		if (mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
			Serial.println("Conectado!");
			Serial.println("[MQTT] MQTT OK");
			mqttConnected = true;
			mqttClient.subscribe(MQTT_TOPIC_COMMANDS);
			syncOfflineBuffer();
			Serial.println("[MQTT] Buffer offline sincronizado tras conexion");
			mqttConnectInProgress = false;
			return;
		}

		Serial.print("Codigo de error: ");
		Serial.println(mqttClient.state());
		mqttClient.disconnect();
		espClient.stop();
		vTaskDelay(pdMS_TO_TICKS(2000));
		attempts++;
	}

	mqttConnected = false;
	mqttConnectInProgress = false;
	if (attempts >= maxAttempts) {
		Serial.println("[MQTT] No se pudo conectar despues de intentos");
	}
}

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
	configureNtp();
	refreshTimeSyncState();
	applyTlsPolicyForCurrentTime();

	mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
	mqttClient.setCallback(onMqttMessage);
	mqttClient.setBufferSize(512);

	Serial.println("[MQTT] Cliente y callbacks configurados");
}

void maintainNetwork() {
	refreshTimeSyncState();
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
