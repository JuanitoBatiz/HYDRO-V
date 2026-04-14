#ifndef STORAGE_FS_H
#define STORAGE_FS_H

#include <Arduino.h>

bool initFS();
bool saveTelemetryOffline(String jsonData);
String getOfflineTelemetry();
bool clearOfflineTelemetry();
void syncOfflineBuffer();

#endif // STORAGE_FS_H
