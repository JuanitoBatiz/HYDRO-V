#include "storage_fs.h"

#include <LittleFS.h>
#include "net_mqtt.h"
#include "config.h"

namespace {
const char* kOfflineFilePath = "/offline_data.txt";
}

bool initFS() {
	return LittleFS.begin(true);
}

bool saveTelemetryOffline(String jsonData) {
	File file = LittleFS.open(kOfflineFilePath, FILE_APPEND);
	if (!file) {
		return false;
	}

	const bool writeOk = file.println(jsonData) > 0;
	file.close();
	return writeOk;
}

String getOfflineTelemetry() {
	File file = LittleFS.open(kOfflineFilePath, FILE_READ);
	if (!file) {
		return String("");
	}

	String data = file.readString();
	file.close();
	return data;
}

bool clearOfflineTelemetry() {
	return LittleFS.remove(kOfflineFilePath);
}

void syncOfflineBuffer() {
	if (!LittleFS.exists(kOfflineFilePath)) {
		return;
	}

	File file = LittleFS.open(kOfflineFilePath, FILE_READ);
	if (!file) {
		return;
	}
	if (file.size() == 0) {
		file.close();
		clearOfflineTelemetry();
		return;
	}

	int linesSent = 0;
	int linesSkipped = 0;
	const int maxBatchLines = 20;
	String offlineTopic = String(MQTT_TOPIC_TELEMETRY) + "/offline";

	File tempFile = LittleFS.open("/temp_offline.txt", FILE_WRITE);
	if (!tempFile) {
		file.close();
		return; 
	}

	while (file.available()) {
		String line = file.readStringUntil('\n');
		line.trim();
		if (line.length() == 0) continue;

		if (linesSent < maxBatchLines && linesSkipped == 0) {
			bool published = mqttClient.publish(offlineTopic.c_str(), line.c_str());
			if (published) {
				linesSent++;
			} else {
				linesSkipped++;
				tempFile.println(line); 
			}
		} else {
			tempFile.println(line); // Líneas restantes o después del fallo
		}
		yield(); // Prevent WDT crash for large files
	}

	file.close();
	tempFile.close();

	// Rotar archivo
	LittleFS.remove(kOfflineFilePath);
	LittleFS.rename("/temp_offline.txt", kOfflineFilePath);

	if (linesSent > 0 && linesSkipped == 0) {
		Serial.printf("[SYNC] Reenviados %d registros offline\n", linesSent);
		
		// Verificar si quedó vacío para llamar su función estricta
		File finalCheck = LittleFS.open(kOfflineFilePath, FILE_READ);
		if (finalCheck) {
			if (finalCheck.size() == 0) {
				finalCheck.close();
				clearOfflineTelemetry();
			} else {
				finalCheck.close();
			}
		}
	} else if (linesSent > 0) {
		Serial.printf("[SYNC] Lote parcial: Reenviados %d registros offline\n", linesSent);
	}
}
