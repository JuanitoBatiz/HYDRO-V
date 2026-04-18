#ifndef NET_MQTT_H
#define NET_MQTT_H

#include <PubSubClient.h>

extern PubSubClient mqttClient;

bool waitForValidTime(uint32_t timeoutMs = 20000);
bool isTimeSynced();
void initNetwork();
void maintainNetwork();
bool isNetworkConnected();

#endif // NET_MQTT_H
