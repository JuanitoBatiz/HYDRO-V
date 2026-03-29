#ifndef NET_MQTT_H
#define NET_MQTT_H

#include <PubSubClient.h>

extern PubSubClient mqttClient;

void initNetwork();
void maintainNetwork();
bool isNetworkConnected();

#endif // NET_MQTT_H
