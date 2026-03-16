#include "storage_fs.h"

#include <LittleFS.h>

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
