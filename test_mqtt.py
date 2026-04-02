import asyncio
import json
import aiomqtt
import time

MQTT_HOST = "56e39f9776c14953958f63d9c18ae8ef.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "hydrov_esp32_01"
MQTT_PASSWORD = "Emmamiamor1"

payload = {
    "device_id": "HYDRO-V-001",
    "timestamp": int(time.time() * 1000),
    "sensors": {
        "turbidity_ntu": 5.2,
        "distance_cm": 45.0,
        "flow_lpm": 12.5,
        "flow_total_liters": 1500.0
    },
    "system_state": {
        "state": "EMERGENCY",
        "state_duration_ms": 12000,
        "intake_cycles": 42,
        "reject_cycles": 3,
        "error_count": 1
    }
}

async def main():
    print("Conectando a HiveMQ...")
    async with aiomqtt.Client(
        hostname=MQTT_HOST,
        port=MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASSWORD,
        tls_params=aiomqtt.TLSParameters()
    ) as client:
        topic = "hydrov/HYDRO-V-001/telemetry"
        print(f"Enviando payload a {topic}...")
        await client.publish(topic, payload=json.dumps(payload), qos=1)
        print("¡Mensaje de telemetría inyectado!")

if __name__ == "__main__":
    asyncio.run(main())
